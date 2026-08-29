from ultralytics import YOLO


def main():
    # Load pretrained YOLOv8 Nano
    model = YOLO("yolov8n.pt")

    # Run detection
    results = model("bus.jpg")

    # Save annotated image
    results[0].save(filename="data/outputs/yolo_test.jpg")

    # Print detected objects
    print("\nDetection Results:")

    for box in results[0].boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        class_name = model.names[class_id]

        print(
            f"Class: {class_name:<12} "
            f"Confidence: {confidence:.2f}"
        )

    print("\nAnnotated image saved to:")
    print("data/outputs/yolo_test.jpg")


if __name__ == "__main__":
    main()