# algorithm.py

import networkx as nx
from routing import nearest_node

def route_eta_minutes(G, source, target, speed_kmph=40):
    """
    Compute ETA in minutes between two nodes using shortest path.
    speed_kmph: assumed average ambulance speed.
    """
    try:
        route = nx.shortest_path(G, source, target, weight="length")
        length_m = nx.path_weight(G, route, weight="length")
        time_hr = (length_m / 1000) / speed_kmph
        time_min = time_hr * 60
        return time_min, route
    except Exception:
        return float("inf"), None


def select_ambulance_and_hospital(G, ambulances, incident, hospitals_gdf):
    """
    Select best ambulance-hospital using ETA in minutes.
    All nodes used are from G (which is Surat graph), so ambulances and incident are in Surat.
    """
    # find nearest graph node to incident location
    inc_node = nearest_node(G, incident["lon"], incident["lat"])
    
    best_amb = None
    best_time = float("inf")
    best_route_to_inc = None
    # find best ambulance to incident
    for amb in ambulances:
        t, route = route_eta_minutes(G, amb["node"], inc_node)
        if t < best_time:
            best_time = t
            best_amb = amb
            best_route_to_inc = route

    if best_amb is None:
        return None, None, None, None, None, None

    # find best hospital from incident
    best_hosp = None
    best_hosp_time = float("inf")
    best_route_inc_hosp = None
    for idx, row in hospitals_gdf.iterrows():
        hosp_node = nearest_node(G, row.geometry.x, row.geometry.y)
        t_h, route_h = route_eta_minutes(G, inc_node, hosp_node)
        if t_h < best_hosp_time:
            best_hosp_time = t_h
            best_hosp = row
            best_route_inc_hosp = route_h

    return best_amb, best_hosp, best_route_to_inc, best_route_inc_hosp, best_time, best_hosp_time
