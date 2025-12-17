"""
Download YOLO Models
Downloads the required YOLO model weights
"""

import logging
from pathlib import Path
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_models():
    """
    Download all required YOLO models
    """
    models = ['yolov8n', 'yolov8s', 'yolov8m']
    
    logger.info("Downloading YOLO models...")
    
    for model_name in models:
        try:
            logger.info(f"Downloading {model_name}...")
            model = YOLO(f"{model_name}.pt")
            logger.info(f"✓ {model_name} downloaded successfully")
        except Exception as e:
            logger.error(f"✗ Failed to download {model_name}: {e}")
    
    logger.info("Model download complete!")


if __name__ == "__main__":
    download_models()
