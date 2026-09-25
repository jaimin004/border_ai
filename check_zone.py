import cv2
from zone_logic import ZONES

VIDEO_PATH = "video.mp4"

cap = cv2.VideoCapture(VIDEO_PATH)
ret, frame = cap.read()
if not ret:
    print("Could not read a frame.")
    exit()

h, w = frame.shape[:2]
print(f"Video frame size: {w}x{h}")

# Draw the CURRENT zone polygon on the frame so you can see if it lines up
# with anywhere a person would actually walk.
for zone_name, polygon in ZONES.items():
    pts = [(int(x), int(y)) for x, y in polygon]
    for i in range(len(pts)):
        cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], (0, 0, 255), 3)
    cv2.putText(frame, zone_name, pts[0], cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

cv2.imwrite("zone_check.jpg", frame)
print("Saved zone_check.jpg — open it and see if the red box overlaps where the person actually walks.")
print(f"If not, edit ZONES in zone_logic.py — coordinates should be within (0,0) to ({w},{h}).")
