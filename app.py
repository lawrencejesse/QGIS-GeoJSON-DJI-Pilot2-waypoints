import streamlit as st
import zipfile
import io
import json
import xml.etree.ElementTree as ET
import copy

# KML namespace for XML parsing
KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}
# WPML may also use the wpml namespace
WPML_NS = {"wpml": "http://www.dji.com/wpml/1.0.2"}
ET.register_namespace("", KML_NS["kml"])
ET.register_namespace("wpml", WPML_NS["wpml"])

def points_from_geojson(file, altitude_override=None):
    """
    Extract point coordinates from a GeoJSON file.
    
    Args:
        file: Uploaded GeoJSON file object
        altitude_override: Optional altitude to use for all points (meters)
        
    Returns:
        list: List of tuples containing (longitude, latitude, altitude)
    """
    gj = json.load(file)
    pts = []
    
    for f in gj["features"]:
        if f["geometry"]["type"].lower() == "point":
            lon, lat = f["geometry"]["coordinates"][:2]
            
            if altitude_override is not None:
                alt = float(altitude_override)
            else:
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
    if pt is None:
        raise ValueError("No Point element found in placemark")
    
    coords = pt.find("kml:coordinates", KML_NS)
    if coords is None:
        raise ValueError("No coordinates element found in Point")
    
    # Format coordinates with 7 decimal places for precision
    old_coords = coords.text
    new_coords = f"{lon:.7f},{lat:.7f},{alt:.2f}"
    coords.text = new_coords
    
    return old_coords, new_coords

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
    # Altitude override section
    st.subheader("Altitude Settings")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        use_override = st.checkbox(
            "Override altitude for all waypoints",
            help="Check this to set the same altitude for all waypoints, ignoring any altitude data in the GeoJSON file"
        )
    
    with col2:
        if use_override:
            altitude_override = st.number_input(
                "Altitude (meters)",
                min_value=0.0,
                max_value=500.0,
                value=7.0,
                step=1.0,
                format="%.1f",
                help="Set the altitude in meters for all waypoints"
            )
        else:
            altitude_override = None
    st.subheader("Process Files")
    
    if st.button("Build KMZ", type="primary"):
        zin = None
        try:
            # Process the uploaded files
            with st.spinner("Processing files..."):
                # Open the seed KMZ file
                zin = zipfile.ZipFile(seed)
                
                # Find the waylines.wpml and template.kml files
                wpml_files = [n for n in zin.namelist() if n.lower().endswith("waylines.wpml")]
                kml_files = [n for n in zin.namelist() if n.lower().endswith("template.kml")]
                
                wpml_name = None
                kml_name = None
                
                if not wpml_files:
                    st.error("❌ No waylines.wpml found in seed KMZ file. Please ensure you uploaded a valid DJI Pilot 2 KMZ export.")
                else:
                    wpml_name = wpml_files[0]
                    st.success(f"✅ Found waylines file: {wpml_name}")
                    
                    if kml_files:
                        kml_name = kml_files[0]
                        st.info(f"📍 Also found template file: {kml_name}")
                    
                    # Parse the XML content
                    wpml_content = zin.read(wpml_name)
                    root = ET.fromstring(wpml_content)
                    
                    # Debug: Show original file size
                    st.info(f"📍 Original WPML file size: {len(wpml_content)} bytes")
                    
                    # Find all placemarks with points
                    placemarks = root.findall(".//kml:Placemark[kml:Point]", KML_NS)
                    st.info(f"📍 Found {len(placemarks)} placemarks in original WPML")
                    
                    # Reset file pointer and extract points from GeoJSON
                    pts_file.seek(0)
                    points = points_from_geojson(pts_file, altitude_override)
                    
                    if len(points) < 2:
                        st.error("❌ Need at least 2 points in the GeoJSON file to create a valid waypoint mission.")
                    else:
                        st.info(f"📍 Processing {len(points)} waypoints")
                        
                        st.info(f"📍 Found {len(placemarks)} existing placemarks, need {len(points)} waypoints")
                        
                        # Get the document element - it might be the root itself or a child
                        document = root.find(".//kml:Document", KML_NS)
                        if document is None:
                            # Check if root itself is Document
                            if root.tag == "{" + KML_NS["kml"] + "}Document":
                                document = root
                                st.info("📍 Root element is Document")
                            else:
                                # Try to find any Document element
                                document = root.find(".//Document", None)
                                if document is None:
                                    st.error("❌ No Document element found in the KML structure")
                                    raise ValueError("Invalid KML structure: missing Document element")
                        
                        # Clear all existing placemarks and create new ones from scratch
                        st.info("📍 Clearing existing placemarks and creating new ones")
                        
                        # Store template before removing
                        template_placemark = placemarks[0] if placemarks else None
                        
                        # Remove all existing placemarks - find their actual parents
                        for pm in placemarks:
                            # Search through all elements to find the parent
                            for elem in root.iter():
                                try:
                                    if pm in elem:
                                        elem.remove(pm)
                                        break
                                except (ValueError, TypeError):
                                    # Element not in this parent, continue searching
                                    continue
                        
                        # Create new placemarks for each point
                        new_placemarks = []
                        
                        for i, (lon, lat, alt) in enumerate(points):
                            # Create new placemark element
                            placemark = ET.SubElement(document, "{" + KML_NS["kml"] + "}Placemark")
                            
                            # Add Point element
                            point = ET.SubElement(placemark, "{" + KML_NS["kml"] + "}Point")
                            
                            # Add coordinates
                            coords = ET.SubElement(point, "{" + KML_NS["kml"] + "}coordinates")
                            coords.text = f"{lon:.7f},{lat:.7f},{alt:.2f}"
                            
                            # If we have a template, copy other elements (like name, style, etc.)
                            if template_placemark is not None:
                                for child in template_placemark:
                                    if not child.tag.endswith("Point"):
                                        placemark.append(copy.deepcopy(child))
                            
                            new_placemarks.append(placemark)
                        
                        placemarks = new_placemarks
                        
                        st.success(f"✅ Created {len(placemarks)} new placemarks with GeoJSON coordinates")
                        
                        # Show the new coordinates
                        with st.expander("View new waypoint coordinates", expanded=False):
                            for i, (lon, lat, alt) in enumerate(points[:5]):
                                st.text(f"Waypoint {i+1}: {lon:.7f},{lat:.7f},{alt:.2f}")
                            if len(points) > 5:
                                st.text(f"... and {len(points) - 5} more waypoints")
                        
                        # Verify the final state
                        final_placemarks = root.findall(".//kml:Placemark[kml:Point]", KML_NS)
                        st.info(f"📍 Final XML contains {len(final_placemarks)} placemarks")
                        
                        # Verify coordinates match what we set
                        with st.expander("Verify final XML state", expanded=False):
                            for i, pm in enumerate(final_placemarks[:5]):
                                pt = pm.find(".//kml:Point", KML_NS)
                                if pt is not None:
                                    coords = pt.find("kml:coordinates", KML_NS)
                                    if coords is not None and coords.text:
                                        expected = points[i] if i < len(points) else None
                                        if expected:
                                            expected_str = f"{expected[0]:.7f},{expected[1]:.7f},{expected[2]:.2f}"
                                            actual = coords.text.strip()
                                            match = "✅" if expected_str == actual else "❌"
                                            st.text(f"Waypoint {i+1}: {actual} {match}")
                        
                        # Process template.kml if it exists
                        template_root = None
                        if kml_name:
                            st.info(f"📍 Processing template.kml for Google Earth/QGIS compatibility")
                            template_content = zin.read(kml_name)
                            template_root = ET.fromstring(template_content)
                            
                            # Find and update placemarks in template.kml
                            template_placemarks = template_root.findall(".//kml:Placemark[kml:Point]", KML_NS)
                            st.info(f"📍 Found {len(template_placemarks)} placemarks in template.kml")
                            
                            # Clear existing placemarks in template
                            for pm in template_placemarks:
                                for elem in template_root.iter():
                                    try:
                                        if pm in elem:
                                            elem.remove(pm)
                                            break
                                    except (ValueError, TypeError):
                                        continue
                            
                            # Find Document element in template
                            template_doc = template_root.find(".//kml:Document", KML_NS)
                            if template_doc is None:
                                if template_root.tag == "{" + KML_NS["kml"] + "}Document":
                                    template_doc = template_root
                                else:
                                    template_doc = template_root.find(".//Document", None)
                            
                            # Add new placemarks to template
                            if template_doc is not None:
                                for i, (lon, lat, alt) in enumerate(points):
                                    placemark = ET.SubElement(template_doc, "{" + KML_NS["kml"] + "}Placemark")
                                    
                                    # Add name
                                    name_elem = ET.SubElement(placemark, "{" + KML_NS["kml"] + "}name")
                                    name_elem.text = f"Waypoint {i+1}"
                                    
                                    # Add Point element
                                    point = ET.SubElement(placemark, "{" + KML_NS["kml"] + "}Point")
                                    
                                    # Add coordinates
                                    coords = ET.SubElement(point, "{" + KML_NS["kml"] + "}coordinates")
                                    coords.text = f"{lon:.7f},{lat:.7f},{alt:.2f}"
                                    
                                    # Copy style from template if available
                                    if template_placemarks and len(template_placemarks) > 0:
                                        for child in template_placemarks[0]:
                                            if child.tag.endswith("Style") or child.tag.endswith("styleUrl"):
                                                placemark.append(copy.deepcopy(child))
                                
                                st.success(f"✅ Updated template.kml with {len(points)} waypoints")
                        
                        # Create output KMZ file
                        buf = io.BytesIO()
                        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
                            for name in zin.namelist():
                                if name == wpml_name:
                                    # Convert the modified waylines.wpml to bytes
                                    modified_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                                    st.info(f"📍 Writing modified waylines.wpml ({len(modified_xml)} bytes)")
                                    zout.writestr(name, modified_xml)
                                elif kml_name and name == kml_name and template_root is not None:
                                    # Write modified template.kml
                                    modified_template = ET.tostring(template_root, encoding="utf-8", xml_declaration=True)
                                    st.info(f"📍 Writing modified template.kml ({len(modified_template)} bytes)")
                                    zout.writestr(name, modified_template)
                                else:
                                    # Copy other files unchanged
                                    zout.writestr(name, zin.read(name))
                        
                        # Ensure buffer is at the beginning for download
                        buf.seek(0)
                        
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
            if zin is not None:
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
