import pandas as pd
import numpy as np
from pathlib import Path

INPUT = Path("data/outputs/day5_motion_features/day5_motion_features.csv")
OUTPUT_DIR = Path("data/outputs/day6_behavior_analysis")

OUTPUT = OUTPUT_DIR / "day6_behavior_analysis.csv"
SUMMARY = OUTPUT_DIR / "day6_behavior_summary.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print()
print("==============================================")
print("BORDER-AI DAY 6")
print("VEHICLE BEHAVIOR & ANOMALY ANALYSIS")
print("==============================================")

if not INPUT.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT}")

df = pd.read_csv(INPUT)

print("Input:", INPUT)
print("Input rows:", len(df))
print("Vehicles:", df["track_id"].nunique())
print("Frames:", df["frame"].nunique())

df = df.sort_values(["track_id", "frame"]).reset_index(drop=True)

# ------------------------------------------------
# Numeric cleanup
# ------------------------------------------------

numeric_columns = [
    "speed_normalized",
    "acceleration",
    "displacement",
    "direction_deg",
    "vx",
    "vy"
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

# ------------------------------------------------
# Vehicle-level statistics
# ------------------------------------------------

vehicle_stats = df.groupby("track_id").agg(
    speed_mean=("speed_normalized", "mean"),
    speed_std=("speed_normalized", "std"),
    speed_max=("speed_normalized", "max"),
    acceleration_mean=("acceleration", "mean"),
    acceleration_std=("acceleration", "std"),
    acceleration_max=("acceleration", "max"),
    displacement_mean=("displacement", "mean"),
    observations=("frame", "count")
).reset_index()

vehicle_stats = vehicle_stats.fillna(0)

df = df.merge(
    vehicle_stats,
    on="track_id",
    how="left"
)

# ------------------------------------------------
# SPEED ANOMALY
# ------------------------------------------------

speed_std_safe = df["speed_std"].replace(0, 1e-6)

df["speed_zscore"] = (
    (
        df["speed_normalized"]
        - df["speed_mean"]
    ).abs()
    / speed_std_safe
)

df["speed_anomaly"] = np.clip(
    df["speed_zscore"] / 3.0,
    0,
    1
)

# ------------------------------------------------
# ACCELERATION ANOMALY
# ------------------------------------------------

acc_std_safe = df["acceleration_std"].replace(0, 1e-6)

df["acceleration_zscore"] = (
    (
        df["acceleration"]
        - df["acceleration_mean"]
    ).abs()
    / acc_std_safe
)

df["acceleration_anomaly"] = np.clip(
    df["acceleration_zscore"] / 3.0,
    0,
    1
)

# ------------------------------------------------
# DIRECTION CHANGE
# ------------------------------------------------

df["direction_change"] = (
    df.groupby("track_id")["direction_deg"]
    .diff()
    .abs()
)

df["direction_change"] = (
    df["direction_change"]
    .fillna(0)
)

# Circular angle correction
df["direction_change"] = np.minimum(
    df["direction_change"],
    360 - df["direction_change"]
)

df["direction_anomaly"] = np.clip(
    df["direction_change"] / 90.0,
    0,
    1
)

# ------------------------------------------------
# SLOW / STOPPED BEHAVIOR
# ------------------------------------------------

speed_threshold = 0.01

df["slow_or_stopped"] = (
    df["speed_normalized"] <= speed_threshold
).astype(int)

# ------------------------------------------------
# SUDDEN ACCELERATION
# ------------------------------------------------

acceleration_threshold = (
    df["acceleration"]
    .abs()
    .quantile(0.95)
)

df["sudden_acceleration"] = (
    df["acceleration"].abs()
    >= acceleration_threshold
).astype(int)

# ------------------------------------------------
# OVERALL BEHAVIOR ANOMALY SCORE
# ------------------------------------------------

df["behavior_anomaly_score"] = (
    0.35 * df["speed_anomaly"]
    + 0.35 * df["acceleration_anomaly"]
    + 0.20 * df["direction_anomaly"]
    + 0.10 * df["slow_or_stopped"]
)

df["behavior_anomaly_score"] = np.clip(
    df["behavior_anomaly_score"],
    0,
    1
)

# ------------------------------------------------
# BEHAVIOR CLASSIFICATION
# ------------------------------------------------

def classify_behavior(row):

    score = row["behavior_anomaly_score"]

    if score >= 0.75:
        return "CRITICAL_ANOMALY"

    if score >= 0.50:
        return "HIGH_ANOMALY"

    if score >= 0.25:
        return "MODERATE_ANOMALY"

    if row["slow_or_stopped"] == 1:
        return "SLOW_OR_STOPPED"

    return "NORMAL"


df["behavior_class"] = df.apply(
    classify_behavior,
    axis=1
)

# ------------------------------------------------
# VEHICLE-LEVEL INTELLIGENCE
# ------------------------------------------------

vehicle_summary = df.groupby("track_id").agg(
    observations=("frame", "count"),
    mean_speed=("speed_normalized", "mean"),
    max_speed=("speed_normalized", "max"),
    mean_acceleration=("acceleration", "mean"),
    max_acceleration=("acceleration", "max"),
    max_direction_change=("direction_change", "max"),
    anomaly_mean=("behavior_anomaly_score", "mean"),
    anomaly_max=("behavior_anomaly_score", "max"),
    anomaly_events=(
        "behavior_anomaly_score",
        lambda x: int((x >= 0.50).sum())
    ),
    slow_stopped_frames=(
        "slow_or_stopped",
        "sum"
    )
).reset_index()

vehicle_summary["vehicle_risk_score"] = np.clip(
    (
        0.45 * vehicle_summary["anomaly_mean"]
        + 0.35 * vehicle_summary["anomaly_max"]
        + 0.20 * (
            vehicle_summary["anomaly_events"]
            / vehicle_summary["observations"].clip(lower=1)
        )
    ),
    0,
    1
)

# ------------------------------------------------
# VEHICLE RISK LEVEL
# ------------------------------------------------

def risk_level(score):

    if score >= 0.75:
        return "CRITICAL"

    if score >= 0.50:
        return "HIGH"

    if score >= 0.25:
        return "MEDIUM"

    return "LOW"


vehicle_summary["risk_level"] = (
    vehicle_summary["vehicle_risk_score"]
    .apply(risk_level)
)

# ------------------------------------------------
# SAVE OUTPUTS
# ------------------------------------------------

df.to_csv(
    OUTPUT,
    index=False
)

vehicle_summary.to_csv(
    SUMMARY,
    index=False
)

# ------------------------------------------------
# REPORT
# ------------------------------------------------

print()
print("==============================================")
print("DAY 6 BEHAVIOR ANALYSIS COMPLETE")
print("==============================================")

print("Detailed output:")
print(OUTPUT)

print()
print("Vehicle summary:")
print(SUMMARY)

print()
print("Rows:", len(df))
print("Frames:", df["frame"].nunique())
print("Vehicles:", df["track_id"].nunique())

print()
print("Behavior classes:")
print(
    df["behavior_class"]
    .value_counts()
)

print()
print("Vehicle risk levels:")
print(
    vehicle_summary["risk_level"]
    .value_counts()
)

print()
print("Anomaly observations:")
print(
    int(
        (
            df["behavior_anomaly_score"]
            >= 0.50
        ).sum()
    )
)

print()
print("==============================================")
