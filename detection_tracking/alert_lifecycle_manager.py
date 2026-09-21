"""
BORDER-AI DAY 14
Alert Deduplication & Lifecycle Management

Purpose
-------
Convert repeated frame-level operator alerts into
incident-level alerts.

This reduces alert flooding while preserving the
underlying evidence and priority information.

Important scientific note
-------------------------
This is an explainable rule-based incident aggregation
layer. It is not a newly trained machine-learning model.

Input
-----
Day 13:
    day13_prioritized_alerts.csv

Outputs
-------
data/outputs/day14_alert_lifecycle/
    day14_incident_alerts.csv
    day14_operator_incident_queue.csv
    day14_alert_history.csv
    day14_statistics.txt
"""

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "outputs"
    / "day13_alert_prioritization"
    / "day13_prioritized_alerts.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "outputs"
    / "day14_alert_lifecycle"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# Alerts belonging to the same vehicle/event are considered
# part of the same incident when their frame gap is within
# this development threshold.
FRAME_GAP_THRESHOLD = 30


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):

    try:
        value = float(value)

        if np.isnan(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):

    try:
        value = int(float(value))
        return value

    except (TypeError, ValueError):
        return default


def text_value(value, default=""):

    if pd.isna(value):
        return default

    return str(value)


# ============================================================
# LOAD DATA
# ============================================================

def load_alerts():

    print("=" * 70)
    print("BORDER-AI DAY 14 ALERT LIFECYCLE MANAGEMENT")
    print("=" * 70)

    print()
    print("LOADING DAY 13 PRIORITIZED ALERTS")
    print("-" * 70)

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Missing Day 13 input:\n{INPUT_FILE}"
        )

    alerts = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"Input alerts: {len(alerts)}"
    )

    if "track_id" in alerts.columns:

        print(
            f"Vehicles: "
            f"{alerts['track_id'].nunique()}"
        )

    required_columns = [
        "track_id",
        "frame",
        "priority_score",
        "priority_level",
        "prediction_probability",
        "dynamic_risk_score",
        "risk_trend",
        "temporal_state",
        "alert_level",
        "event_id",
        "camera_path",
        "cross_camera_event",
        "priority_explanation",
        "recommended_action",
        "queue_position",
    ]

    missing = [
        column
        for column in required_columns
        if column not in alerts.columns
    ]

    if missing:

        raise ValueError(
            "Missing required Day 13 columns: "
            + ", ".join(missing)
        )

    return alerts


# ============================================================
# NORMALIZE DATA
# ============================================================

def normalize_alerts(alerts):

    df = alerts.copy()

    df["track_id"] = pd.to_numeric(
        df["track_id"],
        errors="coerce"
    )

    df["frame"] = pd.to_numeric(
        df["frame"],
        errors="coerce"
    )

    df["priority_score"] = pd.to_numeric(
        df["priority_score"],
        errors="coerce"
    ).fillna(0.0)

    df["prediction_probability"] = pd.to_numeric(
        df["prediction_probability"],
        errors="coerce"
    ).fillna(0.0)

    df["dynamic_risk_score"] = pd.to_numeric(
        df["dynamic_risk_score"],
        errors="coerce"
    ).fillna(0.0)

    df["risk_trend"] = pd.to_numeric(
        df["risk_trend"],
        errors="coerce"
    ).fillna(0.0)

    df["priority_level"] = (
        df["priority_level"]
        .fillna("LOW")
        .astype(str)
        .str.upper()
    )

    df["alert_level"] = (
        df["alert_level"]
        .fillna("LOW")
        .astype(str)
        .str.upper()
    )

    df["temporal_state"] = (
        df["temporal_state"]
        .fillna("STABLE")
        .astype(str)
        .str.upper()
    )

    df["event_id"] = (
        df["event_id"]
        .fillna("NO_CROSS_CAMERA_EVENT")
        .astype(str)
    )

    df["camera_path"] = (
        df["camera_path"]
        .fillna("SINGLE-CAMERA")
        .astype(str)
    )

    df["priority_explanation"] = (
        df["priority_explanation"]
        .fillna("")
        .astype(str)
    )

    df["recommended_action"] = (
        df["recommended_action"]
        .fillna("")
        .astype(str)
    )

    df["cross_camera_event"] = (
        df["cross_camera_event"]
        .fillna(False)
        .astype(bool)
    )

    df = df.sort_values(
        [
            "track_id",
            "frame"
        ]
    ).reset_index(
        drop=True
    )

    return df


# ============================================================
# INCIDENT GROUPING
# ============================================================

def build_incident_groups(alerts):

    """
    Group frame-level alerts into incidents.

    A new incident starts when:
      1. vehicle changes, or
      2. event/camera context changes substantially, or
      3. frame gap exceeds FRAME_GAP_THRESHOLD.

    For NO_CROSS_CAMERA_EVENT alerts, the vehicle and temporal
    continuity are used as the main grouping signals.
    """

    groups = []

    current = []

    previous_track = None
    previous_frame = None
    previous_event = None
    previous_camera = None

    def flush():

        nonlocal current

        if current:

            groups.append(
                current
            )

            current = []

    for index, row in alerts.iterrows():

        track_id = row["track_id"]
        frame = safe_int(
            row["frame"]
        )

        event_id = row["event_id"]
        camera_path = row["camera_path"]

        new_group = False

        if not current:

            new_group = True

        else:

            if track_id != previous_track:

                new_group = True

            frame_gap = (
                frame
                - previous_frame
            )

            if frame_gap > FRAME_GAP_THRESHOLD:

                new_group = True

            # Real correlated event IDs define a stronger
            # incident boundary.
            if (
                event_id
                != "NO_CROSS_CAMERA_EVENT"
                and previous_event
                != "NO_CROSS_CAMERA_EVENT"
                and event_id != previous_event
            ):

                new_group = True

            # Different camera paths should remain separate
            # unless they belong to the same correlated event.
            if (
                camera_path != previous_camera
                and event_id
                == "NO_CROSS_CAMERA_EVENT"
            ):

                new_group = True

        if new_group:

            flush()

        current.append(
            index
        )

        previous_track = track_id
        previous_frame = frame
        previous_event = event_id
        previous_camera = camera_path

    flush()

    return groups


# ============================================================
# INCIDENT STATE
# ============================================================

def determine_lifecycle(
    group,
    alerts
):

    subset = alerts.loc[
        group
    ].copy()

    max_priority = (
        subset["priority_score"]
        .max()
    )

    max_risk = (
        subset["dynamic_risk_score"]
        .max()
    )

    temporal_states = set(
        subset["temporal_state"]
        .astype(str)
        .str.upper()
    )

    priority_levels = set(
        subset["priority_level"]
        .astype(str)
        .str.upper()
    )

    if "RAPID_ESCALATION" in temporal_states:

        return "ESCALATING"

    if (
        "URGENT" in priority_levels
        or max_priority >= 65
    ):

        return "ACTIVE"

    if (
        "HIGH" in priority_levels
        or max_priority >= 40
    ):

        return "MONITORING"

    if max_risk >= 15:

        return "MONITORING"

    return "RESOLVED"


# ============================================================
# INCIDENT CREATION
# ============================================================

def create_incident_record(
    incident_number,
    group,
    alerts
):

    subset = alerts.loc[
        group
    ].copy()

    subset = subset.sort_values(
        "frame"
    )

    first = subset.iloc[0]
    last = subset.iloc[-1]

    track_id = first["track_id"]

    event_ids = [
        value
        for value in subset[
            "event_id"
        ].astype(str).unique()
        if value
        != "NO_CROSS_CAMERA_EVENT"
    ]

    if event_ids:

        event_id = event_ids[0]

    else:

        event_id = (
            "INCIDENT_"
            + str(
                safe_int(track_id)
            )
            + "_"
            + str(
                incident_number
            )
        )

    camera_paths = [
        value
        for value in subset[
            "camera_path"
        ].astype(str).unique()
    ]

    camera_path = " -> ".join(
        camera_paths
    )

    start_frame = safe_int(
        first["frame"]
    )

    end_frame = safe_int(
        last["frame"]
    )

    duration_frames = (
        end_frame
        - start_frame
        + 1
    )

    max_priority_row = (
        subset.sort_values(
            "priority_score",
            ascending=False
        )
        .iloc[0]
    )

    max_probability = (
        subset[
            "prediction_probability"
        ]
        .max()
    )

    max_risk = (
        subset[
            "dynamic_risk_score"
        ]
        .max()
    )

    max_priority = (
        subset[
            "priority_score"
        ]
        .max()
    )

    alert_level = (
        subset[
            "alert_level"
        ]
        .iloc[
            subset[
                "priority_score"
            ]
            .argmax()
        ]
    )

    priority_level = (
        max_priority_row[
            "priority_level"
        ]
    )

    lifecycle_state = (
        determine_lifecycle(
            group,
            alerts
        )
    )

    explanation_values = (
        subset[
            "priority_explanation"
        ]
        .dropna()
        .astype(str)
        .tolist()
    )

    unique_explanations = []

    for explanation in explanation_values:

        if (
            explanation
            and explanation
            not in unique_explanations
        ):

            unique_explanations.append(
                explanation
            )

    # Limit incident explanation size while
    # retaining multiple supporting evidence sources.
    incident_explanation = " | ".join(
        unique_explanations[:5]
    )

    action_values = (
        subset[
            "recommended_action"
        ]
        .dropna()
        .astype(str)
        .tolist()
    )

    if action_values:

        recommended_action = (
            action_values[
                0
            ]
        )

    else:

        recommended_action = (
            "Continue automated monitoring"
        )

    cross_camera = bool(
        subset[
            "cross_camera_event"
        ].any()
    )

    temporal_states = (
        " -> ".join(
            subset[
                "temporal_state"
            ]
            .astype(str)
            .drop_duplicates()
            .tolist()
        )
    )

    return {
        "incident_id":
            f"INC-{safe_int(track_id):04d}-{incident_number:03d}",

        "track_id":
            safe_int(track_id),

        "event_id":
            event_id,

        "camera_path":
            camera_path,

        "start_frame":
            start_frame,

        "end_frame":
            end_frame,

        "duration_frames":
            duration_frames,

        "supporting_alert_count":
            len(subset),

        "max_priority_score":
            round(
                safe_float(
                    max_priority
                ),
                4
            ),

        "max_prediction_probability":
            round(
                safe_float(
                    max_probability
                ),
                6
            ),

        "max_dynamic_risk":
            round(
                safe_float(
                    max_risk
                ),
                6
            ),

        "alert_level":
            text_value(
                alert_level,
                "LOW"
            ),

        "priority_level":
            text_value(
                priority_level,
                "LOW"
            ),

        "temporal_states":
            temporal_states,

        "lifecycle_state":
            lifecycle_state,

        "cross_camera_event":
            cross_camera,

        "incident_explanation":
            incident_explanation,

        "recommended_action":
            recommended_action,

        "first_queue_position":
            safe_int(
                subset[
                    "queue_position"
                ].min()
            ),
    }


# ============================================================
# BUILD INCIDENT DATA
# ============================================================

def build_incidents(alerts):

    print()
    print(
        "BUILDING INCIDENT GROUPS"
    )
    print("-" * 70)

    groups = build_incident_groups(
        alerts
    )

    print(
        f"Frame-level alerts: {len(alerts)}"
    )

    print(
        f"Incident groups: {len(groups)}"
    )

    incidents = []

    for number, group in enumerate(
        groups,
        start=1
    ):

        incidents.append(
            create_incident_record(
                number,
                group,
                alerts
            )
        )

    incidents = pd.DataFrame(
        incidents
    )

    if not incidents.empty:

        incidents = incidents.sort_values(
            [
                "max_priority_score",
                "max_prediction_probability",
                "max_dynamic_risk"
            ],
            ascending=[
                False,
                False,
                False
            ]
        ).reset_index(
            drop=True
        )

        incidents[
            "incident_queue_position"
        ] = (
            np.arange(
                len(incidents)
            )
            + 1
        )

    return incidents, groups


# ============================================================
# ALERT HISTORY
# ============================================================

def build_alert_history(
    alerts,
    groups,
    incidents
):

    rows = []

    for incident_index, group in enumerate(
        groups
    ):

        if incident_index >= len(incidents):

            continue

        incident = incidents.iloc[
            incident_index
        ]

        for row_index in group:

            row = alerts.loc[
                row_index
            ].to_dict()

            row[
                "incident_id"
            ] = incident[
                "incident_id"
            ]

            row[
                "incident_lifecycle_state"
            ] = incident[
                "lifecycle_state"
            ]

            row[
                "incident_queue_position"
            ] = incident[
                "incident_queue_position"
            ]

            rows.append(
                row
            )

    history = pd.DataFrame(
        rows
    )

    return history


# ============================================================
# OPERATOR INCIDENT QUEUE
# ============================================================

def build_operator_queue(
    incidents
):

    if incidents.empty:

        return incidents.copy()

    columns = [
        "incident_queue_position",
        "incident_id",
        "track_id",
        "event_id",
        "camera_path",
        "start_frame",
        "end_frame",
        "duration_frames",
        "supporting_alert_count",
        "max_priority_score",
        "max_prediction_probability",
        "max_dynamic_risk",
        "alert_level",
        "priority_level",
        "temporal_states",
        "lifecycle_state",
        "cross_camera_event",
        "incident_explanation",
        "recommended_action",
    ]

    available = [
        column
        for column in columns
        if column in incidents.columns
    ]

    return incidents[
        available
    ].copy()


# ============================================================
# STATISTICS
# ============================================================

def write_statistics(
    alerts,
    incidents
):

    output_file = (
        OUTPUT_DIR
        / "day14_statistics.txt"
    )

    lines = []

    lines.append(
        "BORDER-AI DAY 14 "
        "ALERT DEDUPLICATION "
        "AND LIFECYCLE MANAGEMENT"
    )

    lines.append(
        "=" * 70
    )

    lines.append("")
    lines.append(
        "MODULE DESCRIPTION"
    )
    lines.append(
        "------------------"
    )

    lines.append(
        "Day 14 converts repeated frame-level "
        "alerts into incident-level alerts."
    )

    lines.append(
        "This is an explainable rule-based "
        "aggregation layer, not a newly "
        "trained machine-learning model."
    )

    lines.append("")
    lines.append(
        "INPUT"
    )
    lines.append(
        "-----"
    )

    lines.append(
        f"Frame-level alerts: {len(alerts)}"
    )

    lines.append(
        f"Unique vehicles: "
        f"{alerts['track_id'].nunique()}"
    )

    lines.append("")
    lines.append(
        "INCIDENT SUMMARY"
    )
    lines.append(
        "----------------"
    )

    lines.append(
        f"Incidents created: {len(incidents)}"
    )

    if not incidents.empty:

        reduction = (
            1
            - (
                len(incidents)
                / len(alerts)
            )
        ) * 100

        lines.append(
            f"Alert-count reduction: "
            f"{reduction:.2f}%"
        )

        lines.append(
            f"Mean alerts per incident: "
            f"{incidents['supporting_alert_count'].mean():.2f}"
        )

        lines.append(
            f"Maximum alerts per incident: "
            f"{incidents['supporting_alert_count'].max()}"
        )

        lines.append(
            f"Maximum priority: "
            f"{incidents['max_priority_score'].max():.4f}"
        )

        lines.append(
            f"Maximum dynamic risk: "
            f"{incidents['max_dynamic_risk'].max():.4f}"
        )

        lines.append("")
        lines.append(
            "LIFECYCLE DISTRIBUTION"
        )
        lines.append(
            "----------------------"
        )

        lifecycle = (
            incidents[
                "lifecycle_state"
            ]
            .value_counts()
        )

        for state in [
            "ESCALATING",
            "ACTIVE",
            "MONITORING",
            "RESOLVED"
        ]:

            lines.append(
                f"{state}: "
                f"{int(lifecycle.get(state, 0))}"
            )

        lines.append("")
        lines.append(
            "PRIORITY DISTRIBUTION"
        )
        lines.append(
            "---------------------"
        )

        priority = (
            incidents[
                "priority_level"
            ]
            .value_counts()
        )

        for level in [
            "IMMEDIATE",
            "URGENT",
            "HIGH",
            "NORMAL",
            "LOW"
        ]:

            lines.append(
                f"{level}: "
                f"{int(priority.get(level, 0))}"
            )

        lines.append("")
        lines.append(
            "CROSS-CAMERA INCIDENTS"
        )
        lines.append(
            "----------------------"
        )

        lines.append(
            f"Cross-camera incidents: "
            f"{int(incidents['cross_camera_event'].sum())}"
        )

        lines.append("")
        lines.append(
            "TOP INCIDENTS"
        )
        lines.append(
            "-------------"
        )

        for _, incident in (
            incidents.head(10).iterrows()
        ):

            lines.append(
                f"#{int(incident['incident_queue_position']):02d} | "
                f"{incident['incident_id']} | "
                f"Vehicle {int(incident['track_id'])} | "
                f"{incident['lifecycle_state']} | "
                f"Priority "
                f"{incident['max_priority_score']:.2f}"
            )

            lines.append(
                f"  Frames: "
                f"{int(incident['start_frame'])}"
                f"-"
                f"{int(incident['end_frame'])}"
            )

            lines.append(
                f"  Camera: "
                f"{incident['camera_path']}"
            )

            lines.append(
                f"  Supporting alerts: "
                f"{int(incident['supporting_alert_count'])}"
            )

    lines.append("")
    lines.append(
        "DATASET LIMITATION"
    )
    lines.append(
        "------------------"
    )

    lines.append(
        "Current camera paths are deterministic "
        "development segments derived from the "
        "single source video. They do not represent "
        "physical camera metadata or independently "
        "verified cross-camera identity."
    )

    output_file.write_text(
        "\n".join(lines)
    )

    return output_file


# ============================================================
# SAVE OUTPUTS
# ============================================================

def save_outputs(
    alerts,
    incidents,
    groups
):

    incident_file = (
        OUTPUT_DIR
        / "day14_incident_alerts.csv"
    )

    queue_file = (
        OUTPUT_DIR
        / "day14_operator_incident_queue.csv"
    )

    history_file = (
        OUTPUT_DIR
        / "day14_alert_history.csv"
    )

    statistics_file = (
        OUTPUT_DIR
        / "day14_statistics.txt"
    )

    queue = build_operator_queue(
        incidents
    )

    history = build_alert_history(
        alerts,
        groups,
        incidents
    )

    incidents.to_csv(
        incident_file,
        index=False
    )

    queue.to_csv(
        queue_file,
        index=False
    )

    history.to_csv(
        history_file,
        index=False
    )

    write_statistics(
        alerts,
        incidents
    )

    print()
    print(
        "OUTPUTS"
    )
    print("-" * 70)

    print(incident_file)
    print(queue_file)
    print(history_file)
    print(statistics_file)

    return (
        incidents,
        queue,
        history
    )


# ============================================================
# MAIN
# ============================================================

def main():

    alerts = load_alerts()

    alerts = normalize_alerts(
        alerts
    )

    incidents, groups = (
        build_incidents(
            alerts
        )
    )

    print()
    print(
        "INCIDENT LIFECYCLE DISTRIBUTION"
    )
    print("-" * 70)

    if not incidents.empty:

        print(
            incidents[
                "lifecycle_state"
            ].value_counts()
        )

    print()
    print(
        "TOP INCIDENTS"
    )
    print("-" * 70)

    if not incidents.empty:

        for _, incident in (
            incidents.head(10).iterrows()
        ):

            print(
                f"#{int(incident['incident_queue_position']):02d} | "
                f"Vehicle {int(incident['track_id']):>4} | "
                f"{incident['lifecycle_state']:<11} | "
                f"Priority "
                f"{incident['max_priority_score']:6.2f} | "
                f"Alerts "
                f"{int(incident['supporting_alert_count']):>3} | "
                f"{incident['camera_path']}"
            )

    (
        incidents,
        queue,
        history
    ) = save_outputs(
        alerts,
        incidents,
        groups
    )

    print()
    print("=" * 70)
    print(
        "DAY 14 ALERT LIFECYCLE MANAGEMENT COMPLETE"
    )
    print("=" * 70)

    print(
        f"Frame alerts: {len(alerts)}"
    )

    print(
        f"Incidents: {len(incidents)}"
    )

    if len(alerts) > 0:

        reduction = (
            1
            - (
                len(incidents)
                / len(alerts)
            )
        ) * 100

        print(
            f"Alert reduction: {reduction:.2f}%"
        )

    print(
        f"Cross-camera incidents: "
        f"{int(incidents['cross_camera_event'].sum())}"
    )


if __name__ == "__main__":
    main()
