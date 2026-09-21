from pathlib import Path
import pandas as pd
import numpy as np

# =========================================================
# BORDER-AI DAY 8
# DYNAMIC TEMPORAL RISK + EARLY WARNING DATASET
# =========================================================

INPUT = Path(
    "data/outputs/day6_behavior_analysis/day6_behavior_analysis.csv"
)

RISK_INPUT = Path(
    "data/outputs/day7_risk_intelligence/day7_vehicle_risk_intelligence.csv"
)

OUTPUT_DIR = Path(
    "data/outputs/day8_temporal_prediction"
)

OUTPUT_DATASET = OUTPUT_DIR / "day8_temporal_dataset.csv"
OUTPUT_STATS = OUTPUT_DIR / "day8_temporal_statistics.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# LOAD DATA
# =========================================================

df = pd.read_csv(INPUT)
risk = pd.read_csv(RISK_INPUT)

df = df.sort_values(
    ["track_id", "frame"]
).reset_index(drop=True)

# =========================================================
# DAY 7 VEHICLE-LEVEL BASELINE
# =========================================================

risk_cols = [
    "track_id",
    "threat_score",
    "threat_level",
    "priority"
]

risk = risk[risk_cols].copy()

df = df.merge(
    risk,
    on="track_id",
    how="left"
)

df["threat_score"] = df["threat_score"].fillna(0)
df["priority"] = df["priority"].fillna(5)

df["threat_level"] = df["threat_level"].fillna("SAFE")

# =========================================================
# GROUP
# =========================================================

group = df.groupby(
    "track_id",
    group_keys=False
)

# =========================================================
# TEMPORAL MOTION FEATURES
# =========================================================

df["speed_change"] = (
    group["speed_normalized"]
    .diff()
    .fillna(0)
)

df["acceleration_change"] = (
    group["acceleration"]
    .diff()
    .fillna(0)
)

df["direction_change"] = (
    group["direction_deg"]
    .diff()
    .abs()
    .fillna(0)
)

# Normalize direction changes to 0-1.
df["direction_change_norm"] = (
    df["direction_change"].clip(0, 180) / 180.0
)

df["position_change"] = np.sqrt(
    df["dx"].fillna(0) ** 2 +
    df["dy"].fillna(0) ** 2
)

# =========================================================
# BEHAVIOR SIGNAL NORMALIZATION
# =========================================================

def safe_norm(series, low=0.0, high=1.0):
    return (
        (series - low) /
        (high - low)
    ).clip(0, 1)


df["behavior_anomaly_norm"] = safe_norm(
    df["behavior_anomaly_score"],
    0,
    1
)

df["speed_anomaly_norm"] = safe_norm(
    df["speed_anomaly"],
    0,
    1
)

df["acceleration_anomaly_norm"] = safe_norm(
    df["acceleration_anomaly"],
    0,
    1
)

df["direction_anomaly_norm"] = safe_norm(
    df["direction_anomaly"],
    0,
    1
)

df["sudden_acceleration_norm"] = (
    df["sudden_acceleration"]
    .astype(float)
    .clip(0, 1)
)

df["slow_stopped_norm"] = (
    df["slow_or_stopped"]
    .astype(float)
    .clip(0, 1)
)

# =========================================================
# ROLLING BEHAVIOR
# =========================================================

df["speed_rolling_mean"] = (
    group["speed_normalized"]
    .rolling(
        10,
        min_periods=1
    )
    .mean()
    .reset_index(
        level=0,
        drop=True
    )
)

df["acceleration_rolling_mean"] = (
    group["acceleration"]
    .rolling(
        10,
        min_periods=1
    )
    .mean()
    .reset_index(
        level=0,
        drop=True
    )
)

df["anomaly_rolling_mean"] = (
    group["behavior_anomaly_score"]
    .rolling(
        10,
        min_periods=1
    )
    .mean()
    .reset_index(
        level=0,
        drop=True
    )

)

# =========================================================
# DYNAMIC FRAME-LEVEL RISK SCORE
# =========================================================

# Convert Day 7 vehicle-level threat score
# into a normalized baseline.

baseline_risk = (
    df["threat_score"] / 40.0
).clip(0, 1)

# Dynamic behavior risk.

behavior_risk = (
    0.30 * df["behavior_anomaly_norm"]
    + 0.15 * df["speed_anomaly_norm"]
    + 0.15 * df["acceleration_anomaly_norm"]
    + 0.15 * df["direction_anomaly_norm"]
    + 0.10 * df["sudden_acceleration_norm"]
    + 0.05 * df["slow_stopped_norm"]
    + 0.10 * df["direction_change_norm"]
)

behavior_risk = behavior_risk.clip(0, 1)

# Combine static intelligence with
# frame-level temporal behavior.

df["dynamic_risk_score"] = (
    40.0 *
    (
        0.45 * baseline_risk
        + 0.55 * behavior_risk
    )
).clip(0, 40)

# =========================================================
# TEMPORAL RISK TREND
# =========================================================

df["risk_trend"] = (
    group["dynamic_risk_score"]
    .diff(10)
    .fillna(0)
)

df["risk_increasing"] = (
    df["risk_trend"] > 1.0
).astype(int)

# =========================================================
# FUTURE RISK TARGET
# =========================================================

FUTURE_HORIZON = 15

df["future_threat_score"] = (
    group["dynamic_risk_score"]
    .shift(-FUTURE_HORIZON)
)

# =========================================================
# REMOVE INVALID FUTURE WINDOWS
# =========================================================

valid = (
    df.groupby("track_id")["frame"]
    .transform("max")
    - df["frame"]
) >= FUTURE_HORIZON

temporal = df[valid].copy()

# =========================================================
# FUTURE RISK CHANGE
# =========================================================

temporal["future_risk_increase"] = (
    temporal["future_threat_score"]
    - temporal["dynamic_risk_score"]
)

# =========================================================
# EARLY WARNING TARGET
# =========================================================

temporal["early_warning"] = (
    temporal["future_risk_increase"] >= 3.0
).astype(int)

# =========================================================
# TEMPORAL STATE
# =========================================================

def temporal_state(row):

    increase = row["future_risk_increase"]

    if increase >= 10:
        return "RAPID_ESCALATION"

    elif increase >= 3:
        return "ESCALATING"

    elif increase <= -3:
        return "DE_ESCALATING"

    else:
        return "STABLE"


temporal["temporal_state"] = (
    temporal.apply(
        temporal_state,
        axis=1
    )
)

# =========================================================
# DYNAMIC RISK LEVEL
# =========================================================

def dynamic_risk_level(score):

    if score >= 30:
        return "CRITICAL"

    elif score >= 20:
        return "HIGH"

    elif score >= 10:
        return "SUSPICIOUS"

    elif score >= 5:
        return "WATCH"

    else:
        return "SAFE"


temporal["dynamic_risk_level"] = (
    temporal["dynamic_risk_score"]
    .apply(dynamic_risk_level)
)

# =========================================================
# RISK ROLLING MEAN
# =========================================================

temporal["risk_rolling_mean"] = (
    temporal
    .groupby("track_id")["dynamic_risk_score"]
    .rolling(
        10,
        min_periods=1
    )
    .mean()
    .reset_index(
        level=0,
        drop=True
    )
)

# =========================================================
# FINAL DATASET
# =========================================================

columns = [

    # Identity
    "frame",
    "track_id",

    # Bounding box
    "center_x",
    "center_y",
    "width",
    "height",

    # Motion
    "speed_normalized",
    "acceleration",
    "direction_deg",
    "displacement",

    # Temporal motion
    "speed_change",
    "acceleration_change",
    "direction_change",
    "position_change",

    # Rolling behavior
    "speed_rolling_mean",
    "acceleration_rolling_mean",
    "anomaly_rolling_mean",

    # Behavior signals
    "behavior_anomaly_score",
    "speed_anomaly",
    "acceleration_anomaly",
    "direction_anomaly",
    "sudden_acceleration",
    "slow_or_stopped",

    # Day 7 intelligence
    "threat_score",
    "threat_level",
    "priority",

    # Dynamic temporal intelligence
    "dynamic_risk_score",
    "dynamic_risk_level",
    "risk_rolling_mean",
    "risk_trend",
    "risk_increasing",

    # Future target
    "future_threat_score",
    "future_risk_increase",
    "early_warning",

    # Temporal state
    "temporal_state"
]

temporal = temporal[columns].replace(
    [np.inf, -np.inf],
    np.nan
).dropna()

# =========================================================
# SAVE DATASET
# =========================================================

temporal.to_csv(
    OUTPUT_DATASET,
    index=False,
    float_format="%.5f"
)

# =========================================================
# STATISTICS
# =========================================================

with OUTPUT_STATS.open("w") as f:

    f.write(
        "==============================================\n"
    )

    f.write(
        "BORDER-AI DAY 8 TEMPORAL DATASET\n"
    )

    f.write(
        "DYNAMIC RISK + EARLY WARNING\n"
    )

    f.write(
        "==============================================\n\n"
    )

    f.write(
        f"Original observations: {len(df)}\n"
    )

    f.write(
        f"Temporal observations: {len(temporal)}\n"
    )

    f.write(
        f"Vehicles: {temporal['track_id'].nunique()}\n"
    )

    f.write(
        f"Frames: {temporal['frame'].nunique()}\n"
    )

    f.write(
        f"Future horizon: {FUTURE_HORIZON} frames\n\n"
    )

    f.write(
        "EARLY WARNING TARGET\n"
    )

    f.write(
        "--------------------\n"
    )

    f.write(
        temporal["early_warning"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    f.write("\n\n")

    f.write(
        "TEMPORAL STATE\n"
    )

    f.write(
        "--------------\n"
    )

    f.write(
        temporal["temporal_state"]
        .value_counts()
        .to_string()
    )

    f.write("\n\n")

    f.write(
        "DYNAMIC RISK LEVEL\n"
    )

    f.write(
        "------------------\n"
    )

    f.write(
        temporal["dynamic_risk_level"]
        .value_counts()
        .to_string()
    )

    f.write("\n\n")

    f.write(
        "DYNAMIC RISK STATISTICS\n"
    )

    f.write(
        "-----------------------\n"
    )

    f.write(
        temporal["dynamic_risk_score"]
        .describe()
        .to_string()
    )

    f.write("\n\n")

    f.write(
        "RISK TREND STATISTICS\n"
    )

    f.write(
        "---------------------\n"
    )

    f.write(
        temporal["risk_trend"]
        .describe()
        .to_string()
    )

    f.write("\n\n")

    f.write(
        "FUTURE RISK CHANGE STATISTICS\n"
    )

    f.write(
        "-----------------------------\n"
    )

    f.write(
        temporal["future_risk_increase"]
        .describe()
        .to_string()
    )

# =========================================================
# CONSOLE SUMMARY
# =========================================================

print()
print(
    "=============================================="
)

print(
    "DAY 8 TEMPORAL DATASET COMPLETE"
)

print(
    "DYNAMIC RISK + EARLY WARNING"
)

print(
    "=============================================="
)

print(
    f"Original observations: {len(df)}"
)

print(
    f"Temporal observations: {len(temporal)}"
)

print(
    f"Vehicles:              {temporal['track_id'].nunique()}"
)

print(
    f"Frames:                {temporal['frame'].nunique()}"
)

print()
print(
    "Dynamic risk range:"
)

print(
    f"  {temporal['dynamic_risk_score'].min():.2f}"
    f" -> "
    f"{temporal['dynamic_risk_score'].max():.2f}"
)

print()
print(
    "Early-warning target:"
)

print(
    temporal["early_warning"]
    .value_counts()
    .sort_index()
)

print()
print(
    "Temporal states:"
)

print(
    temporal["temporal_state"]
    .value_counts()
)

print()
print(
    "Dynamic risk levels:"
)

print(
    temporal["dynamic_risk_level"]
    .value_counts()
)

print()
print(
    "Risk trend statistics:"
)

print(
    temporal["risk_trend"]
    .describe()
)

print()
print(
    "Output:"
)

print(
    OUTPUT_DATASET
)

print(
    OUTPUT_STATS
)

print(
    "=============================================="
)
