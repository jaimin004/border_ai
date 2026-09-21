from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# BORDER-AI DAY 11
# EXPLAINABLE TEMPORAL ALERT ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DAY10_DIR = BASE_DIR / "data" / "outputs" / "day10_temporal_inference"
DAY8_DIR = BASE_DIR / "data" / "outputs" / "day8_temporal_prediction"

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "outputs"
    / "day11_explainable_alerts"
)

DAY10_PREDICTIONS = (
    DAY10_DIR / "day10_temporal_predictions.csv"
)

DAY8_DATASET = (
    DAY8_DIR / "day8_temporal_dataset.csv"
)

ALERT_FILE = (
    OUTPUT_DIR / "day11_explainable_alerts.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "day11_alert_summary.csv"
)

STATISTICS_FILE = (
    OUTPUT_DIR / "day11_statistics.txt"
)


# ============================================================
# CONFIGURATION
# ============================================================

HIGH_PROBABILITY = 0.75
WATCH_PROBABILITY = 0.50

HIGH_RISK_SCORE = 20.0
WATCH_RISK_SCORE = 15.0

TOP_EVIDENCE_COUNT = 5


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    print()
    print("=" * 60)
    print("BORDER-AI DAY 11 EXPLAINABLE ALERT ENGINE")
    print("=" * 60)

    print()
    print("LOADING DAY 10 TEMPORAL PREDICTIONS")
    print("-" * 60)

    if not DAY10_PREDICTIONS.exists():
        raise FileNotFoundError(
            f"Day 10 predictions not found:\n{DAY10_PREDICTIONS}"
        )

    predictions = pd.read_csv(DAY10_PREDICTIONS)

    print(f"Prediction rows: {len(predictions)}")

    print()
    print("LOADING DAY 8 TEMPORAL FEATURES")
    print("-" * 60)

    if not DAY8_DATASET.exists():
        raise FileNotFoundError(
            f"Day 8 dataset not found:\n{DAY8_DATASET}"
        )

    temporal = pd.read_csv(DAY8_DATASET)

    print(f"Day 8 rows:      {len(temporal)}")

    return predictions, temporal


# ============================================================
# NUMERIC HELPERS
# ============================================================

def numeric_value(row, column, default=np.nan):
    if column not in row.index:
        return default

    value = row[column]

    try:
        value = float(value)

        if np.isnan(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def binary_value(row, column):
    value = numeric_value(row, column, 0.0)

    if np.isnan(value):
        return 0

    return int(value >= 0.5)


# ============================================================
# QUANTILE THRESHOLDS
# ============================================================

def calculate_thresholds(dataset):
    thresholds = {}

    percentile_features = [
        "dynamic_risk_score",
        "behavior_anomaly_score",
        "speed_anomaly",
        "acceleration_anomaly",
        "direction_anomaly",
        "speed_change",
        "acceleration_change",
        "direction_change",
        "position_change",
        "risk_trend",
    ]

    for feature in percentile_features:

        if feature not in dataset.columns:
            continue

        values = pd.to_numeric(
            dataset[feature],
            errors="coerce",
        ).dropna()

        if len(values) == 0:
            continue

        thresholds[feature] = {
            "p75": float(values.quantile(0.75)),
            "p90": float(values.quantile(0.90)),
            "p95": float(values.quantile(0.95)),
        }

    return thresholds


# ============================================================
# BUILD EXPLANATION
# ============================================================

def build_explanation(row, thresholds):
    evidence = []

    probability = numeric_value(
        row,
        "prediction_probability",
        0.0,
    )

    risk_score = numeric_value(
        row,
        "dynamic_risk_score",
        np.nan,
    )

    risk_trend = numeric_value(
        row,
        "risk_trend",
        np.nan,
    )

    risk_increasing = binary_value(
        row,
        "risk_increasing",
    )

    sudden_acceleration = binary_value(
        row,
        "sudden_acceleration",
    )

    slow_or_stopped = binary_value(
        row,
        "slow_or_stopped",
    )

    behavior_score = numeric_value(
        row,
        "behavior_anomaly_score",
        np.nan,
    )

    speed_anomaly = numeric_value(
        row,
        "speed_anomaly",
        np.nan,
    )

    acceleration_anomaly = numeric_value(
        row,
        "acceleration_anomaly",
        np.nan,
    )

    direction_anomaly = numeric_value(
        row,
        "direction_anomaly",
        np.nan,
    )

    # --------------------------------------------------------
    # MODEL EVIDENCE
    # --------------------------------------------------------

    if probability >= HIGH_PROBABILITY:

        evidence.append(
            (
                100,
                f"GRU early-warning probability is high "
                f"({probability:.3f})"
            )
        )

    elif probability >= WATCH_PROBABILITY:

        evidence.append(
            (
                70,
                f"GRU early-warning probability is elevated "
                f"({probability:.3f})"
            )
        )

    # --------------------------------------------------------
    # DYNAMIC RISK
    # --------------------------------------------------------

    if not np.isnan(risk_score):

        if risk_score >= HIGH_RISK_SCORE:

            evidence.append(
                (
                    95,
                    f"Dynamic risk score is high "
                    f"({risk_score:.2f})"
                )
            )

        elif risk_score >= WATCH_RISK_SCORE:

            evidence.append(
                (
                    70,
                    f"Dynamic risk score is elevated "
                    f"({risk_score:.2f})"
                )
            )

        elif (
            "dynamic_risk_score" in thresholds
            and risk_score >= thresholds["dynamic_risk_score"]["p90"]
        ):

            evidence.append(
                (
                    85,
                    f"Dynamic risk score is in the upper "
                    f"10% of observed values ({risk_score:.2f})"
                )
            )

    # --------------------------------------------------------
    # RISK TREND
    # --------------------------------------------------------

    if risk_increasing == 1:

        evidence.append(
            (
                90,
                "Risk is currently increasing"
            )
        )

    if (
        not np.isnan(risk_trend)
        and "risk_trend" in thresholds
        and risk_trend >= thresholds["risk_trend"]["p90"]
    ):

        evidence.append(
            (
                88,
                f"Risk trend is strongly positive "
                f"({risk_trend:.2f})"
            )
        )

    # --------------------------------------------------------
    # BEHAVIOR ANOMALY
    # --------------------------------------------------------

    if (
        not np.isnan(behavior_score)
        and "behavior_anomaly_score" in thresholds
        and behavior_score >= thresholds["behavior_anomaly_score"]["p90"]
    ):

        evidence.append(
            (
                82,
                f"Behavior anomaly score is unusually high "
                f"({behavior_score:.3f})"
            )
        )

    # --------------------------------------------------------
    # MOTION ANOMALIES
    # --------------------------------------------------------

    if (
        not np.isnan(speed_anomaly)
        and "speed_anomaly" in thresholds
        and speed_anomaly >= thresholds["speed_anomaly"]["p90"]
    ):

        evidence.append(
            (
                75,
                "Unusual speed behavior detected"
            )
        )

    if (
        not np.isnan(acceleration_anomaly)
        and "acceleration_anomaly" in thresholds
        and acceleration_anomaly >= thresholds["acceleration_anomaly"]["p90"]
    ):

        evidence.append(
            (
                78,
                "Unusual acceleration behavior detected"
            )
        )

    if (
        not np.isnan(direction_anomaly)
        and "direction_anomaly" in thresholds
        and direction_anomaly >= thresholds["direction_anomaly"]["p90"]
    ):

        evidence.append(
            (
                76,
                "Unusual direction-change behavior detected"
            )
        )

    if sudden_acceleration == 1:

        evidence.append(
            (
                80,
                "Sudden acceleration event detected"
            )
        )

    if slow_or_stopped == 1:

        evidence.append(
            (
                65,
                "Vehicle is slow or temporarily stopped"
            )
        )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if not evidence:

        evidence.append(
            (
                10,
                "No strong individual anomaly feature identified"
            )
        )

    evidence.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    top_evidence = evidence[:TOP_EVIDENCE_COUNT]

    explanation = " | ".join(
        item[1]
        for item in top_evidence
    )

    evidence_scores = "; ".join(
        str(item[0])
        for item in top_evidence
    )

    return explanation, evidence_scores, top_evidence


# ============================================================
# CLASSIFY ALERT
# ============================================================

def classify_alert(probability, risk_score):
    if probability >= HIGH_PROBABILITY:

        if (
            not np.isnan(risk_score)
            and risk_score >= HIGH_RISK_SCORE
        ):
            return "CRITICAL"

        return "HIGH"

    if probability >= WATCH_PROBABILITY:
        return "WATCH"

    if (
        not np.isnan(risk_score)
        and risk_score >= HIGH_RISK_SCORE
    ):
        return "HIGH"

    if (
        not np.isnan(risk_score)
        and risk_score >= WATCH_RISK_SCORE
    ):
        return "WATCH"

    return "LOW"


# ============================================================
# MERGE DAY 8 + DAY 10
# ============================================================

def merge_features(predictions, temporal):
    merge_columns = [
        "track_id",
        "frame",
    ]

    available = [
        column
        for column in merge_columns
        if column in predictions.columns
        and column in temporal.columns
    ]

    if len(available) != 2:
        raise ValueError(
            "Unable to merge Day 8 and Day 10 data. "
            "Both track_id and frame are required."
        )

    feature_columns = [
        "dynamic_risk_score",
        "risk_rolling_mean",
        "risk_trend",
        "risk_increasing",
        "behavior_anomaly_score",
        "speed_anomaly",
        "acceleration_anomaly",
        "direction_anomaly",
        "sudden_acceleration",
        "slow_or_stopped",
        "speed_change",
        "acceleration_change",
        "direction_change",
        "position_change",
    ]

    feature_columns = [
        column
        for column in feature_columns
        if column in temporal.columns
    ]

    temporal_subset = temporal[
        available + feature_columns
    ].copy()

    temporal_subset = temporal_subset.drop_duplicates(
        subset=available,
        keep="last",
    )

    merged = predictions.merge(
        temporal_subset,
        on=available,
        how="left",
        suffixes=("", "_day8"),
    )

    # If prediction already contains a column, preserve it.
    # Otherwise use the Day 8 value.
    for column in feature_columns:

        day8_column = f"{column}_day8"

        if column not in merged.columns:
            if day8_column in merged.columns:
                merged[column] = merged[day8_column]

        elif day8_column in merged.columns:

            merged[column] = merged[column].fillna(
                merged[day8_column]
            )

    drop_columns = [
        f"{column}_day8"
        for column in feature_columns
        if f"{column}_day8" in merged.columns
    ]

    if drop_columns:
        merged = merged.drop(
            columns=drop_columns
        )

    return merged


# ============================================================
# BUILD EXPLAINABLE ALERTS
# ============================================================

def build_alerts(data, thresholds):
    records = []

    for _, row in data.iterrows():

        probability = numeric_value(
            row,
            "prediction_probability",
            0.0,
        )

        risk_score = numeric_value(
            row,
            "dynamic_risk_score",
            np.nan,
        )

        predicted_warning = binary_value(
            row,
            "predicted_early_warning",
        )

        alert_level = classify_alert(
            probability,
            risk_score,
        )

        explanation, evidence_scores, evidence = (
            build_explanation(
                row,
                thresholds,
            )
        )

        track_id = row.get(
            "track_id",
            -1,
        )

        frame = row.get(
            "frame",
            -1,
        )

        temporal_state = row.get(
            "temporal_state",
            row.get(
                "day8_temporal_state",
                "UNKNOWN",
            ),
        )

        records.append(
            {
                "track_id": track_id,
                "frame": frame,
                "prediction_probability": probability,
                "predicted_early_warning": predicted_warning,
                "dynamic_risk_score": risk_score,
                "risk_trend": numeric_value(
                    row,
                    "risk_trend",
                    np.nan,
                ),
                "risk_increasing": binary_value(
                    row,
                    "risk_increasing",
                ),
                "temporal_state": temporal_state,
                "alert_level": alert_level,
                "evidence_count": len(evidence),
                "evidence_scores": evidence_scores,
                "explanation": explanation,
                "center_x": numeric_value(
                    row,
                    "center_x",
                    np.nan,
                ),
                "center_y": numeric_value(
                    row,
                    "center_y",
                    np.nan,
                ),
                "actual_early_warning": binary_value(
                    row,
                    "actual_early_warning",
                ),
            }
        )

    alerts = pd.DataFrame(records)

    return alerts


# ============================================================
# SAVE OUTPUTS
# ============================================================

def save_outputs(alerts):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Save all explainable results
    # --------------------------------------------------------

    alerts = alerts.sort_values(
        [
            "prediction_probability",
            "dynamic_risk_score",
        ],
        ascending=False,
    )

    alerts.to_csv(
        ALERT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Summary per vehicle
    # --------------------------------------------------------

    summary = (
        alerts
        .groupby("track_id")
        .agg(
            observations=("track_id", "size"),
            max_probability=(
                "prediction_probability",
                "max",
            ),
            mean_probability=(
                "prediction_probability",
                "mean",
            ),
            max_dynamic_risk=(
                "dynamic_risk_score",
                "max",
            ),
            warning_count=(
                "predicted_early_warning",
                "sum",
            ),
            high_count=(
                "alert_level",
                lambda x: int(
                    (x == "HIGH").sum()
                ),
            ),
            critical_count=(
                "alert_level",
                lambda x: int(
                    (x == "CRITICAL").sum()
                ),
            ),
        )
        .reset_index()
    )

    summary["priority"] = np.where(
        summary["critical_count"] > 0,
        "CRITICAL",
        np.where(
            summary["high_count"] > 0,
            "HIGH",
            np.where(
                summary["warning_count"] > 0,
                "WATCH",
                "LOW",
            ),
        ),
    )

    summary = summary.sort_values(
        [
            "priority",
            "max_probability",
        ],
        ascending=[True, False],
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    alert_distribution = (
        alerts["alert_level"]
        .value_counts()
        .to_dict()
    )

    state_distribution = (
        alerts["temporal_state"]
        .value_counts()
        .to_dict()
    )

    warning_rows = alerts[
        alerts["predicted_early_warning"] == 1
    ]

    warning_vehicles = (
        warning_rows["track_id"].nunique()
        if len(warning_rows)
        else 0
    )

    stats = []

    stats.append(
        "BORDER-AI DAY 11 EXPLAINABLE ALERT ENGINE"
    )
    stats.append(
        "=" * 60
    )
    stats.append("")
    stats.append(
        f"Total evaluated sequences: {len(alerts)}"
    )
    stats.append(
        f"Vehicles evaluated: "
        f"{alerts['track_id'].nunique()}"
    )
    stats.append(
        f"Predicted early warnings: "
        f"{int(alerts['predicted_early_warning'].sum())}"
    )
    stats.append(
        f"Vehicles with warnings: "
        f"{warning_vehicles}"
    )
    stats.append("")

    stats.append(
        "ALERT LEVEL DISTRIBUTION"
    )
    stats.append(
        "-" * 28
    )

    for level in [
        "CRITICAL",
        "HIGH",
        "WATCH",
        "LOW",
    ]:

        stats.append(
            f"{level}: "
            f"{alert_distribution.get(level, 0)}"
        )

    stats.append("")
    stats.append(
        "TEMPORAL STATE DISTRIBUTION"
    )
    stats.append(
        "-" * 32
    )

    for state, count in state_distribution.items():

        stats.append(
            f"{state}: {count}"
        )

    stats.append("")
    stats.append(
        "MODEL PROBABILITY"
    )
    stats.append(
        "-" * 24
    )

    stats.append(
        f"Mean: "
        f"{alerts['prediction_probability'].mean():.6f}"
    )

    stats.append(
        f"Maximum: "
        f"{alerts['prediction_probability'].max():.6f}"
    )

    stats.append(
        f"Minimum: "
        f"{alerts['prediction_probability'].min():.6f}"
    )

    stats.append("")
    stats.append(
        "EXPLAINABILITY"
    )
    stats.append(
        "-" * 24
    )

    stats.append(
        "Explanations are generated from "
        "observable temporal and motion features."
    )

    stats.append(
        "The explanation layer does not claim "
        "to expose internal GRU neural weights."
    )

    STATISTICS_FILE.write_text(
        "\n".join(stats)
        + "\n"
    )

    return summary


# ============================================================
# MAIN
# ============================================================

def main():

    predictions, temporal = load_data()

    print()
    print(
        "CALCULATING FEATURE THRESHOLDS"
    )
    print("-" * 60)

    thresholds = calculate_thresholds(
        temporal
    )

    print(
        f"Threshold features: "
        f"{len(thresholds)}"
    )

    print()
    print(
        "MERGING TEMPORAL EVIDENCE"
    )
    print("-" * 60)

    merged = merge_features(
        predictions,
        temporal,
    )

    print(
        f"Merged rows: {len(merged)}"
    )

    print()
    print(
        "BUILDING EXPLAINABLE ALERTS"
    )
    print("-" * 60)

    alerts = build_alerts(
        merged,
        thresholds,
    )

    print(
        f"Explainable alerts: {len(alerts)}"
    )

    summary = save_outputs(
        alerts
    )

    print()
    print("=" * 60)
    print(
        "DAY 11 EXPLAINABLE ALERT ENGINE COMPLETE"
    )
    print("=" * 60)

    print()
    print("ALERT DISTRIBUTION")
    print("-" * 60)

    for level in [
        "CRITICAL",
        "HIGH",
        "WATCH",
        "LOW",
    ]:

        count = int(
            (alerts["alert_level"] == level).sum()
        )

        print(
            f"{level:10s}: {count}"
        )

    print()
    print("TOP EXPLAINABLE ALERTS")
    print("-" * 60)

    top_alerts = (
        alerts
        .sort_values(
            [
                "prediction_probability",
                "dynamic_risk_score",
            ],
            ascending=False,
        )
        .head(10)
    )

    for _, row in top_alerts.iterrows():

        print(
            f"Vehicle {int(row['track_id']):4d} | "
            f"Frame {int(row['frame']):4d} | "
            f"Probability "
            f"{row['prediction_probability']:.3f} | "
            f"{row['alert_level']:8s}"
        )

        print(
            f"  Why: {row['explanation']}"
        )

    print()
    print("OUTPUTS")
    print("-" * 60)

    print(ALERT_FILE)
    print(SUMMARY_FILE)
    print(STATISTICS_FILE)


if __name__ == "__main__":
    main()
