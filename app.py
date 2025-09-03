import streamlit as st
import zipfile
import io
import json
import xml.etree.ElementTree as ET

# KML namespace
KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}
ET.register_namespace("", KML_NS["kml"])

def points_from_geojson(file):
    """Extract points from GeoJSON file."""
    gj = json.load(file)
    pts = []
    for f in gj["features"]:
        if f["geometry"]["type"].lower() == "point":
            lon, lat = f["geometry"]["coordinates"][:2]
            # Get altitude from properties or use default
            alt = float(f.get("properties", {}).get("alt_m", 30))
            pts.append((lon, lat, alt))
    return pts

def set_coords(pm, lon, lat, alt):
    """Update coordinates in a placemark."""
    pt = pm.find(".//kml:Point", KML_NS)
    if pt is not None:
        coords = pt.find("kml:coordinates", KML_NS)
        if coords is not None:
            coords.text = f"{lon:.7f},{lat:.7f},{alt:.2f}"

st.title("QGIS → DJI WPML Converter")
st.write("Convert QGIS waypoints to DJI drone mission format")

# File uploaders
seed = st.file_uploader("Upload seed KMZ from DJI Pilot 2", type=["kmz"])
pts_file = st.file_uploader("Upload waypoints file (GeoJSON/JSON)", type=["geojson", "json"])

# Optional altitude override
col1, col2 = st.columns([3, 1])
with col1:
    override_alt = st.checkbox("Override altitude for all waypoints")
with col2:
    if override_alt:
        alt_value = st.number_input("Altitude (m)", value=30.0, min_value=0.0, max_value=500.0, step=1.0)

if seed and pts_file and st.button("Convert to DJI Format", type="primary"):
    try:
        # Open the seed KMZ
        zin = zipfile.ZipFile(seed)
        
        # Find waylines.wpml file
        wpml_name = None
        for name in zin.namelist():
            if name.lower().endswith("waylines.wpml"):
                wpml_name = name
                break
        
        if not wpml_name:
            st.error("❌ No waylines.wpml found in seed KMZ. Please use a KMZ exported from DJI Pilot 2.")
        else:
            # Parse the WPML file
            root = ET.fromstring(zin.read(wpml_name))
            
            # Find all placemarks with points
            placemarks = root.findall(".//kml:Placemark[kml:Point]", KML_NS)
            
            # Extract points from GeoJSON
            points = points_from_geojson(pts_file)
            
            # Apply altitude override if enabled
            if override_alt:
                points = [(lon, lat, alt_value) for lon, lat, _ in points]
            
            if len(points) < 2:
                st.error("❌ Need at least 2 waypoints in GeoJSON file.")
            else:
                st.info(f"📍 Processing {len(points)} waypoints from GeoJSON")
                st.info(f"📋 Found {len(placemarks)} placemarks in seed KMZ")
                
                # Find Document element
                doc = root.find(".//kml:Document", KML_NS)
                
                if doc is None:
                    st.error("❌ No Document element found in WPML file")
                else:
                    # Adjust number of placemarks to match points
                    if len(placemarks) < len(points):
                        # Need to add more placemarks - clone the last one
                        st.info(f"➕ Adding {len(points) - len(placemarks)} placemarks")
                        while len(placemarks) < len(points):
                            # Clone the last placemark
                            clone = ET.fromstring(ET.tostring(placemarks[-1], encoding="utf-8"))
                            doc.append(clone)
                            placemarks.append(clone)
                    
                    elif len(placemarks) > len(points):
                        # Need to remove extra placemarks
                        st.info(f"➖ Removing {len(placemarks) - len(points)} excess placemarks")
                        for _ in range(len(placemarks) - len(points)):
                            doc.remove(placemarks.pop())
                    
                    # Update coordinates for each placemark
                    st.info("🔄 Updating waypoint coordinates...")
                    for i, (pm, (lon, lat, alt)) in enumerate(zip(placemarks, points)):
                        set_coords(pm, lon, lat, alt)
                        if i < 5:  # Show first 5 for confirmation
                            st.text(f"   Waypoint {i+1}: {lon:.7f}, {lat:.7f}, {alt:.2f}m")
                    
                    if len(points) > 5:
                        st.text(f"   ... and {len(points) - 5} more waypoints")
                    
                    # Create output KMZ
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
                        for name in zin.namelist():
                            if name == wpml_name:
                                # Write the modified WPML
                                zout.writestr(name, ET.tostring(root, encoding="utf-8", xml_declaration=True))
                            else:
                                # Copy all other files as-is
                                zout.writestr(name, zin.read(name))
                    
                    # Success!
                    st.success(f"✅ Successfully converted {len(points)} waypoints to DJI format!")
                    
                    # Download button
                    st.download_button(
                        label="📥 Download Modified KMZ",
                        data=buf.getvalue(),
                        file_name="mission_from_qgis.kmz",
                        mime="application/vnd.google-earth.kmz"
                    )
    
    except json.JSONDecodeError:
        st.error("❌ Invalid JSON/GeoJSON file. Please check the file format.")
    except Exception as e:
        st.error(f"❌ Error processing files: {str(e)}")
        st.exception(e)