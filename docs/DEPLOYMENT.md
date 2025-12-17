# Deployment Guide

## Prerequisites

### Raspberry Pi 5
- Raspberry Pi OS (64-bit) installed
- Two CSI camera modules connected
- Tailscale installed and configured
- Miniforge/Conda installed
- Internet connection for initial setup

### WSL Server
- Windows 10/11 with WSL2 enabled
- Ubuntu 20.04+ installed on WSL
- NVIDIA GPU with CUDA support
- CUDA Toolkit 11.8+ installed
- Miniconda/Conda installed
- Tailscale installed and configured

## Step-by-Step Deployment

### 1. Raspberry Pi Setup

#### Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Install Miniforge (if not already installed)
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3-Linux-aarch64.sh

# Clone repository
git clone <repository-url> ~/kebak_sorting
cd ~/kebak_sorting
```

#### Create Conda Environment
```bash
cd rpi
conda env create -f environment.yml
conda activate rpi-vision
```

#### Test Cameras
```bash
python test_cameras.py
```

#### Configure System
```bash
# Copy example config
cp config.example.yml config.yml

# Edit configuration
nano config.yml

# Set server_host to WSL Tailscale IP
# Get WSL IP: ssh to WSL and run: tailscale ip -4
```

#### Deploy Service
```bash
cd ..
sudo chmod +x scripts/*.sh
sudo ./scripts/deploy_rpi.sh
```

### 2. WSL Server Setup

#### Install CUDA (if not installed)
```bash
# Check CUDA installation
nvidia-smi

# If CUDA not installed, follow NVIDIA CUDA installation guide
# https://docs.nvidia.com/cuda/wsl-user-guide/index.html
```

#### Install Tailscale
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

#### Setup Project
```bash
# Clone repository
git clone <repository-url> ~/kebak_sorting
cd ~/kebak_sorting

# Create Conda environment
cd wsl
conda env create -f environment.yml
conda activate wsl-vision

# Download YOLO models
python download_models.py
```

#### Configure System
```bash
# Copy example config
cp config.example.yml config.yml

# Edit configuration (optional)
nano config.yml
```

#### Deploy Service
```bash
cd ..
sudo chmod +x scripts/*.sh
sudo ./scripts/deploy_wsl.sh
```

### 3. Verify Deployment

#### Check Services
```bash
# On RPi
sudo systemctl status rpi-vision

# On WSL
sudo systemctl status wsl-vision
```

#### Health Check
```bash
# Run health check script
sudo ./scripts/health_check.sh
```

#### Access Dashboard
Open browser on WSL or any machine on network:
```
http://<wsl-tailscale-ip>:8000/dashboard
```

## Troubleshooting

### Raspberry Pi Issues

**Camera not detected:**
```bash
# Check camera connection
libcamera-hello --list-cameras

# Enable camera interface
sudo raspi-config
# Navigate to Interface Options > Camera > Enable
```

**Service fails to start:**
```bash
# Check logs
sudo journalctl -u rpi-vision -n 50

# Check permissions
ls -la /var/log/rpi-vision/

# Verify conda environment
conda activate rpi-vision
python -c "import picamera2; print('OK')"
```

### WSL Server Issues

**GPU not accessible:**
```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA in Python
python -c "import torch; print(torch.cuda.is_available())"
```

**Port already in use:**
```bash
# Check what's using port 5000
sudo lsof -i :5000

# Or port 8000
sudo lsof -i :8000
```

**Model download fails:**
```bash
# Manually download models
conda activate wsl-vision
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Network Issues

**UDP packets not arriving:**
```bash
# Check Tailscale connection
tailscale status

# Test connectivity
ping <tailscale-ip>

# Check firewall (WSL)
sudo ufw status
sudo ufw allow 5000/udp
sudo ufw allow 8000/tcp
```

**High latency:**
```bash
# Check Tailscale performance
tailscale ping <peer-ip>

# Reduce frame rate in RPi config
# Edit rpi/config.yml: fps: 15
```

## Configuration Tuning

### Performance Optimization

**Raspberry Pi:**
- Reduce resolution: `resolution: [1280, 720]`
- Lower frame rate: `fps: 15`
- Increase compression: `initial_quality: 70`
- Disable second camera if not needed

**WSL Server:**
- Use lighter models: Only yolov8n
- Adjust confidence thresholds
- Reduce max_det if needed
- Monitor GPU memory usage

### Quality vs Bandwidth

**Low Bandwidth (<1 Mbps):**
```yaml
# RPi config
preprocessing:
  resize: [416, 416]
compression:
  initial_quality: 60
  min_quality: 40
```

**High Quality (>5 Mbps):**
```yaml
# RPi config
preprocessing:
  resize: [640, 480]
compression:
  initial_quality: 90
  min_quality: 70
```

## Monitoring

### View Logs
```bash
# RPi
tail -f /var/log/rpi-vision/app.log
sudo journalctl -u rpi-vision -f

# WSL
tail -f /var/log/wsl-vision/app.log
sudo journalctl -u wsl-vision -f
```

### Check Statistics
```bash
# API
curl http://localhost:8000/api/v1/stats | jq

# Health
curl http://localhost:8000/health
```

### Performance Metrics
Dashboard provides real-time metrics:
- Frame rate (FPS)
- Inference time
- Detection counts
- Network latency
- System resources

## Updates and Maintenance

### Update Code
```bash
# Pull latest changes
git pull

# Restart service
sudo systemctl restart rpi-vision  # or wsl-vision
```

### Update Dependencies
```bash
# Update conda environment
conda env update -f environment.yml --prune
```

### Backup Configuration
```bash
# Backup configs
cp /opt/rpi-vision/config.yml ~/config-backup.yml
cp /opt/wsl-vision/config.yml ~/config-backup.yml
```

## Production Checklist

- [ ] Tailscale configured and connected
- [ ] Cameras tested and working
- [ ] GPU accessible and tested
- [ ] Configuration files customized
- [ ] Services enabled and running
- [ ] Dashboard accessible
- [ ] Logs rotating properly
- [ ] Health checks passing
- [ ] Network bandwidth adequate
- [ ] System resources monitored
