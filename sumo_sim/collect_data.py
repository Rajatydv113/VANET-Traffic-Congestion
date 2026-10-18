
import traci
import pandas as pd
import os

# Get the folder where collect_data.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Use the absolute path to the SUMO configuration
CONFIG_FILE = os.path.join(BASE_DIR, "simulation.sumocfg")

# Save the output inside sumo_sim
OUTPUT_FILE = os.path.join(BASE_DIR, "traffic_data.csv")

sumo_cmd = [
    "sumo",
    "-c", CONFIG_FILE
]

traffic_data = []

print("Configuration file:", CONFIG_FILE)
print("Starting SUMO simulation...")

try:
    traci.start(sumo_cmd)

    step = 0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        vehicle_ids = traci.vehicle.getIDList()
        vehicle_count = len(vehicle_ids)

        for vehicle_id in vehicle_ids:
            x, y = traci.vehicle.getPosition(vehicle_id)

            traffic_data.append({
                "time": step,
                "vehicle_id": vehicle_id,
                "road_id": traci.vehicle.getRoadID(vehicle_id),
                "speed": traci.vehicle.getSpeed(vehicle_id),
                "x": x,
                "y": y,
                "vehicle_count": vehicle_count
            })

        step += 1

        if step % 100 == 0:
            print(f"Step: {step}, Vehicles: {vehicle_count}")

finally:
    traci.close()

df = pd.DataFrame(
    traffic_data,
    columns=[
        "time", "vehicle_id", "road_id",
        "speed", "x", "y", "vehicle_count"
    ]
)

df.to_csv(OUTPUT_FILE, index=False)

print("\nSimulation finished.")
print("CSV saved at:", OUTPUT_FILE)
print("Total records:", len(df))
print(df.head())
