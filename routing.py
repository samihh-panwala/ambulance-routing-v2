# routing.py - robust helpers for OSMnx 2.x, hospital loading strictly in Surat
import osmnx as ox
import networkx as nx
import geopandas as gpd
import streamlit as st
from shapely.geometry import Point
import math

@st.cache_resource
def load_graph(place_name="Surat, India"):
    st.info(f"Loading graph for: {place_name} ... (first run may take time)")
    # ✅ Strictly get Surat boundary polygon
    city = ox.geocode_to_gdf(place_name)
    G = ox.graph_from_polygon(city.geometry.iloc[0], network_type="drive", simplify=True)

    try:
        G = ox.add_edge_speeds(G)
        G = ox.add_edge_travel_times(G)
    except Exception:
        pass
    return G

def nearest_node(G, lon, lat):
    try:
        return ox.nearest_nodes(G, lon, lat)
    except Exception:
        return ox.distance.nearest_nodes(G, lon, lat)

def route_travel_time_seconds(G, orig_node, dest_node):
    # choose weight
    weight = "travel_time" if any("travel_time" in d for u,v,d in G.edges(data=True)) else "length"
    route = nx.shortest_path(G, orig_node, dest_node, weight=weight)
    total = 0.0
    for u, v in zip(route[:-1], route[1:]):
        edge_data = G.get_edge_data(u, v)
        if not edge_data: continue
        vals = []
        for _, d in edge_data.items():
            if "travel_time" in d:
                vals.append(d.get("travel_time", 0.0))
            else:
                speed_kph = d.get("speed_kph", 30)
                speed_ms = speed_kph / 3.6 if speed_kph else 8.33
                vals.append(d.get("length", 0.0) / (speed_ms if speed_ms > 0 else 1.0))
        total += min(vals) if vals else 0.0
    return total, route

def nodes_to_latlon(G, route):
    return [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]

@st.cache_data
def load_hospitals_with_fallback(place, _G, min_count=5):
    try:
        tags = {"amenity": "hospital"}
        gdf = ox.geometries_from_place(place, tags)
        hospitals = gdf[gdf.geometry.type == "Point"]

        if hospitals is not None and len(hospitals) >= min_count:
            return hospitals
    except Exception as e:
        print(f"OSMnx failed to load hospitals: {e}")

    # ✅ Fallback hospitals strictly inside Surat
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
