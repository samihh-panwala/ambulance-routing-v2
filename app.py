# app.py - Streamlit app (Surat fixed, inside city nodes only)
import streamlit as st
import pandas as pd
from routing import load_graph, nearest_node, nodes_to_latlon, load_hospitals_with_fallback
from algorithm import select_ambulance_and_hospital, route_eta_minutes
import folium
from streamlit_folium import st_folium
import random

st.set_page_config(layout="wide", page_title="Emergency Ambulance Dispatch")
st.title("🚑 Emergency Ambulance Dispatch")
st.markdown("Fixed scenario: 1 incident, 3 ambulances at random locations, 5 hospitals. Greedy algorithm assigns the ambulance with minimum ETA to incident, then nearest hospital.")

PLACE = "Surat, India"

# Initialize Graph only once
if "G" not in st.session_state:
    st.session_state["G"] = load_graph(PLACE)

G = st.session_state["G"]
nodes = list(G.nodes)

# Function to reset ambulances + incident
def reset_scenario():
    random_nodes = random.sample(nodes, 3)  # 3 ambulance positions
    ambulances = [{"id": f"A{i+1}", "node": random_nodes[i], "status": "available"} for i in range(3)]
    inc_node = random.choice(nodes)  # Incident also inside Surat
    inc_lon, inc_lat = G.nodes[inc_node]['x'], G.nodes[inc_node]['y']
    incident = {"id": "I1", "lon": inc_lon, "lat": inc_lat, "status": "unassigned"}
    hospitals = load_hospitals_with_fallback(PLACE, G, min_count=5)

    st.session_state["ambulances"] = ambulances
    st.session_state["incident"] = incident
    st.session_state["hospitals"] = hospitals
    if "assigned" in st.session_state:
        del st.session_state["assigned"]

# Reset button
if st.button("🔄 Reset Scenario (New Incident & Ambulances)"):
    reset_scenario()

# Initialize scenario if not already
if "ambulances" not in st.session_state:
    reset_scenario()

# Run selection algorithm
if "assigned" not in st.session_state:
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
    else:
        st.error("Assignment failed (unexpected)")

# Map visualization
col1, col2 = st.columns([3, 1])
with col1:
    xs = [G.nodes[n]['x'] for n in G.nodes]
    ys = [G.nodes[n]['y'] for n in G.nodes]
    mean_lat = sum(ys) / len(ys)
    mean_lon = sum(xs) / len(xs)
    m = folium.Map(location=[mean_lat, mean_lon], zoom_start=12)

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

        # Draw routes
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

    st_folium(m, width=900, height=700)

# Sidebar Details
with col2:
    st.header("📋 Details")
    inc = st.session_state["incident"]
    st.markdown("**Incident**")
    st.write(f'ID: {inc["id"]}')
    st.write(f'Location (lon,lat): ({inc["lon"]:.6f}, {inc["lat"]:.6f})')

    st.markdown("**Ambulances**")
    for amb in st.session_state["ambulances"]:
        st.write(f'{amb["id"]}: status={amb["status"]}, node={amb["node"]}')
        if amb.get("status") == "dispatched":
            st.write(f'  Assigned hospital: {amb.get("hospital_name","-")}, ETA to incident: {amb.get("eta_to_inc_min",0):.1f} min')

    st.markdown("**Hospitals (5 selected)**")
    for idx, row in st.session_state["hospitals"].iterrows():
        st.write(f'{idx+1}. {row.get("name","Hospital")} — ({row.geometry.x:.6f}, {row.geometry.y:.6f})')

# Algorithm explanation
st.markdown("---")
st.subheader("⚙️ Algorithm Choice")
st.markdown("""
We used the **Greedy algorithm**:  
- Step 1: Choose the ambulance with the smallest ETA to the incident.  
- Step 2: Send patient to the hospital with the smallest ETA from the incident.  

### Why Greedy?
- **Fast & Simple**: Works well for single-incident, real-time dispatch.  
- **Other approaches**:  
  - *Divide & Conquer*: Breaks into subproblems, but no clear substructure here.  
  - *Dynamic Programming*: Overkill for one incident (useful if multiple simultaneous requests).  
  - *Backtracking*: Too slow for real-time (explores many possibilities).  
  - *String Matching*: Irrelevant (not path optimization).  

### Comparison with Shortest Distance
- Shortest distance may not equal shortest time (traffic, speed, road type).  
- Greedy by ETA ensures fastest arrival, which is critical in emergencies.  

### Time Complexity
- For each ambulance → shortest path: **O(E log V)** (Dijkstra).  
- For hospitals → again **O(E log V)**.  
- With `A` ambulances and `H` hospitals: **O((A+H) * E log V)**.  
""")

# ETA Comparison Table
st.subheader("📊 ETA Breakdown (Minutes)")
inc_node = nearest_node(G, inc["lon"], inc["lat"])
for amb in st.session_state["ambulances"]:
    t, _ = route_eta_minutes(G, amb["node"], inc_node)
    st.write(f'🚑 {amb["id"]} → Incident: {t:.1f} min')

best_amb = next((a for a in st.session_state["ambulances"] if a.get("status") == "dispatched"), None)
if best_amb:
    st.success(f"✅ Greedy algorithm selected {best_amb['id']} (ETA {best_amb['eta_to_inc_min']:.1f} min)")

st.markdown("**Hospitals ETA from Incident:**")
for idx, row in st.session_state["hospitals"].iterrows():
    hosp_node = nearest_node(G, row.geometry.x, row.geometry.y)
    t, _ = route_eta_minutes(G, inc_node, hosp_node)
    st.write(f'{row.get("name","Hospital")}: {t:.1f} min')


# Algorithm Comparison Table

st.subheader("📊 Algorithm Comparison Table")

data = {
    "Approach": [
        "Greedy (ETA-based)",
        "Shortest Distance",
        "Divide & Conquer",
        "Dynamic Programming",
        "Backtracking",
        "String Matching"
    ],
    "How it Works": [
        "Pick ambulance with minimum ETA → nearest hospital ETA",
        "Pick ambulance/hospital by shortest path length",
        "Split into subproblems, combine results",
        "Solve overlapping subproblems with optimal substructure",
        "Explore all possible ambulance-hospital assignments",
        "Pattern search (not relevant here)"
    ],
    "Pros": [
        "Fast, real-time, minimizes actual arrival time",
        "Simple to implement",
        "Structured approach, good for decomposable tasks",
        "Guarantees global optimum (for multi-requests)",
        "Exhaustive, guarantees exact best result",
        "Good for text/pattern problems"
    ],
    "Cons": [
        "Locally optimal, not always global optimum if multiple incidents",
        "Ignores traffic/speed, may not minimize ETA",
        "No natural subproblems for single dispatch",
        "Overkill for single incident, heavy computation",
        "Too slow for emergencies, exponential complexity",
        "Not applicable at all"
    ],
    "Time Complexity": [
        "O((A+H) * E log V)",
        "O((A+H) * E log V)",
        "Depends on partitioning, often O(n log n)",
        "O(n * W) (pseudo-poly, higher memory)",
        "O(2^n) (exponential)",
        "O(n*m) (irrelevant)"
    ]
}

df = pd.DataFrame(data)
st.table(df)
