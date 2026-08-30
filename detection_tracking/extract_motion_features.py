from pathlib import Path
import pandas as pd
import numpy as np

INPUT = Path("data/outputs/day4_trajectories.csv")
OUTPUT_DIR = Path("data/outputs/day5_motion_features")
OUTPUT = OUTPUT_DIR / "day5_motion_features.csv"
SUMMARY = OUTPUT_DIR / "day5_vehicle_summary.csv"

FPS = 30.0

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT)

required = [
    "frame",
    "track_id",
    "class_id",
    "center_x",
    "center_y",
    "width",
    "height"
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

df = df.sort_values(["track_id", "frame"]).reset_index(drop=True)

group = df.groupby("track_id", group_keys=False)

df["dt_frames"] = group["frame"].diff()

df["dt_seconds"] = df["dt_frames"] / FPS

df["dx"] = group["center_x"].diff()
df["dy"] = group["center_y"].diff()

df["vx"] = df["dx"] / df["dt_seconds"]
df["vy"] = df["dy"] / df["dt_seconds"]

df["speed_normalized"] = np.sqrt(
    df["vx"] ** 2 + df["vy"] ** 2
)

df["acceleration"] = (
    group["speed_normalized"].diff()
    / df["dt_seconds"]
)

df["displacement"] = np.sqrt(
    df["dx"] ** 2 + df["dy"] ** 2
)

df["direction_deg"] = np.degrees(
    np.arctan2(df["dy"], df["dx"])
)

df["direction_deg"] = (
    df["direction_deg"] + 360
) % 360

df["vx"] = df["vx"].replace([np.inf, -np.inf], np.nan)
df["vy"] = df["vy"].replace([np.inf, -np.inf], np.nan)
df["speed_normalized"] = df["speed_normalized"].replace(
    [np.inf, -np.inf], np.nan
)
df["acceleration"] = df["acceleration"].replace(
    [np.inf, -np.inf], np.nan
)

df["vx"] = df["vx"].fillna(0)
df["vy"] = df["vy"].fillna(0)
df["speed_normalized"] = df["speed_normalized"].fillna(0)
df["acceleration"] = df["acceleration"].fillna(0)
df["displacement"] = df["displacement"].fillna(0)
df["direction_deg"] = df["direction_deg"].fillna(0)

df["motion_state"] = np.select(
    [
        df["speed_normalized"] < 0.001,
        df["speed_normalized"] < 0.01,
        df["speed_normalized"] < 0.03
    ],
    [
        "stationary",
        "slow",
        "moving"
    ],
    default="fast"
)

summary = df.groupby("track_id").agg(
    class_id=("class_id", "first"),
    first_frame=("frame", "min"),
    last_frame=("frame", "max"),
    observations=("frame", "count"),
    mean_speed=("speed_normalized", "mean"),
    max_speed=("speed_normalized", "max"),
    mean_acceleration=("acceleration", "mean"),
    max_acceleration=("acceleration", "max"),
    total_displacement=("displacement", "sum"),
    mean_direction=("direction_deg", "mean"),
    min_x=("center_x", "min"),
    max_x=("center_x", "max"),
    min_y=("center_y", "min"),
    max_y=("center_y", "max")
).reset_index()

summary["track_duration_seconds"] = (
    summary["last_frame"] - summary["first_frame"]
) / FPS

summary["path_length"] = summary["total_displacement"]

summary["motion_consistency"] = (
    summary["observations"]
    / summary["track_duration_seconds"].replace(0, np.nan)
)

summary["motion_consistency"] = (
    summary["motion_consistency"].replace(
        [np.inf, -np.inf], np.nan
    ).fillna(0)
)

df.to_csv(OUTPUT, index=False)
summary.to_csv(SUMMARY, index=False)

print()
print("==============================================")
print("DAY 5 MOTION FEATURE EXTRACTION COMPLETE")
print("==============================================")
print(f"Input:                 {INPUT}")
print(f"Motion features:       {OUTPUT}")
print(f"Vehicle summary:       {SUMMARY}")
print()
print(f"Rows:                  {len(df)}")
print(f"Frames:                {df['frame'].nunique()}")
print(f"Vehicles:              {df['track_id'].nunique()}")
print()
print("Motion features:")
print("  - dx")
print("  - dy")
print("  - vx")
print("  - vy")
print("  - speed_normalized")
print("  - acceleration")
print("  - displacement")
print("  - direction_deg")
print("  - motion_state")
print()
print("==============================================")
