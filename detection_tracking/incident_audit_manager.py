"""
BORDER-AI Day 15
Incident Audit & Operator Evidence Management

Purpose:
    Convert Day 14 incident lifecycle records into an auditable,
    evidence-based incident record suitable for an operator dashboard.

This module does NOT train a new ML model.

It provides:
    - Incident evidence extraction
    - Priority justification
    - Risk evidence
    - Temporal evidence
    - Cross-camera evidence
    - Operator response recommendation
    - Audit trail
    - Incident-level statistics
    - Data-quality validation

Source:
    Day 14 alert lifecycle management

Outputs:
    data/outputs/day15_incident_audit/
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_DIR = BASE_DIR / "data" / "outputs" / "day14_alert_lifecycle"
OUTPUT_DIR = BASE_DIR / "data" / "outputs" / "day15_incident_audit"

INCIDENT_FILE = INPUT_DIR / "day14_incident_alerts.csv"
QUEUE_FILE = INPUT_DIR / "day14_operator_incident_queue.csv"
HISTORY_FILE = INPUT_DIR / "day14_alert_history.csv"

AUDIT_FILE = OUTPUT_DIR / "day15_incident_audit.csv"
EVIDENCE_FILE = OUTPUT_DIR / "day15_incident_evidence.csv"
QUEUE_FILE_OUT = OUTPUT_DIR / "day15_operator_audit_queue.csv"
SUMMARY_FILE = OUTPUT_DIR / "day15_audit_summary.csv"
STATS_FILE = OUTPUT_DIR / "day15_statistics.txt"


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_text(value, default=""):
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if text.lower() in {"nan", "none", "nat"}:
        return default

    return text


def normalize_bool(value):
    if isinstance(value, bool):
        return value

    text = safe_text(value).upper()

    return text in {
        "TRUE",
        "1",
        "YES",
        "Y",
        "CROSS_CAMERA",
    }


def ensure_columns(df: pd.DataFrame, columns: dict) -> pd.DataFrame:
    """
    Ensure expected columns exist.

    columns:
        {column_name: default_value}
    """

    df = df.copy()

    for column, default in columns.items():
        if column not in df.columns:
            df[column] = default

    return df


# ---------------------------------------------------------------------
# LOADING
# ---------------------------------------------------------------------

def load_day14_data():
    print("\n" + "=" * 70)
    print("DAY 15 — INCIDENT AUDIT MANAGER")
    print("=" * 70)

    for path in [INCIDENT_FILE, QUEUE_FILE, HISTORY_FILE]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required Day 14 file not found:\n{path}"
            )

    incidents = pd.read_csv(INCIDENT_FILE)
    queue = pd.read_csv(QUEUE_FILE)
    history = pd.read_csv(HISTORY_FILE)

    print(f"Incident records : {len(incidents):,}")
    print(f"Queue records    : {len(queue):,}")
    print(f"History records  : {len(history):,}")

    return incidents, queue, history


# ---------------------------------------------------------------------
# NORMALIZATION
# ---------------------------------------------------------------------

def normalize_incidents(df: pd.DataFrame) -> pd.DataFrame:

    defaults = {
        "incident_id": "",
        "track_id": "",
        "event_id": "",
        "camera_path": "SINGLE-CAMERA",
        "start_frame": 0,
        "end_frame": 0,
        "duration_frames": 0,
        "supporting_alert_count": 0,
        "max_priority": 0.0,
        "max_prediction_probability": 0.0,
        "max_dynamic_risk": 0.0,
        "alert_level": "LOW",
        "priority_level": "NORMAL",
        "temporal_states": "",
        "lifecycle_state": "RESOLVED",
        "cross_camera": False,
        "explanation": "",
        "recommended_action": "",
        "queue_position": 0,
    }

    df = ensure_columns(df, defaults)

    numeric_columns = [
        "start_frame",
        "end_frame",
        "duration_frames",
        "supporting_alert_count",
        "max_priority",
        "max_prediction_probability",
        "max_dynamic_risk",
        "queue_position",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)

    text_columns = [
        "incident_id",
        "track_id",
        "event_id",
        "camera_path",
        "alert_level",
        "priority_level",
        "temporal_states",
        "lifecycle_state",
        "explanation",
        "recommended_action",
    ]

    for column in text_columns:
        df[column] = df[column].map(safe_text)

    df["cross_camera"] = df["cross_camera"].map(normalize_bool)

    return df


# ---------------------------------------------------------------------
# EVIDENCE EXTRACTION
# ---------------------------------------------------------------------

def build_priority_evidence(row):
    priority = safe_float(row["max_priority"])
    priority_level = safe_text(row["priority_level"], "NORMAL")

    reasons = []

    if priority >= 65:
        reasons.append(
            f"high operator priority score ({priority:.2f})"
        )
    elif priority >= 40:
        reasons.append(
            f"elevated operator priority score ({priority:.2f})"
        )
    else:
        reasons.append(
            f"routine operator priority score ({priority:.2f})"
        )

    if safe_text(row["alert_level"]).upper() in {
        "CRITICAL",
        "HIGH",
    }:
        reasons.append(
            f"{safe_text(row['alert_level']).upper()} alert level"
        )

    if safe_text(row["priority_level"]).upper() in {
        "URGENT",
        "IMMEDIATE",
    }:
        reasons.append(
            f"{priority_level} priority classification"
        )

    if normalize_bool(row["cross_camera"]):
        reasons.append(
            "cross-camera correlation available"
        )

    return "; ".join(reasons)


def build_risk_evidence(row):
    risk = safe_float(row["max_dynamic_risk"])
    probability = safe_float(row["max_prediction_probability"])

    evidence = []

    evidence.append(
        f"maximum dynamic risk={risk:.2f}"
    )

    evidence.append(
        f"maximum temporal warning probability={probability:.3f}"
    )

    alert_level = safe_text(row["alert_level"]).upper()

    if alert_level:
        evidence.append(
            f"alert level={alert_level}"
        )

    return "; ".join(evidence)


def build_temporal_evidence(row):
    states = safe_text(row["temporal_states"])

    if not states:
        states = "NOT_RECORDED"

    lifecycle = safe_text(
        row["lifecycle_state"],
        "RESOLVED"
    ).upper()

    return (
        f"observed temporal states={states}; "
        f"incident lifecycle={lifecycle}"
    )


def build_camera_evidence(row):
    camera_path = safe_text(
        row["camera_path"],
        "SINGLE-CAMERA"
    )

    if normalize_bool(row["cross_camera"]):
        return (
            f"cross-camera path observed: {camera_path}; "
            "camera correlation is based on the Day 12 development "
            "camera-segmentation architecture"
        )

    return (
        f"single-camera context: {camera_path}; "
        "no verified cross-camera transition recorded"
    )


# ---------------------------------------------------------------------
# OPERATOR ACTION
# ---------------------------------------------------------------------

def determine_operator_action(row):
    lifecycle = safe_text(
        row["lifecycle_state"],
        "RESOLVED"
    ).upper()

    priority = safe_text(
        row["priority_level"],
        "NORMAL"
    ).upper()

    alert_level = safe_text(
        row["alert_level"],
        "LOW"
    ).upper()

    cross_camera = normalize_bool(row["cross_camera"])

    if lifecycle == "ACTIVE" or priority in {"IMMEDIATE", "URGENT"}:
        return (
            "Review promptly, verify supporting evidence, "
            "and maintain active incident awareness."
        )

    if lifecycle == "ESCALATING":
        return (
            "Review the incident trend and supporting evidence; "
            "prepare for escalation if risk continues increasing."
        )

    if lifecycle == "MONITORING":
        if cross_camera:
            return (
                "Monitor the correlated camera path and retain "
                "supporting evidence for situational awareness."
            )

        return (
            "Monitor the incident and retain supporting evidence "
            "for situational awareness."
        )

    if alert_level in {"HIGH", "CRITICAL"}:
        return (
            "Review the supporting evidence and confirm whether "
            "operator intervention is required."
        )

    return (
        "Retain the incident record for audit and historical analysis."
    )


# ---------------------------------------------------------------------
# INCIDENT AUDIT
# ---------------------------------------------------------------------

def build_audit_records(incidents):
    records = []

    generated_at = datetime.now(timezone.utc).isoformat()

    for _, row in incidents.iterrows():

        incident_id = safe_text(
            row["incident_id"],
            f"INCIDENT_{len(records) + 1:04d}"
        )

        lifecycle = safe_text(
            row["lifecycle_state"],
            "RESOLVED"
        ).upper()

        record = {
            "audit_id": f"AUDIT_{len(records) + 1:04d}",
            "incident_id": incident_id,
            "track_id": safe_text(row["track_id"]),
            "event_id": safe_text(row["event_id"]),
            "camera_path": safe_text(
                row["camera_path"],
                "SINGLE-CAMERA"
            ),
            "start_frame": safe_int(row["start_frame"]),
            "end_frame": safe_int(row["end_frame"]),
            "duration_frames": safe_int(row["duration_frames"]),
            "supporting_alert_count": safe_int(
                row["supporting_alert_count"]
            ),
            "max_priority": safe_float(row["max_priority"]),
            "max_prediction_probability": safe_float(
                row["max_prediction_probability"]
            ),
            "max_dynamic_risk": safe_float(
                row["max_dynamic_risk"]
            ),
            "alert_level": safe_text(
                row["alert_level"],
                "LOW"
            ).upper(),
            "priority_level": safe_text(
                row["priority_level"],
                "NORMAL"
            ).upper(),
            "temporal_states": safe_text(
                row["temporal_states"]
            ),
            "lifecycle_state": lifecycle,
            "cross_camera": normalize_bool(
                row["cross_camera"]
            ),
            "priority_evidence": build_priority_evidence(row),
            "risk_evidence": build_risk_evidence(row),
            "temporal_evidence": build_temporal_evidence(row),
            "camera_evidence": build_camera_evidence(row),
            "original_explanation": safe_text(
                row["explanation"]
            ),
            "operator_action": determine_operator_action(row),
            "audit_status": (
                "REVIEW_REQUIRED"
                if lifecycle in {"ACTIVE", "ESCALATING"}
                else "RECORDED"
            ),
            "generated_at_utc": generated_at,
        }

        records.append(record)

    return pd.DataFrame(records)


# ---------------------------------------------------------------------
# EVIDENCE TABLE
# ---------------------------------------------------------------------

def build_evidence_table(audit_df):
    evidence_rows = []

    for _, row in audit_df.iterrows():

        evidence_rows.extend([
            {
                "incident_id": row["incident_id"],
                "evidence_type": "PRIORITY",
                "evidence": row["priority_evidence"],
                "severity": row["priority_level"],
            },
            {
                "incident_id": row["incident_id"],
                "evidence_type": "RISK",
                "evidence": row["risk_evidence"],
                "severity": row["alert_level"],
            },
            {
                "incident_id": row["incident_id"],
                "evidence_type": "TEMPORAL",
                "evidence": row["temporal_evidence"],
                "severity": row["lifecycle_state"],
            },
            {
                "incident_id": row["incident_id"],
                "evidence_type": "CAMERA",
                "evidence": row["camera_evidence"],
                "severity": (
                    "CROSS_CAMERA"
                    if row["cross_camera"]
                    else "SINGLE_CAMERA"
                ),
            },
        ])

    return pd.DataFrame(evidence_rows)


# ---------------------------------------------------------------------
# OPERATOR QUEUE
# ---------------------------------------------------------------------

def build_operator_queue(audit_df):
    queue = audit_df.copy()

    lifecycle_order = {
        "ACTIVE": 0,
        "ESCALATING": 1,
        "MONITORING": 2,
        "RESOLVED": 3,
    }

    queue["lifecycle_rank"] = queue[
        "lifecycle_state"
    ].map(lifecycle_order).fillna(99)

    queue = queue.sort_values(
        by=[
            "lifecycle_rank",
            "max_priority",
            "max_prediction_probability",
            "max_dynamic_risk",
        ],
        ascending=[
            True,
            False,
            False,
            False,
        ],
    ).reset_index(drop=True)

    queue["operator_queue_position"] = (
        np.arange(len(queue)) + 1
    )

    queue["operator_attention"] = queue.apply(
        lambda row: (
            "IMMEDIATE_REVIEW"
            if row["lifecycle_state"] == "ACTIVE"
            else
            "ESCALATION_REVIEW"
            if row["lifecycle_state"] == "ESCALATING"
            else
            "MONITOR"
            if row["lifecycle_state"] == "MONITORING"
            else
            "ARCHIVE"
        ),
        axis=1,
    )

    columns = [
        "operator_queue_position",
        "audit_id",
        "incident_id",
        "track_id",
        "event_id",
        "camera_path",
        "lifecycle_state",
        "priority_level",
        "alert_level",
        "max_priority",
        "max_prediction_probability",
        "max_dynamic_risk",
        "supporting_alert_count",
        "cross_camera",
        "operator_attention",
        "operator_action",
    ]

    return queue[columns].copy()


# ---------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------

def build_summary(audit_df):
    rows = []

    rows.append({
        "metric": "incidents",
        "value": len(audit_df),
    })

    rows.append({
        "metric": "cross_camera_incidents",
        "value": int(audit_df["cross_camera"].sum()),
    })

    rows.append({
        "metric": "active_incidents",
        "value": int(
            (audit_df["lifecycle_state"] == "ACTIVE").sum()
        ),
    })

    rows.append({
        "metric": "escalating_incidents",
        "value": int(
            (audit_df["lifecycle_state"] == "ESCALATING").sum()
        ),
    })

    rows.append({
        "metric": "monitoring_incidents",
        "value": int(
            (audit_df["lifecycle_state"] == "MONITORING").sum()
        ),
    })

    rows.append({
        "metric": "resolved_incidents",
        "value": int(
            (audit_df["lifecycle_state"] == "RESOLVED").sum()
        ),
    })

    rows.append({
        "metric": "mean_supporting_alerts",
        "value": round(
            audit_df["supporting_alert_count"].mean(),
            4,
        ),
    })

    rows.append({
        "metric": "max_supporting_alerts",
        "value": int(
            audit_df["supporting_alert_count"].max()
        ),
    })

    rows.append({
        "metric": "mean_priority",
        "value": round(
            audit_df["max_priority"].mean(),
            4,
        ),
    })

    rows.append({
        "metric": "max_priority",
        "value": round(
            audit_df["max_priority"].max(),
            4,
        ),
    })

    rows.append({
        "metric": "mean_dynamic_risk",
        "value": round(
            audit_df["max_dynamic_risk"].mean(),
            4,
        ),
    })

    rows.append({
        "metric": "max_dynamic_risk",
        "value": round(
            audit_df["max_dynamic_risk"].max(),
            4,
        ),
    })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------------------

def write_statistics(
    incidents,
    audit_df,
    evidence_df,
    queue_df,
    summary_df,
):
    lines = []

    lines.append("BORDER-AI DAY 15")
    lines.append("INCIDENT AUDIT & OPERATOR EVIDENCE MANAGEMENT")
    lines.append("=" * 60)
    lines.append("")

    lines.append(
        f"Generated UTC: "
        f"{datetime.now(timezone.utc).isoformat()}"
    )
    lines.append("")

    lines.append("INPUT")
    lines.append("-" * 60)
    lines.append(
        f"Day 14 incidents: {len(incidents):,}"
    )
    lines.append("")

    lines.append("AUDIT")
    lines.append("-" * 60)
    lines.append(
        f"Audit records: {len(audit_df):,}"
    )
    lines.append(
        f"Evidence records: {len(evidence_df):,}"
    )
    lines.append(
        f"Operator queue records: {len(queue_df):,}"
    )
    lines.append("")

    lines.append("LIFECYCLE DISTRIBUTION")
    lines.append("-" * 60)

    lifecycle_counts = (
        audit_df["lifecycle_state"]
        .value_counts()
        .to_dict()
    )

    for key in [
        "ACTIVE",
        "ESCALATING",
        "MONITORING",
        "RESOLVED",
    ]:
        lines.append(
            f"{key}: {lifecycle_counts.get(key, 0)}"
        )

    lines.append("")

    lines.append("PRIORITY DISTRIBUTION")
    lines.append("-" * 60)

    priority_counts = (
        audit_df["priority_level"]
        .value_counts()
        .to_dict()
    )

    for key in [
        "IMMEDIATE",
        "URGENT",
        "HIGH",
        "NORMAL",
        "LOW",
    ]:
        lines.append(
            f"{key}: {priority_counts.get(key, 0)}"
        )

    lines.append("")

    lines.append("RISK")
    lines.append("-" * 60)
    lines.append(
        f"Mean priority: "
        f"{audit_df['max_priority'].mean():.4f}"
    )
    lines.append(
        f"Maximum priority: "
        f"{audit_df['max_priority'].max():.4f}"
    )
    lines.append(
        f"Mean dynamic risk: "
        f"{audit_df['max_dynamic_risk'].mean():.4f}"
    )
    lines.append(
        f"Maximum dynamic risk: "
        f"{audit_df['max_dynamic_risk'].max():.4f}"
    )

    lines.append("")

    lines.append("CROSS-CAMERA")
    lines.append("-" * 60)
    lines.append(
        f"Cross-camera incidents: "
        f"{int(audit_df['cross_camera'].sum())}"
    )

    lines.append("")

    lines.append("DATA QUALITY")
    lines.append("-" * 60)

    audit_nan = int(audit_df.isna().sum().sum())
    evidence_nan = int(evidence_df.isna().sum().sum())
    queue_nan = int(queue_df.isna().sum().sum())

    duplicate_audits = int(
        audit_df["audit_id"].duplicated().sum()
    )

    duplicate_incidents = int(
        audit_df["incident_id"].duplicated().sum()
    )

    duplicate_queue_positions = int(
        queue_df["operator_queue_position"]
        .duplicated()
        .sum()
    )

    lines.append(f"Audit NaNs: {audit_nan}")
    lines.append(f"Evidence NaNs: {evidence_nan}")
    lines.append(f"Queue NaNs: {queue_nan}")
    lines.append(f"Duplicate audit IDs: {duplicate_audits}")
    lines.append(
        f"Duplicate incident IDs: {duplicate_incidents}"
    )
    lines.append(
        f"Duplicate queue positions: "
        f"{duplicate_queue_positions}"
    )

    result = (
        audit_nan == 0
        and evidence_nan == 0
        and queue_nan == 0
        and duplicate_audits == 0
        and duplicate_incidents == 0
        and duplicate_queue_positions == 0
    )

    lines.append("")
    lines.append(
        f"DAY 15 DATA QUALITY RESULT: "
        f"{'PASS' if result else 'FAIL'}"
    )

    STATS_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return result


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    incidents, queue, history = load_day14_data()

    incidents = normalize_incidents(incidents)

    print("\nBuilding incident audit records...")
    audit_df = build_audit_records(incidents)

    print("Building evidence records...")
    evidence_df = build_evidence_table(audit_df)

    print("Building operator audit queue...")
    operator_queue = build_operator_queue(audit_df)

    print("Building summary...")
    summary_df = build_summary(audit_df)

    audit_df.to_csv(
        AUDIT_FILE,
        index=False,
    )

    evidence_df.to_csv(
        EVIDENCE_FILE,
        index=False,
    )

    operator_queue.to_csv(
        QUEUE_FILE_OUT,
        index=False,
    )

    summary_df.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    quality_pass = write_statistics(
        incidents,
        audit_df,
        evidence_df,
        operator_queue,
        summary_df,
    )

    print("\n" + "=" * 70)
    print("DAY 15 COMPLETE")
    print("=" * 70)

    print(
        f"Incident audits       : {len(audit_df):,}"
    )
    print(
        f"Evidence records      : {len(evidence_df):,}"
    )
    print(
        f"Operator queue        : {len(operator_queue):,}"
    )

    print("\nLifecycle distribution:")
    print(
        audit_df["lifecycle_state"]
        .value_counts()
        .to_string()
    )

    print("\nPriority distribution:")
    print(
        audit_df["priority_level"]
        .value_counts()
        .to_string()
    )

    print(
        f"\nCross-camera incidents: "
        f"{int(audit_df['cross_camera'].sum())}"
    )

    print(
        f"Maximum priority      : "
        f"{audit_df['max_priority'].max():.4f}"
    )

    print(
        f"Maximum dynamic risk  : "
        f"{audit_df['max_dynamic_risk'].max():.4f}"
    )

    print("\nOutputs:")
    print(f"  {AUDIT_FILE}")
    print(f"  {EVIDENCE_FILE}")
    print(f"  {QUEUE_FILE_OUT}")
    print(f"  {SUMMARY_FILE}")
    print(f"  {STATS_FILE}")

    print(
        f"\nDATA QUALITY: "
        f"{'PASS' if quality_pass else 'FAIL'}"
    )

    if not quality_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
