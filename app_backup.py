
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
# 2. ROAD NETWORK CONFIGURATION
# ==========================================

ROADS = {
    "Road A": {"capacity": 40, "free_speed": 60},
    "Road B": {"capacity": 40, "free_speed": 50},
    "Road C": {"capacity": 40, "free_speed": 40},
    "Road D": {"capacity": 40, "free_speed": 45},
}

# Simplified connections between roads.
# This is a conceptual network, not a real road map.

ALTERNATIVES = {
    "Road A": ["Road B", "Road C"],
    "Road B": ["Road A", "Road D"],
    "Road C": ["Road A", "Road D"],
    "Road D": ["Road B", "Road C"],
}


# ==========================================
# 3. VEHICLE GENERATION
# ==========================================

def generate_vehicles(vehicle_count, scenario, seed):
    rng = random.Random(seed)

    road_names = list(ROADS.keys())

    # Distribute traffic differently by scenario.
    if scenario == "Rush hour":
        weights = [0.70, 0.12, 0.10, 0.08]
    else:
        weights = [0.25, 0.25, 0.25, 0.25]

    assigned_roads = rng.choices(
        road_names,
        weights=weights,
        k=vehicle_count
    )

    # Count the vehicles on each road.
    road_counts = {
        road: assigned_roads.count(road)
        for road in road_names
    }

    vehicles = []

    for number, road in enumerate(assigned_roads, start=1):
        road_info = ROADS[road]

        capacity = road_info["capacity"]
        free_speed = road_info["free_speed"]

        # Occupancy compared with the model capacity.
        density = road_counts[road] / capacity

        # Traffic becomes slower as density increases.
        # The speed factor is bounded to avoid unrealistic
        # negative speeds.
        slowdown = max(0, density - 0.35) * 0.90
        speed_factor = max(0.20, 1 - slowdown)

        speed = (
            free_speed * speed_factor
            + rng.uniform(-3, 3)
        )

        speed = max(3, min(speed, free_speed))

        vehicles.append({
            "Vehicle ID": f"V{number:03}",
            "Road": road,
            "Speed (km/h)": round(speed, 1),
            "Position (m)": round(
                rng.uniform(0, 1000), 1
            )
        })

    return pd.DataFrame(vehicles)


# ==========================================
# 4. SIMULATED VANET COMMUNICATION
# ==========================================

def simulate_vanet_messages(vehicles, communication_range, seed):
    """
    Simulate local vehicle-to-vehicle message reception.

    Vehicles are considered able to exchange messages when
    they are on the same road and within the configured range.

    This is a simplified model. It does not simulate actual
    radio propagation, packet collisions or wireless hardware.
    """

    rng = random.Random(seed)

    messages = []

    for _, sender in vehicles.iterrows():
        for _, receiver in vehicles.iterrows():

            if sender["Vehicle ID"] == receiver["Vehicle ID"]:
                continue

            if sender["Road"] != receiver["Road"]:
                continue

            distance = abs(
                sender["Position (m)"]
                - receiver["Position (m)"]
            )

            if distance <= communication_range:
                messages.append({
                    "Sender": sender["Vehicle ID"],
                    "Receiver": receiver["Vehicle ID"],
                    "Road": sender["Road"],
                    "Distance (m)": round(distance, 1),
                    "Speed (km/h)": sender["Speed (km/h)"],
                    "Message Type": "Traffic Status Beacon",
                    "Timestamp": datetime.now().strftime(
                        "%H:%M:%S"
                    )
                })

    return pd.DataFrame(
        messages,
        columns=[
            "Sender",
            "Receiver",
            "Road",
            "Distance (m)",
            "Speed (km/h)",
            "Message Type",
            "Timestamp"
        ]
    )


# ==========================================
# 5. TRAFFIC CONGESTION DETECTION
# ==========================================

def analyze_traffic(vehicles):
    results = []

    for road, info in ROADS.items():
        road_vehicles = vehicles[
            vehicles["Road"] == road
        ]

        count = len(road_vehicles)

        capacity = info["capacity"]
        free_speed = info["free_speed"]

        if count > 0:
            average_speed = road_vehicles[
                "Speed (km/h)"
            ].mean()
        else:
            average_speed = free_speed

        # Capacity-based occupancy indicator.
        density = count / capacity

        # Speed compared with the free-flow reference speed.
        speed_ratio = average_speed / free_speed

        # Illustrative model thresholds.
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
            "Average Speed (km/h)": round(
                average_speed, 1
            ),
            "Traffic Status": status
        })

    return pd.DataFrame(results)


# ==========================================
# 6. ROUTE RECOMMENDATION
# ==========================================

def recommend_routes(traffic):
    recommendations = []

    for _, road_data in traffic.iterrows():
        road = road_data["Road"]

        if road_data["Traffic Status"] != "Congested":
            continue

        # Cost of travelling on the congested road.
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
                + 1 / max(
                    alt_data["Average Speed (km/h)"], 1
                )
            )

            if alternative_cost < current_cost:
                recommendations.append({
                    "Congested Road": road,
                    "Suggested Road": alternative,
                    "Suggested Road Status": (
                        alt_data["Traffic Status"]
                    ),
                    "Suggested Road Speed (km/h)": (
                        alt_data["Average Speed (km/h)"]
                    ),
                    "Reason": (
                        "Lower estimated traffic cost"
                    )
                })

                # Recommend the best available alternative
                # according to the current road ordering.
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

st.title("🚗 VANET Traffic Congestion Detection")

st.caption(
    "Academic prototype for simulated vehicle communication, "
    "traffic analysis and route recommendations."
)


# ==========================================
# 8. SIMULATION CONTROLS
# ==========================================

with st.sidebar:
    st.header("Simulation Controls")

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
# 9. RUN AND STORE SIMULATION
# ==========================================

# Run once at startup, then when the user presses the button.
if "simulation_results" not in st.session_state:
    st.session_state.simulation_results = None

if run_simulation or st.session_state.simulation_results is None:

    vehicles = generate_vehicles(
        vehicle_count,
        scenario,
        int(seed)
    )

    messages = simulate_vanet_messages(
        vehicles,
        communication_range,
        int(seed)
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
# 10. SUMMARY METRICS
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

c1.metric(
    "Vehicles",
    len(vehicles)
)

c2.metric(
    "Congested Roads",
    congested_count
)

c3.metric(
    "Moderate Roads",
    moderate_count
)

c4.metric(
    "V2V Messages",
    len(messages)
)

st.caption(
    f"Showing the last run: {results['scenario']} | "
    f"Communication range: {results['communication_range']} m | "
    f"Seed: {results['seed']}"
)

st.divider()


# ==========================================
# 11. TRAFFIC ANALYSIS TABLE AND CHART
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
                "Free Flow",
                "Moderate",
                "Congested"
            ]
        }
    )

    st.plotly_chart(
        count_chart,
        use_container_width=True
    )


# ==========================================
# 12. SPEED CHART
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
            "Free Flow",
            "Moderate",
            "Congested"
        ]
    }
)

st.plotly_chart(
    speed_chart,
    use_container_width=True
)


# ==========================================
# 13. CONGESTION STATUS SUMMARY
# ==========================================

st.subheader("Road Status Summary")

summary_col1, summary_col2, summary_col3 = st.columns(3)

summary_col1.metric("Free Flow", free_flow_count)
summary_col2.metric("Moderate", moderate_count)
summary_col3.metric("Congested", congested_count)


# ==========================================
# 14. ROUTE RECOMMENDATIONS
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
# 15. VANET MESSAGE LOG
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
# 16. DOWNLOAD REPORTS
# ==========================================

st.subheader("Download Simulation Results")

download_col1, download_col2, download_col3 = st.columns(3)

with download_col1:
    st.download_button(
        "Download Traffic CSV",
        data=traffic.to_csv(index=False),
        file_name="vanet_traffic_analysis.csv",
        mime="text/csv",
        use_container_width=True
    )

with download_col2:
    st.download_button(
        "Download Vehicles CSV",
        data=vehicles.to_csv(index=False),
        file_name="vanet_vehicles.csv",
        mime="text/csv",
        use_container_width=True
    )

with download_col3:
    st.download_button(
        "Download V2V Messages CSV",
        data=messages.to_csv(index=False),
        file_name="vanet_messages.csv",
        mime="text/csv",
        use_container_width=True
    )


# ==========================================
# 17. PROJECT LIMITATIONS
# ==========================================

with st.expander("About this simulation"):
    st.markdown(
        """
        **Traffic generation:** Vehicles are assigned to road
        segments using scenario-dependent probabilities.

        **Capacity:** Capacity is an assumed maximum reference
        count for each road segment, used to calculate a
        capacity-based occupancy percentage.

        **Congestion detection:** Traffic is classified using
        illustrative occupancy and relative-speed thresholds.

        **VANET communication:** Messages are simulated between
        vehicles on the same road within the configured distance.
        This version does not model real radio propagation,
        wireless packet collisions, or network latency.

        **Routing:** Alternative roads are simplified connections.
        The system recommends a less costly alternative when
        one is available.
        """
    )

st.caption(
    "College project prototype — results are simulated, "
    "not live road traffic data."
)
