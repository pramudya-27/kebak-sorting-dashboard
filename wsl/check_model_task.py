from ultralytics import YOLO
import sys

for path in sys.argv[1:]:
    try:
        model = YOLO(path)
        print(f"{path}: task={model.task}")
    except Exception as e:
        print(f"Error loading {path}: {e}")
