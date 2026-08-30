from pathlib import Path
import csv

LABEL_DIR = Path("runs/detect/runs/track/day3_tracking_data/labels")
OUTPUT = Path("data/outputs/day4_trajectories.csv")

rows = []

for label_file in sorted(LABEL_DIR.glob("traffic_test_*.txt")):
    frame_text = label_file.stem.replace("traffic_test_", "")
    if not frame_text.isdigit():
        continue

    frame = int(frame_text)

    with label_file.open() as f:
        for line in f:
            parts = line.strip().split()

            if len(parts) < 6:
                continue

            class_id = int(parts[0])
            center_x = float(parts[1])
            center_y = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])
            track_id = int(parts[5])

            rows.append([
                frame,
                track_id,
                class_id,
                center_x,
                center_y,
                width,
                height
            ])

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "frame",
        "track_id",
        "class_id",
        "center_x",
        "center_y",
        "width",
        "height"
    ])
    writer.writerows(sorted(rows, key=lambda r: (r[0], r[1])))

print("Trajectory extraction complete")
print("Rows:", len(rows))
print("Output:", OUTPUT)
print("Frames:", len(set(r[0] for r in rows)))
print("Unique track IDs:", len(set(r[1] for r in rows)))
