# routing.py - Robust helpers for OSMnx 2.x, caching + fallback hospitals
import os
import osmnx as ox
import networkx as nx
import geopandas as gpd
import streamlit as st
from shapely.geometry import Point

# Local cache filename for the Surat graph
GRAPH_FILE = "surat_graph.gpickle"


# -------------------------------
# 🚦 Load Graph (Surat road network)
# -------------------------------
@st.cache_resource
def load_graph(place_name="Surat, India"):
    """
    Load a road network graph for the given place.
    - Uses OSMnx if online.
    - Falls back to a cached gpickle if offline.
    """
    st.info(f"Loading graph for: {place_name} ... (first run may take time)")

    try:
        # ✅ Prefer local cache if exists
        if os.path.exists(GRAPH_FILE):
            return nx.read_gpickle(GRAPH_FILE)

        # Get Surat boundary polygon
        city = ox.geocode_to_gdf(place_name)
        G = ox.graph_from_polygon(city.geometry.iloc[0], network_type="drive", simplify=True)

        # Add travel speeds & times if possible
        try:
            G = ox.add_edge_speeds(G)
            G = ox.add_edge_travel_times(G)
        except Exception:
            pass

        # Save to disk for future runs
        nx.write_gpickle(G, GRAPH_FILE)
        return G

    except Exception as e:
        st.error(f"❌ Could not load graph from OSM: {e}")

        if os.path.exists(GRAPH_FILE):
            st.warning("⚠️ Using cached Surat graph instead.")
            return nx.read_gpickle(GRAPH_FILE)

        st.stop()  # Abort gracefully if no graph available


# -------------------------------
# 📍 Nearest Node
# -------------------------------
def nearest_node(G, lon, lat):
    """Find nearest graph node to a coordinate (lon, lat)."""
    try:
        return ox.nearest_nodes(G, lon, lat)
    except Exception:
        # OSMnx 1.x fallback
        return ox.distance.nearest_nodes(G, lon, lat)


# -------------------------------
# ⏱️ Route Travel Time (seconds)
# -------------------------------
def route_travel_time_seconds(G, orig_node, dest_node):
    """
    Compute shortest path travel time (seconds) between two nodes.
    Uses 'travel_time' if available, else falls back to edge length.
    """
    # Decide weight
    if any("travel_time" in d for _, _, d in G.edges(data=True)):
        weight = "travel_time"
    else:
        weight = "length"

    # Shortest path
    route = nx.shortest_path(G, orig_node, dest_node, weight=weight)

    # Total cost
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
                # length / speed (default 30 km/h if missing)
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
    """Convert node IDs in route to list of (lat, lon) pairs."""
    return [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]


# -------------------------------
# 🏥 Hospitals Loader (with fallback)
# -------------------------------
@st.cache_data
def load_hospitals_with_fallback(place="Surat, India", _G=None, min_count=5):
    """
    Load hospitals in a given city.
    - First tries OSM data (strictly inside city boundary).
    - Falls back to a fixed set of known hospitals in Surat.
    """
    try:
        city = ox.geocode_to_gdf(place)
        tags = {"amenity": "hospital"}
        gdf = ox.geometries_from_polygon(city.geometry.iloc[0], tags)
        hospitals = gdf[gdf.geometry.type == "Point"]

        if hospitals is not None and len(hospitals) >= min_count:
            return hospitals

    except Exception as e:
        print(f"⚠️ OSMnx failed to load hospitals: {e}")

    # ✅ Fallback: Fixed hospitals inside Surat
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
