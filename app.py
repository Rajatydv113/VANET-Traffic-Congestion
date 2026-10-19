import os
import random
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="VANET Traffic Management",
    page_icon="🚗",
    layout="wide"
)


# ==========================================
# 2. ROAD NETWORK CONFIGURATION (DEMO MODE)
# ==========================================

ROADS = {
    "Road A": {"capacity": 40, "free_speed": 60},
    "Road B": {"capacity": 40, "free_speed": 50},
    "Road C": {"capacity": 40, "free_speed": 40},
    "Road D": {"capacity": 40, "free_speed": 45},
}

ALTERNATIVES = {
    "Road A": ["Road B", "Road C"],
    "Road B": ["Road A", "Road D"],
    "Road C": ["Road A", "Road D"],
    "Road D": ["Road B", "Road C"],
}


# ==========================================
# 3. DEMO VEHICLE GENERATION
# ==========================================

def generate_vehicles(vehicle_count, scenario, seed):
    rng = random.Random(seed)
    road_names = list(ROADS.keys())

    if scenario == "Rush hour":
        weights = [0.70, 0.12, 0.10, 0.08]
    else:
        weights = [0.25, 0.25, 0.25, 0.25]

    assigned_roads = rng.choices(
        road_names, weights=weights, k=vehicle_count
    )

    road_counts = {
        road: assigned_roads.count(road)
        for road in road_names
    }

    vehicles = []

    for number, road in enumerate(assigned_roads, start=1):
        road_info = ROADS[road]
        capacity = road_info["capacity"]
        free_speed = road_info["free_speed"]

        density = road_counts[road] / capacity
        slowdown = max(0, density - 0.35) * 0.90
        speed_factor = max(0.20, 1 - slowdown)

        speed = free_speed * speed_factor + rng.uniform(-3, 3)
        speed = max(3, min(speed, free_speed))

        vehicles.append({
            "Vehicle ID": f"V{number:03}",
            "Road": road,
            "Speed (km/h)": round(speed, 1),
            "Position (m)": round(rng.uniform(0, 1000), 1)
        })

    return pd.DataFrame(vehicles)


# ==========================================
# 4. DEMO VANET COMMUNICATION
# ==========================================

def simulate_vanet_messages(vehicles, communication_range, seed):
    messages = []

    for _, sender in vehicles.iterrows():
        for _, receiver in vehicles.iterrows():
            if sender["Vehicle ID"] == receiver["Vehicle ID"]:
                continue

            if sender["Road"] != receiver["Road"]:
                continue

            distance = abs(
                sender["Position (m)"] - receiver["Position (m)"]
            )

            if distance <= communication_range:
                messages.append({
                    "Sender": sender["Vehicle ID"],
                    "Receiver": receiver["Vehicle ID"],
                    "Road": sender["Road"],
                    "Distance (m)": round(distance, 1),
                    "Speed (km/h)": sender["Speed (km/h)"],
                    "Message Type": "Traffic Status Beacon",
                    "Timestamp": datetime.now().strftime("%H:%M:%S")
                })

    return pd.DataFrame(
        messages,
        columns=[
            "Sender", "Receiver", "Road", "Distance (m)",
            "Speed (km/h)", "Message Type", "Timestamp"
        ]
    )


# ==========================================
# 5. DEMO CONGESTION DETECTION
# ==========================================

def analyze_traffic(vehicles):
    results = []

    for road, info in ROADS.items():
        road_vehicles = vehicles[vehicles["Road"] == road]
        count = len(road_vehicles)

        capacity = info["capacity"]
        free_speed = info["free_speed"]

        average_speed = (
            road_vehicles["Speed (km/h)"].mean()
            if count > 0 else free_speed
        )

        density = count / capacity
        speed_ratio = average_speed / free_speed

        if density >= 0.85 or (
            density >= 0.65 and speed_ratio < 0.60
        ):
            status = "Congested"
        elif density >= 0.50 or speed_ratio < 0.75:
            status = "Moderate"
        else:
            status = "Free Flow"

        results.append({
            "Road": road,
            "Vehicles": count,
            "Capacity": capacity,
            "Density (%)": round(density * 100, 1),
            "Average Speed (km/h)": round(average_speed, 1),
            "Traffic Status": status
        })

    return pd.DataFrame(results)


# ==========================================
# 6. DEMO ROUTE RECOMMENDATIONS
# ==========================================

def recommend_routes(traffic):
    recommendations = []

    for _, road_data in traffic.iterrows():
        road = road_data["Road"]

        if road_data["Traffic Status"] != "Congested":
            continue

        current_cost = (
            road_data["Vehicles"] / road_data["Capacity"]
            + 1 / max(road_data["Average Speed (km/h)"], 1)
        )

        for alternative in ALTERNATIVES[road]:
            alt_data = traffic[
                traffic["Road"] == alternative
            ].iloc[0]

            if alt_data["Traffic Status"] == "Congested":
                continue

            alternative_cost = (
                alt_data["Vehicles"] / alt_data["Capacity"]
                + 1 / max(alt_data["Average Speed (km/h)"], 1)
            )

            if alternative_cost < current_cost:
                recommendations.append({
                    "Congested Road": road,
                    "Suggested Road": alternative,
                    "Suggested Road Status": alt_data["Traffic Status"],
                    "Suggested Road Speed (km/h)": (
                        alt_data["Average Speed (km/h)"]
                    ),
                    "Reason": "Lower estimated traffic cost"
                })
                break

    return pd.DataFrame(
        recommendations,
        columns=[
            "Congested Road",
            "Suggested Road",
            "Suggested Road Status",
            "Suggested Road Speed (km/h)",
            "Reason"
        ]
    )


# ==========================================
# 7. DASHBOARD HEADER
# ==========================================

st.title("VANET Traffic Congestion Detection")

st.caption(
    "Academic prototype for simulated vehicle communication, "
    "traffic analysis and route recommendations."
)


# ==========================================
# 8. SIDEBAR CONTROLS
# ==========================================

with st.sidebar:
    st.header("Simulation Controls")

    data_source = st.selectbox(
        "Data Source",
        ["Demo Simulation", "SUMO Simulation"]
    )

    vehicle_count = st.slider(
        "Number of vehicles",
        min_value=10,
        max_value=100,
        value=60,
        step=5
    )

    scenario = st.selectbox(
        "Traffic scenario",
        ["Normal traffic", "Rush hour"]
    )

    communication_range = st.slider(
        "Assumed communication range (metres)",
        min_value=50,
        max_value=500,
        value=200,
        step=50
    )

    seed = st.number_input(
        "Simulation seed",
        min_value=1,
        max_value=9999,
        value=42,
        step=1
    )

    run_simulation = st.button(
        "Run Simulation",
        type="primary",
        use_container_width=True
    )


# ==========================================
# 9. SUMO SIMULATION DASHBOARD
# ==========================================

if data_source == "SUMO Simulation":

    st.subheader("SUMO Traffic Simulation Results")

    st.caption(
        "Recorded vehicle data and rule-based congestion analysis "
        "from your SUMO simulation."
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))
    sumo_dir = os.path.join(base_dir, "sumo_sim")

    traffic_file = os.path.join(sumo_dir, "traffic_data.csv")
    congestion_file = os.path.join(
        sumo_dir, "congestion_results.csv"
    )

    if not os.path.exists(traffic_file):
        st.error(
            "traffic_data.csv was not found. Run collect_data.py first."
        )
        st.stop()

    if not os.path.exists(congestion_file):
        st.error(
            "congestion_results.csv was not found. "
            "Run analyze_congestion.py first."
        )
        st.stop()

    vehicle_data = pd.read_csv(traffic_file)
    road_data = pd.read_csv(congestion_file)

    if vehicle_data.empty or road_data.empty:
        st.warning("The SUMO CSV files contain no records.")
        st.stop()

    available_times = sorted(
        pd.to_numeric(road_data["time"], errors="coerce")
        .dropna().astype(int).unique().tolist()
    )

    if not available_times:
        st.error("No valid simulation time steps were found.")
        st.stop()

    selected_time = st.slider(
        "SUMO simulation time step",
        min_value=int(min(available_times)),
        max_value=int(max(available_times)),
        value=int(max(available_times)),
        step=1
    )

    current_roads = road_data[
        pd.to_numeric(road_data["time"], errors="coerce")
        == selected_time
    ].copy()

    current_vehicles = vehicle_data[
        pd.to_numeric(vehicle_data["time"], errors="coerce")
        == selected_time
    ].copy()

    current_roads["Traffic Status"] = (
        current_roads["congestion_status"].replace({
            "Normal": "Free Flow",
            "Moderate": "Moderate",
            "Congested": "Congested"
        })
    )

    current_roads = current_roads.rename(columns={
        "road_id": "Road ID",
        "vehicle_count": "Vehicles",
        "average_speed_kmh": "Average Speed (km/h)"
    })

    current_roads["Average Speed (km/h)"] = (
        current_roads["Average Speed (km/h)"].round(1)
    )

    total_vehicles = len(current_vehicles)

    congested_roads = int(
        (current_roads["Traffic Status"] == "Congested").sum()
    )

    moderate_roads = int(
        (current_roads["Traffic Status"] == "Moderate").sum()
    )

    average_speed = (
        current_vehicles["speed"].mean() * 3.6
        if total_vehicles > 0 else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Vehicles at Selected Step", total_vehicles)
    c2.metric("Congested Roads", congested_roads)
    c3.metric("Moderate Roads", moderate_roads)
    c4.metric("Average Vehicle Speed", f"{average_speed:.1f} km/h")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Road Congestion Analysis")

        st.dataframe(
            current_roads[
                [
                    "Road ID",
                    "Vehicles",
                    "Average Speed (km/h)",
                    "Traffic Status"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    with right:
        st.subheader("Vehicle Count by Road")

        vehicle_chart = px.bar(
            current_roads,
            x="Road ID",
            y="Vehicles",
            color="Traffic Status",
            title=f"Traffic at simulation step {selected_time}"
        )

        st.plotly_chart(
            vehicle_chart,
            use_container_width=True
        )

    st.subheader("Average Speed by Road")

    speed_chart = px.bar(
        current_roads,
        x="Road ID",
        y="Average Speed (km/h)",
        color="Traffic Status",
        title="Average SUMO Vehicle Speed"
    )

    st.plotly_chart(
        speed_chart,
        use_container_width=True
    )

    st.subheader("Congestion Alerts")

    alerts = current_roads[
        current_roads["Traffic Status"] == "Congested"
    ]

    if alerts.empty:
        st.success(
            "No roads were classified as congested "
            "at this simulation step."
        )
    else:
        st.warning(
            f"{len(alerts)} road(s) classified as congested "
            f"at simulation step {selected_time}."
        )

        st.dataframe(
            alerts[
                [
                    "Road ID",
                    "Vehicles",
                    "Average Speed (km/h)",
                    "Traffic Status"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    st.subheader("SUMO Vehicle Records")

    display_vehicles = current_vehicles.rename(columns={
        "time": "Time Step",
        "vehicle_id": "Vehicle ID",
        "road_id": "Road ID",
        "speed": "Speed (m/s)",
        "x": "X Position (m)",
        "y": "Y Position (m)",
        "vehicle_count": "Total Vehicles"
    })

    st.dataframe(
        display_vehicles.head(100),
        use_container_width=True,
        hide_index=True
    )

    d1, d2 = st.columns(2)

    with d1:
        st.download_button(
            "Download SUMO Congestion Results",
            data=road_data.to_csv(index=False),
            file_name="sumo_congestion_results.csv",
            mime="text/csv",
            use_container_width=True
        )

    with d2:
        st.download_button(
            "Download SUMO Vehicle Data",
            data=vehicle_data.to_csv(index=False),
            file_name="sumo_traffic_data.csv",
            mime="text/csv",
            use_container_width=True
        )

    # ==========================================
    # SUMO CONGESTION-AWARE ROUTE RECOMMENDATIONS
    # ==========================================

    st.divider()
    st.subheader("Congestion-Aware Route Recommendations")

    st.caption(
        "Recommendations are loaded from route_recommendations.csv, "
        "generated by route_recommendations.py."
    )

    recommendations_file = os.path.join(
        sumo_dir, "route_recommendations.csv"
    )

    if not os.path.exists(recommendations_file):
        st.warning(
            "The route recommendations file was not found. "
            "Generate it using the command below."
        )

        st.code(
            "python .\\sumo_sim\\route_recommendations.py",
            language="powershell"
        )

    else:
        try:
            route_data = pd.read_csv(recommendations_file)

            if route_data.empty:
                st.info(
                    "The route recommendations file is empty. "
                    "Run route_recommendations.py for a time step "
                    "where congestion is detected."
                )

            elif "Time Step" not in route_data.columns:
                st.error(
                    "The recommendations file is missing the "
                    "'Time Step' column. Rerun route_recommendations.py."
                )

            else:
                route_times = pd.to_numeric(
                    route_data["Time Step"], errors="coerce"
                )

                selected_routes = route_data[
                    route_times == selected_time
                ].copy()

                if selected_routes.empty:
                    valid_times = sorted(
                        route_times.dropna().astype(int).unique().tolist()
                    )

                    st.info(
                        f"No saved route recommendations exist for step "
                        f"{selected_time}. Saved steps: "
                        f"{', '.join(map(str, valid_times)) or 'none'}. "
                        "Run the recommendation script for this time step."
                    )

                else:
                    total_routes = len(selected_routes)

                    if "Avoids Congestion" in selected_routes.columns:
                        successful_routes = int(
                            (
                                selected_routes["Avoids Congestion"]
                                .astype(str)
                                .str.strip()
                                .str.lower() == "yes"
                            ).sum()
                        )
                    else:
                        successful_routes = 0

                    route_col1, route_col2 = st.columns(2)

                    route_col1.metric(
                        "Vehicles Analyzed", total_routes
                    )

                    route_col2.metric(
                        "Routes Avoiding Congestion",
                        successful_routes
                    )

                    st.dataframe(
                        selected_routes,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.download_button(
                        "Download Route Recommendations CSV",
                        data=selected_routes.to_csv(index=False),
                        file_name=(
                            f"route_recommendations_step_{selected_time}.csv"
                        ),
                        mime="text/csv",
                        use_container_width=True
                    )

            if not route_data.empty:
                with st.expander(
                    "View all saved route recommendations"
                ):
                    st.dataframe(
                        route_data,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.download_button(
                        "Download All Route Recommendations",
                        data=route_data.to_csv(index=False),
                        file_name="route_recommendations.csv",
                        mime="text/csv",
                        key="download_all_route_recommendations",
                        use_container_width=True
                    )

        except (pd.errors.ParserError, OSError, ValueError) as error:
            st.error(
                f"Could not read route_recommendations.csv: {error}. "
                "Please rerun route_recommendations.py."
            )

    st.info(
        "This view uses recorded SUMO data. Congestion labels use "
        "the rules in analyze_congestion.py. Route recommendations are "
        "suggestions from route_recommendations.py; they do not "
        "automatically reroute vehicles inside SUMO."
    )

    st.stop()


# ==========================================
# 10. DEMO SIMULATION
# ==========================================

if "simulation_results" not in st.session_state:
    st.session_state.simulation_results = None

if run_simulation or st.session_state.simulation_results is None:

    vehicles = generate_vehicles(
        vehicle_count, scenario, int(seed)
    )

    messages = simulate_vanet_messages(
        vehicles, communication_range, int(seed)
    )

    traffic = analyze_traffic(vehicles)
    recommendations = recommend_routes(traffic)

    st.session_state.simulation_results = {
        "vehicles": vehicles,
        "messages": messages,
        "traffic": traffic,
        "recommendations": recommendations,
        "scenario": scenario,
        "vehicle_count": vehicle_count,
        "communication_range": communication_range,
        "seed": int(seed)
    }


results = st.session_state.simulation_results

vehicles = results["vehicles"]
messages = results["messages"]
traffic = results["traffic"]
recommendations = results["recommendations"]


# ==========================================
# 11. DEMO SUMMARY METRICS
# ==========================================

congested_count = int(
    (traffic["Traffic Status"] == "Congested").sum()
)

moderate_count = int(
    (traffic["Traffic Status"] == "Moderate").sum()
)

free_flow_count = int(
    (traffic["Traffic Status"] == "Free Flow").sum()
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Vehicles", len(vehicles))
c2.metric("Congested Roads", congested_count)
c3.metric("Moderate Roads", moderate_count)
c4.metric("V2V Messages", len(messages))

st.caption(
    f"Showing the last run: {results['scenario']} | "
    f"Communication range: {results['communication_range']} m | "
    f"Seed: {results['seed']}"
)

st.divider()


# ==========================================
# 12. DEMO TRAFFIC ANALYSIS
# ==========================================

left, right = st.columns(2)

with left:
    st.subheader("Road Traffic Analysis")

    st.dataframe(
        traffic,
        use_container_width=True,
        hide_index=True
    )

with right:
    st.subheader("Vehicle Count by Road")

    count_chart = px.bar(
        traffic,
        x="Road",
        y="Vehicles",
        color="Traffic Status",
        title="Vehicles on Each Road",
        category_orders={
            "Traffic Status": [
                "Free Flow", "Moderate", "Congested"
            ]
        }
    )

    st.plotly_chart(
        count_chart,
        use_container_width=True
    )


# ==========================================
# 13. DEMO SPEED CHART
# ==========================================

st.subheader("Average Speed by Road")

speed_chart = px.bar(
    traffic,
    x="Road",
    y="Average Speed (km/h)",
    color="Traffic Status",
    title="Estimated Average Vehicle Speed",
    category_orders={
        "Traffic Status": [
            "Free Flow", "Moderate", "Congested"
        ]
    }
)

st.plotly_chart(
    speed_chart,
    use_container_width=True
)


# ==========================================
# 14. DEMO STATUS SUMMARY
# ==========================================

st.subheader("Road Status Summary")

s1, s2, s3 = st.columns(3)

s1.metric("Free Flow", free_flow_count)
s2.metric("Moderate", moderate_count)
s3.metric("Congested", congested_count)


# ==========================================
# 15. DEMO ROUTE RECOMMENDATIONS
# ==========================================

st.subheader("Traffic Management Recommendations")

if recommendations.empty:
    st.info(
        "No suitable alternative route was identified "
        "under the current simulation conditions."
    )
else:
    st.warning(
        "These are simulated route recommendations. "
        "The road network and costs are simplified."
    )

    st.dataframe(
        recommendations,
        use_container_width=True,
        hide_index=True
    )


# ==========================================
# 16. DEMO VANET MESSAGE LOG
# ==========================================

st.subheader("Simulated VANET Message Log")

if messages.empty:
    st.info(
        "No vehicle-to-vehicle messages were generated "
        "within the selected communication range."
    )
else:
    st.caption(
        f"Showing up to 50 of {len(messages)} simulated "
        "vehicle-to-vehicle message receptions."
    )

    st.dataframe(
        messages.head(50),
        use_container_width=True,
        hide_index=True
    )


# ==========================================
# 17. DEMO DOWNLOAD REPORTS
# ==========================================

st.subheader("Download Simulation Results")

d1, d2, d3 = st.columns(3)

with d1:
    st.download_button(
        "Download Traffic CSV",
        data=traffic.to_csv(index=False),
        file_name="vanet_traffic_analysis.csv",
        mime="text/csv",
        use_container_width=True
    )

with d2:
    st.download_button(
        "Download Vehicles CSV",
        data=vehicles.to_csv(index=False),
        file_name="vanet_vehicles.csv",
        mime="text/csv",
        use_container_width=True
    )

with d3:
    st.download_button(
        "Download V2V Messages CSV",
        data=messages.to_csv(index=False),
        file_name="vanet_messages.csv",
        mime="text/csv",
        use_container_width=True
    )


# ==========================================
# 18. PROJECT LIMITATIONS
# ==========================================

with st.expander("About this simulation"):
    st.markdown(
        """
        **Demo traffic generation:** Vehicles are assigned to
        conceptual road segments using scenario-dependent probabilities.

        **Demo congestion detection:** Traffic is classified using
        illustrative occupancy and relative-speed thresholds.

        **Demo VANET communication:** Messages are simulated between
        vehicles on the same conceptual road within the configured
        distance. Actual radio propagation and packet collisions
        are not modelled.

        **Demo routing:** Alternative roads are simplified conceptual
        connections, not routes computed on the SUMO network.

        **SUMO mode:** Uses recorded vehicle positions, speeds and
        road-level classifications collected from the SUMO simulation.
        SUMO congestion labels are rule-based and depend on the
        thresholds in analyze_congestion.py.
        """
    )

st.caption(
    "College project prototype — simulation results are not "
    "live road traffic data."
)