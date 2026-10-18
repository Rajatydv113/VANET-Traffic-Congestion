
import os
import heapq
import xml.etree.ElementTree as ET

import pandas as pd
import traci


# ==================================================
# 1. FILE PATHS
# ==================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NETWORK_FILE = os.path.join(BASE_DIR, "network.net.xml")
CONFIG_FILE = os.path.join(BASE_DIR, "simulation.sumocfg")
CONGESTION_FILE = os.path.join(BASE_DIR, "congestion_results.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "route_recommendations.csv")


# ==================================================
# 2. LOAD CONGESTED ROADS
# ==================================================

def load_congested_edges(time_step):
    data = pd.read_csv(CONGESTION_FILE)

    selected = data[
        (data["time"] == time_step)
        & (data["congestion_status"] == "Congested")
    ]

    return set(selected["road_id"].astype(str))


# ==================================================
# 3. LOAD ROAD INFORMATION FROM SUMO NETWORK
# ==================================================

def load_edge_costs():
    root = ET.parse(NETWORK_FILE).getroot()
    edges = {}

    for edge in root.findall("edge"):
        edge_id = edge.get("id")

        # Ignore internal junction edges
        if not edge_id or edge.get("function"):
            continue

        lane = edge.find("lane")

        if lane is None:
            continue

        length = float(lane.get("length", "1"))
        speed = float(lane.get("speed", "10"))

        edges[edge_id] = {
            "from": edge.get("from"),
            "to": edge.get("to"),
            "length": length,
            "speed": max(speed, 0.1),
        }

    return edges


# ==================================================
# 4. FIND A ROUTE THAT AVOIDS CONGESTED ROADS
# ==================================================


def find_route_avoiding_congestion(
    start_edge,
    destination_edge,
    edges,
    congested_edges,
):
    """
    Find a connected route from the vehicle's current road
    to its destination, avoiding congested roads after the
    current road wherever a valid path exists.
    """

    if start_edge not in edges or destination_edge not in edges:
        return None

    # The vehicle is already travelling on the current road.
    start_node = edges[start_edge]["to"]

    # We must enter the destination road at its starting junction.
    destination_node = edges[destination_edge]["from"]

    if start_edge == destination_edge:
        return [start_edge]

    # Build a graph excluding congested edges.
    # The current road is already behind the vehicle's position,
    # so it does not need to be included in this graph.
    graph = {}

    for edge_id, info in edges.items():
        if edge_id in congested_edges:
            continue

        graph.setdefault(info["from"], []).append(
            (
                info["to"],
                edge_id,
                info["length"] / info["speed"],
            )
        )

    # Dijkstra's shortest-path algorithm.
    queue = [(0.0, start_node, [])]
    best_cost = {start_node: 0.0}

    while queue:
        cost, node, path = heapq.heappop(queue)

        if cost > best_cost.get(node, float("inf")):
            continue

        if node == destination_node:
            # Include the current road and the destination road.
            route = [start_edge] + path + [destination_edge]

            # Verify that every consecutive pair of roads connects.
            for first, second in zip(route, route[1:]):
                if (
                    first not in edges
                    or second not in edges
                    or edges[first]["to"] != edges[second]["from"]
                ):
                    return None

            return route

        for next_node, edge_id, travel_time in graph.get(node, []):
            new_cost = cost + travel_time

            if new_cost < best_cost.get(next_node, float("inf")):
                best_cost[next_node] = new_cost

                heapq.heappush(
                    queue,
                    (
                        new_cost,
                        next_node,
                        path + [edge_id],
                    ),
                )

    # No connected route avoiding the congested roads was found.
    return None



# ==================================================
# 5. MAIN PROGRAM
# ==================================================

def main():
    # Check required files
    for file_path in (
        NETWORK_FILE,
        CONFIG_FILE,
        CONGESTION_FILE,
    ):
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Required file not found: {file_path}"
            )

    congestion_data = pd.read_csv(CONGESTION_FILE)

    required_columns = {
        "time",
        "road_id",
        "congestion_status",
    }

    if not required_columns.issubset(congestion_data.columns):
        raise ValueError(
            "congestion_results.csv must contain: "
            "time, road_id, congestion_status"
        )

    available_times = sorted(
        congestion_data["time"].dropna().unique()
    )

    if not available_times:
        print("No simulation time steps found.")
        return

    print("=" * 60)
    print(" VANET CONGESTION-AWARE ROUTE RECOMMENDATION ")
    print("=" * 60)

    print(
        f"Available time steps: {int(min(available_times))} "
        f"to {int(max(available_times))}"
    )

    try:
        time_step = int(
            input("\nEnter simulation time step (e.g. 105): ")
        )
    except ValueError:
        print("Invalid input. Enter a whole number.")
        return

    if time_step not in set(available_times):
        print("This time step is not available.")
        return

    congested_edges = load_congested_edges(time_step)
    edges = load_edge_costs()

    print(f"\nSelected time step: {time_step}")
    print("Congested roads:", sorted(congested_edges))

    if not congested_edges:
        print("No roads are classified as congested at this step.")
        return

    recommendations = []
    sumo_started = False

    try:
        # Start SUMO
        traci.start(["sumo", "-c", CONFIG_FILE])
        sumo_started = True

        # Advance simulation to the selected time
        while traci.simulation.getTime() < time_step:
            traci.simulationStep()

            if traci.simulation.getMinExpectedNumber() == 0:
                break

        vehicles = traci.vehicle.getIDList()

        print(f"SUMO time reached: {traci.simulation.getTime()}")
        print("Vehicles present:", len(vehicles))

        # Examine vehicles on congested roads
        for vehicle_id in vehicles:
            try:
                current_edge = traci.vehicle.getRoadID(vehicle_id)

                if current_edge.startswith(":"):
                    continue

                if current_edge not in congested_edges:
                    continue

                original_route = list(
                    traci.vehicle.getRoute(vehicle_id)
                )

                if not original_route:
                    continue

                destination = original_route[-1]

                alternative_route = find_route_avoiding_congestion(
                    current_edge,
                    destination,
                    edges,
                    congested_edges,
                )

                if alternative_route is None:
                    recommendations.append({
                        "Time Step": time_step,
                        "Vehicle ID": vehicle_id,
                        "Current Road": current_edge,
                        "Destination Road": destination,
                        "Original Route": " -> ".join(original_route),
                        "Alternative Route": (
                            "No congestion-free route found"
                        ),
                        "Avoids Congestion": "No",
                        "Estimated Travel Time (s)": None,
                    })
                    continue

                # The vehicle is already on the first road.
                # Evaluate congestion avoidance on the remaining route.
                roads_after_current = alternative_route[1:]

                avoids_congestion = not any(
                    road in congested_edges
                    for road in roads_after_current
                )

                # Estimate travel time using free-flow speed limits.
                estimated_time = sum(
                    edges[road]["length"] / edges[road]["speed"]
                    for road in alternative_route
                    if road in edges
                )

                recommendations.append({
                    "Time Step": time_step,
                    "Vehicle ID": vehicle_id,
                    "Current Road": current_edge,
                    "Destination Road": destination,
                    "Original Route": " -> ".join(original_route),
                    "Alternative Route": " -> ".join(alternative_route),
                    "Avoids Congestion": (
                        "Yes" if avoids_congestion else "No"
                    ),
                    "Estimated Travel Time (s)": round(
                        estimated_time, 2
                    ),
                })

            except traci.TraCIException as error:
                print(f"Skipping vehicle {vehicle_id}: {error}")

    except Exception as error:
        print(f"SUMO error: {error}")
        return

    finally:
        if sumo_started:
            try:
                traci.close()
            except traci.TraCIException:
                pass

    # ==================================================
    # 6. DISPLAY AND SAVE RESULTS
    # ==================================================

    columns = [
        "Time Step",
        "Vehicle ID",
        "Current Road",
        "Destination Road",
        "Original Route",
        "Alternative Route",
        "Avoids Congestion",
        "Estimated Travel Time (s)",
    ]

    result = pd.DataFrame(recommendations, columns=columns)

    result.to_csv(OUTPUT_FILE, index=False)

    print("\n" + "=" * 60)
    print(" ROUTE RECOMMENDATION RESULTS ")
    print("=" * 60)

    if result.empty:
        print("No vehicles were found on congested roads.")
    else:
        print(result.to_string(index=False))

        successful = int(
            (result["Avoids Congestion"] == "Yes").sum()
        )

        print(f"\nTotal records: {len(result)}")
        print(f"Congestion-avoiding routes: {successful}")

    print(f"\nResults saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
