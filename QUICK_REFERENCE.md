# Quick Reference Guide

## Essential Commands

### Raspberry Pi

#### Service Management
```bash
# Start service
sudo systemctl start rpi-vision

# Stop service
sudo systemctl stop rpi-vision

# Restart service
sudo systemctl restart rpi-vision

# Check status
sudo systemctl status rpi-vision

# Enable on boot
sudo systemctl enable rpi-vision

# View logs
sudo journalctl -u rpi-vision -f
tail -f /var/log/rpi-vision/app.log
```

#### Testing
```bash
# Test cameras
python rpi/test_cameras.py

# Run health check
sudo ./scripts/health_check.sh

# Check configuration
cat /opt/rpi-vision/config.yml
```

#### Monitoring
```bash
# CPU temperature
cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000}'

# System resources
htop

# Network stats
iftop
```

---

### WSL Server

#### Service Management
```bash
# Start service
sudo systemctl start wsl-vision

# Stop service
sudo systemctl stop wsl-vision

# Restart service
sudo systemctl restart wsl-vision

# Check status
sudo systemctl status wsl-vision

# Enable on boot
sudo systemctl enable wsl-vision

# View logs
sudo journalctl -u wsl-vision -f
tail -f /var/log/wsl-vision/app.log
```

#### Testing
```bash
# Check GPU
nvidia-smi

# Test CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Download models
python wsl/download_models.py

# Run health check
sudo ./scripts/health_check.sh
```

#### API Testing
```bash
# Health check
curl http://localhost:8000/health

# Get statistics
curl http://localhost:8000/api/v1/stats | jq

# Get latest detection
curl http://localhost:8000/api/v1/detections/latest | jq
```

---

## Configuration Files

### Raspberry Pi Config (`rpi/config.yml`)
```yaml
cameras:
  camera0:
    enabled: true
    resolution: [1920, 1080]
    fps: 30

network:
  server_host: "100.x.x.x"  # WSL Tailscale IP
  server_port: 5000

compression:
  format: "jpeg"
  initial_quality: 85
  adaptive: true
```

### WSL Config (`wsl/config.yml`)
```yaml
models:
  - name: "yolov8n"
    weight: 0.25
    confidence_threshold: 0.25

inference:
  device: "cuda:0"

api:
  host: "0.0.0.0"
  port: 8000
```

---

## Network

### Tailscale
```bash
# Check status
tailscale status

# Get IP
tailscale ip -4

# Ping peer
tailscale ping <peer-ip>

# Connect
sudo tailscale up

# Disconnect
sudo tailscale down
```

### Firewall (WSL)
```bash
# Allow UDP for frames
sudo ufw allow 5000/udp

# Allow HTTP for API
sudo ufw allow 8000/tcp

# Check status
sudo ufw status
```

---

## Troubleshooting

### Quick Fixes

#### Service won't start
```bash
# Check logs
sudo journalctl -u <service> -n 50

# Check permissions
sudo chown -R $USER:$USER /var/log/<service>/

# Test manually
cd /opt/<service>
conda activate <env>
python main.py
```

#### No camera detected (RPi)
```bash
# List cameras
libcamera-hello --list-cameras

# Enable camera
sudo raspi-config
# Interface Options > Camera > Enable
```

#### GPU not working (WSL)
```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch
pip install torch torchvision --upgrade
```

#### Network issues
```bash
# Test connectivity
ping <server-ip>

# Check Tailscale
tailscale status

# Monitor traffic
sudo tcpdump -i any port 5000

# Check bandwidth
iperf3 -c <server-ip>
```

---

## Performance Tuning

### Low Bandwidth
```yaml
# RPi config
preprocessing:
  resize: [416, 416]
compression:
  initial_quality: 60
  min_quality: 40
cameras:
  camera0:
    fps: 15
```

### High Quality
```yaml
# RPi config
preprocessing:
  resize: [640, 480]
compression:
  initial_quality: 90
  min_quality: 70
cameras:
  camera0:
    fps: 30
```

### Performance Mode (WSL)
```yaml
# Use only fast model
models:
  - name: "yolov8n"
    weight: 1.0
    confidence_threshold: 0.25
```

### Quality Mode (WSL)
```yaml
# Use all models
models:
  - name: "yolov8n"
    weight: 0.25
  - name: "yolov8s"
    weight: 0.35
  - name: "yolov8m"
    weight: 0.40
```

---

## URLs

### Dashboard
```
http://<wsl-ip>:8000/dashboard
```

### API Endpoints
```
http://<wsl-ip>:8000/health
http://<wsl-ip>:8000/api/v1/stats
http://<wsl-ip>:8000/api/v1/detections/latest
```

### WebSocket
```
ws://<wsl-ip>:8000/ws/detections
```

---

## File Locations

### Raspberry Pi
```
Installation: /opt/rpi-vision/
Config: /opt/rpi-vision/config.yml
Logs: /var/log/rpi-vision/
Service: /etc/systemd/system/rpi-vision.service
```

### WSL Server
```
Installation: /opt/wsl-vision/
Config: /opt/wsl-vision/config.yml
Logs: /var/log/wsl-vision/
Service: /etc/systemd/system/wsl-vision.service
Models: /opt/wsl-vision/*.pt
```

---

## Useful Aliases

Add to `~/.bashrc`:

```bash
# Service shortcuts
alias rpi-start='sudo systemctl start rpi-vision'
alias rpi-stop='sudo systemctl stop rpi-vision'
alias rpi-status='sudo systemctl status rpi-vision'
alias rpi-logs='sudo journalctl -u rpi-vision -f'

alias wsl-start='sudo systemctl start wsl-vision'
alias wsl-stop='sudo systemctl stop wsl-vision'
alias wsl-status='sudo systemctl status wsl-vision'
alias wsl-logs='sudo journalctl -u wsl-vision -f'

# Health check
alias health='sudo /path/to/scripts/health_check.sh'

# GPU check
alias gpu='watch -n 1 nvidia-smi'
```

---

## Emergency Procedures

### System Not Responding
```bash
# 1. Check if service is running
sudo systemctl status <service>

# 2. Check system resources
htop
df -h

# 3. Check logs for errors
sudo journalctl -u <service> -n 100

# 4. Restart service
sudo systemctl restart <service>

# 5. If still failing, reboot
sudo reboot
```

### High CPU/Memory Usage
```bash
# 1. Identify process
top -o %CPU
top -o %MEM

# 2. Reduce load
# Edit config to reduce resolution/FPS

# 3. Restart service
sudo systemctl restart <service>
```

### Network Issues
```bash
# 1. Check Tailscale
tailscale status

# 2. Reconnect if needed
sudo tailscale down
sudo tailscale up

# 3. Test connectivity
ping <peer-ip>

# 4. Check firewall
sudo ufw status
```

---

## Common Workflows

### Update System
```bash
# 1. Stop service
sudo systemctl stop <service>

# 2. Pull updates
git pull

# 3. Update environment
conda env update -f environment.yml

# 4. Restart service
sudo systemctl start <service>
```

### Change Configuration
```bash
# 1. Edit config
sudo nano /opt/<service>/config.yml

# 2. Validate
python -c "import yaml; yaml.safe_load(open('config.yml'))"

# 3. Restart service
sudo systemctl restart <service>

# 4. Verify
sudo systemctl status <service>
```

### Backup Configuration
```bash
# Backup
sudo cp /opt/rpi-vision/config.yml ~/rpi-config-backup.yml
sudo cp /opt/wsl-vision/config.yml ~/wsl-config-backup.yml

# Restore
sudo cp ~/rpi-config-backup.yml /opt/rpi-vision/config.yml
sudo systemctl restart rpi-vision
```

---

## Performance Metrics

### Good Performance
- FPS: > 20
- Inference time: < 60ms
- Network latency: < 50ms
- Packet loss: < 1%
- GPU utilization: 70-90%

### Needs Optimization
- FPS: < 10
- Inference time: > 100ms
- Network latency: > 100ms
- Packet loss: > 5%
- GPU utilization: < 50% or > 95%

---

## Support Resources

1. **Documentation**: `README.md`, `docs/`
2. **Troubleshooting**: `docs/TROUBLESHOOTING.md`
3. **API Reference**: `docs/API.md`
4. **Deployment Guide**: `docs/DEPLOYMENT.md`
5. **Project Summary**: `PROJECT_SUMMARY.md`
6. **Contributing**: `CONTRIBUTING.md`

---

## Key Keyboard Shortcuts

### systemctl logs
- `Space` - Page down
- `b` - Page up
- `g` - Jump to beginning
- `G` - Jump to end
- `/` - Search
- `q` - Quit

### htop
- `F5` - Tree view
- `F6` - Sort by
- `F9` - Kill process
- `q` - Quit

### Less (log files)
- `Space` - Page down
- `b` - Page up
- `/` - Search forward
- `?` - Search backward
- `F` - Follow (like tail -f)
- `q` - Quit
