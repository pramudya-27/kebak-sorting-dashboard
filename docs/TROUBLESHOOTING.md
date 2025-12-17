# Troubleshooting Guide

## Common Issues and Solutions

### Raspberry Pi Issues

#### Camera Not Detected

**Symptoms:**
- Error: "Failed to initialize cameras"
- Camera not listed in `libcamera-hello --list-cameras`

**Solutions:**
```bash
# 1. Check physical connection
# Ensure ribbon cable is properly seated

# 2. Enable camera interface
sudo raspi-config
# Navigate: Interface Options > Camera > Enable

# 3. Update firmware
sudo apt update
sudo apt full-upgrade
sudo reboot

# 4. Test with libcamera
libcamera-hello --list-cameras
libcamera-still -o test.jpg

# 5. Check for conflicts
sudo dmesg | grep -i camera
```

#### High CPU Temperature

**Symptoms:**
- Temperature > 75°C
- System throttling
- Performance degradation

**Solutions:**
```bash
# 1. Add heatsink/fan
# 2. Reduce workload
# Edit rpi/config.yml:
cameras:
  camera0:
    fps: 15  # Reduce from 30
preprocessing:
  resize: [416, 416]  # Smaller resolution

# 3. Monitor temperature
watch -n 1 'cat /sys/class/thermal/thermal_zone0/temp | awk "{print \$1/1000}"'
```

#### Network Connectivity Issues

**Symptoms:**
- "Failed to connect to server"
- High packet loss
- UDP transmission errors

**Solutions:**
```bash
# 1. Verify Tailscale connection
tailscale status
tailscale ping <wsl-ip>

# 2. Check server is listening
# On WSL: sudo netstat -ulnp | grep 5000

# 3. Test basic connectivity
ping <wsl-tailscale-ip>

# 4. Check config
cat /opt/rpi-vision/config.yml | grep server_host

# 5. Verify no firewall blocking
# On WSL: sudo ufw allow 5000/udp
```

#### Service Won't Start

**Symptoms:**
- `systemctl status rpi-vision` shows failed
- Service stops immediately after starting

**Solutions:**
```bash
# 1. Check logs
sudo journalctl -u rpi-vision -n 50 --no-pager

# 2. Test manually
cd /opt/rpi-vision
conda activate rpi-vision
python main.py --config config.yml

# 3. Check permissions
ls -la /var/log/rpi-vision/
sudo chown -R pi:pi /var/log/rpi-vision/

# 4. Verify dependencies
conda activate rpi-vision
python -c "import picamera2, cv2, numpy; print('OK')"

# 5. Check config syntax
python -c "import yaml; yaml.safe_load(open('config.yml'))"
```

---

### WSL Server Issues

#### GPU Not Accessible

**Symptoms:**
- Error: "CUDA not available"
- Models running on CPU
- Slow inference

**Solutions:**
```bash
# 1. Verify GPU visibility
nvidia-smi

# 2. Check CUDA in PyTorch
python -c "import torch; print(torch.cuda.is_available())"
python -c "import torch; print(torch.cuda.get_device_name(0))"

# 3. Reinstall CUDA toolkit
# Follow: https://docs.nvidia.com/cuda/wsl-user-guide/

# 4. Update PyTorch
conda activate wsl-vision
pip install torch torchvision --upgrade --index-url https://download.pytorch.org/whl/cu118

# 5. Check environment
echo $CUDA_VISIBLE_DEVICES
# Should be empty or "0"
```

#### Models Not Found

**Symptoms:**
- Error: "Model file not found"
- "Failed to load yolov8n.pt"

**Solutions:**
```bash
# 1. Download models
cd /opt/wsl-vision
conda activate wsl-vision
python download_models.py

# 2. Manual download
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
python -c "from ultralytics import YOLO; YOLO('yolov8s.pt')"
python -c "from ultralytics import YOLO; YOLO('yolov8m.pt')"

# 3. Check file locations
ls -la *.pt

# 4. Verify ultralytics installation
pip show ultralytics
```

#### API Not Responding

**Symptoms:**
- Cannot access http://localhost:8000
- Connection refused
- Timeout errors

**Solutions:**
```bash
# 1. Check service status
sudo systemctl status wsl-vision

# 2. Check port availability
sudo netstat -tlnp | grep 8000
# If port is in use:
sudo lsof -ti:8000 | xargs kill -9

# 3. Test API manually
cd /opt/wsl-vision
conda activate wsl-vision
python main.py --config config.yml
# Then in browser: http://localhost:8000/health

# 4. Check firewall
sudo ufw status
sudo ufw allow 8000/tcp

# 5. Verify config
cat config.yml | grep -A 3 "api:"
```

#### High Memory Usage

**Symptoms:**
- Out of memory errors
- System slowdown
- CUDA out of memory

**Solutions:**
```bash
# 1. Monitor GPU memory
watch -n 1 nvidia-smi

# 2. Reduce model count
# Edit wsl/config.yml - use only yolov8n

# 3. Reduce batch size
inference:
  batch_size: 1

# 4. Clear cache periodically
# Add to code:
# torch.cuda.empty_cache()

# 5. Use smaller models
models:
  - name: "yolov8n"  # Only use nano model
```

#### UDP Packets Not Receiving

**Symptoms:**
- "No frames received"
- Empty detection list
- Assembler shows 0 frames

**Solutions:**
```bash
# 1. Verify receiver is running
sudo systemctl status wsl-vision
sudo journalctl -u wsl-vision -f

# 2. Check UDP port
sudo netstat -ulnp | grep 5000

# 3. Test with tcpdump
sudo tcpdump -i any port 5000 -n

# 4. Verify RPi is sending
# On RPi: tail -f /var/log/rpi-vision/app.log

# 5. Check Tailscale routing
tailscale status
```

---

### Network Issues

#### High Latency

**Symptoms:**
- Ping > 100ms
- Dropped frames
- Jerky video

**Solutions:**
```bash
# 1. Test latency
tailscale ping <peer-ip>

# 2. Use direct connection if possible
# Configure both devices on same local network

# 3. Reduce frame rate
# rpi/config.yml:
cameras:
  camera0:
    fps: 10  # Reduce from 30

# 4. Increase compression
compression:
  initial_quality: 60
  min_quality: 40

# 5. Check network load
iftop  # Install: sudo apt install iftop
```

#### Packet Loss

**Symptoms:**
- Incomplete frames
- "Frame timed out" messages
- High dropped frame count

**Solutions:**
```bash
# 1. Check network quality
mtr <destination-ip>

# 2. Reduce packet size
# rpi/config.yml:
network:
  max_packet_size: 30000  # Reduce from 60000

# 3. Increase retry attempts
network:
  retry_attempts: 5  # Increase from 3

# 4. Use adaptive compression
compression:
  adaptive: true
  min_quality: 40

# 5. Monitor network stats
# Check dashboard: Network metrics section
```

#### Bandwidth Limitations

**Symptoms:**
- Slow frame rate
- High compression artifacts
- "Bandwidth too low" messages

**Solutions:**
```bash
# 1. Test bandwidth
iperf3 -s  # On WSL
iperf3 -c <wsl-ip>  # On RPi

# 2. Optimize compression
# For <1 Mbps:
preprocessing:
  resize: [416, 416]
compression:
  initial_quality: 50

# For >5 Mbps:
preprocessing:
  resize: [640, 480]
compression:
  initial_quality: 85

# 3. Use H.264 compression (future)
compression:
  format: "h264"

# 4. Disable second camera
cameras:
  camera1:
    enabled: false
```

---

### Performance Issues

#### Low FPS

**Symptoms:**
- FPS < 10
- Slow inference
- Dashboard shows low throughput

**Solutions:**
```bash
# 1. Check GPU utilization
nvidia-smi
# GPU should be 70-90% utilized

# 2. Use lighter models
models:
  - name: "yolov8n"  # Only nano

# 3. Reduce resolution
# On RPi:
preprocessing:
  resize: [416, 416]

# 4. Profile inference
# Add timing logs to identify bottlenecks

# 5. Check CPU usage
htop
# If CPU is maxed, reduce workload
```

#### Detection Quality Issues

**Symptoms:**
- Missing objects
- False positives
- Low confidence scores

**Solutions:**
```bash
# 1. Adjust confidence thresholds
models:
  - name: "yolov8n"
    confidence_threshold: 0.20  # Lower for more detections

# 2. Use larger models
models:
  - name: "yolov8m"  # Medium model

# 3. Improve lighting
# Physical: Add lighting to scene

# 4. Adjust fusion settings
fusion:
  iou_threshold: 0.40  # Lower for more grouping

# 5. Increase resolution
preprocessing:
  resize: [640, 480]  # Higher resolution
```

---

### System Issues

#### Log Files Growing Too Large

**Solutions:**
```bash
# 1. Setup log rotation
sudo nano /etc/logrotate.d/vision-system

# Add:
/var/log/rpi-vision/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}

/var/log/wsl-vision/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}

# 2. Manual cleanup
sudo find /var/log/rpi-vision -name "*.log" -mtime +7 -delete
sudo find /var/log/wsl-vision -name "*.log" -mtime +7 -delete
```

#### Disk Space Issues

**Solutions:**
```bash
# 1. Check disk usage
df -h
du -sh /opt/*
du -sh ~/.cache/*

# 2. Clean conda cache
conda clean --all

# 3. Clean pip cache
pip cache purge

# 4. Remove old logs
sudo journalctl --vacuum-time=7d
```

#### Service Crashes

**Symptoms:**
- Service stops unexpectedly
- "Service failed" messages
- Automatic restarts

**Solutions:**
```bash
# 1. Check crash logs
sudo journalctl -u rpi-vision -n 100 --no-pager
sudo journalctl -u wsl-vision -n 100 --no-pager

# 2. Check system logs
dmesg | tail -50

# 3. Monitor resources
htop
nvidia-smi

# 4. Enable core dumps
ulimit -c unlimited
echo "/tmp/core.%e.%p" > /proc/sys/kernel/core_pattern

# 5. Add watchdog (systemd handles this)
# Services already configured with Restart=always
```

---

## Debugging Tools

### Useful Commands

```bash
# System monitoring
htop                           # CPU/Memory usage
nvidia-smi -l 1               # GPU monitoring (WSL)
iftop                         # Network traffic
iotop                         # Disk I/O

# Service management
sudo systemctl status <service>
sudo journalctl -u <service> -f
sudo systemctl restart <service>

# Network diagnostics
ping <host>
mtr <host>
traceroute <host>
tcpdump -i any port 5000

# Performance profiling
perf top                      # CPU profiling
py-spy top --pid <pid>       # Python profiling
```

### Log Locations

```bash
# RPi
/var/log/rpi-vision/app.log
/var/log/rpi-vision/stdout.log
/var/log/rpi-vision/stderr.log

# WSL
/var/log/wsl-vision/app.log
/var/log/wsl-vision/stdout.log
/var/log/wsl-vision/stderr.log

# Systemd
sudo journalctl -u rpi-vision
sudo journalctl -u wsl-vision
```

### Configuration Validation

```bash
# Test YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yml'))"

# Test camera access
python test_cameras.py

# Test network connectivity
./scripts/health_check.sh
```

---

## Getting Help

If issues persist:

1. **Check logs**: Detailed error messages in log files
2. **Run health check**: `./scripts/health_check.sh`
3. **Test components individually**: cameras, network, models
4. **Review configuration**: Verify all settings
5. **Check resources**: CPU, memory, disk, GPU
6. **Update system**: Latest software versions
7. **Consult documentation**: README, DEPLOYMENT.md, API.md

For additional support, include:
- System specifications
- Error messages
- Logs
- Configuration files
- Steps to reproduce
