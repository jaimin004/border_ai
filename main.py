import cv2
import easyocr
from ultralytics import YOLO

PLATE_MODEL_PATH = "runs/detect/indian_plate_finetune/weights/best.pt"  # fine-tuned on Indian plates
VIDEO_PATH = "sample.mp4"
OUTPUT_PATH = "output_license_plate.mp4"

# Load models once
model = YOLO(PLATE_MODEL_PATH)
reader = easyocr.Reader(["en"], gpu=False)


def preprocess_plate(crop):
    """Grayscale + adaptive upscale + local contrast boost.

    No hard threshold here. Otsu binarization is a Tesseract-era trick —
    it helps a classical OCR engine that expects clean black/white document
    text. EasyOCR is a neural model trained on natural grayscale/color crops,
    so forcing a hard black/white threshold tends to destroy the detail it
    actually relies on. That was likely the single biggest accuracy killer.
    """
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # Adaptive upscale: target a minimum height of ~150px regardless of how
    # small the detected box was. A flat 2x is nowhere near enough when the
    # plate box itself is only 25-40px tall, which is common on video with
    # a vehicle that isn't right next to the camera.
    h, w = gray.shape[:2]
    if h == 0 or w == 0:
        return gray
    target_h = 150
    scale = max(1.0, target_h / h)
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.bilateralFilter(gray, 9, 40, 40)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    return enhanced


def read_plate_text(processed_crop):
    """OCR via EasyOCR, filtering out low-confidence noise fragments
    before they get concatenated into the final (garbage) string."""
    results = reader.readtext(processed_crop)

    if not results:
        return "", 0.0

    words, confs = [], []
    for _bbox, text, conf in results:
        text = text.strip()
        # Drop fragments EasyOCR itself isn't confident about — these are
        # usually what turns a real plate into something like "#A-T-IMI".
        if text and conf > 0.25:
            words.append(text)
            confs.append(conf)

    if not words:
        return "", 0.0

    plate_text = "".join(words).upper().replace(" ", "")
    ocr_confidence = round((sum(confs) / len(confs)) * 100, 1)
    return plate_text, ocr_confidence


def detect_plates(frame, pad_ratio=0.15):
    """YOLO plate detection with a small padding margin added to each box.
    A tight box sometimes clips the leftmost/rightmost character, which
    OCR then either misses or misreads."""
    results = model(frame, verbose=False)[0]
    h, w = frame.shape[:2]
    plates = []

    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        detect_conf = float(box.conf[0])

        box_w, box_h = x2 - x1, y2 - y1
        pad_x = int(box_w * pad_ratio)
        pad_y = int(box_h * pad_ratio)

        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        plates.append((crop, detect_conf, (x1, y1, x2, y2)))

    return plates


def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("Could not open video.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))
    if not out.isOpened():
        print("Could not create output video.")
        cap.release()
        return

    print("Processing video...")
    print(f"Output will be saved as: {OUTPUT_PATH}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        plates = detect_plates(frame)

        for crop, detect_conf, bbox in plates:
            x1, y1, x2, y2 = bbox

            processed = preprocess_plate(crop)
            plate_text, ocr_conf = read_plate_text(processed)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            label = f"{plate_text} | {ocr_conf:.0f}%" if plate_text else "Unreadable"

            text_y = max(y1 - 10, 35)
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2
            )
            cv2.rectangle(
                frame,
                (x1, text_y - text_height - 10),
                (x1 + text_width + 10, text_y + 5),
                (0, 0, 0),
                -1,
            )
            cv2.putText(
                frame, label, (x1 + 5, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
            )

            print(f"Plate: {plate_text} | Detection: {detect_conf:.2f} | OCR: {ocr_conf:.1f}%")

        cv2.imshow("License Plate Detection", frame)
        out.write(frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    print("\nProcessing completed!")
    print(f"Saved video: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()