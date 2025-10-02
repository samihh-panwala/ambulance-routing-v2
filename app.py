# app.py
import streamlit as st
from routing import load_graph, nearest_node, nodes_to_latlon, load_hospitals_with_fallback
from algorithm import select_ambulance_and_hospital, route_eta_minutes
import folium
from streamlit_folium import st_folium
import random

st.set_page_config(layout="wide", page_title="Emergency Ambulance Dispatch")
st.title("🚑 Emergency Ambulance Dispatch (Surat Only)")

PLACE = "Surat, India"

# Load graph once
if "G" not in st.session_state:
    st.session_state["G"] = load_graph(PLACE)

G = st.session_state["G"]
nodes = list(G.nodes)

def reset_scenario():
    if len(nodes) < 5:
        st.error("Graph does not contain enough nodes to place ambulances/incidents.")
        return

    # pick random ambulance nodes
    amb_nodes = random.sample(nodes, min(3, len(nodes)))
    ambulances = [{"id": f"A{i+1}", "node": amb_nodes[i], "status": "available"} for i in range(len(amb_nodes))]

    # incident inside Surat
    inc_node = random.choice(nodes)
    inc_lon, inc_lat = G.nodes[inc_node]['x'], G.nodes[inc_node]['y']
    incident = {"id": "I1", "lon": inc_lon, "lat": inc_lat, "status": "unassigned"}

    hospitals = load_hospitals_with_fallback(PLACE, G, min_count=5)

    st.session_state["ambulances"] = ambulances
    st.session_state["incident"] = incident
    st.session_state["hospitals"] = hospitals
    if "assigned" in st.session_state:
        del st.session_state["assigned"]

# Button to refresh everything
if st.button("🔄 Reset Scenario (New Incident & Ambulances)"):
    reset_scenario()

# Initialize if not already
if "ambulances" not in st.session_state:
    reset_scenario()

# Run greedy selection
if "assigned" not in st.session_state and "ambulances" in st.session_state:
    best_amb, best_hosp, route_to_inc, route_inc_hosp, t_amb, t_hosp = select_ambulance_and_hospital(
        G, st.session_state["ambulances"], st.session_state["incident"], st.session_state["hospitals"]
    )
    if best_amb is not None:
        best_amb["status"] = "dispatched"
        best_amb["route_to_inc"] = route_to_inc
        best_amb["route_to_hosp"] = route_inc_hosp
        best_amb["eta_to_inc_min"] = t_amb
        best_amb["hospital_name"] = best_hosp.get("name", "Hospital") if best_hosp is not None else "Hospital"
        st.session_state["incident"]["status"] = "assigned"
        st.session_state["incident"]["assigned_to"] = best_amb["id"]
        st.session_state["assigned"] = True
        st.success(f"🚑 Ambulance {best_amb['id']} assigned (ETA {t_amb:.1f} min) → hospital {best_amb['hospital_name']} (ETA {t_hosp:.1f} min)")

# Map
xs = [G.nodes[n]['x'] for n in G.nodes]
ys = [G.nodes[n]['y'] for n in G.nodes]
m = folium.Map(location=[sum(ys)/len(ys), sum(xs)/len(xs)], zoom_start=12)

# Hospitals
for idx, row in st.session_state["hospitals"].iterrows():
    folium.Marker(
        [row.geometry.y, row.geometry.x],
        popup=str(row.get("name", "Hospital")),
        icon=folium.Icon(color="green", icon="plus-sign"),
    ).add_to(m)

# Ambulances
for amb in st.session_state["ambulances"]:
    n = amb["node"]
    folium.Marker(
        [G.nodes[n]["y"], G.nodes[n]["x"]],
        popup=f'{amb["id"]} ({amb["status"]})',
        icon=folium.Icon(color="blue" if amb["status"] == "available" else "red", icon="ambulance", prefix="fa"),
    ).add_to(m)

    if amb.get("status") == "dispatched" and amb.get("route_to_inc"):
        coords = nodes_to_latlon(G, amb["route_to_inc"])
        folium.PolyLine(coords, weight=5, color="red").add_to(m)
    if amb.get("status") == "dispatched" and amb.get("route_to_hosp"):
        coords = nodes_to_latlon(G, amb["route_to_hosp"])
        folium.PolyLine(coords, weight=4, color="green", dash_array="5").add_to(m)

# Incident
inc = st.session_state["incident"]
folium.Marker(
    [inc["lat"], inc["lon"]],
    popup=f'{inc["id"]} ({inc["status"]})',
    icon=folium.Icon(color="orange", icon="exclamation-triangle", prefix="fa"),
).add_to(m)

st_folium(m, width=900, height=600)
