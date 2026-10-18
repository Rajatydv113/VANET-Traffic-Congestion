
import os
import pandas as pd

# Locate input and output files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "traffic_data.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "congestion_results.csv")

# Load SUMO traffic data
df = pd.read_csv(INPUT_FILE)

if df.empty:
    raise ValueError("traffic_data.csv contains no traffic records.")

# Calculate traffic conditions for each road at each simulation step
road_data = (
    df.groupby(["time", "road_id"], as_index=False)
    .agg(
        vehicle_count=("vehicle_id", "nunique"),
        average_speed=("speed", "mean")
    )
)

# Convert speed from m/s to km/h
road_data["average_speed_kmh"] = road_data["average_speed"] * 3.6

# Initial rule-based congestion thresholds
def detect_congestion(row):
    if row["vehicle_count"] >= 3 and row["average_speed"] < 5:
        return "Congested"
    elif row["vehicle_count"] >= 3 and row["average_speed"] < 8:
        return "Moderate"
    else:
        return "Normal"

road_data["congestion_status"] = road_data.apply(
    detect_congestion,
    axis=1
)

# Save results
road_data.to_csv(OUTPUT_FILE, index=False)

print("\nCONGESTION ANALYSIS COMPLETED")
print("-" * 45)
print("Total road-time records:", len(road_data))
print("\nCongestion status counts:")
print(road_data["congestion_status"].value_counts())

print("\nSample results:")
print(road_data.head(10).to_string(index=False))

print("\nResults saved to:", OUTPUT_FILE)
