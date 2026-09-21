"""
BORDER-AI DAY 10
Temporal GRU Inference + Early Warning Engine

Loads the Day 9 trained GRU model and performs temporal
early-warning inference on vehicle sequences.

Input:
    data/outputs/day8_temporal_prediction/day8_temporal_dataset.csv

Model:
    models/day9_temporal_model/border_ai_temporal_gru.keras

Scaler:
    models/day9_temporal_model/feature_scaler.npz

Output:
    data/outputs/day10_temporal_inference/day10_temporal_predictions.csv
    data/outputs/day10_temporal_inference/day10_alerts.csv
    data/outputs/day10_temporal_inference/day10_statistics.txt
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)


# ============================================================
# PATHS
# ============================================================

INPUT_FILE = Path(
    "data/outputs/day8_temporal_prediction/day8_temporal_dataset.csv"
)

MODEL_FILE = Path(
    "models/day9_temporal_model/border_ai_temporal_gru.keras"
)

SCALER_FILE = Path(
    "models/day9_temporal_model/feature_scaler.npz"
)

OUTPUT_DIR = Path(
    "data/outputs/day10_temporal_inference"
)

PREDICTION_FILE = OUTPUT_DIR / "day10_temporal_predictions.csv"
ALERT_FILE = OUTPUT_DIR / "day10_alerts.csv"
STATS_FILE = OUTPUT_DIR / "day10_statistics.txt"


# ============================================================
# MODEL CONFIGURATION
# ============================================================

SEQUENCE_LENGTH = 20

# IMPORTANT:
# These must match the features used during Day 9 training.
FEATURES = [
    "center_x",
    "center_y",
    "width",
    "height",

    "speed_normalized",
    "acceleration",
    "direction_deg",
    "displacement",

    "speed_change",
    "acceleration_change",
    "direction_change",
    "position_change",

    "speed_rolling_mean",
    "acceleration_rolling_mean",
    "anomaly_rolling_mean",

    "behavior_anomaly_score",
    "speed_anomaly",
    "acceleration_anomaly",
    "direction_anomaly",
    "sudden_acceleration",
    "slow_or_stopped",

    "dynamic_risk_score",
    "risk_rolling_mean",
    "risk_trend",
    "risk_increasing",
]


# ============================================================
# THRESHOLDS
# ============================================================

# Main early-warning threshold.
EARLY_WARNING_THRESHOLD = 0.50

# Strong warning threshold.
HIGH_WARNING_THRESHOLD = 0.75


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def risk_level(probability: float) -> str:
    """Convert model probability into an interpretable risk level."""

    if probability >= HIGH_WARNING_THRESHOLD:
        return "HIGH"

    if probability >= EARLY_WARNING_THRESHOLD:
        return "WATCH"

    return "LOW"


def temporal_state(
    probabilities: list[float],
) -> str:
    """
    Determine whether the model's predicted risk is increasing,
    decreasing, or stable across recent sequences.
    """

    if len(probabilities) < 2:
        return "STABLE"

    previous = probabilities[-2]
    current = probabilities[-1]

    change = current - previous

    if change >= 0.15:
        return "RAPID_ESCALATION"

    if change >= 0.05:
        return "ESCALATING"

    if change <= -0.05:
        return "DE_ESCALATING"

    return "STABLE"


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    print("=" * 60)
    print("BORDER-AI DAY 10 TEMPORAL INFERENCE")
    print("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT_FILE}"
        )

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"GRU model not found: {MODEL_FILE}"
        )

    if not SCALER_FILE.exists():
        raise FileNotFoundError(
            f"Scaler not found: {SCALER_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(f"Input rows:       {len(df)}")
    print(f"Vehicles:         {df['track_id'].nunique()}")
    print(f"Frames:           {df['frame'].nunique()}")

    missing = [column for column in FEATURES if column not in df.columns]

    if missing:
        raise ValueError(
            "Missing required Day 9 features:\n"
            + "\n".join(f"  - {column}" for column in missing)
        )

    return df


# ============================================================
# LOAD MODEL + SCALER
# ============================================================

def load_model_and_scaler():

    print()
    print("LOADING DAY 9 GRU MODEL")
    print("-" * 60)

    model = tf.keras.models.load_model(MODEL_FILE)

    scaler_data = np.load(SCALER_FILE)

    scaler_mean = scaler_data["mean"]
    scaler_scale = scaler_data["scale"]

    # Verify that inference features exactly match the
    # feature ordering used during Day 9 training.
    saved_features = scaler_data["features"].tolist()

    if saved_features != FEATURES:
        print()
        print("ERROR: Feature ordering mismatch!")
        print()
        print("Day 9 scaler features:")
        for i, feature in enumerate(saved_features, 1):
            print(f"  {i:02d}. {feature}")

        print()
        print("Day 10 inference features:")
        for i, feature in enumerate(FEATURES, 1):
            print(f"  {i:02d}. {feature}")

        raise ValueError(
            "Day 10 features do not exactly match "
            "the Day 9 training features."
        )

    print(f"Model:  {MODEL_FILE}")
    print(f"Scaler: {SCALER_FILE}")
    print(f"Features: {len(FEATURES)}")
    print("Feature ordering: VERIFIED")

    return model, scaler_mean, scaler_scale


# ============================================================
# SCALE FEATURES
# ============================================================

def scale_features(values, scaler_mean, scaler_scale):

    values = np.asarray(values, dtype=np.float32)

    return (
        values - scaler_mean
    ) / np.where(
        scaler_scale == 0,
        1.0,
        scaler_scale,
    )


# ============================================================
# BUILD SEQUENCES
# ============================================================

def build_sequences(df, scaler_mean, scaler_scale):

    sequences = []
    metadata = []

    print()
    print("BUILDING TEMPORAL SEQUENCES")
    print("-" * 60)

    for track_id, vehicle_df in df.groupby("track_id"):

        vehicle_df = vehicle_df.sort_values("frame").reset_index(drop=True)

        if len(vehicle_df) < SEQUENCE_LENGTH:
            continue

        feature_values = vehicle_df[FEATURES].astype(float).values

        scaled_values = scale_features(
            feature_values,
            scaler_mean,
            scaler_scale,
        )

        for end_idx in range(
            SEQUENCE_LENGTH,
            len(vehicle_df) + 1
        ):

            start_idx = end_idx - SEQUENCE_LENGTH

            sequence = scaled_values[start_idx:end_idx]

            if sequence.shape != (
                SEQUENCE_LENGTH,
                len(FEATURES),
            ):
                continue

            last_row = vehicle_df.iloc[end_idx - 1]

            sequences.append(sequence)

            metadata.append(
                {
                    "track_id": int(track_id),
                    "frame": int(last_row["frame"]),
                    "center_x": float(last_row["center_x"]),
                    "center_y": float(last_row["center_y"]),
                    "threat_score": float(
                        last_row["threat_score"]
                    ),
                    "risk_trend": float(
                        last_row["risk_trend"]
                    ),
                    "risk_increasing": int(
                        last_row["risk_increasing"]
                    ),
                    "actual_early_warning": int(
                        last_row["early_warning"]
                    ),
                    "day8_temporal_state": str(
                        last_row["temporal_state"]
                    ),
                }
            )

    X = np.asarray(sequences, dtype=np.float32)

    metadata_df = pd.DataFrame(metadata)

    print(f"Sequences created: {len(X)}")
    print(f"Sequence shape:    {X.shape}")

    return X, metadata_df


# ============================================================
# RUN INFERENCE
# ============================================================

def run_inference(model, X, metadata_df):

    print()
    print("RUNNING GRU INFERENCE")
    print("-" * 60)

    probabilities = model.predict(
        X,
        batch_size=128,
        verbose=1,
    ).reshape(-1)

    predictions = (
        probabilities >= EARLY_WARNING_THRESHOLD
    ).astype(int)

    results = metadata_df.copy()

    results["prediction_probability"] = probabilities
    results["predicted_early_warning"] = predictions

    results["predicted_risk_level"] = [
        risk_level(probability)
        for probability in probabilities
    ]

    # Calculate temporal state per vehicle.
    results["predicted_temporal_state"] = "STABLE"

    for track_id in results["track_id"].unique():

        mask = results["track_id"] == track_id

        vehicle_results = results.loc[
            mask
        ].sort_values("frame")

        vehicle_probabilities = (
            vehicle_results[
                "prediction_probability"
            ].tolist()
        )

        states = []

        for i in range(len(vehicle_probabilities)):

            recent_start = max(
                0,
                i - 2,
            )

            recent = vehicle_probabilities[
                recent_start:i + 1
            ]

            states.append(
                temporal_state(recent)
            )

        results.loc[
            vehicle_results.index,
            "predicted_temporal_state",
        ] = states

    # Human-readable alert.
    results["alert"] = np.where(
        results["predicted_early_warning"] == 1,
        "TEMPORAL EARLY WARNING",
        "NO ALERT",
    )

    # Alert priority.
    results["alert_priority"] = np.select(
        [
            results["prediction_probability"]
            >= HIGH_WARNING_THRESHOLD,

            results["prediction_probability"]
            >= EARLY_WARNING_THRESHOLD,
        ],
        [
            "HIGH",
            "MEDIUM",
        ],
        default="NONE",
    )

    return results


# ============================================================
# EVALUATION
# ============================================================

def evaluate_predictions(results):

    y_true = results["actual_early_warning"].astype(int)
    y_pred = results["predicted_early_warning"].astype(int)
    y_prob = results["prediction_probability"].astype(float)

    metrics = {
        "accuracy": float(
            accuracy_score(y_true, y_pred)
        ),
        "precision": float(
            precision_score(
                y_true,
                y_pred,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_true,
                y_pred,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                y_true,
                y_pred,
                zero_division=0,
            )
        ),
        "roc_auc": float(
            roc_auc_score(y_true, y_prob)
        ),
        "pr_auc": float(
            average_precision_score(y_true, y_prob)
        ),
    }

    cm = confusion_matrix(y_true, y_pred)

    return metrics, cm


# ============================================================
# SAVE OUTPUTS
# ============================================================

def save_outputs(results, evaluation_metrics):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results.to_csv(
        PREDICTION_FILE,
        index=False,
    )

    alerts = results[
        results["predicted_early_warning"] == 1
    ].copy()

    alerts = alerts.sort_values(
        "prediction_probability",
        ascending=False,
    )

    alerts.to_csv(
        ALERT_FILE,
        index=False,
    )

    # Statistics.
    total = len(results)
    warning_count = int(
        results["predicted_early_warning"].sum()
    )

    high_count = int(
        (
            results["prediction_probability"]
            >= HIGH_WARNING_THRESHOLD
        ).sum()
    )

    unique_warning_vehicles = int(
        alerts["track_id"].nunique()
    ) if len(alerts) else 0

    stats = [
        "BORDER-AI DAY 10 TEMPORAL INFERENCE",
        "=" * 45,
        "",
        f"Total inference sequences: {total}",
        f"Early warnings:            {warning_count}",
        f"Early warning rate:        "
        f"{warning_count / total * 100:.2f}%"
        if total
        else "Early warning rate:        0.00%",
        f"High-confidence warnings:  {high_count}",
        f"Vehicles with warnings:    {unique_warning_vehicles}",
        "",
        f"Mean prediction probability: "
        f"{results['prediction_probability'].mean():.6f}",
        f"Maximum prediction probability: "
        f"{results['prediction_probability'].max():.6f}",
        f"Minimum prediction probability: "
        f"{results['prediction_probability'].min():.6f}",
        "",
        "RISK DISTRIBUTION",
        "-" * 25,
    ]

    risk_counts = (
        results["predicted_risk_level"]
        .value_counts()
        .to_dict()
    )

    for level in ["LOW", "WATCH", "HIGH"]:
        stats.append(
            f"{level}: {risk_counts.get(level, 0)}"
        )

    stats.extend(
        [
            "",
            "DAY 10 EVALUATION",
            "-" * 25,
            f"Accuracy:  {evaluation_metrics['accuracy']:.6f}",
            f"Precision: {evaluation_metrics['precision']:.6f}",
            f"Recall:    {evaluation_metrics['recall']:.6f}",
            f"F1:        {evaluation_metrics['f1']:.6f}",
            f"ROC-AUC:   {evaluation_metrics['roc_auc']:.6f}",
            f"PR-AUC:    {evaluation_metrics['pr_auc']:.6f}",
            "",
            "TEMPORAL STATE DISTRIBUTION",
            "-" * 30,
        ]
    )

    state_counts = (
        results["predicted_temporal_state"]
        .value_counts()
        .to_dict()
    )

    for state in [
        "STABLE",
        "ESCALATING",
        "RAPID_ESCALATION",
        "DE_ESCALATING",
    ]:
        stats.append(
            f"{state}: {state_counts.get(state, 0)}"
        )

    STATS_FILE.write_text(
        "\n".join(stats),
        encoding="utf-8",
    )

    return alerts, stats


# ============================================================
# MAIN
# ============================================================

def main():

    df = load_data()

    model, scaler_mean, scaler_scale = (
        load_model_and_scaler()
    )

    X, metadata_df = build_sequences(
        df,
        scaler_mean,
        scaler_scale,
    )

    if len(X) == 0:
        raise RuntimeError(
            "No valid temporal sequences were created."
        )

    results = run_inference(
        model,
        X,
        metadata_df,
    )

    evaluation_metrics, confusion = evaluate_predictions(
        results
    )

    results["evaluation_correct"] = (
        results["predicted_early_warning"]
        == results["actual_early_warning"]
    ).astype(int)

    evaluation_metrics, confusion = evaluate_predictions(results)
    alerts, stats = save_outputs(results, evaluation_metrics)

    print()
    print("=" * 60)
    print("DAY 10 TEMPORAL INFERENCE COMPLETE")
    print("=" * 60)

    print()
    print("INFERENCE RESULTS")
    print("-" * 60)

    print(
        f"Sequences:             {len(results)}"
    )

    print(
        f"Early warnings:        "
        f"{results['predicted_early_warning'].sum()}"
    )

    print(
        f"Warning vehicles:      "
        f"{alerts['track_id'].nunique() if len(alerts) else 0}"
    )

    print(
        f"Max prediction:        "
        f"{results['prediction_probability'].max():.4f}"
    )

    print()
    print("DAY 10 EVALUATION")
    print("-" * 60)

    print(
        f"Accuracy : {evaluation_metrics['accuracy']:.4f}"
    )
    print(
        f"Precision: {evaluation_metrics['precision']:.4f}"
    )
    print(
        f"Recall   : {evaluation_metrics['recall']:.4f}"
    )
    print(
        f"F1       : {evaluation_metrics['f1']:.4f}"
    )
    print(
        f"ROC-AUC  : {evaluation_metrics['roc_auc']:.4f}"
    )
    print(
        f"PR-AUC   : {evaluation_metrics['pr_auc']:.4f}"
    )

    print()
    print("CONFUSION MATRIX")
    print("-" * 60)
    print(confusion)

    print()
    print("TOP 10 EARLY WARNINGS")
    print("-" * 60)

    if len(alerts):

        top_alerts = alerts.head(10)

        for _, row in top_alerts.iterrows():

            print(
                f"Vehicle {int(row['track_id']):>4} | "
                f"Frame {int(row['frame']):>4} | "
                f"Probability "
                f"{row['prediction_probability']:.3f} | "
                f"{row['predicted_risk_level']:<5} | "
                f"{row['predicted_temporal_state']}"
            )

    else:
        print("No early-warning events detected.")

    print()
    print("OUTPUTS")
    print("-" * 60)

    print(PREDICTION_FILE)
    print(ALERT_FILE)
    print(STATS_FILE)


if __name__ == "__main__":
    main()
