# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-16

### Added
- Initial release of Distributed Computer Vision System
- Raspberry Pi 5 dual CSI camera capture module
- Synchronized frame capture from two cameras
- Frame preprocessing and adaptive compression
- UDP transmission over Tailscale VPN with network monitoring
- Adaptive quality control based on network conditions
- WSL YOLO inference server with multi-model support
- Parallel execution of YOLOv8n, YOLOv8s, and YOLOv8m
- GPU-accelerated inference using CUDA
- Detection fusion with weighted confidence scores
- FastAPI REST API for detection results
- WebSocket support for real-time updates
- Interactive web dashboard with live visualization
- Real-time detection overlays on video feeds
- System health monitoring and metrics
- Comprehensive logging and alerting
- Production-ready deployment scripts
- Systemd service integration
- Conda environment configurations
- Complete documentation (README, API, Deployment, Troubleshooting)

### Features
- **Raspberry Pi Components:**
  - Dual camera synchronized capture at 30 FPS
  - Configurable resolution and preprocessing
  - JPEG/PNG compression with adaptive quality
  - UDP packet chunking and reassembly
  - Network health monitoring
  - Automatic reconnection and error recovery
  - CPU temperature monitoring
  - System resource tracking

- **WSL Server Components:**
  - UDP frame receiver with buffer management
  - Multi-model parallel YOLO inference
  - Detection fusion algorithms (weighted, average, max)
  - Non-Maximum Suppression (NMS)
  - REST API with comprehensive endpoints
  - WebSocket streaming for real-time updates
  - Interactive web dashboard
  - Performance metrics and statistics
  - Model performance tracking

- **Network Features:**
  - Low-latency UDP streaming
  - Tailscale VPN integration
  - Adaptive quality adjustment
  - Packet loss detection and recovery
  - Network bandwidth monitoring
  - Latency tracking

- **Monitoring & Management:**
  - Real-time system health checks
  - Performance benchmarking
  - Comprehensive logging
  - Systemd service management
  - Automatic service restart
  - Log rotation support

### Documentation
- Comprehensive README with architecture overview
- API documentation with all endpoints
- Deployment guide with step-by-step instructions
- Troubleshooting guide for common issues
- Contributing guidelines
- Example configurations

### Infrastructure
- Conda environment specifications
- Production deployment scripts
- Systemd service files
- Health check utilities
- Camera test utilities
- Model download scripts

## [Unreleased]

### Planned Features
- H.264 hardware encoding support on Raspberry Pi
- Additional YOLO model support (YOLOv9, YOLOv10)
- Advanced fusion algorithms (Bayesian fusion)
- Mobile application for monitoring
- Docker containerization
- Multi-camera support (>2 cameras)
- Recording and playback features
- Email/SMS alerting
- Database integration for historical data
- User authentication and authorization
- Cloud deployment options
- Load balancing for multiple RPi devices
