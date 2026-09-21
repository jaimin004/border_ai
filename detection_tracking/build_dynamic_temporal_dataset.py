from pathlib import Path
import pandas as pd
import numpy as np

# =========================================================
# BORDER-AI
# DAY 8.1 — DYNAMIC TEMPORAL RISK DATASET
# =========================================================

INPUT = Path(
    "data/outputs/day6_behavior_analysis/day6_behavior_analysis.csv"
)

RISK_INPUT = Path(
    "data/outputs/day7_risk_intelligence/day7_vehicle_risk_intelligence.csv"
)

OUTPUT_DIR = Path(
    "data/outputs/day8_temporal_prediction_v2"
)

OUTPUT_DATASET = OUTPUT_DIR / "day8_dynamic_temporal_dataset.csv"
OUTPUT_STATS = OUTPUT_DIR / "day8_dynamic_temporal_statistics.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print()
print("==============================================")
print("BORDER-AI DAY 8.1")
print("DYNAMIC TEMPORAL RISK DATASET")
print("==============================================")

# =========================================================
# LOAD DATA
# =========================================================

df = pd.read_csv(INPUT)
risk = pd.read_csv(RISK_INPUT)

print("Behavior observations:", len(df))
print("Behavior vehicles:", df["track_id"].nunique())

# =========================================================
# MERGE VEHICLE-LEVEL RISK
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

# =========================================================
# SORT TEMPORALLY
# =========================================================

df = df.sort_values(
    ["track_id", "frame"]
).reset_index(drop=True)

group = df.groupby(
    "track_id",
    group_keys=False
)

# =========================================================
# CLEAN INPUT FEATURES
# =========================================================

numeric_columns = [
    "speed_normalized",
    "acceleration",
    "displacement",
    "behavior_anomaly_score",
    "direction_change",
    "slow_or_stopped",
    "sudden_acceleration",
    "threat_score"
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

# =========================================================
# FRAME-LEVEL TEMPORAL CHANGES
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

df["direction_change_delta"] = (
    group["direction_change"]
    .diff()
    .abs()
    .fillna(0)
)

df["position_change"] = np.sqrt(
    df["dx"].fillna(0) ** 2
    +
    df["dy"].fillna(0) ** 2
)

# =========================================================
# ABSOLUTE TEMPORAL FEATURES
# =========================================================

df["speed_change_abs"] = (
    df["speed_change"].abs()
)

df["acceleration_abs"] = (
    df["acceleration"].abs()
)

df["direction_change_abs"] = (
    df["direction_change"].abs()
)

# =========================================================
# ROLLING FEATURES
# =========================================================

df["speed_rolling_mean"] = (
    group["speed_normalized"]
    .rolling(
        10,
        min_periods=1
    )
    .mean()
    .reset_index(level=0, drop=True)
)

df["acceleration_rolling_mean"] = (
    group["acceleration"]
    .rolling(
        10,
        min_periods=1
    )
    .mean()
    .reset_index(level=0, drop=True)
)

df["anomaly_rolling_mean"] = (
    group["behavior_anomaly_score"]
    .rolling(
        10,
        min_periods=1
    )
    .mean()
    .reset_index(level=0, drop=True)
)

df["direction_rolling_mean"] = (
    group["direction_change"]
    .rolling(
        10,
        min_periods=1
    )
    .mean()
    .reset_index(level=0, drop=True)
)

# =========================================================
# PERSISTENCE
# =========================================================

df["track_age"] = (
    group.cumcount() + 1
)

df["persistent_track"] = (
    df["track_age"] >= 30
).astype(int)

# =========================================================
# NORMALIZATION HELPERS
# =========================================================

def robust_normalize(series):
    series = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)

    low = series.quantile(0.05)
    high = series.quantile(0.95)

    if high <= low:
        return pd.Series(
            np.zeros(len(series)),
            index=series.index
        )

    result = (
        (series - low)
        /
        (high - low)
    )

    return result.clip(0, 1)


# =========================================================
# DYNAMIC COMPONENT SCORES
# =========================================================

df["speed_risk"] = robust_normalize(
    df["speed_normalized"]
)

df["acceleration_risk"] = robust_normalize(
    df["acceleration_abs"]
)

df["direction_risk"] = robust_normalize(
    df["direction_change_abs"]
)

df["anomaly_risk"] = robust_normalize(
    df["behavior_anomaly_score"]
)

df["stop_risk"] = (
    df["slow_or_stopped"]
    .clip(0, 1)
)

df["sudden_acceleration_risk"] = (
    df["sudden_acceleration"]
    .clip(0, 1)
)

df["base_vehicle_risk"] = (
    robust_normalize(
        df["threat_score"]
    )
)

# =========================================================
# DYNAMIC TEMPORAL RISK SCORE
# =========================================================
#
# Important:
# Day 7 threat_score is only a vehicle-level prior.
# This score changes from frame to frame.
#
# =========================================================

df["dynamic_risk_raw"] = (
      0.20 * df["speed_risk"]
    + 0.20 * df["acceleration_risk"]
    + 0.20 * df["direction_risk"]
    + 0.20 * df["anomaly_risk"]
    + 0.05 * df["stop_risk"]
    + 0.05 * df["sudden_acceleration_risk"]
    + 0.10 * df["base_vehicle_risk"]
)

# Convert to 0–100
df["dynamic_risk_score"] = (
    df["dynamic_risk_raw"] * 100
)

# =========================================================
# TEMPORAL RISK TREND
# =========================================================

df["risk_trend_5"] = (
    group["dynamic_risk_score"]
    .diff(5)
    .fillna(0)
)

df["risk_trend_10"] = (
    group["dynamic_risk_score"]
    .diff(10)
    .fillna(0)
)

df["risk_velocity"] = (
    group["dynamic_risk_score"]
    .diff()
    .fillna(0)
)

# =========================================================
# ROLLING DYNAMIC RISK
# =========================================================

df["dynamic_risk_rolling_mean"] = (
    group["dynamic_risk_score"]
    .rolling(
        10,
        min_periods=1
    )
    .mean()
    .reset_index(level=0, drop=True)
)

df["dynamic_risk_rolling_std"] = (
    group["dynamic_risk_score"]
    .rolling(
        10,
        min_periods=2
    )
    .std()
    .reset_index(level=0, drop=True)
    .fillna(0)
)

# =========================================================
# FUTURE RISK TARGET
# =========================================================

# 15 frames ≈ 0.5 seconds at 30 FPS
FUTURE_FRAMES = 15

df["future_dynamic_risk"] = (
    group["dynamic_risk_score"]
    .shift(-FUTURE_FRAMES)
)

# =========================================================
# FUTURE RISK CHANGE
# =========================================================

df["future_risk_increase"] = (
    df["future_dynamic_risk"]
    -
    df["dynamic_risk_score"]
)

# =========================================================
# EARLY WARNING TARGET
# =========================================================

df["early_warning"] = (
    df["future_risk_increase"] >= 5
).astype(int)

# =========================================================
# TEMPORAL STATE
# =========================================================

def get_temporal_state(row):

    increase = row["future_risk_increase"]

    if increase >= 15:
        return "RAPID_ESCALATION"

    elif increase >= 5:
        return "ESCALATING"

    elif increase <= -5:
        return "DE_ESCALATING"

    else:
        return "STABLE"


df["temporal_state"] = (
    df.apply(
        get_temporal_state,
        axis=1
    )
)

# =========================================================
# CURRENT DYNAMIC RISK LEVEL
# =========================================================

def get_dynamic_risk_level(score):

    if score >= 75:
        return "CRITICAL"

    elif score >= 55:
        return "HIGH"

    elif score >= 35:
        return "SUSPICIOUS"

    elif score >= 20:
        return "WATCH"

    else:
        return "SAFE"


df["dynamic_risk_level"] = (
    df["dynamic_risk_score"]
    .apply(get_dynamic_risk_level)
)

# =========================================================
# REMOVE INVALID FUTURE WINDOWS
# =========================================================

last_frame = (
    group["frame"]
    .transform("max")
)

valid = (
    (last_frame - df["frame"])
    >= FUTURE_FRAMES
)

temporal = df[valid].copy()

# =========================================================
# FINAL DATASET
# =========================================================

columns = [
    "frame",
    "track_id",

    "center_x",
    "center_y",
    "width",
    "height",

    "speed_normalized",
    "acceleration",
    "displacement",
    "direction_deg",

    "speed_change",
    "acceleration_change",
    "direction_change_delta",
    "position_change",

    "speed_rolling_mean",
    "acceleration_rolling_mean",
    "anomaly_rolling_mean",
    "direction_rolling_mean",

    "behavior_anomaly_score",
    "slow_or_stopped",
    "sudden_acceleration",

    "threat_score",
    "threat_level",
    "priority",

    "dynamic_risk_score",
    "dynamic_risk_level",

    "risk_trend_5",
    "risk_trend_10",
    "risk_velocity",

    "dynamic_risk_rolling_mean",
    "dynamic_risk_rolling_std",

    "future_dynamic_risk",
    "future_risk_increase",

    "early_warning",
    "temporal_state",

    "track_age",
    "persistent_track"
]

# Keep only columns that actually exist
columns = [
    col
    for col in columns
    if col in temporal.columns
]

temporal = temporal[columns]

temporal = temporal.replace(
    [np.inf, -np.inf],
    np.nan
)

temporal = temporal.dropna(
    subset=[
        "dynamic_risk_score",
        "future_dynamic_risk",
        "future_risk_increase"
    ]
)

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

stats = []

stats.append(
    "=============================================="
)

stats.append(
    "BORDER-AI DAY 8.1 DYNAMIC TEMPORAL DATASET"
)

stats.append(
    "=============================================="
)

stats.append("")

stats.append(
    f"Original observations: {len(df)}"
)

stats.append(
    f"Temporal observations: {len(temporal)}"
)

stats.append(
    f"Vehicles: {temporal['track_id'].nunique()}"
)

stats.append(
    f"Frames: {temporal['frame'].nunique()}"
)

stats.append("")

stats.append(
    "DYNAMIC RISK SCORE"
)

stats.append(
    "------------------"
)

stats.append(
    f"Minimum: {temporal['dynamic_risk_score'].min():.4f}"
)

stats.append(
    f"Maximum: {temporal['dynamic_risk_score'].max():.4f}"
)

stats.append(
    f"Mean: {temporal['dynamic_risk_score'].mean():.4f}"
)

stats.append(
    f"Std: {temporal['dynamic_risk_score'].std():.4f}"
)

stats.append("")

stats.append(
    "DYNAMIC RISK LEVEL"
)

stats.append(
    "------------------"
)

stats.append(
    temporal["dynamic_risk_level"]
    .value_counts()
    .to_string()
)

stats.append("")

stats.append(
    "EARLY WARNING TARGET"
)

stats.append(
    "--------------------"
)

stats.append(
    temporal["early_warning"]
    .value_counts()
    .sort_index()
    .to_string()
)

stats.append("")

stats.append(
    "TEMPORAL STATE"
)

stats.append(
    "--------------"
)

stats.append(
    temporal["temporal_state"]
    .value_counts()
    .to_string()
)

stats.append("")

stats.append(
    "RISK TREND"
)

stats.append(
    "----------"
)

stats.append(
    temporal["risk_trend_10"]
    .describe()
    .to_string()
)

stats.append("")

stats.append(
    "EARLY WARNING RATE"
)

stats.append(
    "------------------"
)

stats.append(
    f"{temporal['early_warning'].mean() * 100:.2f}%"
)

stats.append("")

stats.append(
    f"Future horizon: {FUTURE_FRAMES} frames"
)

stats.append(
    "At 30 FPS: approximately 0.5 seconds"
)

stats.append("")

stats.append(
    f"Output: {OUTPUT_DATASET}"
)

OUTPUT_STATS.write_text(
    "\n".join(stats)
)

# =========================================================
# CONSOLE SUMMARY
# =========================================================

print()
print("==============================================")
print("DAY 8.1 DYNAMIC TEMPORAL DATASET COMPLETE")
print("==============================================")

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
print("Dynamic risk score:")
print(
    f"  Minimum: {temporal['dynamic_risk_score'].min():.2f}"
)
print(
    f"  Maximum: {temporal['dynamic_risk_score'].max():.2f}"
)
print(
    f"  Mean:    {temporal['dynamic_risk_score'].mean():.2f}"
)

print()
print("Dynamic risk levels:")
print(
    temporal["dynamic_risk_level"]
    .value_counts()
    .to_string()
)

print()
print("Early-warning target:")
print(
    temporal["early_warning"]
    .value_counts()
    .sort_index()
    .to_string()
)

print()
print("Temporal states:")
print(
    temporal["temporal_state"]
    .value_counts()
    .to_string()
)

print()
print(
    f"Early-warning rate: "
    f"{temporal['early_warning'].mean() * 100:.2f}%"
)

print()
print("Outputs:")
print(f"  {OUTPUT_DATASET}")
print(f"  {OUTPUT_STATS}")

print()
print("==============================================")
