# Analysis & Report (v3)

## Scenario requirements implemented
- Fixed city: Surat, India.
- 1 incident (placed near city center).
- 3 ambulances at random nodes within Surat graph.
- 5 hospitals loaded from OSM (with robust fallback to ensure 5 entries).
- Greedy algorithm selects ambulance with minimum ETA to incident, then selects nearest hospital by ETA from incident.

## Why Greedy?
For single-incident, low-scale dispatch, greedy is low-latency and effective. It minimizes time-to-arrival for the immediate incident.

## Files
- app.py, routing.py, algorithm.py, requirements.txt
