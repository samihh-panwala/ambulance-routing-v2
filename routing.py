# routing.py - fixed helpers for ambulances & hospitals in Surat
import networkx as nx
from shapely.geometry import Point
import geopandas as gpd
import streamlit as st

@st.cache_resource
def load_graph(place_name="Surat, India"):
    # Minimal graph for compatibility; no OSMnx hospital fetching
    G = nx.Graph()
    return G

def nearest_node(G, lon, lat):
    # Dummy nearest_node function for compatibility
    # Returns a unique hash to simulate a node
    return hash((lon, lat)) % 100000

def route_travel_time_seconds(G, orig_node, dest_node):
    # Dummy function: returns arbitrary travel time for compatibility
    # In actual app, we use Haversine based ETA
    return 60, [orig_node, dest_node]

def nodes_to_latlon(G, route):
    # Dummy conversion
    return [(0,0) for n in route]

@st.cache_data
def load_hospitals_with_fallback(min_count=5):
    # Fixed hospitals in Surat
    fixed_hospitals = [
        ("New Civil Hospital", 21.1730, 72.8310),
        ("SMIMER Hospital", 21.1570, 72.8370),
        ("Apple Hospital", 21.1650, 72.8240),
        ("Unique Hospital", 21.1780, 72.8260),
        ("Sunshine Global Hospital", 21.1690, 72.8400),
    ]
    gdf_fallback = gpd.GeoDataFrame(
        [{"name": name, "geometry": Point(lon, lat)} for name, lat, lon in fixed_hospitals],
        crs="EPSG:4326"
    )
    return gdf_fallback
