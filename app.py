import streamlit as st
import zipfile, io, json, xml.etree.ElementTree as ET
import time
from datetime import datetime, timedelta

# --- Constants and Namespace Setup ---
KML_URI = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_URI)

# --- Utility Functions ---

def detect_wpml_uri_and_prefix(root):
    """Finds the WPML namespace URI and registers 'wpml' as its prefix."""
    wpml_uri = None
    for el in root.iter():
        if el.tag.startswith("{") and "wpmz" in el.tag:
            wpml_uri = el.tag.split("}")[0].strip("{")
            break
    if not wpml_uri:
        # Fallback if the root doesn't immediately have the namespace
        for _, val in ET.iterparse(io.StringIO(ET.tostring(root, encoding='unicode')), events=['start-ns']):
            if 'wpmz' in val[1]:
                wpml_uri = val[1]
                break
    if not wpml_uri:
        raise RuntimeError("Could not detect WPML namespace in the seed file.")

    ET.register_namespace("wpml", wpml_uri)
    return wpml_uri

def NS(wpml_uri):
    """Returns the namespace map for searches."""
    return {"kml": KML_URI, "wpml": wpml_uri}

def points_from_geojson(file, default_alt=30.0):
    """Extracts a list of (lon, lat, alt) tuples from a GeoJSON file."""
    gj = json.load(file)
    pts = []
    for f in gj.get("features", []):
        g = f.get("geometry") or {}
        if (g.get("type") or "").lower() == "point":
            lon, lat = g["coordinates"][:2]
            alt = float((f.get("properties") or {}).get("alt_m", default_alt))
            pts.append((lon, lat, alt))
    return pts

def find_route_folder(root, ns):
    """Finds the most likely mission Folder in a KML/WPML document."""
    candidates = root.findall(".//kml:Document/kml:Folder", ns)
    best = (0, None)
    for f in candidates:
        pts = f.findall("kml:Placemark[kml:Point]", ns)
        if pts: # A folder must contain points to be a candidate
            score = len(pts)
            if bool(f.findall(".//wpml:*", ns)):
                score += 100
            if score > best[0]:
                best = (score, f)
    return best[1]

# --- Core Logic for Modifying KML/WPML ---

def update_mission_file(root, points, ns, is_template_kml):
    """
    The core logic for updating a KML/WPML file tree.
    This function modifies the XML root in-place.
    """
    folder = find_route_folder(root, ns)
    if folder is None:
        raise RuntimeError(f"Could not find a valid route Folder in {'template.kml' if is_template_kml else 'waylines.wpml'}.")

    pms = folder.findall("kml:Placemark[kml:Point]", ns)
    if not pms:
        raise RuntimeError(f"The route folder in {'template.kml' if is_template_kml else 'waylines.wpml'} contains no Point placemarks to use as a template.")

    template_pm = pms[-1]

    # Clear existing waypoints
    for pm in pms:
        folder.remove(pm)

    # Add new waypoints based on the template
    for i, (lon, lat, alt) in enumerate(points):
        clone = ET.fromstring(ET.tostring(template_pm, encoding="utf-8"))

        # Set coordinates and altitude
        coords_el = clone.find(".//kml:coordinates", ns)
        if coords_el is not None:
            if is_template_kml:
                coords_el.text = f"{lon:.7f},{lat:.7f},{alt:.2f}"
            else: # waylines.wpml
                coords_el.text = f"{lon:.7f},{lat:.7f}"
                eh_el = clone.find("wpml:executeHeight", ns)
                if eh_el is not None:
                    eh_el.text = f"{alt:.2f}"

        # **CRITICAL FIX**: Re-index for BOTH file types.
        # DJI uses 0-based index in waylines.wpml and 1-based in template.kml
        index_el = clone.find("wpml:index", ns)
        if index_el is not None:
            index_el.text = str(i if not is_template_kml else i + 1)

        folder.append(clone)

    # Update the LineString that visualizes the path
    ls_coords_el = folder.find(".//kml:LineString/kml:coordinates", ns)
    if ls_coords_el is not None:
        if is_template_kml:
            ls_coords_el.text = " ".join(f"{lon:.7f},{lat:.7f},{alt:.2f}" for lon, lat, alt in points)
        else: # waylines.wpml often has no altitude in its linestring
            ls_coords_el.text = " ".join(f"{lon:.7f},{lat:.7f},0" for lon, lat, _ in points)

    # Update waypoint count in waylines.wpml
    if not is_template_kml:
        for el in folder.findall(".//wpml:*", ns):
            local = el.tag.split("}", 1)[-1].lower()
            if "waypoint" in local and ("num" in local or "count" in local):
                el.text = str(len(points))


# --- Streamlit UI ---

st.title("QGIS → DJI WPML (KMZ) — M3E/M3M")
st.write("This tool updates both `template.kml` (geometry) and `waylines.wpml` (flight params) in a seed KMZ.")

seed = st.file_uploader("Seed KMZ (from DJI Pilot 2)", type=["kmz"])
pts_file = st.file_uploader("Waypoints (GeoJSON/JSON)", type=["geojson", "json"])
c1, c2 = st.columns([3,2])
with c1:
    override_alt = st.checkbox("Override altitude for all points", value=True)
with c2:
    alt_value = st.number_input("Altitude (m rel. to takeoff)", 0.0, 1200.0, 30.0, 1.0)

# Simple verification
verification = st.selectbox(
    "✅ Verification: What type of aircraft is this tool designed for?",
    ["", "Fixed-wing aircraft", "DJI drones", "Helicopters", "Hot air balloons"],
    help="Select the correct answer to proceed"
)

# Validate file sizes
max_kmz_size = 10 * 1024 * 1024  # 10MB
max_geojson_size = 5 * 1024 * 1024  # 5MB

if seed and seed.size > max_kmz_size:
    st.error("KMZ file too large. Maximum size is 10MB.")
    st.stop()

if pts_file and pts_file.size > max_geojson_size:
    st.error("GeoJSON file too large. Maximum size is 5MB.")
    st.stop()

if seed and pts_file and verification == "DJI drones" and st.button("Build KMZ", type="primary"):
    # Rate limiting - max 3 conversions per 5 minutes per session
    if 'last_conversions' not in st.session_state:
        st.session_state.last_conversions = []
    
    # Clean old timestamps
    now = datetime.now()
    st.session_state.last_conversions = [
        ts for ts in st.session_state.last_conversions 
        if now - ts < timedelta(minutes=5)
    ]
    
    # Check rate limit
    if len(st.session_state.last_conversions) >= 3:
        st.error("⚠️ Rate limit exceeded. Please wait 5 minutes between conversions.")
        st.stop()
    
    # Add current timestamp
    st.session_state.last_conversions.append(now)
    
    try:
        zin = zipfile.ZipFile(seed, "r")

        file_names = zin.namelist()
        wpml_name = next((n for n in file_names if n.lower().endswith("waylines.wpml")), None)
        template_name = next((n for n in file_names if n.lower().endswith("template.kml")), None)

        if not wpml_name or not template_name:
            st.error("Seed KMZ must contain both 'template.kml' and 'waylines.wpml'.")
            st.stop()

        wpml_root = ET.fromstring(zin.read(wpml_name))
        template_root = ET.fromstring(zin.read(template_name))

        wpml_uri = detect_wpml_uri_and_prefix(wpml_root)
        ns = NS(wpml_uri)

        points = points_from_geojson(pts_file, default_alt=alt_value)
        if len(points) < 2:
            st.error("GeoJSON must contain at least 2 Point features.")
            st.stop()
        if len(points) > 1000:  # DJI missions rarely need more than 1000 waypoints
            st.error("Too many waypoints. Maximum supported is 1000 points.")
            st.stop()
        if override_alt:
            points = [(lon, lat, alt_value) for lon, lat, _ in points]

        # --- UPDATE BOTH FILES ---
        st.info("Updating template.kml (geometry)...")
        update_mission_file(template_root, points, ns, is_template_kml=True)

        st.info("Updating waylines.wpml (flight parameters)...")
        update_mission_file(wpml_root, points, ns, is_template_kml=False)

        # --- REPACK THE KMZ ---
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == template_name:
                    zout.writestr(item, ET.tostring(template_root, encoding="utf-8", xml_declaration=True))
                elif item.filename == wpml_name:
                    zout.writestr(item, ET.tostring(wpml_root, encoding="utf-8", xml_declaration=True))
                else:
                    zout.writestr(item, zin.read(item.filename))

        st.success(f"✅ Success! Rebuilt KMZ with {len(points)} waypoints.")
        st.download_button(
            "📥 Download KMZ",
            data=buf.getvalue(),
            file_name="mission_from_qgis.kmz",
            mime="application/vnd.google-earth.kmz"
        )

    except json.JSONDecodeError:
        st.error("Invalid GeoJSON file.")
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.exception(e)

# --- Footer ---
st.markdown("---")
st.markdown(
    "© Created by Jesse Lawrence / Broken Arrow Consulting ~ Feeling Optimistic on AI and The Future.",
    unsafe_allow_html=True
)
st.markdown(
    "🌐 [jesselawrence.pro](https://jesselawrence.pro)",
    unsafe_allow_html=True
)