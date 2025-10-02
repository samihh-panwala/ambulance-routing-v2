# routing.py - Offline-first routing with cached Surat graph
import os
import osmnx as ox
import networkx as nx
import geopandas as gpd
import streamlit as st
from shapely.geometry import Point

GRAPH_FILE = "surat_graph.gpickle"


# -------------------------------
# 🚦 Load Graph (Offline-first)
# -------------------------------
@st.cache_resource
def load_graph():
    """
    Load the Surat road network graph.
    - Always loads from local gpickle if present.
    - If not present, builds once (needs internet) then caches.
    """
    if os.path.exists(GRAPH_FILE):
        st.success("✅ Loaded Surat graph from local cache")
        return nx.read_gpickle(GRAPH_FILE)

    st.warning("⚠️ Surat graph not found locally. Trying to build from OSM (needs internet)...")
    try:
        # Directly define Surat bounding box instead of geocoding
        north, south, east, west = 21.30, 21.10, 72.90, 72.70  # approx Surat
        G = ox.graph_from_bbox(north, south, east, west, network_type="drive", simplify=True)

        # Add speeds & times
        G = ox.add_edge_speeds(G)
        G = ox.add_edge_travel_times(G)

        # Save locally
        nx.write_gpickle(G, GRAPH_FILE)
        st.success("✅ Built and cached Surat graph")
        return G
    except Exception as e:
        st.error(f"❌ Could not build graph: {e}")
        st.stop()


# -------------------------------
# 📍 Nearest Node
# -------------------------------
def nearest_node(G, lon, lat):
    try:
        return ox.nearest_nodes(G, lon, lat)
    except Exception:
        return ox.distance.nearest_nodes(G, lon, lat)


# -------------------------------
# ⏱️ Route Travel Time (seconds)
# -------------------------------
def route_travel_time_seconds(G, orig_node, dest_node):
    if any("travel_time" in d for _, _, d in G.edges(data=True)):
        weight = "travel_time"
    else:
        weight = "length"

    route = nx.shortest_path(G, orig_node, dest_node, weight=weight)

    time_sec = 0.0
    for u, v in zip(route[:-1], route[1:]):
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            continue
        vals = []
        for _, d in edge_data.items():
            if weight == "travel_time":
                vals.append(d.get("travel_time", 0.0))
            else:
                length = d.get("length", 0.0)
                speed_kph = d.get("speed_kph", 30)
                speed_ms = speed_kph / 3.6 if speed_kph else 8.33
                vals.append(length / max(speed_ms, 1.0))
        if vals:
            time_sec += min(vals)
    return time_sec, route


# -------------------------------
# 🌍 Route to Lat/Lon
# -------------------------------
def nodes_to_latlon(G, route):
    return [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]


# -------------------------------
# 🏥 Hospitals (with fallback)
# -------------------------------
@st.cache_data
def load_hospitals_with_fallback(_G=None):
    try:
        tags = {"amenity": "hospital"}
        # Use bounding box for Surat
        north, south, east, west = 21.30, 21.10, 72.90, 72.70
        gdf = ox.geometries_from_bbox(north, south, east, west, tags)
        hospitals = gdf[gdf.geometry.type == "Point"]
        if hospitals is not None and len(hospitals) > 0:
            return hospitals
    except Exception as e:
        print(f"⚠️ OSMnx failed to load hospitals: {e}")

    # Fallback
    fallback_hospitals = [
        ("New Civil Hospital Surat", 72.8311, 21.2090),
        ("Kiran Hospital", 72.7804, 21.1702),
        ("Sunshine Global Hospital", 72.7928, 21.2040),
        ("Apple Hospital", 72.8019, 21.1972),
        ("Unique Hospital", 72.7991, 21.1911),
    ]
    gdf_fallback = gpd.GeoDataFrame(
        [{"name": name, "geometry": Point(lon, lat)} for name, lon, lat in fallback_hospitals],
        crs="EPSG:4326"
    )
    return gdf_fallback
