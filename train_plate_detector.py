from ultralytics import YOLO

model = YOLO("license_plate_detector.pt")

results = model.train(
    data="data.yaml",     
    epochs=50,            
    imgsz=640,
    batch=8,               
    patience=15,           
    name="indian_plate_finetune",
)

# Best weights land at:
# runs/detect/indian_plate_finetune/weights/best.pt
# Point PLATE_MODEL_PATH at this file in main.py once training finishes.
