from pathlib import Path
import json
import random

import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report,
)

# ============================================================
# BORDER-AI DAY 9
# TEMPORAL EARLY-WARNING MODEL
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

INPUT = Path(
    "data/outputs/day8_temporal_prediction/day8_temporal_dataset.csv"
)

OUTPUT_DIR = Path(
    "data/outputs/day9_temporal_model"
)

MODEL_DIR = Path(
    "models/day9_temporal_model"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "border_ai_temporal_gru.keras"
SCALER_PATH = MODEL_DIR / "feature_scaler.npz"
METRICS_PATH = OUTPUT_DIR / "day9_metrics.json"
PREDICTIONS_PATH = OUTPUT_DIR / "day9_test_predictions.csv"
REPORT_PATH = OUTPUT_DIR / "day9_classification_report.txt"
CONFUSION_PATH = OUTPUT_DIR / "day9_confusion_matrix.csv"
HISTORY_PATH = OUTPUT_DIR / "day9_training_history.csv"

# ============================================================
# CONFIGURATION
# ============================================================

SEQUENCE_LENGTH = 20
FUTURE_HORIZON = 15

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

BATCH_SIZE = 32
EPOCHS = 50

# ============================================================
# FEATURES
# ============================================================

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

TARGET = "early_warning"

# ============================================================
# LOAD
# ============================================================

print()
print("=" * 60)
print("BORDER-AI DAY 9 TEMPORAL MODEL")
print("=" * 60)

df = pd.read_csv(INPUT)

print(f"Input rows:       {len(df)}")
print(f"Vehicles:          {df.track_id.nunique()}")
print(f"Frames:            {df.frame.nunique()}")

required = FEATURES + [
    TARGET,
    "track_id",
    "frame",
]

missing = [
    c for c in required
    if c not in df.columns
]

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )

df = df.sort_values(
    ["track_id", "frame"]
).reset_index(drop=True)

# ============================================================
# IMPORTANT:
# SPLIT BY VEHICLE, NOT RANDOM ROWS
# ============================================================

vehicles = sorted(
    df["track_id"].unique()
)

rng = np.random.default_rng(SEED)

rng.shuffle(vehicles)

n_vehicles = len(vehicles)

n_train = max(
    1,
    int(n_vehicles * TRAIN_RATIO)
)

n_val = max(
    1,
    int(n_vehicles * VAL_RATIO)
)

train_vehicles = set(
    vehicles[:n_train]
)

val_vehicles = set(
    vehicles[
        n_train:n_train + n_val
    ]
)

test_vehicles = set(
    vehicles[
        n_train + n_val:
    ]
)

print()
print("VEHICLE-LEVEL SPLIT")
print("-" * 60)

print(
    "Train vehicles:",
    len(train_vehicles),
    sorted(train_vehicles)
)

print(
    "Validation vehicles:",
    len(val_vehicles),
    sorted(val_vehicles)
)

print(
    "Test vehicles:",
    len(test_vehicles),
    sorted(test_vehicles)
)

# ============================================================
# SCALE FEATURES
# FIT ONLY ON TRAIN VEHICLES
# ============================================================

train_df = df[
    df.track_id.isin(train_vehicles)
].copy()

val_df = df[
    df.track_id.isin(val_vehicles)
].copy()

test_df = df[
    df.track_id.isin(test_vehicles)
].copy()

scaler = StandardScaler()

scaler.fit(
    train_df[FEATURES].replace(
        [np.inf, -np.inf],
        np.nan
    ).fillna(0)
)

np.savez(
    SCALER_PATH,
    mean=scaler.mean_,
    scale=scaler.scale_,
    features=np.array(FEATURES)
)

# ============================================================
# SEQUENCE CREATION
# ============================================================

def build_sequences(dataframe, split_name):

    X_sequences = []
    y_values = []

    metadata = []

    for track_id, group in dataframe.groupby(
        "track_id"
    ):

        group = group.sort_values(
            "frame"
        ).reset_index(drop=True)

        if len(group) < SEQUENCE_LENGTH:
            continue

        feature_values = (
            group[FEATURES]
            .replace(
                [np.inf, -np.inf],
                np.nan
            )
            .fillna(0)
            .to_numpy(
                dtype=np.float32
            )
        )

        feature_values = scaler.transform(
            feature_values
        ).astype(np.float32)

        targets = group[
            TARGET
        ].to_numpy(
            dtype=np.int32
        )

        frames = group[
            "frame"
        ].to_numpy(
            dtype=np.int32
        )

        for end_idx in range(
            SEQUENCE_LENGTH - 1,
            len(group)
        ):

            start_idx = (
                end_idx -
                SEQUENCE_LENGTH +
                1
            )

            sequence = feature_values[
                start_idx:end_idx + 1
            ]

            target = targets[
                end_idx
            ]

            X_sequences.append(
                sequence
            )

            y_values.append(
                target
            )

            metadata.append({
                "split": split_name,
                "track_id": int(track_id),
                "start_frame": int(
                    frames[start_idx]
                ),
                "end_frame": int(
                    frames[end_idx]
                ),
                "target": int(target),
            })

    if not X_sequences:
        raise ValueError(
            f"No sequences generated for {split_name}"
        )

    return (
        np.asarray(
            X_sequences,
            dtype=np.float32
        ),
        np.asarray(
            y_values,
            dtype=np.int32
        ),
        metadata
    )

# ============================================================
# BUILD SPLITS
# ============================================================

X_train, y_train, meta_train = build_sequences(
    train_df,
    "train"
)

X_val, y_val, meta_val = build_sequences(
    val_df,
    "validation"
)

X_test, y_test, meta_test = build_sequences(
    test_df,
    "test"
)

print()
print("SEQUENCE DATA")
print("-" * 60)

print(
    "Train:",
    X_train.shape,
    "positive:",
    int(y_train.sum())
)

print(
    "Validation:",
    X_val.shape,
    "positive:",
    int(y_val.sum())
)

print(
    "Test:",
    X_test.shape,
    "positive:",
    int(y_test.sum())
)

# ============================================================
# CLASS WEIGHTS
# ============================================================

negative_count = int(
    np.sum(y_train == 0)
)

positive_count = int(
    np.sum(y_train == 1)
)

if positive_count == 0:
    raise ValueError(
        "Training split contains no positive early-warning samples."
    )

total = negative_count + positive_count

class_weight = {
    0: total / (
        2.0 * negative_count
    ),
    1: total / (
        2.0 * positive_count
    ),
}

print()
print("CLASS WEIGHTS")
print("-" * 60)

print(class_weight)

# ============================================================
# MODEL
# ============================================================

model = tf.keras.Sequential([

    tf.keras.layers.Input(
        shape=(
            SEQUENCE_LENGTH,
            len(FEATURES)
        )
    ),

    tf.keras.layers.GRU(
        64,
        return_sequences=True
    ),

    tf.keras.layers.Dropout(
        0.25
    ),

    tf.keras.layers.GRU(
        32
    ),

    tf.keras.layers.Dropout(
        0.25
    ),

    tf.keras.layers.Dense(
        16,
        activation="relu"
    ),

    tf.keras.layers.Dropout(
        0.20
    ),

    tf.keras.layers.Dense(
        1,
        activation="sigmoid"
    ),
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(
        learning_rate=1e-3
    ),
    loss="binary_crossentropy",
    metrics=[
        tf.keras.metrics.BinaryAccuracy(
            name="accuracy"
        ),
        tf.keras.metrics.Precision(
            name="precision"
        ),
        tf.keras.metrics.Recall(
            name="recall"
        ),
        tf.keras.metrics.AUC(
            name="roc_auc"
        ),
        tf.keras.metrics.AUC(
            name="pr_auc",
            curve="PR"
        ),
    ],
)

print()
print("MODEL")
print("-" * 60)

model.summary()

# ============================================================
# CALLBACKS
# ============================================================

callbacks = [

    tf.keras.callbacks.EarlyStopping(
        monitor="val_pr_auc",
        mode="max",
        patience=8,
        restore_best_weights=True,
        verbose=1,
    ),

    tf.keras.callbacks.ModelCheckpoint(
        filepath=str(MODEL_PATH),
        monitor="val_pr_auc",
        mode="max",
        save_best_only=True,
        verbose=1,
    ),

    tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_pr_auc",
        mode="max",
        factor=0.5,
        patience=4,
        min_lr=1e-6,
        verbose=1,
    ),
]

# ============================================================
# TRAIN
# ============================================================

print()
print("=" * 60)
print("TRAINING")
print("=" * 60)

history = model.fit(
    X_train,
    y_train,
    validation_data=(
        X_val,
        y_val
    ),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    class_weight=class_weight,
    callbacks=callbacks,
    verbose=1,
)

# ============================================================
# SAVE HISTORY
# ============================================================

history_df = pd.DataFrame(
    history.history
)

history_df.insert(
    0,
    "epoch",
    np.arange(
        1,
        len(history_df) + 1
    )
)

history_df.to_csv(
    HISTORY_PATH,
    index=False
)

# ============================================================
# LOAD BEST MODEL
# ============================================================

if MODEL_PATH.exists():

    model = tf.keras.models.load_model(
        MODEL_PATH
    )

# ============================================================
# TEST PREDICTIONS
# ============================================================

probabilities = model.predict(
    X_test,
    batch_size=BATCH_SIZE,
    verbose=0
).reshape(-1)

predictions = (
    probabilities >= 0.5
).astype(int)

# ============================================================
# METRICS
# ============================================================

accuracy = accuracy_score(
    y_test,
    predictions
)

precision = precision_score(
    y_test,
    predictions,
    zero_division=0
)

recall = recall_score(
    y_test,
    predictions,
    zero_division=0
)

f1 = f1_score(
    y_test,
    predictions,
    zero_division=0
)

if len(np.unique(y_test)) == 2:

    roc_auc = roc_auc_score(
        y_test,
        probabilities
    )

    pr_auc = average_precision_score(
        y_test,
        probabilities
    )

else:

    roc_auc = None
    pr_auc = None

cm = confusion_matrix(
    y_test,
    predictions,
    labels=[0, 1]
)

# ============================================================
# SAVE PREDICTIONS
# ============================================================

prediction_df = pd.DataFrame(
    meta_test
)

prediction_df["probability"] = (
    probabilities
)

prediction_df["prediction"] = (
    predictions
)

prediction_df["correct"] = (
    prediction_df["target"] ==
    prediction_df["prediction"]
)

prediction_df.to_csv(
    PREDICTIONS_PATH,
    index=False,
    float_format="%.6f"
)

# ============================================================
# SAVE CONFUSION MATRIX
# ============================================================

cm_df = pd.DataFrame(
    cm,
    index=[
        "actual_0",
        "actual_1"
    ],
    columns=[
        "predicted_0",
        "predicted_1"
    ]
)

cm_df.to_csv(
    CONFUSION_PATH
)

# ============================================================
# CLASSIFICATION REPORT
# ============================================================

report = classification_report(
    y_test,
    predictions,
    labels=[0, 1],
    target_names=[
        "NO_EARLY_WARNING",
        "EARLY_WARNING"
    ],
    zero_division=0
)

with REPORT_PATH.open("w") as f:

    f.write(
        "BORDER-AI DAY 9 TEMPORAL MODEL\n"
    )

    f.write(
        "================================\n\n"
    )

    f.write(
        f"Sequence length: {SEQUENCE_LENGTH}\n"
    )

    f.write(
        f"Future horizon: {FUTURE_HORIZON}\n"
    )

    f.write(
        f"Features: {len(FEATURES)}\n"
    )

    f.write(
        f"Train vehicles: {len(train_vehicles)}\n"
    )

    f.write(
        f"Validation vehicles: {len(val_vehicles)}\n"
    )

    f.write(
        f"Test vehicles: {len(test_vehicles)}\n\n"
    )

    f.write(
        "TEST METRICS\n"
    )

    f.write(
        "------------\n"
    )

    f.write(
        f"Accuracy:  {accuracy:.6f}\n"
    )

    f.write(
        f"Precision: {precision:.6f}\n"
    )

    f.write(
        f"Recall:    {recall:.6f}\n"
    )

    f.write(
        f"F1:        {f1:.6f}\n"
    )

    f.write(
        f"ROC-AUC:   {roc_auc}\n"
    )

    f.write(
        f"PR-AUC:    {pr_auc}\n\n"
    )

    f.write(
        "CONFUSION MATRIX\n"
    )

    f.write(
        str(cm_df)
    )

    f.write("\n\nCLASSIFICATION REPORT\n")
    f.write(
        report
    )

# ============================================================
# SAVE METRICS JSON
# ============================================================

metrics = {

    "model": "GRU",

    "sequence_length": SEQUENCE_LENGTH,

    "future_horizon": FUTURE_HORIZON,

    "feature_count": len(FEATURES),

    "train_vehicles": len(
        train_vehicles
    ),

    "validation_vehicles": len(
        val_vehicles
    ),

    "test_vehicles": len(
        test_vehicles
    ),

    "train_sequences": len(
        X_train
    ),

    "validation_sequences": len(
        X_val
    ),

    "test_sequences": len(
        X_test
    ),

    "test_positive_samples": int(
        y_test.sum()
    ),

    "test_negative_samples": int(
        np.sum(y_test == 0)
    ),

    "accuracy": float(
        accuracy
    ),

    "precision": float(
        precision
    ),

    "recall": float(
        recall
    ),

    "f1": float(
        f1
    ),

    "roc_auc": (
        None
        if roc_auc is None
        else float(roc_auc)
    ),

    "pr_auc": (
        None
        if pr_auc is None
        else float(pr_auc)
    ),

    "confusion_matrix": cm.tolist(),

    "class_weight": class_weight,
}

with METRICS_PATH.open("w") as f:

    json.dump(
        metrics,
        f,
        indent=2
    )

# ============================================================
# FINAL OUTPUT
# ============================================================

print()
print("=" * 60)
print("DAY 9 TEMPORAL MODEL COMPLETE")
print("=" * 60)

print()
print("MODEL:")
print(MODEL_PATH)

print()
print("TEST METRICS")
print("-" * 60)

print(
    f"Accuracy : {accuracy:.4f}"
)

print(
    f"Precision: {precision:.4f}"
)

print(
    f"Recall   : {recall:.4f}"
)

print(
    f"F1       : {f1:.4f}"
)

print(
    f"ROC-AUC  : {roc_auc}"
)

print(
    f"PR-AUC   : {pr_auc}"
)

print()
print("CONFUSION MATRIX")
print(cm_df)

print()
print("OUTPUTS:")
print(METRICS_PATH)
print(PREDICTIONS_PATH)
print(REPORT_PATH)
print(CONFUSION_PATH)
print(HISTORY_PATH)

print()
print("=" * 60)
