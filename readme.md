
# QGIS → DJI WPML (KMZ) Converter

A Streamlit web application that enables seamless waypoint planning workflow from **QGIS** to **DJI Pilot 2**. Export professional drone missions by converting GeoJSON waypoints into DJI-compatible **KMZ** files using the **WPML Waypoint 3.x** format.

> **✈️ Optimized for DJI Matrice 3E/3M series and other WPML 3.x compatible aircraft**

---

## 🎯 Problem Solved

Planning complex drone missions in DJI Pilot 2 can be limiting for precision work. This tool bridges the gap by allowing you to:

- Plan detailed waypoint missions in **QGIS** with full GIS capabilities
- Export waypoints as **GeoJSON** from QGIS
- Convert them into **DJI Pilot 2**-ready KMZ files  that can be uploaded to your controller and opened in DJI Pilot 2
- Maintain all DJI mission metadata and flight parameters.

## Intended Use
- I'm really interested in using Drones as "point sampling tool". Using low altitude NADIR drone photos to collect images from pastures, crop, etc.
- What I want to be able to do is create zones or polygons in a field, and then use QGIS to create random points within each polygon that i can "sample" with the drone.
- Now I can do all that work in QGIS, save the points as a geojson, and easily convert to a waypoint mission for my Mavic 3M.

---

## 🔧 How It Works

DJI route files (KMZ) contain two critical components:
- `wpmz/waylines.wpml` → **Executable flight path** (what the aircraft flies)
- `wpmz/template.kml` → **Planning visualization** (what Pilot 2 displays)

This application intelligently updates **both files** ensuring:
- ✅ Pilot 2 doesn't revert to original seed waypoints
- ✅ Mission parameters are preserved from your seed file
- ✅ Flight paths match your QGIS planning exactly

---

## 🚀 Features

### Core Functionality
- **Seed KMZ Upload** - Use any DJI Pilot 2 exported mission as a template (or use the one provided in this project (seed.kmz))
- **GeoJSON Import** - Point features in WGS84 (EPSG:4326) coordinate system
- **Dual File Updates** - Modifies both waylines.wpml and template.kml
- **Altitude Management** - Override or preserve individual waypoint altitudes

### Technical Capabilities
- **Coordinate Precision** - Maintains 7 decimal place accuracy for coordinates
- **Index Management** - Proper waypoint indexing (0-based for waylines, 1-based for template)
- **Namespace Preservation** - Keeps original DJI WPML namespaces intact
- **Metadata Retention** - Preserves flight parameters, speeds, and actions from seed
- **File Integrity** - Maintains all KMZ assets (icons, styles, manifests)

### User Experience
- **Web-Based Interface** - No software installation required
- **Real-Time Processing** - Instant feedback and error handling
- **Download Ready** - One-click KMZ download for immediate use

---

## 📋 Requirements

### Seed KMZ Requirements
- Export from **DJI Pilot 2** on the same controller/firmware you'll use for flight
- Must contain at least 2 waypoints
- Should include your desired flight parameters (speed, altitude, actions)

### GeoJSON Requirements
- **Point features only** (LineString/Polygon not supported)
- **WGS84 coordinate system** (EPSG:4326)
- **Minimum 2 points** required
- Optional `alt_m` property in feature properties for individual altitudes

---

## 🎯 Quick Start

### 1. Launch the Application
Access the Streamlit app by clicking the **Run** button above.

### 2. Prepare Your Files
**Create a seed KMZ:**
1. Open DJI Pilot 2
2. Create a simple 2-point mission with your desired flight parameters
3. Export as KMZ file

**Export from QGIS:**
1. Create Point features for your waypoints
2. Ensure CRS is set to WGS84 (EPSG:4326)
3. Export layer as GeoJSON
4. (Optional) Add `alt_m` field with altitude values in meters

### 3. Convert Mission
1. Upload your seed KMZ file
2. Upload your GeoJSON waypoints
3. Configure altitude settings
4. Click "Build KMZ"
5. Download your mission-ready file

---

## 📁 Example GeoJSON Structure

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.4194, 37.7749]
      },
      "properties": {
        "alt_m": 50.0,
        "name": "Waypoint 1"
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.4094, 37.7849]
      },
      "properties": {
        "alt_m": 45.0,
        "name": "Waypoint 2"
      }
    }
  ]
}
```

---

## 🔧 Technical Details

### Supported File Formats
- **Input**: KMZ (seed), GeoJSON/JSON (waypoints)
- **Output**: KMZ (DJI Pilot 2 compatible)

### Coordinate Handling
- **Template.kml**: 3D coordinates (`lon,lat,alt`)
- **Waylines.wpml**: 2D coordinates (`lon,lat`) + separate `<wpml:executeHeight>`
- **LineString**: Updated for flight path visualization

### WPML Compatibility
- **WPML 3.x** format support
- **Namespace preservation** from seed files
- **Metadata retention** for all flight parameters

---

## 📝 Best Practices

### For Optimal Results
1. **Create seed missions** on the same controller you'll use for flight
2. **Test with simple missions** first (2-3 waypoints)
3. **Verify altitude references** match your takeoff location
4. **Check coordinate precision** in QGIS (should be WGS84)
5. **Validate in DJI Pilot 2** before flight

### Troubleshooting
- **"Invalid WPML namespace"**: Ensure seed KMZ is from DJI Pilot 2
- **"No Point features found"**: Check GeoJSON contains Point geometry types
- **"Altitude issues"**: Verify altitude units are in meters above takeoff

---

## 🤝 Contributing

This tool supports the open WPML standard promoted by DJI. Feedback and improvements are welcome to enhance drone automation workflows.

---

## ⚠️ Disclaimer

- Always validate generated missions in DJI Pilot 2 before flight
- Test missions in safe environments first
- Ensure compliance with local aviation regulations
- Verify altitude references match your operational requirements

---

**Built with Streamlit • Optimized for DJI WPML 3.x • QGIS Integration Ready**
