"""
Detection Fusion Module
Fuses detections from multiple YOLO models using weighted confidence scores
"""

import numpy as np
import logging
from typing import List, Dict, Tuple
from scipy.optimize import linear_sum_assignment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DetectionFusion:
    """
    Fuses detections from multiple models using various strategies
    """
    
    def __init__(self, config: dict):
        """
        Initialize detection fusion
        
        Args:
            config: Fusion configuration
        """
        self.config = config
        self.fusion_config = config.get('fusion', {})
        
        # Fusion parameters
        self.iou_threshold = self.fusion_config.get('iou_threshold', 0.45)
        self.fusion_method = self.fusion_config.get('confidence_weights', 'weighted')
        
        # Statistics
        self.total_fusions = 0
        self.total_input_detections = 0
        self.total_output_detections = 0
        
        logger.info(f"DetectionFusion initialized: method={self.fusion_method}, "
                   f"iou_threshold={self.iou_threshold}")
    
    def calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """
        Calculate Intersection over Union between two boxes
        
        Args:
            box1: First box [x1, y1, x2, y2]
            box2: Second box [x1, y1, x2, y2]
            
        Returns:
            float: IoU score
        """
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # Calculate intersection area
        intersect_x_min = max(x1_min, x2_min)
        intersect_y_min = max(y1_min, y2_min)
        intersect_x_max = min(x1_max, x2_max)
        intersect_y_max = min(y1_max, y2_max)
        
        if intersect_x_max <= intersect_x_min or intersect_y_max <= intersect_y_min:
            return 0.0
        
        intersect_area = (intersect_x_max - intersect_x_min) * (intersect_y_max - intersect_y_min)
        
        # Calculate union area
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = box1_area + box2_area - intersect_area
        
        iou = intersect_area / union_area if union_area > 0 else 0.0
        return iou
    
    def group_detections(self, detections: List[Dict]) -> List[List[Dict]]:
        """
        Group overlapping detections from different models
        
        Args:
            detections: List of all detections
            
        Returns:
            list: List of detection groups
        """
        if not detections:
            return []
        
        # Sort by confidence
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        groups = []
        used = set()
        
        for i, det1 in enumerate(detections):
            if i in used:
                continue
            
            group = [det1]
            used.add(i)
            
            for j, det2 in enumerate(detections):
                if j in used or j <= i:
                    continue
                
                # Check if same class
                if det1['class_id'] != det2['class_id']:
                    continue
                
                # Check IoU
                iou = self.calculate_iou(det1['bbox'], det2['bbox'])
                if iou >= self.iou_threshold:
                    group.append(det2)
                    used.add(j)
            
            groups.append(group)
        
        return groups
    
    def fuse_detection_group(self, group: List[Dict]) -> Dict:
        """
        Fuse a group of overlapping detections
        
        Args:
            group: List of detections to fuse
            
        Returns:
            dict: Fused detection
        """
        if len(group) == 1:
            return group[0]
        
        # Extract information
        bboxes = np.array([det['bbox'] for det in group])
        confidences = np.array([det['confidence'] for det in group])
        weights = np.array([det.get('model_weight', 1.0) for det in group])
        
        # Calculate weighted confidence
        if self.fusion_method == 'weighted':
            # Use model weights and confidence
            weighted_confidences = confidences * weights
            final_confidence = np.sum(weighted_confidences) / np.sum(weights)
        elif self.fusion_method == 'average':
            # Simple average
            final_confidence = np.mean(confidences)
        elif self.fusion_method == 'max':
            # Maximum confidence
            final_confidence = np.max(confidences)
        else:
            # Default to weighted
            weighted_confidences = confidences * weights
            final_confidence = np.sum(weighted_confidences) / np.sum(weights)
        
        # Fuse bounding boxes (weighted average)
        if self.fusion_method == 'weighted':
            bbox_weights = (confidences * weights).reshape(-1, 1)
            fused_bbox = np.sum(bboxes * bbox_weights, axis=0) / np.sum(bbox_weights)
        else:
            fused_bbox = np.mean(bboxes, axis=0)
        
        # Create fused detection
        fused_detection = {
            'bbox': fused_bbox.tolist(),
            'confidence': float(final_confidence),
            'class_id': group[0]['class_id'],
            'class_name': group[0]['class_name'],
            'num_models': len(group),
            'models': [det['model'] for det in group],
            'original_confidences': confidences.tolist()
        }
        
        return fused_detection
    
    def fuse_detections(self, model_results: List[Dict]) -> List[Dict]:
        """
        Fuse detections from multiple models
        
        Args:
            model_results: List of results from each model
            
        Returns:
            list: Fused detections
        """
        # Collect all detections
        all_detections = []
        for result in model_results:
            all_detections.extend(result.get('detections', []))
        
        self.total_input_detections += len(all_detections)
        
        if not all_detections:
            return []
        
        # Group overlapping detections
        groups = self.group_detections(all_detections)
        
        # Fuse each group
        fused_detections = []
        for group in groups:
            fused = self.fuse_detection_group(group)
            fused_detections.append(fused)
        
        # Sort by confidence
        fused_detections = sorted(fused_detections, 
                                 key=lambda x: x['confidence'], 
                                 reverse=True)
        
        # Update statistics
        self.total_fusions += 1
        self.total_output_detections += len(fused_detections)
        
        return fused_detections
    
    def apply_nms(self, detections: List[Dict], nms_threshold: float = 0.4) -> List[Dict]:
        """
        Apply Non-Maximum Suppression to fused detections
        
        Args:
            detections: List of detections
            nms_threshold: NMS IoU threshold
            
        Returns:
            list: Filtered detections
        """
        if not detections:
            return []
        
        # Group by class
        class_groups = {}
        for det in detections:
            class_id = det['class_id']
            if class_id not in class_groups:
                class_groups[class_id] = []
            class_groups[class_id].append(det)
        
        # Apply NMS per class
        final_detections = []
        for class_id, class_dets in class_groups.items():
            # Sort by confidence
            class_dets = sorted(class_dets, key=lambda x: x['confidence'], reverse=True)
            
            keep = []
            while class_dets:
                best = class_dets.pop(0)
                keep.append(best)
                
                # Remove overlapping detections
                class_dets = [
                    det for det in class_dets
                    if self.calculate_iou(best['bbox'], det['bbox']) < nms_threshold
                ]
            
            final_detections.extend(keep)
        
        return sorted(final_detections, key=lambda x: x['confidence'], reverse=True)
    
    def get_stats(self) -> Dict:
        """
        Get fusion statistics
        
        Returns:
            dict: Statistics
        """
        avg_input = (self.total_input_detections / self.total_fusions 
                    if self.total_fusions > 0 else 0)
        avg_output = (self.total_output_detections / self.total_fusions 
                     if self.total_fusions > 0 else 0)
        reduction = ((avg_input - avg_output) / avg_input * 100 
                    if avg_input > 0 else 0)
        
        return {
            'total_fusions': self.total_fusions,
            'avg_input_detections': avg_input,
            'avg_output_detections': avg_output,
            'reduction_percent': reduction,
            'fusion_method': self.fusion_method,
            'iou_threshold': self.iou_threshold
        }


if __name__ == "__main__":
    # Test configuration
    test_config = {
        'fusion': {
            'iou_threshold': 0.45,
            'confidence_weights': 'weighted'
        }
    }
    
    # Create test detections
    model_results = [
        {
            'model_name': 'yolov8n',
            'detections': [
                {'bbox': [100, 100, 200, 200], 'confidence': 0.8, 'class_id': 0, 
                 'class_name': 'person', 'model': 'yolov8n', 'model_weight': 0.25},
                {'bbox': [300, 150, 400, 250], 'confidence': 0.7, 'class_id': 1, 
                 'class_name': 'car', 'model': 'yolov8n', 'model_weight': 0.25}
            ]
        },
        {
            'model_name': 'yolov8s',
            'detections': [
                {'bbox': [105, 105, 205, 205], 'confidence': 0.85, 'class_id': 0, 
                 'class_name': 'person', 'model': 'yolov8s', 'model_weight': 0.35},
                {'bbox': [305, 155, 405, 255], 'confidence': 0.75, 'class_id': 1, 
                 'class_name': 'car', 'model': 'yolov8s', 'model_weight': 0.35}
            ]
        },
        {
            'model_name': 'yolov8m',
            'detections': [
                {'bbox': [102, 102, 202, 202], 'confidence': 0.9, 'class_id': 0, 
                 'class_name': 'person', 'model': 'yolov8m', 'model_weight': 0.40}
            ]
        }
    ]
    
    fusion = DetectionFusion(test_config)
    
    logger.info("Testing detection fusion...")
    fused = fusion.fuse_detections(model_results)
    
    logger.info(f"Input detections: {sum(len(r['detections']) for r in model_results)}")
    logger.info(f"Fused detections: {len(fused)}")
    
    for i, det in enumerate(fused):
        logger.info(f"Detection {i}: {det['class_name']}, "
                   f"confidence={det['confidence']:.3f}, "
                   f"models={det['num_models']}")
    
    logger.info(f"Stats: {fusion.get_stats()}")
