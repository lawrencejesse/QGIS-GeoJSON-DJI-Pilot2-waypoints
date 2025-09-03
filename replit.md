# Overview

A Streamlit web application that converts QGIS waypoints to DJI WPML (KMZ) format for drone flight planning. The tool takes a seed KMZ file from DJI Pilot 2 and replaces its waypoints with coordinates from a GeoJSON file, enabling users to plan drone missions using QGIS and export them in DJI's native format.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Streamlit Framework**: Single-page web application with file upload interface
- **User Interface Components**: 
  - File uploaders for seed KMZ and GeoJSON input files
  - Optional altitude override control
  - Processing button to trigger conversion
  - Error handling and status messages

## Backend Architecture
- **Python-based Processing Engine**: Streamlined logic for WPML manipulation
- **Function Design**: 
  - `points_from_geojson()`: Extracts coordinates from GeoJSON features
  - `set_coords()`: Updates placemark coordinates in-place
- **XML Processing**: Direct manipulation of waylines.wpml with namespace preservation
- **Archive Management**: Preserves all original KMZ files, only modifying waylines.wpml

## Data Processing Pipeline
1. **Input Validation**: Checks for waylines.wpml and minimum waypoint count
2. **Coordinate Extraction**: Parses GeoJSON point features with altitude support
3. **Placemark Adjustment**: Clones or removes placemarks to match point count
4. **Coordinate Update**: In-place modification preserving all WPML metadata
5. **Archive Generation**: Outputs KMZ with modified waylines.wpml, preserving all other files

## File Format Support
- **Input Formats**: KMZ (seed files), GeoJSON/JSON (waypoint data)
- **Output Format**: KMZ compatible with DJI flight planning systems
- **Coordinate System**: WGS84 geographic coordinates with altitude support

# External Dependencies

## Core Libraries
- **Streamlit**: Web application framework for user interface
- **Python Standard Library**:
  - `zipfile`: KMZ archive handling
  - `json`: GeoJSON parsing
  - `xml.etree.ElementTree`: KML file manipulation
  - `io`: In-memory file operations

## File Format Standards
- **KML 2.2 Specification**: OpenGIS standard for geographic markup
- **GeoJSON**: RFC 7946 geographic data format
- **DJI WPML**: Proprietary waypoint markup language format