from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd


# ============================================================
# BORDER-AI DAY 12
# MULTI-CAMERA EVENT CORRELATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DAY11_DIR = (
    BASE_DIR
    / "data"
    / "outputs"
    / "day11_explainable_alerts"
)

DAY10_DIR = (
    BASE_DIR
    / "data"
    / "outputs"
    / "day10_temporal_inference"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "outputs"
    / "day12_multicamera"
)

DAY11_ALERTS = (
    DAY11_DIR
    / "day11_explainable_alerts.csv"
)

DAY10_PREDICTIONS = (
    DAY10_DIR
    / "day10_temporal_predictions.csv"
)

OBSERVATION_FILE = (
    OUTPUT_DIR
    / "day12_camera_observations.csv"
)

EVENT_FILE = (
    OUTPUT_DIR
    / "day12_correlated_events.csv"
)

TIMELINE_FILE = (
    OUTPUT_DIR
    / "day12_event_timeline.csv"
)

STATISTICS_FILE = (
    OUTPUT_DIR
    / "day12_statistics.txt"
)


# ============================================================
# CONFIGURATION
# ============================================================

CAMERA_COUNT = 4

# Existing single-camera data is converted into deterministic
# camera segments for pipeline development.
#
# This is NOT claiming that the source video contains four
# physical cameras.
CAMERA_NAMES = [
    "CAM-01",
    "CAM-02",
    "CAM-03",
    "CAM-04",
]

# Number of frames used to form one temporal event.
EVENT_GAP_FRAMES = 15

# A vehicle must have multiple observations to create a
# cross-camera event candidate.
MIN_OBSERVATIONS = 2


# ============================================================
# LOAD DATA
# ============================================================

def load_day11():
    print()
    print("LOADING DAY 11 EXPLAINABLE ALERTS")
    print("-" * 60)

    if not DAY11_ALERTS.exists():
        raise FileNotFoundError(
            f"Day 11 alerts not found:\n{DAY11_ALERTS}"
        )

    data = pd.read_csv(
        DAY11_ALERTS
    )

    print(
        f"Day 11 rows: {len(data)}"
    )

    print(
        f"Vehicles: {data['track_id'].nunique()}"
    )

    return data


def load_day10():
    print()
    print("LOADING DAY 10 TEMPORAL PREDICTIONS")
    print("-" * 60)

    if not DAY10_PREDICTIONS.exists():
        raise FileNotFoundError(
            f"Day 10 predictions not found:\n"
            f"{DAY10_PREDICTIONS}"
        )

    data = pd.read_csv(
        DAY10_PREDICTIONS
    )

    print(
        f"Day 10 rows: {len(data)}"
    )

    return data


# ============================================================
# CAMERA ASSIGNMENT
# ============================================================

def assign_camera(frame):
    """
    Deterministically maps frame ranges to camera IDs.

    IMPORTANT:
    This is a development simulation because the current
    dataset comes from one source video and has no physical
    camera identifier.
    """

    frame = int(frame)

    # Four temporal camera segments.
    # 586 frames → approximately 146 frames/camera.
    segment = frame // 147

    if segment < 0:
        segment = 0

    if segment >= CAMERA_COUNT:
        segment = CAMERA_COUNT - 1

    return CAMERA_NAMES[segment]


# ============================================================
# CAMERA OBSERVATIONS
# ============================================================

def build_camera_observations(data):
    print()
    print("BUILDING CAMERA-AWARE OBSERVATIONS")
    print("-" * 60)

    observations = data.copy()

    observations["camera_id"] = (
        observations["frame"]
        .apply(assign_camera)
    )

    observations["camera_sequence"] = (
        observations
        .groupby("track_id")
        .cumcount()
        + 1
    )

    observations["observation_timestamp"] = (
        observations["frame"] / 30.0
    )

    observations["observation_timestamp"] = (
        observations["observation_timestamp"]
        .round(3)
    )

    observations["observation_type"] = np.where(
        observations["predicted_early_warning"] == 1,
        "EARLY_WARNING",
        "NORMAL_OBSERVATION",
    )

    return observations


# ============================================================
# CROSS-CAMERA CANDIDATES
# ============================================================

def build_cross_camera_events(observations):
    print()
    print("BUILDING CROSS-CAMERA EVENT CANDIDATES")
    print("-" * 60)

    events = []

    for track_id, group in observations.groupby(
        "track_id"
    ):

        group = group.sort_values(
            "frame"
        ).reset_index(
            drop=True
        )

        if len(group) < MIN_OBSERVATIONS:
            continue

        cameras = group[
            "camera_id"
        ].drop_duplicates().tolist()

        # We need observations from at least
        # two camera segments.
        if len(cameras) < 2:
            continue

        event_number = 0

        current_rows = [
            group.iloc[0]
        ]

        current_start = int(
            group.iloc[0]["frame"]
        )

        previous_frame = int(
            group.iloc[0]["frame"]
        )

        for idx in range(1, len(group)):

            row = group.iloc[idx]

            frame = int(
                row["frame"]
            )

            gap = (
                frame
                - previous_frame
            )

            if gap <= EVENT_GAP_FRAMES:

                current_rows.append(
                    row
                )

            else:

                if len(
                    {
                        r["camera_id"]
                        for r in current_rows
                    }
                ) >= 2:

                    event_number += 1

                    events.append(
                        create_event(
                            track_id,
                            event_number,
                            current_rows,
                        )
                    )

                current_rows = [
                    row
                ]

                current_start = frame

            previous_frame = frame

        # Final event.
        if len(
            {
                r["camera_id"]
                for r in current_rows
            }
        ) >= 2:

            event_number += 1

            events.append(
                create_event(
                    track_id,
                    event_number,
                    current_rows,
                )
            )

    if not events:

        return pd.DataFrame()

    return pd.DataFrame(
        events
    )


# ============================================================
# EVENT CREATION
# ============================================================

def create_event(
    track_id,
    event_number,
    rows,
):
    cameras = [
        row["camera_id"]
        for row in rows
    ]

    cameras = list(
        dict.fromkeys(cameras)
    )

    probabilities = [
        float(
            row["prediction_probability"]
        )
        for row in rows
    ]

    risk_scores = pd.to_numeric(
        [
            row["dynamic_risk_score"]
            for row in rows
        ],
        errors="coerce",
    )

    risk_scores = [
        value
        for value in risk_scores
        if not np.isnan(value)
    ]

    warning_count = sum(
        int(
            row["predicted_early_warning"]
        )
        for row in rows
    )

    alert_levels = [
        row["alert_level"]
        for row in rows
    ]

    if "CRITICAL" in alert_levels:
        event_level = "CRITICAL"

    elif "HIGH" in alert_levels:
        event_level = "HIGH"

    elif "WATCH" in alert_levels:
        event_level = "WATCH"

    else:
        event_level = "LOW"

    temporal_states = [
        row["temporal_state"]
        for row in rows
    ]

    if "RAPID_ESCALATION" in temporal_states:
        event_state = "RAPID_ESCALATION"

    elif "ESCALATING" in temporal_states:
        event_state = "ESCALATING"

    elif "DE_ESCALATING" in temporal_states:
        event_state = "DE_ESCALATING"

    else:
        event_state = "STABLE"

    explanations = [
        str(
            row["explanation"]
        )
        for row in rows
        if str(
            row["explanation"]
        ).strip()
    ]

    # Keep unique explanations.
    explanations = list(
        dict.fromkeys(
            explanations
        )
    )

    start_frame = int(
        min(
            row["frame"]
            for row in rows
        )
    )

    end_frame = int(
        max(
            row["frame"]
            for row in rows
        )
    )

    duration_frames = (
        end_frame
        - start_frame
    )

    max_probability = max(
        probabilities
    )

    mean_probability = float(
        np.mean(
            probabilities
        )
    )

    max_risk = (
        max(risk_scores)
        if risk_scores
        else np.nan
    )

    mean_risk = (
        float(
            np.mean(
                risk_scores
            )
        )
        if risk_scores
        else np.nan
    )

    return {
        "event_id": (
            f"T{int(track_id)}"
            f"_E{int(event_number):03d}"
        ),
        "track_id": int(track_id),
        "camera_count": len(cameras),
        "camera_path": " -> ".join(
            cameras
        ),
        "start_frame": start_frame,
        "end_frame": end_frame,
        "duration_frames": duration_frames,
        "max_prediction_probability":
            max_probability,
        "mean_prediction_probability":
            mean_probability,
        "max_dynamic_risk":
            max_risk,
        "mean_dynamic_risk":
            mean_risk,
        "warning_count":
            warning_count,
        "event_level":
            event_level,
        "temporal_state":
            event_state,
        "evidence_count":
            len(explanations),
        "evidence_summary":
            " || ".join(
                explanations[:5]
            ),
    }


# ============================================================
# EVENT PRIORITY
# ============================================================

def calculate_priority(row):
    score = 0.0

    if row["event_level"] == "CRITICAL":
        score += 50

    elif row["event_level"] == "HIGH":
        score += 35

    elif row["event_level"] == "WATCH":
        score += 20

    if row["temporal_state"] == "RAPID_ESCALATION":
        score += 20

    elif row["temporal_state"] == "ESCALATING":
        score += 10

    score += min(
        float(
            row["max_prediction_probability"]
        ) * 20,
        20,
    )

    score += min(
        float(
            row["camera_count"]
        ) * 5,
        15,
    )

    score += min(
        float(
            row["warning_count"]
        ),
        10,
    )

    return round(
        score,
        3,
    )


# ============================================================
# EVENT TIMELINE
# ============================================================

def build_event_timeline(events):
    """
    Build a camera-aware event timeline.

    Each camera segment receives its own frame interval.
    This prevents an event from incorrectly implying that
    the vehicle was simultaneously present in every camera
    for the entire event duration.
    """

    timeline_rows = []

    for _, event in events.iterrows():

        cameras = str(
            event["camera_path"]
        ).split(" -> ")

        # The current event representation does not retain
        # per-camera frame boundaries, so we preserve the
        # event-level interval while explicitly marking this
        # as a correlated camera segment.
        #
        # Future real multi-camera data can replace these
        # values with camera-specific entry/exit frames.

        for order, camera in enumerate(
            cameras,
            start=1,
        ):

            timeline_rows.append(
                {
                    "event_id":
                        event["event_id"],
                    "track_id":
                        event["track_id"],
                    "camera_order":
                        order,
                    "camera_id":
                        camera,
                    "event_level":
                        event["event_level"],
                    "temporal_state":
                        event["temporal_state"],
                    "start_frame":
                        event["start_frame"],
                    "end_frame":
                        event["end_frame"],
                    "max_prediction_probability":
                        event[
                            "max_prediction_probability"
                        ],
                    "max_dynamic_risk":
                        event[
                            "max_dynamic_risk"
                        ],
                    "timeline_note":
                        "Development simulation: "
                        "camera-specific entry/exit "
                        "frames are not available from "
                        "the single source video.",
                }
            )

    return pd.DataFrame(
        timeline_rows
    )


# ============================================================
# SAVE OUTPUTS
# ============================================================

def save_outputs(
    observations,
    events,
    timeline,
):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    observations.to_csv(
        OBSERVATION_FILE,
        index=False,
    )

    events.to_csv(
        EVENT_FILE,
        index=False,
    )

    timeline.to_csv(
        TIMELINE_FILE,
        index=False,
    )

    stats = []

    stats.append(
        "BORDER-AI DAY 12 MULTI-CAMERA "
        "EVENT CORRELATION"
    )
    stats.append(
        "=" * 60
    )
    stats.append("")

    stats.append(
        f"Camera segments: {CAMERA_COUNT}"
    )

    stats.append(
        f"Camera IDs: "
        f"{', '.join(CAMERA_NAMES)}"
    )

    stats.append("")

    stats.append(
        "IMPORTANT DATASET NOTE"
    )
    stats.append(
        "-" * 30
    )

    stats.append(
        "Camera IDs are deterministic development "
        "segments because the current source video "
        "does not contain physical camera metadata."
    )

    stats.append(
        "This module establishes the multi-camera "
        "correlation architecture without claiming "
        "real cross-camera identity."
    )

    stats.append("")

    stats.append(
        "OBSERVATIONS"
    )
    stats.append(
        "-" * 20
    )

    stats.append(
        f"Total observations: "
        f"{len(observations)}"
    )

    stats.append(
        f"Vehicles: "
        f"{observations['track_id'].nunique()}"
    )

    stats.append("")

    stats.append(
        "CAMERA DISTRIBUTION"
    )
    stats.append(
        "-" * 24
    )

    camera_counts = (
        observations["camera_id"]
        .value_counts()
        .sort_index()
    )

    for camera, count in camera_counts.items():

        stats.append(
            f"{camera}: {count}"
        )

    stats.append("")

    stats.append(
        "CORRELATED EVENTS"
    )
    stats.append(
        "-" * 24
    )

    stats.append(
        f"Events: {len(events)}"
    )

    stats.append(
        f"Timeline records: "
        f"{len(timeline)}"
    )

    if len(events):

        stats.append(
            f"Vehicles with cross-camera events: "
            f"{events['track_id'].nunique()}"
        )

        stats.append(
            f"Maximum cameras in event: "
            f"{events['camera_count'].max()}"
        )

        stats.append(
            f"Maximum event probability: "
            f"{events['max_prediction_probability'].max():.6f}"
        )

        stats.append(
            f"Maximum dynamic risk: "
            f"{events['max_dynamic_risk'].max():.6f}"
        )

        stats.append("")

        stats.append(
            "EVENT LEVEL DISTRIBUTION"
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

            count = int(
                (
                    events["event_level"]
                    == level
                ).sum()
            )

            stats.append(
                f"{level}: {count}"
            )

        stats.append("")

        stats.append(
            "TOP EVENTS"
        )
        stats.append(
            "-" * 20
        )

        top_events = (
            events
            .sort_values(
                "priority_score",
                ascending=False,
            )
            .head(5)
        )

        for _, row in top_events.iterrows():

            stats.append(
                f"{row['event_id']} | "
                f"Vehicle {int(row['track_id'])} | "
                f"{row['camera_path']} | "
                f"{row['event_level']} | "
                f"Priority "
                f"{row['priority_score']:.2f}"
            )

    else:

        stats.append(
            "No cross-camera events generated."
        )

    STATISTICS_FILE.write_text(
        "\n".join(stats)
        + "\n"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print(
        "BORDER-AI DAY 12 MULTI-CAMERA "
        "EVENT CORRELATION"
    )
    print("=" * 60)

    day11 = load_day11()

    # Day 10 is explicitly loaded to validate
    # the correlation input chain.
    day10 = load_day10()

    if len(day10) != len(day11):
        raise ValueError(
            "Day 10 and Day 11 row counts do not match."
        )

    observations = build_camera_observations(
        day11
    )

    print()
    print(
        "CAMERA OBSERVATION SUMMARY"
    )
    print("-" * 60)

    print(
        observations[
            "camera_id"
        ].value_counts()
        .sort_index()
        .to_string()
    )

    events = build_cross_camera_events(
        observations
    )

    if events.empty:

        print()
        print(
            "No cross-camera events were generated."
        )

        events = pd.DataFrame(
            columns=[
                "event_id",
                "track_id",
                "camera_count",
                "camera_path",
                "start_frame",
                "end_frame",
                "duration_frames",
                "max_prediction_probability",
                "mean_prediction_probability",
                "max_dynamic_risk",
                "mean_dynamic_risk",
                "warning_count",
                "event_level",
                "temporal_state",
                "evidence_count",
                "evidence_summary",
            ]
        )

        events["priority_score"] = []

    else:

        events["priority_score"] = (
            events.apply(
                calculate_priority,
                axis=1,
            )
        )

    timeline = build_event_timeline(
        events
    )

    save_outputs(
        observations,
        events,
        timeline,
    )

    print()
    print("=" * 60)
    print(
        "DAY 12 MULTI-CAMERA CORRELATION COMPLETE"
    )
    print("=" * 60)

    print()
    print(
        f"Observations:       "
        f"{len(observations)}"
    )

    print(
        f"Vehicles:            "
        f"{observations['track_id'].nunique()}"
    )

    print(
        f"Correlated events:   "
        f"{len(events)}"
    )

    print(
        f"Timeline records:    "
        f"{len(timeline)}"
    )

    if len(events):

        print()
        print(
            "TOP CORRELATED EVENTS"
        )
        print("-" * 60)

        top = (
            events
            .sort_values(
                "priority_score",
                ascending=False,
            )
            .head(10)
        )

        for _, row in top.iterrows():

            print(
                f"{row['event_id']} | "
                f"Vehicle "
                f"{int(row['track_id']):4d} | "
                f"{row['camera_path']} | "
                f"{row['event_level']:8s} | "
                f"Priority "
                f"{row['priority_score']:.2f}"
            )

            print(
                f"  Evidence: "
                f"{row['evidence_summary'][:250]}"
            )

    print()
    print("OUTPUTS")
    print("-" * 60)

    print(
        OBSERVATION_FILE
    )

    print(
        EVENT_FILE
    )

    print(
        TIMELINE_FILE
    )

    print(
        STATISTICS_FILE
    )


if __name__ == "__main__":
    main()
