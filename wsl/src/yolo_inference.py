"""
Multi-Model YOLO Inference Engine
Runs multiple YOLO models in parallel with GPU acceleration
"""

import torch
import numpy as np
import cv2
import logging
import time
import shutil
import zipfile
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _resolve_path_anywhere(path_str: str) -> Path:
    candidate = Path(path_str)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    bases = [
        Path.cwd(),
        Path(__file__).resolve().parents[1],
        Path(__file__).resolve().parents[2],
    ]

    def _with_machine_case(p: Path) -> List[Path]:
        try:
            parts = list(p.parts)
        except Exception:
            return [p]

        if not parts:
            return [p]

        first = parts[0]
        alts = [p]
        if first == "machine":
            alts.append(Path("Machine", *parts[1:]))
        elif first == "Machine":
            alts.append(Path("machine", *parts[1:]))
        return alts

    if candidate.exists():
        return candidate

    for base in bases:
        for rel in _with_machine_case(candidate):
            resolved = (base / rel).resolve()
            if resolved.exists():
                return resolved

    return candidate


def _prepare_weights_path(model_path: str, model_config: dict) -> str:
    raw = str(model_path)
    resolved = _resolve_path_anywhere(raw)

    explicit_path = bool(model_config.get('path') or model_config.get('model_path'))

    if resolved.suffix.lower() == ".zip" or (explicit_path and raw.lower().endswith(".zip")):
        zip_path = resolved if resolved.suffix.lower() == ".zip" else _resolve_path_anywhere(raw)
        if not zip_path.exists():
            raise FileNotFoundError(f"Model archive not found: {raw}")

        member = (
            model_config.get("zip_member")
            or model_config.get("archive_member")
            or model_config.get("member")
        )

        with zipfile.ZipFile(zip_path) as z:
            if not member:
                pt_members = [n for n in z.namelist() if n.lower().endswith(".pt")]
                best = [n for n in pt_members if n.lower().endswith("best.pt")]
                pick = sorted(best or pt_members)
                if len(pick) != 1:
                    raise ValueError(
                        f"Archive {zip_path} has multiple .pt weights; set zip_member in config. "
                        f"Found: {pick[:10]}"
                    )
                member = pick[0]

            if member not in z.namelist():
                raise FileNotFoundError(f"zip_member not found in {zip_path}: {member}")

            cache_dir = model_config.get("extract_dir")
            if cache_dir:
                out_dir = Path(cache_dir)
            else:
                out_dir = Path(__file__).resolve().parents[1] / "models_cache"
            out_dir.mkdir(parents=True, exist_ok=True)

            key = f"{zip_path.resolve()}::{member}".encode("utf-8")
            digest = hashlib.sha256(key).hexdigest()[:16]
            out_path = out_dir / f"{zip_path.stem}_{digest}.pt"

            if not out_path.exists():
                with z.open(member) as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        return str(out_path)

    if explicit_path:
        if resolved.exists():
            return str(resolved)
        raise FileNotFoundError(f"Model weights not found: {raw}")

    if resolved.exists():
        return str(resolved)

    return raw



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

        prepared_path = _prepare_weights_path(str(model_path), model_config)
        logger.info(f"Loading model from {prepared_path} on {device} (task={self.task})...")
        self.model = YOLO(prepared_path)
        try:
            # YOLO model handles device in predict but try to move it if possible
            self.model.to(device)
        except Exception:
            logger.debug("Model .to() failed or not supported; relying on YOLO.predict device handling")

        try:
            names_obj = getattr(self.model, "names", None)
            if names_obj is None and hasattr(self.model, "model"):
                names_obj = getattr(self.model.model, "names", None)

            if isinstance(names_obj, dict):
                names_map = {int(k): str(v) for k, v in names_obj.items()}
            elif isinstance(names_obj, (list, tuple)):
                names_map = {i: str(v) for i, v in enumerate(names_obj)}
            else:
                names_map = {}

            if names_map:
                sample = [names_map[i] for i in sorted(names_map)[:10] if i in names_map]
                logger.info(f"{self.model_name} classes: {len(names_map)} (sample={sample})")
                values = set(v.lower() for v in names_map.values())
                if "person" in values or "cat" in values:
                    logger.warning(f"{self.model_name} appears to be COCO/pretrained (contains person/cat). Check weights path.")
        except Exception as e:
            logger.debug(f"Failed to read class names for {self.model_name}: {e}")
        
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
                verbose=False,
                max_det=10
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
                box = boxes[i].tolist()

                
                detection = {
                    'bbox': box,  # [x1, y1, x2, y2]
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

                # OpenCV heuristic for Jantan/Betina line if no polygon yet
                if 'mask_polygons' not in detection and hasattr(result, 'orig_img') and detection['class_name'].lower() in ['jantan', 'betina']:
                    try:
                        x1, y1, x2, y2 = map(int, box)
                        h_img, w_img = result.orig_img.shape[:2]
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w_img, x2), min(h_img, y2)
                        
                        if x2 > x1 and y2 > y1:
                            roi = result.orig_img[y1:y2, x1:x2]
                            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                            edges = cv2.Canny(blurred, 30, 100)
                            
                            kernel = np.ones((3,3), np.uint8)
                            edges = cv2.dilate(edges, kernel, iterations=1)
                            
                            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            if contours:
                                largest = max(contours, key=cv2.arcLength)
                                epsilon = 0.02 * cv2.arcLength(largest, True)
                                approx = cv2.approxPolyDP(largest, epsilon, True)
                                
                                poly = []
                                for pt in approx:
                                    px = pt[0][0] + x1
                                    py = pt[0][1] + y1
                                    poly.append([float(px), float(py)])
                                
                                if len(poly) > 2:
                                    detection['mask_polygons'] = [poly]
                    except Exception as e:
                        logger.debug(f"Failed OpenCV line detection for {detection['class_name']}: {e}")

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
    
    def predict_parallel(self, frame: np.ndarray, model_filter: List[str] = None) -> Dict:
        """
        Run parallel inference on all models or specific models
        
        Args:
            frame: Input frame
            model_filter: Optional list of model names to run (runs all if None)
            
        Returns:
            dict: Combined results from all models
        """
        start_time = time.time()
        
        # Filter models if requested
        models_to_run = self.models
        if model_filter is not None:
            models_to_run = [m for m in self.models if m.model_name in model_filter]
            if not models_to_run:
                logger.warning(f"No models matched filter: {model_filter}")
                models_to_run = self.models
        
        # Submit inference tasks
        futures = {}
        for model in models_to_run:
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
                'path': 'Machine/Deteksi Gender/run_YOLO11m.pt-Split801010/runs/detect/train/weights/best.pt',
                'weight': 0.33,
                'confidence_threshold': 0.25,
                'task': 'detection'
            },
            {
                'name': 'kelengkapan_seg',
                'path': 'Machine/Kelengkapan Tubuh Kepiting Bakau/FIKS YOLO SEG-V8/test.zip',
                'zip_member': 'kaggle/working/runs/segment/train4/weights/best.pt',
                'weight': 0.33,
                'confidence_threshold': 0.25,
                'task': 'segmentation'
            },
            {
                'name': 'health_detector',
                'path': 'Machine/Deteksi kesehatan kepiting/YOLO11 health specific/YOLO11 health specific/best.pt',
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
