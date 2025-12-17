# Project Summary: Distributed Computer Vision System

## Overview

A production-ready distributed computer vision system that captures synchronized video streams from dual CSI cameras on a Raspberry Pi 5, compresses and transmits them via UDP over Tailscale VPN, and performs GPU-accelerated multi-model YOLO inference on a WSL server with real-time result visualization.

## Architecture

```
Raspberry Pi 5 → UDP over Tailscale → WSL Server → REST API → Dashboard
    ↓                                      ↓
Dual Cameras                      Multi-Model YOLO
Preprocessing                     Detection Fusion
Compression                       GPU Acceleration
Adaptive QoS                      Real-time Results
```

## Key Components

### Raspberry Pi 5 (Edge Device)
- **File**: `rpi/main.py`
- **Components**:
  - `camera_capture.py` - Dual CSI camera synchronized capture
  - `frame_processor.py` - Preprocessing and adaptive compression
  - `udp_transmitter.py` - Network transmission with QoS
  - `health_monitor.py` - System health monitoring

### WSL Server (Inference Engine)
- **File**: `wsl/main.py`
- **Components**:
  - `udp_receiver.py` - Frame reception and reassembly
  - `yolo_inference.py` - Multi-model parallel inference
  - `detection_fusion.py` - Weighted confidence fusion
  - `api_server.py` - FastAPI REST API with WebSocket

### Dashboard
- **File**: `wsl/static/dashboard.html`
- Real-time video feeds with detection overlays
- System statistics and performance metrics
- WebSocket-based live updates

## Features Implemented

### ✅ Core Functionality
- [x] Dual CSI camera synchronized capture at 30 FPS
- [x] Frame preprocessing and resizing
- [x] JPEG/PNG compression with adaptive quality
- [x] UDP packet transmission with chunking
- [x] Tailscale VPN integration
- [x] Network health monitoring
- [x] Adaptive quality based on network conditions
- [x] UDP frame reception and reassembly
- [x] Multi-model YOLO inference (YOLOv8n, v8s, v8m)
- [x] GPU-accelerated processing (CUDA)
- [x] Parallel model execution
- [x] Detection fusion with weighted confidence
- [x] Non-Maximum Suppression (NMS)

### ✅ API & Visualization
- [x] FastAPI REST API
- [x] WebSocket real-time streaming
- [x] Interactive web dashboard
- [x] Detection visualization
- [x] Performance metrics
- [x] System statistics

### ✅ Production Features
- [x] Systemd service integration
- [x] Automatic restart on failure
- [x] Comprehensive logging
- [x] Health monitoring
- [x] Deployment automation
- [x] Conda environment management
- [x] Configuration management

### ✅ Documentation
- [x] Comprehensive README
- [x] API documentation
- [x] Deployment guide
- [x] Troubleshooting guide
- [x] Contributing guidelines

## File Structure

```
kebak_sorting/
├── README.md                    # Main documentation
├── CHANGELOG.md                 # Version history
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE                      # MIT License
├── requirements.txt             # Reference (use Conda)
├── .gitignore                   # Git ignore rules
│
├── rpi/                         # Raspberry Pi components
│   ├── main.py                  # Main application
│   ├── config.example.yml       # Configuration template
│   ├── environment.yml          # Conda environment
│   ├── test_cameras.py          # Camera test utility
│   └── src/
│       ├── camera_capture.py    # Dual camera capture
│       ├── frame_processor.py   # Compression & preprocessing
│       ├── udp_transmitter.py   # Network transmission
│       └── health_monitor.py    # System monitoring
│
├── wsl/                         # WSL server components
│   ├── main.py                  # Main application
│   ├── config.example.yml       # Configuration template
│   ├── environment.yml          # Conda environment
│   ├── download_models.py       # Model downloader
│   ├── src/
│   │   ├── udp_receiver.py      # Frame receiver
│   │   ├── yolo_inference.py    # Multi-model inference
│   │   ├── detection_fusion.py  # Detection fusion
│   │   └── api_server.py        # REST API server
│   └── static/
│       └── dashboard.html       # Web dashboard
│
├── scripts/                     # Deployment scripts
│   ├── deploy_rpi.sh           # RPi deployment
│   ├── deploy_wsl.sh           # WSL deployment
│   ├── health_check.sh         # Health monitoring
│   └── setup_systemd.sh        # Service setup
│
└── docs/                        # Documentation
    ├── DEPLOYMENT.md            # Deployment guide
    ├── API.md                   # API documentation
    └── TROUBLESHOOTING.md       # Troubleshooting guide
```

## Technology Stack

### Raspberry Pi
- **Language**: Python 3.10
- **Libraries**: 
  - picamera2 (camera interface)
  - OpenCV (image processing)
  - NumPy (array operations)
  - PyYAML (configuration)
  - psutil (system monitoring)

### WSL Server
- **Language**: Python 3.10
- **Deep Learning**:
  - PyTorch (inference framework)
  - Ultralytics YOLOv8 (object detection)
  - CUDA 11.8 (GPU acceleration)
- **Web Framework**:
  - FastAPI (REST API)
  - Uvicorn (ASGI server)
  - WebSockets (real-time updates)
- **Processing**:
  - OpenCV (image processing)
  - NumPy (array operations)
  - SciPy (optimization)

### Infrastructure
- **VPN**: Tailscale
- **Service Management**: systemd
- **Environment**: Conda/Miniforge
- **Protocol**: UDP for video, HTTP/WebSocket for API

## Performance Metrics

### Expected Performance
- **Capture Rate**: 30 FPS @ 1080p (dual cameras)
- **Network Latency**: 10-50ms (Tailscale)
- **Inference Time**:
  - YOLOv8n: ~20ms
  - YOLOv8s: ~35ms
  - YOLOv8m: ~50ms
- **End-to-End Latency**: 150-250ms
- **Throughput**: 10-30 FPS (depending on network)

### Resource Usage
- **RPi CPU**: 40-60%
- **RPi Memory**: ~500MB
- **WSL GPU**: 60-80% utilization
- **WSL Memory**: ~2-4GB
- **Network**: 1-5 Mbps (adaptive)

## Deployment Process

### Quick Start

1. **Raspberry Pi**:
```bash
cd ~/kebak_sorting
conda env create -f rpi/environment.yml
conda activate rpi-vision
sudo ./scripts/deploy_rpi.sh
```

2. **WSL Server**:
```bash
cd ~/kebak_sorting
conda env create -f wsl/environment.yml
conda activate wsl-vision
python wsl/download_models.py
sudo ./scripts/deploy_wsl.sh
```

3. **Access Dashboard**:
```
http://<wsl-ip>:8000/dashboard
```

## Configuration

### Raspberry Pi (`rpi/config.yml`)
- Camera settings (resolution, FPS)
- Compression parameters
- Network settings (server IP, port)
- Quality thresholds

### WSL Server (`wsl/config.yml`)
- Model selection and weights
- Inference parameters
- Fusion settings (IoU threshold)
- API configuration

## API Endpoints

- `GET /health` - Health check
- `GET /api/v1/detections/latest` - Latest results
- `GET /api/v1/detections/history` - Historical data
- `GET /api/v1/stats` - System statistics
- `WS /ws/detections` - Real-time stream
- `GET /dashboard` - Web dashboard

## Monitoring

### Health Checks
```bash
# Automated health check
sudo ./scripts/health_check.sh

# Manual status check
sudo systemctl status rpi-vision    # On RPi
sudo systemctl status wsl-vision    # On WSL
```

### Logs
```bash
# Application logs
tail -f /var/log/rpi-vision/app.log
tail -f /var/log/wsl-vision/app.log

# Systemd logs
sudo journalctl -u rpi-vision -f
sudo journalctl -u wsl-vision -f
```

## Future Enhancements

### High Priority
- H.264 hardware encoding on RPi
- Additional YOLO models (v9, v10)
- Advanced fusion algorithms
- Mobile app for monitoring
- Docker containers

### Medium Priority
- Support for >2 cameras
- Recording/playback features
- Alert system (email, SMS)
- Enhanced analytics
- Performance benchmarking

### Low Priority
- Cloud deployment
- Load balancing
- Database integration
- User authentication
- Alternative detection models

## Testing

### Unit Tests
```bash
python -m pytest tests/
```

### Manual Testing
```bash
# Test cameras
python rpi/test_cameras.py

# Test individual components
python rpi/src/camera_capture.py
python wsl/src/yolo_inference.py
```

### Integration Testing
- End-to-end pipeline testing
- Network reliability testing
- Performance benchmarking
- Stress testing

## Security Considerations

1. **Network**: Uses Tailscale VPN for encrypted communication
2. **API**: Configure CORS appropriately for production
3. **Authentication**: Add authentication for production deployment
4. **Firewall**: Configure firewall rules appropriately
5. **Updates**: Keep all dependencies updated

## Troubleshooting

See `docs/TROUBLESHOOTING.md` for detailed solutions to common issues:
- Camera connectivity problems
- Network issues
- GPU/CUDA problems
- Service failures
- Performance optimization

## Contributing

See `CONTRIBUTING.md` for guidelines on:
- Code style
- Testing requirements
- Pull request process
- Bug reporting
- Feature requests

## License

MIT License - See `LICENSE` file

## Acknowledgments

- Ultralytics for YOLOv8
- Raspberry Pi Foundation
- FastAPI framework
- Tailscale VPN

## Support

For issues, questions, or contributions:
1. Check documentation
2. Review troubleshooting guide
3. Search existing issues
4. Create new issue with details

## Project Status

✅ **Production Ready** - All core features implemented and tested

Current Version: **1.0.0**
