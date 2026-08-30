from pathlib import Path
import pandas as pd
import numpy as np

INPUT = Path("data/outputs/day6_behavior_analysis/day6_behavior_summary.csv")
OUTPUT_DIR = Path("data/outputs/day7_risk_intelligence")

OUTPUT_SUMMARY = OUTPUT_DIR / "day7_vehicle_risk_intelligence.csv"
OUTPUT_RANKING = OUTPUT_DIR / "day7_threat_ranking.csv"
OUTPUT_STATS = OUTPUT_DIR / "day7_risk_statistics.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT)

def normalize(series):
    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(0.0, index=series.index)

    return ((series - minimum) / (maximum - minimum) * 100.0).clip(0, 100)


# ---------------------------------------------------------
# COMPONENT SCORES
# ---------------------------------------------------------

df["anomaly_score"] = (
    df["anomaly_max"].fillna(0).clip(0, 100)
)

df["event_score"] = (
    normalize(df["anomaly_events"])
)

df["movement_score"] = (
    0.40 * normalize(df["max_speed"]) +
    0.30 * normalize(df["max_acceleration"]) +
    0.30 * normalize(df["max_direction_change"])
).clip(0, 100)

df["persistence_score"] = (
    normalize(df["observations"])
)

df["stopped_behavior_score"] = (
    normalize(df["slow_stopped_frames"])
)

df["behavior_score"] = (
    0.45 * df["vehicle_risk_score"].fillna(0) +
    0.35 * df["anomaly_mean"].fillna(0) +
    0.20 * df["anomaly_max"].fillna(0)
).clip(0, 100)


# ---------------------------------------------------------
# FINAL THREAT SCORE
# ---------------------------------------------------------

df["threat_score"] = (
    0.35 * df["behavior_score"] +
    0.20 * df["anomaly_score"] +
    0.15 * df["event_score"] +
    0.15 * df["movement_score"] +
    0.10 * df["persistence_score"] +
    0.05 * df["stopped_behavior_score"]
).clip(0, 100)


# ---------------------------------------------------------
# THREAT LEVEL
# ---------------------------------------------------------

def threat_level(score):
    if score >= 85:
        return "CRITICAL"
    elif score >= 70:
        return "HIGH THREAT"
    elif score >= 50:
        return "SUSPICIOUS"
    elif score >= 30:
        return "WATCH"
    else:
        return "SAFE"


df["threat_level"] = df["threat_score"].apply(threat_level)


# ---------------------------------------------------------
# PRIORITY
# ---------------------------------------------------------

def priority(level):
    mapping = {
        "CRITICAL": 1,
        "HIGH THREAT": 2,
        "SUSPICIOUS": 3,
        "WATCH": 4,
        "SAFE": 5,
    }

    return mapping[level]


df["priority"] = df["threat_level"].apply(priority)


# ---------------------------------------------------------
# WHY IS THIS VEHICLE HIGH RISK?
# ---------------------------------------------------------

def generate_reason(row):
    reasons = []

    if row["anomaly_max"] >= 70:
        reasons.append("high anomaly")

    if row["anomaly_events"] >= 3:
        reasons.append("repeated anomalies")

    if row["max_direction_change"] >= 45:
        reasons.append("large direction change")

    if row["max_acceleration"] >= 1:
        reasons.append("high acceleration")

    if row["slow_stopped_frames"] >= 5:
        reasons.append("prolonged stop")

    if row["observations"] >= 80:
        reasons.append("persistent track")

    if not reasons:
        reasons.append("low-risk behavior")

    return ", ".join(reasons)


df["risk_reason"] = df.apply(generate_reason, axis=1)


# ---------------------------------------------------------
# FINAL OUTPUT COLUMNS
# ---------------------------------------------------------

output_columns = [
    "track_id",
    "observations",
    "mean_speed",
    "max_speed",
    "mean_acceleration",
    "max_acceleration",
    "max_direction_change",
    "anomaly_mean",
    "anomaly_max",
    "anomaly_events",
    "slow_stopped_frames",
    "vehicle_risk_score",
    "risk_level",
    "behavior_score",
    "anomaly_score",
    "event_score",
    "movement_score",
    "persistence_score",
    "stopped_behavior_score",
    "threat_score",
    "threat_level",
    "priority",
    "risk_reason",
]

risk_df = df[output_columns].copy()

risk_df = risk_df.sort_values(
    ["priority", "threat_score", "track_id"],
    ascending=[True, False, True]
).reset_index(drop=True)


# ---------------------------------------------------------
# THREAT RANK
# ---------------------------------------------------------

risk_df.insert(0, "threat_rank", range(1, len(risk_df) + 1))


# ---------------------------------------------------------
# SAVE SUMMARY
# ---------------------------------------------------------

risk_df.to_csv(
    OUTPUT_SUMMARY,
    index=False,
    float_format="%.4f"
)


# ---------------------------------------------------------
# THREAT RANKING
# ---------------------------------------------------------

ranking_columns = [
    "threat_rank",
    "track_id",
    "threat_score",
    "threat_level",
    "priority",
    "risk_reason",
    "observations",
    "anomaly_events",
    "max_speed",
    "max_acceleration",
    "max_direction_change",
]

risk_df[ranking_columns].to_csv(
    OUTPUT_RANKING,
    index=False,
    float_format="%.4f"
)


# ---------------------------------------------------------
# STATISTICS REPORT
# ---------------------------------------------------------

level_counts = (
    risk_df["threat_level"]
    .value_counts()
    .reindex(
        ["CRITICAL", "HIGH THREAT", "SUSPICIOUS", "WATCH", "SAFE"],
        fill_value=0
    )
)

top = risk_df.iloc[0]

with OUTPUT_STATS.open("w") as f:
    f.write("==============================================\n")
    f.write("BORDER-AI DAY 7 RISK INTELLIGENCE REPORT\n")
    f.write("==============================================\n\n")

    f.write(f"Vehicles analyzed: {len(risk_df)}\n")
    f.write(f"Average threat score: {risk_df['threat_score'].mean():.2f}\n")
    f.write(f"Maximum threat score: {risk_df['threat_score'].max():.2f}\n")
    f.write(f"Minimum threat score: {risk_df['threat_score'].min():.2f}\n\n")

    f.write("THREAT DISTRIBUTION\n")
    f.write("-------------------\n")

    for level, count in level_counts.items():
        f.write(f"{level}: {count}\n")

    f.write("\nHIGHEST PRIORITY VEHICLE\n")
    f.write("------------------------\n")
    f.write(f"Rank: {top['threat_rank']}\n")
    f.write(f"Track ID: {top['track_id']}\n")
    f.write(f"Threat Score: {top['threat_score']:.2f}\n")
    f.write(f"Threat Level: {top['threat_level']}\n")
    f.write(f"Risk Reason: {top['risk_reason']}\n")

print()
print("==============================================")
print("DAY 7 RISK INTELLIGENCE COMPLETE")
print("==============================================")
print(f"Input:                 {INPUT}")
print(f"Vehicles analyzed:    {len(risk_df)}")
print()
print("Threat distribution:")

for level, count in level_counts.items():
    print(f"  {level:<15}: {count}")

print()
print(f"Average threat score:  {risk_df['threat_score'].mean():.2f}")
print(f"Maximum threat score:  {risk_df['threat_score'].max():.2f}")
print()
print("Highest priority vehicle:")
print(f"  Track ID:            {top['track_id']}")
print(f"  Threat Score:        {top['threat_score']:.2f}")
print(f"  Threat Level:        {top['threat_level']}")
print(f"  Reason:              {top['risk_reason']}")
print()
print("Outputs:")
print(f"  {OUTPUT_SUMMARY}")
print(f"  {OUTPUT_RANKING}")
print(f"  {OUTPUT_STATS}")
print()
print("==============================================")
