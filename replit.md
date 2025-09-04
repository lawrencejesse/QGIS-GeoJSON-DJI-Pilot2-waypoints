# Overview

This project is a Streamlit web application that converts GeoJSON waypoints from QGIS into DJI Pilot 2-compatible WPML (KMZ) files. It enables precision drone mission planning by allowing users to plan complex waypoint missions in QGIS with full GIS capabilities and export them as flight-ready files for DJI aircraft (optimized for Matrice 3E/3M series and WPML 3.x compatible aircraft).

The application solves the limitation of DJI Pilot 2's mission planning interface by providing a workflow that maintains professional GIS planning capabilities while ensuring compatibility with DJI's flight execution system.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit web application providing a simple, browser-based interface
- **User Interface**: File upload components for seed KMZ files and GeoJSON waypoints
- **Processing Flow**: Sequential workflow from file upload → processing → download of converted KMZ

## Backend Architecture
- **Core Language**: Python with specialized libraries for geospatial and XML processing
- **File Processing**: 
  - ZIP/KMZ handling for DJI mission files
  - XML parsing and manipulation using ElementTree for WPML structure
  - JSON processing for GeoJSON waypoint data
- **Coordinate System**: WGS84 (EPSG:4326) with 7 decimal place precision
- **Dual File Strategy**: Updates both `waylines.wpml` (flight execution) and `template.kml` (visualization) to prevent DJI Pilot 2 from reverting to original waypoints

## Data Processing Pipeline
- **Input Validation**: Detects and validates WPML namespace URIs from seed files
- **Coordinate Transformation**: Extracts longitude, latitude, and altitude from GeoJSON point features
- **Index Management**: Maintains proper waypoint indexing (0-based for waylines, 1-based for template)
- **Namespace Preservation**: Keeps original DJI WPML namespaces intact during XML manipulation

## File Structure Design
- **KMZ Format**: Standard ZIP container with specific DJI structure
- **WPML Compliance**: Adheres to DJI's Waypoint Mission Language specification
- **Template Integration**: Ensures visual planning representation matches flight execution

# External Dependencies

## Core Libraries
- **streamlit**: Web application framework for the user interface
- **xml.etree.ElementTree**: XML parsing and manipulation for WPML/KML processing
- **zipfile**: KMZ file handling (ZIP container format)
- **json**: GeoJSON waypoint data processing

## Standards Compliance
- **KML 2.2**: OpenGIS KML specification (http://www.opengis.net/kml/2.2)
- **DJI WPML**: DJI's Waypoint Mission Language for flight path definition
- **GeoJSON**: RFC 7946 standard for geospatial data exchange

## Coordinate Systems
- **WGS84**: World Geodetic System 1984 (EPSG:4326) for global compatibility
- **Altitude Reference**: Configurable altitude handling with default values

## File Format Dependencies
- **KMZ Input**: DJI Pilot 2 exported mission files as seed templates
- **GeoJSON Input**: Point feature collections from QGIS or other GIS software
- **KMZ Output**: DJI Pilot 2-compatible mission files for flight execution