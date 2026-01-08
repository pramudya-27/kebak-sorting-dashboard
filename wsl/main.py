"""
Main Application for WSL Server
Coordinates UDP reception, YOLO inference, detection fusion, and API services
"""

import sys
import time
import asyncio
import signal
import logging
import yaml
import uvicorn
from pathlib import Path
from threading import Thread

from src.udp_receiver import UDPReceiver
from src.yolo_inference import MultiModelInference
from src.detection_fusion import DetectionFusion
from src.api_server import APIServer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/wsl-vision/app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class WSLVisionSystem:
    """
    Main WSL vision processing system
    """
    
    def __init__(self, config_path: str = "config.yml"):
        """
        Initialize WSL vision system
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.running = False
        
        # Initialize components
        self.udp_receiver = UDPReceiver(self.config)
        self.inference_engine = MultiModelInference(self.config)
        self.fusion_engine = DetectionFusion(self.config)
        self.api_server = APIServer(self.config)
        
        # Statistics
        self.frames_processed = 0
        self.start_time = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # API server thread
        self.api_thread = None
        
        logger.info("WSLVisionSystem initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """
        Load configuration from YAML file
        
        Args:
            config_path: Path to config file
            
        Returns:
            dict: Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.info("Using default configuration")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """
        Get default configuration
        
        Returns:
            dict: Default configuration
        """
        return {
            'models': [
                {
                    'name': 'gender_detector',
                    'path': 'machine/DeteksiGenderKepiting/best.pt',
                    'weight': 0.33,
                    'confidence_threshold': 0.25,
                    'task': 'detection'
                },
                {
                    'name': 'kelengkapan_seg',
                    'path': 'machine/DeteksiKelengkapanTubuhKepiting/FIKS YOLO SEG-V8/best.pt',
                    'weight': 0.33,
                    'confidence_threshold': 0.25,
                    'task': 'segmentation'
                },
                {
                    'name': 'health_detector',
                    'path': 'machine/DeteksiKesehatanKepiting/YOLO11_health_specific/best.pt',
                    'weight': 0.34,
                    'confidence_threshold': 0.25,
                    'task': 'detection'
                }
            ],
            'inference': {
                'device': 'cuda:0',
                'batch_size': 1,
                'max_det': 300
            },
            'fusion': {
                'iou_threshold': 0.45,
                'confidence_weights': 'weighted'
            },
            'network': {
                'listen_host': '0.0.0.0',
                'listen_port': 5000,
                'buffer_size': 65536
            },
            'api': {
                'host': '0.0.0.0',
                'port': 8000,
                'cors_origins': ['*']
            }
        }
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals
        """
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def start(self) -> bool:
        """
        Start the vision system
        
        Returns:
            bool: True if started successfully
        """
        logger.info("Starting WSL Vision System...")
        
        # Start UDP receiver
        if not self.udp_receiver.start():
            logger.error("Failed to start UDP receiver")
            return False
        
        # Start API server in separate thread
        self.api_thread = Thread(target=self._run_api_server, daemon=True)
        self.api_thread.start()
        
        self.running = True
        self.start_time = time.time()
        
        logger.info("WSL Vision System started successfully")
        return True
    
    def _run_api_server(self):
        """
        Run API server in thread
        """
        try:
            api_config = self.config.get('api', {})

            # Get the FastAPI app from APIServer and mount the static files
            app = self.api_server.get_app()

            # Mount static directory and root dashboard (if present)
            try:
                from fastapi.staticfiles import StaticFiles
                from pathlib import Path

                static_dir = Path(__file__).parent / "static"
                if static_dir.exists():
                    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
                    # Mounting root to serve single page app (dashboard)
                    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="dashboard")
            except Exception as _e:
                logger.warning(f"Failed to mount static files: {_e}")

            uvicorn.run(
                app,
                host=api_config.get('host', '0.0.0.0'),
                port=api_config.get('port', 8000),
                log_level="info"
            )
        except Exception as e:
            logger.error(f"API server error: {e}")
    
    def stop(self):
        """
        Stop the vision system
        """
        logger.info("Stopping WSL Vision System...")
        self.running = False
        
        # Stop components
        self.udp_receiver.stop()
        self.inference_engine.shutdown()
        
        # Log final statistics
        self._log_statistics()
        
        logger.info("WSL Vision System stopped")
    
    async def process_frame(self, frame_package: dict):
        """
        Process received frame package
        
        Args:
            frame_package: Frame package from UDP receiver
        """
        try:
            import cv2
            import numpy as np
            import base64
            
            # Extract frame metadata
            frame_id = frame_package.get('frame_id', 0)
            compressed_package = frame_package.get('compressed_package', {})
            metadata = frame_package.get('metadata', {})
            
            # For simplicity, process camera 0 frame
            # In production, could process both cameras
            camera0_data = compressed_package.get('camera0')
            camera1_data = compressed_package.get('camera1')
            
            if camera0_data is None:
                logger.warning(f"No camera data in frame {frame_id}")
                return
            
            # Decompress camera 0 frame
            nparr = np.frombuffer(camera0_data, np.uint8)
            frame_camera0 = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame_camera0 is None:
                logger.error(f"Failed to decode frame {frame_id} from camera 0")
                return
            
            # Decompress camera 1 frame if available
            frame_camera1 = None
            if camera1_data is not None:
                nparr1 = np.frombuffer(camera1_data, np.uint8)
                frame_camera1 = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
            
            # Camera 0: Run health and completeness detection models
            inference_start = time.time()
            camera0_models = ['health_detector', 'kelengkapan_seg']
            camera0_results = self.inference_engine.predict_parallel(
                frame_camera0, 
                model_filter=camera0_models
            )
            
            # Camera 1: Run gender detection model (if frame available)
            camera1_results = None
            if frame_camera1 is not None:
                camera1_results = self.inference_engine.predict_parallel(
                    frame_camera1,
                    model_filter=['gender_detector']
                )
            
            inference_time = time.time() - inference_start
            
            # Fuse detections for camera 0
            fusion_start = time.time()
            camera0_fused = self.fusion_engine.fuse_detections(
                camera0_results['frame_results']
            )
            
            # Fuse detections for camera 1 (if available)
            camera1_fused = []
            if camera1_results is not None:
                camera1_fused = self.fusion_engine.fuse_detections(
                    camera1_results['frame_results']
                )
            
            fusion_time = time.time() - fusion_start
            
            # Encode frames to base64 for WebSocket transmission
            _, buffer = cv2.imencode('.jpg', frame_camera0, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_base64_camera0 = base64.b64encode(buffer).decode('utf-8')
            
            camera_frames = [frame_base64_camera0]
            if frame_camera1 is not None:
                _, buffer1 = cv2.imencode('.jpg', frame_camera1, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_base64_camera1 = base64.b64encode(buffer1).decode('utf-8')
                camera_frames.append(frame_base64_camera1)
            
            # Create result package with separate camera detections
            result = {
                'frame_id': frame_id,
                'timestamp': metadata.get('timestamp'),
                'camera0': {
                    'detections': camera0_fused,
                    'num_detections': len(camera0_fused),
                    'models': ['health_detector', 'kelengkapan_seg']
                },
                'camera1': {
                    'detections': camera1_fused,
                    'num_detections': len(camera1_fused),
                    'models': ['gender_detector']
                },
                'inference_time': inference_time,
                'fusion_time': fusion_time,
                'total_time': inference_time + fusion_time,
                'frame_width': frame_camera0.shape[1],
                'frame_height': frame_camera0.shape[0],
                'camera_frames': camera_frames
            }
            
            # Send to API
            await self.api_server.add_detection(result)
            
            self.frames_processed += 1
            
            # Log progress
            if self.frames_processed % 100 == 0:
                logger.info(f"Processed {self.frames_processed} frames, "
                          f"avg inference: {inference_time*1000:.1f}ms")
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)
    
    def run(self):
        """
        Main processing loop
        """
        logger.info("Starting main processing loop...")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.running:
            try:
                # Get next frame from receiver
                frame_package = self.udp_receiver.get_frame(timeout=1.0)
                
                if frame_package is not None:
                    # Process frame asynchronously
                    loop.run_until_complete(self.process_frame(frame_package))
                
                # Update system statistics periodically
                if self.frames_processed % 50 == 0:
                    self._update_api_stats()
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(0.1)
        
        loop.close()
        logger.info("Main processing loop ended")
    
    def _update_api_stats(self):
        """
        Update API server with system statistics
        """
        stats = {
            'frames_processed': self.frames_processed,
            'uptime': time.time() - self.start_time if self.start_time else 0,
            'receiver': self.udp_receiver.get_stats(),
            'inference': self.inference_engine.get_stats(),
            'fusion': self.fusion_engine.get_stats(),
            'models': [model.get_stats() for model in self.inference_engine.models]
        }
        
        self.api_server.update_system_stats(stats)
    
    def _log_statistics(self):
        """
        Log system statistics
        """
        if self.start_time:
            uptime = time.time() - self.start_time
            fps = self.frames_processed / uptime if uptime > 0 else 0
        else:
            uptime = 0
            fps = 0
        
        receiver_stats = self.udp_receiver.get_stats()
        inference_stats = self.inference_engine.get_stats()
        fusion_stats = self.fusion_engine.get_stats()
        
        logger.info(f"""
=== WSL Vision System Statistics ===
Uptime: {uptime:.1f}s
Processing FPS: {fps:.2f}
Frames Processed: {self.frames_processed}
Receiver Stats: {receiver_stats}
Inference Stats: {inference_stats}
Fusion Stats: {fusion_stats}
        """)


def main():
    """
    Main entry point
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='WSL Multi-Model YOLO Inference Server')
    parser.add_argument('--config', type=str, default='config.yml',
                       help='Path to configuration file')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create log directory if it doesn't exist
    Path('/var/log/wsl-vision').mkdir(parents=True, exist_ok=True)
    
    # Create and run system
    try:
        system = WSLVisionSystem(config_path=args.config)
        
        if system.start():
            system.run()
        else:
            logger.error("Failed to start system")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if 'system' in locals():
            system.stop()


if __name__ == "__main__":
    main()
