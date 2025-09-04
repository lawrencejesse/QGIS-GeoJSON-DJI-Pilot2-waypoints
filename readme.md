# QGIS → DJI WPML (KMZ) Converter

A Streamlit web app that lets you plan waypoints in **QGIS** and export a **DJI Pilot 2**-ready **KMZ** (WPML Waypoint 3.x style).  
You provide a tiny **seed KMZ** (exported from Pilot 2) and a **GeoJSON** of points. The app replaces the seed’s waypoints with your GeoJSON points and keeps all the DJI mission metadata intact.

> **Works best when the seed KMZ is created on the same controller/firmware you’ll fly.**

---

## Why a “seed” KMZ?

DJI route files (KMZ) contain:
- `wpmz/waylines.wpml` → the **executable** route (what the aircraft actually flies)
- `wpmz/template.kml` → the **planning** layer (what Pilot 2 may use to re-generate the exec route)

This app updates **both** files so Pilot 2 doesn’t fall back to the original two seed points.

---

## Features

- ✅ Upload **seed KMZ** (from DJI Pilot 2)  
- ✅ Upload **GeoJSON** (Point features in WGS84 / EPSG:4326)  
- ✅ Optional **altitude override** (meters, relative to takeoff)  
- ✅ Updates:
  - `template.kml` with **3D** coordinates: `lon,lat,alt`
  - `waylines.wpml` with **2D** coordinates: `lon,lat` and per-waypoint `<wpml:executeHeight>`
  - Sequential per-waypoint indexes (0,1,2,…) where applicable
- ✅ Preserves all other files in the KMZ (icons, styles, etc.)
- ✅ Keeps DJI WPML namespace/prefix exactly as in the seed

---

## Quick Start

### 1) Install

```bash
# (optional) create a virtual env first
pip install streamlit
