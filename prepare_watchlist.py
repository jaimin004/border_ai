import os
import cv2

FACE_CASCADE = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
if FACE_CASCADE.empty():
    raise FileNotFoundError("haarcascade_frontalface_default.xml not found in this folder.")

SOURCE_DIR = "watchlist"
DEST_DIR = "watchlist_cropped"
PAD_RATIO = 0.25  # a little room around the face, same spirit as ANPR's plate padding


def crop_largest_face(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        return None

    # If a photo accidentally has multiple faces, keep only the largest —
    # almost always the intended subject in a portrait-style photo.
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

    pad_x, pad_y = int(w * PAD_RATIO), int(h * PAD_RATIO)
    h_img, w_img = img.shape[:2]
    x1, y1 = max(0, x - pad_x), max(0, y - pad_y)
    x2, y2 = min(w_img, x + w + pad_x), min(h_img, y + h + pad_y)

    return img[y1:y2, x1:x2]


def main():
    if not os.path.isdir(SOURCE_DIR):
        print(f"No '{SOURCE_DIR}' folder found.")
        return

    total, cropped, skipped = 0, 0, 0

    for person_name in sorted(os.listdir(SOURCE_DIR)):
        person_dir = os.path.join(SOURCE_DIR, person_name)
        if not os.path.isdir(person_dir):
            continue

        out_dir = os.path.join(DEST_DIR, person_name)
        os.makedirs(out_dir, exist_ok=True)

        for filename in os.listdir(person_dir):
            path = os.path.join(person_dir, filename)
            img = cv2.imread(path)
            if img is None:
                continue
            total += 1

            face = crop_largest_face(img)
            if face is None:
                print(f"  No face found, skipping: {path}")
                skipped += 1
                continue

            # Always save as .jpg for consistency, regardless of source extension
            out_name = os.path.splitext(filename)[0] + ".jpg"
            cv2.imwrite(os.path.join(out_dir, out_name), face)
            cropped += 1

    print(f"\nDone. {cropped}/{total} photos cropped into '{DEST_DIR}/' ({skipped} skipped — no face detected).")
    print("Point WATCHLIST_DIR in day2_stubs.py at this new folder.")


if __name__ == "__main__":
    main()
