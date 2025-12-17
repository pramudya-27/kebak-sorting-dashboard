# Distributed Computer Vision System

A production-ready distributed computer vision system using Raspberry Pi 5 dual cameras and WSL GPU-accelerated YOLO inference.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         Raspberry Pi 5                   │
│  ┌────────────┐      ┌────────────┐    │
│  │ CSI Cam 0  │      │ CSI Cam 1  │    │
│  └─────┬──────┘      └─────┬──────┘    │
│        │                   │             │
│        └────────┬──────────┘             │
│                 ▼                        │
│      ┌──────────────────────┐           │
│      │ Synchronized Capture  │           │
│      │   & Preprocessing     │           │
│      └──────────┬────────────┘           │
│                 ▼                        │
│      ┌──────────────────────┐           │
│      │  Frame Compression    │           │
│      │  (JPEG/H264)          │           │
│      └──────────┬────────────┘           │
│                 ▼                        │
│      ┌──────────────────────┐           │
│      │   UDP Transmitter     │           │
│      │  Adaptive QoS         │           │
│      │  Health Monitor       │           │
│      └──────────┬────────────┘           │
└─────────────────┼────────────────────────┘
                  │
                  │ Tailscale VPN
                  │ (UDP Stream)
                  │
┌─────────────────┼────────────────────────┐
│                 ▼                        │
│      ┌──────────────────────┐           │
│      │   UDP Receiver        │           │
│      │   Buffer Manager      │           │
│      └──────────┬────────────┘           │
│                 ▼                        │
│      ┌──────────────────────┐           │
│      │  Multi-Model YOLO     │           │
│      │  Parallel Inference   │           │
│      │  ┌────┐ ┌────┐ ┌────┐│           │
│      │  │v8n │ │v8s │ │v8m ││           │
│      │  └────┘ └────┘ └────┘│           │
│      │    GPU Accelerated    │           │
│      └──────────┬────────────┘           │
│                 ▼                        │
│      ┌──────────────────────┐           │
│      │  Detection Fusion     │           │
│      │  Weighted Confidence  │           │
│      └──────────┬────────────┘           │
│                 ▼                        │
│      ┌──────────────────────┐           │
│      │   REST API Server     │           │
│      │   WebSocket Updates   │           │
│      └──────────┬────────────┘           │
│                 ▼                        │
│      ┌──────────────────────┐           │
│      │  Prediction Dashboard │           │
│      │  Real-time Viz        │           │
│      └───────────────────────┘           │
│                                          │
│         WSL Ubuntu (GPU)                 │
└──────────────────────────────────────────┘
```

## Features

### Raspberry Pi 5 Components
- **Dual CSI Camera Capture**: Synchronized frame capture from two cameras
- **Frame Preprocessing**: Resizing, normalization, format conversion
- **Adaptive Compression**: Dynamic quality adjustment based on network conditions
- **UDP Transmission**: Low-latency streaming over Tailscale VPN
- **Health Monitoring**: Network metrics, frame rate tracking, error detection
- **Automatic Recovery**: Reconnection logic and error handling

### WSL Server Components
- **GPU-Accelerated Inference**: Parallel execution of 3 YOLO models
- **Multi-Model Fusion**: Weighted confidence score aggregation
- **REST API**: FastAPI-based endpoints for detection results
- **WebSocket Support**: Real-time detection streaming
- **Prediction Dashboard**: Web-based visualization with live updates
- **Health Monitoring**: System metrics, performance tracking, logging

## System Requirements

### Raspberry Pi 5
- Raspberry Pi 5 (4GB+ RAM recommended)
- 2x CSI Camera modules
- Raspberry Pi OS (64-bit)
- Tailscale installed and configured
- Conda/Miniforge installed

### WSL Server
- Windows 10/11 with WSL2
- NVIDIA GPU with CUDA support
- Ubuntu 20.04+ on WSL
- CUDA Toolkit 11.8+
- Conda/Miniconda installed
- Tailscale installed and configured

## Quick Start

### 1. Setup Raspberry Pi

```bash
# Clone repository
cd /home/pi
git clone <repository-url> kebak_sorting
cd kebak_sorting

# Create conda environment
conda env create -f rpi/environment.yml
conda activate rpi-vision

# Configure settings
cp rpi/config.example.yml rpi/config.yml
nano rpi/config.yml  # Edit with your settings

# Test camera setup
python rpi/test_cameras.py

# Deploy service
./scripts/deploy_rpi.sh
```

### 2. Setup WSL Server

```bash
# Clone repository
cd /home/your-user
git clone <repository-url> kebak_sorting
cd kebak_sorting

# Create conda environment
conda env create -f wsl/environment.yml
conda activate wsl-vision

# Configure settings
cp wsl/config.example.yml wsl/config.yml
nano wsl/config.yml  # Edit with your settings

# Download YOLO models
python wsl/download_models.py

# Deploy services
./scripts/deploy_wsl.sh
```

### 3. Access Dashboard

Open browser: `http://localhost:8000/dashboard`

## Configuration

### Raspberry Pi Configuration (`rpi/config.yml`)

```yaml
cameras:
  camera0:
    enabled: true
    resolution: [1920, 1080]
    fps: 30
  camera1:
    enabled: true
    resolution: [1920, 1080]
    fps: 30

network:
  server_host: "100.x.x.x"  # Tailscale IP of WSL
  server_port: 5000
  max_packet_size: 60000
  
compression:
  format: "jpeg"  # jpeg or h264
  initial_quality: 85
  min_quality: 50
  max_quality: 95
  adaptive: true
```

### WSL Configuration (`wsl/config.yml`)

```yaml
models:
  - name: "yolov8n"
    weight: 0.25
    confidence_threshold: 0.25
  - name: "yolov8s"
    weight: 0.35
    confidence_threshold: 0.30
  - name: "yolov8m"
    weight: 0.40
    confidence_threshold: 0.35

inference:
  device: "cuda:0"
  batch_size: 1
  max_det: 300
  
fusion:
  iou_threshold: 0.45
  confidence_weights: "weighted"  # weighted or average

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["*"]
```

## API Endpoints

### REST API

- `GET /health` - System health status
- `GET /api/v1/detections/latest` - Latest detection results
- `GET /api/v1/detections/stream` - SSE stream of detections
- `GET /api/v1/stats` - Performance statistics
- `GET /api/v1/models` - Model information
- `POST /api/v1/config` - Update configuration
- `GET /dashboard` - Web dashboard

### WebSocket

- `ws://localhost:8000/ws/detections` - Real-time detection stream

## Project Structure

```
kebak_sorting/
├── rpi/                      # Raspberry Pi components
│   ├── src/
│   │   ├── camera_capture.py
│   │   ├── frame_processor.py
│   │   ├── udp_transmitter.py
│   │   ├── network_monitor.py
│   │   └── health_check.py
│   ├── config.yml
│   ├── config.example.yml
│   ├── environment.yml
│   ├── main.py
│   └── test_cameras.py
├── wsl/                      # WSL server components
│   ├── src/
│   │   ├── udp_receiver.py
│   │   ├── yolo_inference.py
│   │   ├── detection_fusion.py
│   │   ├── api_server.py
│   │   └── health_monitor.py
│   ├── static/
│   │   ├── dashboard.html
│   │   ├── css/
│   │   └── js/
│   ├── config.yml
│   ├── config.example.yml
│   ├── environment.yml
│   ├── main.py
│   └── download_models.py
├── scripts/                  # Deployment scripts
│   ├── deploy_rpi.sh
│   ├── deploy_wsl.sh
│   ├── setup_systemd.sh
│   └── health_check.sh
├── tests/
│   ├── test_rpi.py
│   ├── test_wsl.py
│   └── test_integration.py
├── docs/
│   ├── DEPLOYMENT.md
│   ├── TROUBLESHOOTING.md
│   └── API.md
└── README.md
```

## Monitoring & Logging

### System Health
- Real-time metrics dashboard
- Automatic alerting on errors
- Performance benchmarks

### Logs Location
- Raspberry Pi: `/var/log/rpi-vision/`
- WSL: `/var/log/wsl-vision/`

### Metrics Tracked
- Frame rate (capture & inference)
- Network latency & bandwidth
- Model inference time
- Detection confidence scores
- System resource usage

## Troubleshooting

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues and solutions.

## Performance

### Expected Performance
- **RPi Capture**: 30 FPS @ 1080p (dual cameras)
- **Network Latency**: 10-50ms (over Tailscale)
- **Inference Time**: 
  - YOLOv8n: ~20ms
  - YOLOv8s: ~35ms
  - YOLOv8m: ~50ms
- **End-to-End Latency**: ~150-250ms

## License

MIT License

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.
