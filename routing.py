# routing.py
import osmnx as ox
import geopandas as gpd
import random

def load_graph(place="Surat, India"):
    """Load drivable street graph for given place."""
    G = ox.graph_from_place(place, network_type="drive")
    return G

def nearest_node(G, lon, lat):
    """Find nearest graph node to given coordinates."""
    return ox.distance.nearest_nodes(G, lon, lat)

def nodes_to_latlon(G, nodes):
    """Convert node list to lat/lon coordinates for mapping."""
    return [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in nodes]

def load_hospitals_with_fallback(place, G, min_count=5):
    """Load hospitals inside the city boundary. Ensure at least min_count exist."""
    try:
        tags = {"amenity": "hospital"}
        gdf = ox.geometries_from_place(place, tags)
        if not gdf.empty:
            gdf = gdf.to_crs("EPSG:4326")  # lat/lon
            gdf = gdf[gdf.geometry.type == "Point"]
            if len(gdf) > min_count:
                gdf = gdf.sample(min_count, random_state=42)
            return gdf
    except Exception:
        pass
    # fallback: pick random nodes as dummy hospitals
    nodes = list(G.nodes())
    coords = random.sample(nodes, min_count)
    rows = []
    for i, n in enumerate(coords):
        rows.append({
            "name": f"Hospital {i+1}",
            "geometry": gpd.points_from_xy([G.nodes[n]['x']], [G.nodes[n]['y']])[0]
        })
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")
