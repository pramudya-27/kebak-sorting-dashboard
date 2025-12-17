"""
Multi-Model YOLO Inference Engine
Runs multiple YOLO models in parallel with GPU acceleration
"""

import torch
import numpy as np
import cv2
import logging
import time
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YOLOModel:
    """
    Wrapper for individual YOLO model
    """
    
    def __init__(self, model_name: str, model_config: dict, device: str = 'cuda:0'):
        """
        Initialize YOLO model
        
        Args:
            model_name: Name of the model (e.g., 'yolov8n')
            model_config: Model configuration
            device: Device to run on
        """
        self.model_name = model_name
        self.config = model_config
        self.device = device
        
        # Model parameters
        # 'weight' in config is used as the fusion weight for this model
        self.model_weight = model_config.get('weight', 1.0)
        self.confidence_threshold = model_config.get('confidence_threshold', 0.25)
        self.task = model_config.get('task', None)  # e.g., 'detection' or 'segmentation'

        # Determine model path: prefer explicit 'path' or 'model_path' in config
        model_path = (model_config.get('path') or model_config.get('model_path'))
        if not model_path:
            # If the provided name looks like a filename/path, use it; otherwise default to name.pt
            if str(model_name).endswith('.pt') or '/' in str(model_name) or '\\' in str(model_name):
                model_path = model_name
            else:
                model_path = f"{model_name}.pt"

        logger.info(f"Loading model from {model_path} on {device} (task={self.task})...")
        self.model = YOLO(model_path)
        try:
            # YOLO model handles device in predict but try to move it if possible
            self.model.to(device)
        except Exception:
            logger.debug("Model .to() failed or not supported; relying on YOLO.predict device handling")
        
        # Statistics
        self.total_inferences = 0
        self.total_inference_time = 0.0
        self.total_detections = 0
        
        logger.info(f"Model {model_name} loaded successfully")
    
    def predict(self, frame: np.ndarray, img_size: int = 640) -> Dict:
        """
        Run inference on frame
        
        Args:
            frame: Input frame
            img_size: Input image size
            
        Returns:
            dict: Detection results
        """
        start_time = time.time()
        
        try:
            # Run inference
            results = self.model.predict(
                frame,
                conf=self.confidence_threshold,
                device=self.device,
                imgsz=img_size,
                verbose=False
            )
            
            inference_time = time.time() - start_time
            
            # Extract detections
            detections = self._extract_detections(results[0])
            
            # Update statistics
            self.total_inferences += 1
            self.total_inference_time += inference_time
            self.total_detections += len(detections)
            
            return {
                'model_name': self.model_name,
                'detections': detections,
                'inference_time': inference_time,
                'num_detections': len(detections)
            }
            
        except Exception as e:
            logger.error(f"Error in {self.model_name} inference: {e}")
            return {
                'model_name': self.model_name,
                'detections': [],
                'inference_time': 0.0,
                'num_detections': 0,
                'error': str(e)
            }
    
    def _extract_detections(self, result) -> List[Dict]:
        """
        Extract detection information from YOLO result
        
        Args:
            result: YOLO result object
            
        Returns:
            list: List of detections
        """
        detections = []
        
        # If there are no boxes and no masks, return empty
        has_boxes = (result.boxes is not None and len(result.boxes) > 0)
        has_masks = False
        try:
            has_masks = (hasattr(result, 'masks') and result.masks is not None and hasattr(result.masks, 'xy') and len(result.masks.xy) > 0)
        except Exception:
            has_masks = False

        if not has_boxes and not has_masks:
            return detections

        # Extract box-based detections when available
        if has_boxes:
            boxes = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
            class_ids = result.boxes.cls.cpu().numpy().astype(int)

            for i in range(len(boxes)):
                detection = {
                    'bbox': boxes[i].tolist(),  # [x1, y1, x2, y2]
                    'confidence': float(confidences[i]),
                    'class_id': int(class_ids[i]),
                    'class_name': result.names[class_ids[i]] if class_ids[i] in result.names else str(class_ids[i]),
                    'model': self.model_name,
                    'model_weight': self.model_weight
                }

                # Try to pull mask polygons if present
                try:
                    if hasattr(result, 'masks') and result.masks is not None and hasattr(result.masks, 'xy'):
                        mask_list = result.masks.xy
                        if len(mask_list) > i:
                            polys = []
                            for poly in mask_list[i]:
                                try:
                                    coords = poly.cpu().numpy().tolist()
                                except Exception:
                                    # poly might already be a list/ndarray
                                    coords = getattr(poly, 'tolist', lambda: poly)()
                                polys.append(coords)
                            detection['mask_polygons'] = polys
                except Exception as e:
                    logger.debug(f"Failed to extract masks for {self.model_name}: {e}")

                detections.append(detection)
        
        return detections
    
    def get_stats(self) -> Dict:
        """
        Get model statistics
        
        Returns:
            dict: Statistics
        """
        avg_inference_time = (self.total_inference_time / self.total_inferences 
                             if self.total_inferences > 0 else 0)
        avg_detections = (self.total_detections / self.total_inferences 
                         if self.total_inferences > 0 else 0)
        
        return {
            'model_name': self.model_name,
            'total_inferences': self.total_inferences,
            'avg_inference_time_ms': avg_inference_time * 1000,
            'avg_detections': avg_detections,
            'total_detections': self.total_detections
        }


class MultiModelInference:
    """
    Manages parallel inference across multiple YOLO models
    """
    
    def __init__(self, config: dict):
        """
        Initialize multi-model inference
        
        Args:
            config: Inference configuration
        """
        self.config = config
        self.inference_config = config.get('inference', {})
        self.model_configs = config.get('models', [])
        
        # Device configuration
        self.device = self.inference_config.get('device', 'cuda:0')
        if not torch.cuda.is_available():
            logger.warning("CUDA not available, using CPU")
            self.device = 'cpu'
        
        # Load models
        self.models = []
        for model_config in self.model_configs:
            model_name = model_config.get('name')
            try:
                model = YOLOModel(model_name, model_config, self.device)
                self.models.append(model)
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
        
        if not self.models:
            raise RuntimeError("No models loaded successfully")
        
        # Thread pool for parallel inference
        self.executor = ThreadPoolExecutor(max_workers=len(self.models))
        
        # Statistics
        self.total_frames = 0
        self.total_time = 0.0
        
        logger.info(f"MultiModelInference initialized with {len(self.models)} models")
    
    def predict_parallel(self, frame: np.ndarray) -> Dict:
        """
        Run parallel inference on all models
        
        Args:
            frame: Input frame
            
        Returns:
            dict: Combined results from all models
        """
        start_time = time.time()
        
        # Submit inference tasks
        futures = {}
        for model in self.models:
            future = self.executor.submit(model.predict, frame)
            futures[future] = model.model_name
        
        # Collect results
        all_results = []
        for future in as_completed(futures):
            model_name = futures[future]
            try:
                result = future.result()
                all_results.append(result)
            except Exception as e:
                logger.error(f"Error getting result from {model_name}: {e}")
        
        total_time = time.time() - start_time
        
        # Update statistics
        self.total_frames += 1
        self.total_time += total_time
        
        return {
            'frame_results': all_results,
            'total_inference_time': total_time,
            'num_models': len(all_results)
        }
    
    def get_stats(self) -> Dict:
        """
        Get inference statistics
        
        Returns:
            dict: Statistics
        """
        avg_time = self.total_time / self.total_frames if self.total_frames > 0 else 0
        
        model_stats = [model.get_stats() for model in self.models]
        
        return {
            'total_frames': self.total_frames,
            'avg_inference_time_ms': avg_time * 1000,
            'device': self.device,
            'models': model_stats
        }
    
    def shutdown(self):
        """
        Shutdown inference engine
        """
        logger.info("Shutting down multi-model inference...")
        self.executor.shutdown(wait=True)
        logger.info("Multi-model inference shutdown complete")


if __name__ == "__main__":
    # Test configuration (example using project model files)
    test_config = {
        'models': [
            {
                'name': 'gender_detector',
                'path': 'machine/DeteksiGenderKepiting/yolo11m.pt',
                'weight': 0.33,
                'confidence_threshold': 0.25,
                'task': 'detection'
            },
            {
                'name': 'kelengkapan_seg',
                'path': 'machine/DeteksiKelengkapanTubuhKepiting/FIKS YOLO SEG-V8/yolov8n-seg.pt',
                'weight': 0.33,
                'confidence_threshold': 0.25,
                'task': 'segmentation'
            },
            {
                'name': 'health_detector',
                'path': 'machine/DeteksiKesehatanKepiting/YOLO11 health specific/YOLO11 health specific/best.pt',
                'weight': 0.34,
                'confidence_threshold': 0.25,
                'task': 'detection'
            }
        ],
        'inference': {
            'device': 'cuda:0',
            'batch_size': 1,
            'max_det': 300
        }
    }
    
    # Create test frame
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    try:
        inference = MultiModelInference(test_config)
        
        logger.info("Running test inference...")
        for i in range(5):
            results = inference.predict_parallel(test_frame)
            logger.info(f"Frame {i}: {len(results['frame_results'])} models, "
                       f"time: {results['total_inference_time']*1000:.1f}ms")
        
        logger.info(f"Final stats: {inference.get_stats()}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        if 'inference' in locals():
            inference.shutdown()
