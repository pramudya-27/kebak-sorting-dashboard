"""
FastAPI REST API Server
Provides real-time detection results and system statistics
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DetectionManager:
    """
    Manages detection results and subscribers
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialize detection manager
        
        Args:
            max_history: Maximum number of detection results to keep
        """
        self.max_history = max_history
        self.detection_history = []
        self.latest_detection = None
        self.subscribers = []
        self.lock = asyncio.Lock()
        
        # Statistics
        self.total_detections = 0
        self.start_time = time.time()
    
    async def add_detection(self, detection_result: Dict):
        """
        Add new detection result
        
        Args:
            detection_result: Detection result dictionary
        """
        async with self.lock:
            # Add timestamp if not present
            if 'timestamp' not in detection_result:
                detection_result['timestamp'] = datetime.now().isoformat()
            
            self.latest_detection = detection_result
            self.detection_history.append(detection_result)
            self.total_detections += 1
            
            # Trim history
            if len(self.detection_history) > self.max_history:
                self.detection_history = self.detection_history[-self.max_history:]
            
            # Notify subscribers
            await self.notify_subscribers(detection_result)
    
    async def notify_subscribers(self, detection: Dict):
        """
        Notify all websocket subscribers of new detection
        
        Args:
            detection: Detection result
        """
        if not self.subscribers:
            return
        
        disconnected = []
        for websocket in self.subscribers:
            try:
                await websocket.send_json(detection)
            except Exception as e:
                logger.warning(f"Failed to send to subscriber: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected subscribers
        for ws in disconnected:
            if ws in self.subscribers:
                self.subscribers.remove(ws)
    
    def subscribe(self, websocket: WebSocket):
        """
        Add websocket subscriber
        
        Args:
            websocket: WebSocket connection
        """
        self.subscribers.append(websocket)
        logger.info(f"New subscriber added, total: {len(self.subscribers)}")
    
    def unsubscribe(self, websocket: WebSocket):
        """
        Remove websocket subscriber
        
        Args:
            websocket: WebSocket connection
        """
        if websocket in self.subscribers:
            self.subscribers.remove(websocket)
            logger.info(f"Subscriber removed, total: {len(self.subscribers)}")
    
    async def get_latest(self) -> Optional[Dict]:
        """
        Get latest detection result
        
        Returns:
            dict: Latest detection or None
        """
        async with self.lock:
            return self.latest_detection
    
    async def get_history(self, limit: int = 50) -> List[Dict]:
        """
        Get detection history
        
        Args:
            limit: Maximum number of results
            
        Returns:
            list: Detection history
        """
        async with self.lock:
            return self.detection_history[-limit:]
    
    def get_stats(self) -> Dict:
        """
        Get detection statistics
        
        Returns:
            dict: Statistics
        """
        uptime = time.time() - self.start_time
        fps = self.total_detections / uptime if uptime > 0 else 0
        
        return {
            'total_detections': self.total_detections,
            'uptime_seconds': uptime,
            'fps': fps,
            'history_size': len(self.detection_history),
            'subscribers': len(self.subscribers)
        }


class APIServer:
    """
    FastAPI server for detection results
    """
    
    def __init__(self, config: dict):
        """
        Initialize API server
        
        Args:
            config: API configuration
        """
        self.config = config
        self.api_config = config.get('api', {})
        
        # Server parameters
        self.host = self.api_config.get('host', '0.0.0.0')
        self.port = self.api_config.get('port', 8000)
        self.cors_origins = self.api_config.get('cors_origins', ['*'])
        
        # Detection manager
        self.detection_manager = DetectionManager()
        
        # Create FastAPI app
        self.app = FastAPI(
            title="YOLO Detection API",
            description="Real-time object detection results from multi-model YOLO inference",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mount static files
        static_dir = Path(__file__).parent.parent / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # Setup routes
        self._setup_routes()
        
        # System stats
        self.system_stats = {}
        
        logger.info(f"APIServer initialized on {self.host}:{self.port}")
    
    def _setup_routes(self):
        """
        Setup API routes
        """
        
        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "service": "YOLO Detection API",
                "version": "1.0.0",
                "status": "running"
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/api/v1/detections/latest")
        async def get_latest_detection():
            """Get latest detection result"""
            latest = await self.detection_manager.get_latest()
            if latest is None:
                raise HTTPException(status_code=404, detail="No detections available")
            return latest
        
        @self.app.get("/api/v1/detections/history")
        async def get_detection_history(limit: int = 50):
            """Get detection history"""
            history = await self.detection_manager.get_history(limit)
            return {
                "count": len(history),
                "history": history
            }
        
        @self.app.get("/api/v1/stats")
        async def get_statistics():
            """Get system statistics"""
            detection_stats = self.detection_manager.get_stats()
            return {
                "detection": detection_stats,
                "system": self.system_stats
            }
        
        @self.app.get("/api/v1/stats/detections")
        async def get_detection_stats():
            """Get detection statistics only"""
            return self.detection_manager.get_stats()
        
        @self.app.post("/api/v1/config")
        async def update_config(config_update: Dict):
            """Update configuration"""
            # This would integrate with actual config management
            logger.info(f"Config update request: {config_update}")
            return {"status": "success", "message": "Configuration update received"}
        
        @self.app.websocket("/ws/detections")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time detection stream"""
            await websocket.accept()
            self.detection_manager.subscribe(websocket)
            
            try:
                # Send initial latest detection
                latest = await self.detection_manager.get_latest()
                if latest:
                    await websocket.send_json(latest)
                
                # Keep connection alive
                while True:
                    # Wait for client messages (ping/pong)
                    try:
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                        if data == "ping":
                            await websocket.send_text("pong")
                    except asyncio.TimeoutError:
                        # Send keepalive
                        await websocket.send_json({"type": "keepalive"})
                        
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                self.detection_manager.unsubscribe(websocket)
        
        @self.app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard():
            """Serve dashboard HTML"""
            dashboard_path = Path(__file__).parent.parent / "static" / "dashboard.html"
            if dashboard_path.exists():
                return HTMLResponse(content=dashboard_path.read_text())
            else:
                return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)
    
    async def add_detection(self, detection_result: Dict):
        """
        Add new detection result
        
        Args:
            detection_result: Detection result
        """
        await self.detection_manager.add_detection(detection_result)
    
    def update_system_stats(self, stats: Dict):
        """
        Update system statistics
        
        Args:
            stats: System statistics
        """
        self.system_stats = stats
    
    def get_app(self) -> FastAPI:
        """
        Get FastAPI application
        
        Returns:
            FastAPI: Application instance
        """
        return self.app


if __name__ == "__main__":
    import uvicorn
    
    # Test configuration
    test_config = {
        'api': {
            'host': '0.0.0.0',
            'port': 8000,
            'cors_origins': ['*']
        }
    }
    
    server = APIServer(test_config)
    app = server.get_app()
    
    # Run server
    logger.info("Starting API server...")
    uvicorn.run(app, host=test_config['api']['host'], port=test_config['api']['port'])
