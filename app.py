import streamlit as st
import zipfile
import io
import json
import xml.etree.ElementTree as ET

# KML namespace for XML parsing
KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}
ET.register_namespace("", KML_NS["kml"])

def points_from_geojson(file):
    """
    Extract point coordinates from a GeoJSON file.
    
    Args:
        file: Uploaded GeoJSON file object
        
    Returns:
        list: List of tuples containing (longitude, latitude, altitude)
    """
    gj = json.load(file)
    pts = []
    
    for f in gj["features"]:
        if f["geometry"]["type"].lower() == "point":
            lon, lat = f["geometry"]["coordinates"][:2]
            # Get altitude from properties, default to 30m if not specified
            alt = float(f.get("properties", {}).get("alt_m", 30))
            pts.append((lon, lat, alt))
    
    return pts

def set_coords(pm, lon, lat, alt):
    """
    Update the coordinates of a KML placemark.
    
    Args:
        pm: KML placemark element
        lon: Longitude coordinate
        lat: Latitude coordinate
        alt: Altitude in meters
    """
    pt = pm.find(".//kml:Point", KML_NS)
    coords = pt.find("kml:coordinates", KML_NS)
    # Format coordinates with 7 decimal places for precision
    coords.text = f"{lon:.7f},{lat:.7f},{alt:.2f}"

# Streamlit UI
st.title("QGIS → DJI WPML (KMZ) Mapper")

st.markdown("""
This application converts QGIS geographic point data to DJI drone waypoint mission files.

**Instructions:**
1. Upload a seed KMZ file exported from DJI Pilot 2
2. Upload a GeoJSON file with point features from QGIS (WGS84 coordinate system)
3. Click 'Build KMZ' to generate the waypoint mission file
4. Download the generated KMZ file for use with your DJI drone
""")

# File upload section
st.subheader("File Uploads")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Seed KMZ File**")
    st.caption("Export from DJI Pilot 2 containing waylines.wpml")
    seed = st.file_uploader(
        "Choose seed KMZ file", 
        type=["kmz"],
        help="Upload a KMZ file exported from DJI Pilot 2 that contains the waylines.wpml template"
    )

with col2:
    st.markdown("**Points File**")
    st.caption("GeoJSON with point features in WGS84")
    pts_file = st.file_uploader(
        "Choose points file", 
        type=["geojson", "json"],
        help="Upload a GeoJSON file containing point features with coordinates in WGS84 format"
    )

# Processing section
if seed and pts_file:
    st.subheader("Process Files")
    
    if st.button("Build KMZ", type="primary"):
        try:
            # Process the uploaded files
            with st.spinner("Processing files..."):
                # Open the seed KMZ file
                zin = zipfile.ZipFile(seed)
                
                # Find the waylines.wpml file
                wpml_name = [n for n in zin.namelist() if n.lower().endswith("waylines.wpml")]
                
                if not wpml_name:
                    st.error("❌ No waylines.wpml found in seed KMZ file. Please ensure you uploaded a valid DJI Pilot 2 KMZ export.")
                else:
                    wpml_name = wpml_name[0]
                    st.success(f"✅ Found waylines file: {wpml_name}")
                    
                    # Parse the XML content
                    root = ET.fromstring(zin.read(wpml_name))
                    placemarks = root.findall(".//kml:Placemark[kml:Point]", KML_NS)
                    
                    # Extract points from GeoJSON
                    points = points_from_geojson(pts_file)
                    
                    if len(points) < 2:
                        st.error("❌ Need at least 2 points in the GeoJSON file to create a valid waypoint mission.")
                    else:
                        st.info(f"📍 Processing {len(points)} waypoints")
                        
                        # Resize placemark list to match number of points
                        # Add placemarks if we have more points than existing placemarks
                        while len(placemarks) < len(points):
                            # Clone the last placemark
                            clone = ET.fromstring(ET.tostring(placemarks[-1], encoding="utf-8"))
                            root.find(".//kml:Document", KML_NS).append(clone)
                            placemarks.append(clone)
                        
                        # Remove excess placemarks if we have fewer points
                        for _ in range(len(placemarks) - len(points)):
                            root.find(".//kml:Document", KML_NS).remove(placemarks.pop())
                        
                        # Update coordinates for each placemark
                        for pm, (lon, lat, alt) in zip(placemarks, points):
                            set_coords(pm, lon, lat, alt)
                        
                        # Create output KMZ file
                        buf = io.BytesIO()
                        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
                            for name in zin.namelist():
                                if name == wpml_name:
                                    # Write updated waylines.wpml
                                    zout.writestr(name, ET.tostring(root, encoding="utf-8", xml_declaration=True))
                                else:
                                    # Copy other files unchanged
                                    zout.writestr(name, zin.read(name))
                        
                        st.success("✅ KMZ file generated successfully!")
                        
                        # Provide download button
                        st.download_button(
                            label="📥 Download KMZ Mission File",
                            data=buf.getvalue(),
                            file_name="mission_from_qgis.kmz",
                            mime="application/vnd.google-earth.kmz",
                            help="Download the generated KMZ file and import it into DJI Pilot 2"
                        )
                        
                        # Display summary information
                        st.subheader("Mission Summary")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Waypoints", len(points))
                        
                        with col2:
                            avg_alt = sum(alt for _, _, alt in points) / len(points)
                            st.metric("Avg Altitude", f"{avg_alt:.1f}m")
                        
                        with col3:
                            min_alt = min(alt for _, _, alt in points)
                            max_alt = max(alt for _, _, alt in points)
                            st.metric("Altitude Range", f"{min_alt:.1f}m - {max_alt:.1f}m")
                
        except json.JSONDecodeError:
            st.error("❌ Invalid GeoJSON file. Please check the file format and try again.")
        except ET.ParseError:
            st.error("❌ Invalid XML content in KMZ file. Please ensure you uploaded a valid DJI KMZ file.")
        except Exception as e:
            st.error(f"❌ An error occurred during processing: {str(e)}")
        finally:
            # Clean up file handles
            if 'zin' in locals():
                zin.close()

else:
    st.info("👆 Please upload both files to begin processing")

# Footer with additional information
st.markdown("---")
st.markdown("""
**Note:** This tool requires:
- A seed KMZ file exported from DJI Pilot 2 (containing waylines.wpml)
- A GeoJSON file with point features in WGS84 coordinate system
- Points should include altitude information in the properties as 'alt_m' (defaults to 30m if not specified)
""")
