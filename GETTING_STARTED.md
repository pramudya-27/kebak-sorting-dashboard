# Getting Started Checklist

Use this checklist to ensure proper setup and deployment of the Distributed Computer Vision System.

## Pre-Deployment

### Hardware Requirements
- [ ] Raspberry Pi 5 with adequate cooling
- [ ] Two CSI camera modules
- [ ] Camera ribbon cables properly connected
- [ ] Power supply (5V, 5A recommended)
- [ ] MicroSD card (32GB+ recommended)
- [ ] WSL server with NVIDIA GPU
- [ ] Stable network connection (Tailscale)

### Software Requirements - Raspberry Pi
- [ ] Raspberry Pi OS (64-bit) installed
- [ ] System updated: `sudo apt update && sudo apt upgrade`
- [ ] Miniforge/Conda installed
- [ ] Tailscale installed and configured
- [ ] Git installed
- [ ] Camera interface enabled in raspi-config

### Software Requirements - WSL Server
- [ ] Windows 10/11 with WSL2 enabled
- [ ] Ubuntu 20.04+ on WSL
- [ ] NVIDIA drivers installed in Windows
- [ ] CUDA Toolkit 11.8+ available
- [ ] Miniconda/Conda installed
- [ ] Tailscale installed and configured
- [ ] Git installed

---

## Raspberry Pi Setup

### 1. System Preparation
- [ ] SSH access configured
- [ ] Static IP or hostname set
- [ ] Tailscale connected: `tailscale status`
- [ ] Note Tailscale IP: `tailscale ip -4`

### 2. Camera Testing
- [ ] Both cameras detected: `libcamera-hello --list-cameras`
- [ ] Camera 0 working: `libcamera-still -o test0.jpg --camera 0`
- [ ] Camera 1 working: `libcamera-still -o test1.jpg --camera 1`

### 3. Repository Setup
- [ ] Repository cloned: `git clone <url> ~/kebak_sorting`
- [ ] Changed to project directory: `cd ~/kebak_sorting`
- [ ] Scripts are executable: `chmod +x scripts/*.sh`

### 4. Environment Setup
- [ ] Conda environment created: `conda env create -f rpi/environment.yml`
- [ ] Environment activated: `conda activate rpi-vision`
- [ ] Dependencies verified: `python -c "import picamera2, cv2; print('OK')"`

### 5. Configuration
- [ ] Config copied: `cp rpi/config.example.yml rpi/config.yml`
- [ ] WSL Tailscale IP added to config
- [ ] Camera settings adjusted if needed
- [ ] Network settings configured
- [ ] Config syntax validated: `python -c "import yaml; yaml.safe_load(open('rpi/config.yml'))"`

### 6. Testing
- [ ] Camera test passed: `python rpi/test_cameras.py`
- [ ] Test images saved successfully
- [ ] Manual run successful: `python rpi/main.py --config rpi/config.yml`

### 7. Deployment
- [ ] Deployment script run: `sudo ./scripts/deploy_rpi.sh`
- [ ] Service enabled
- [ ] Service started
- [ ] Service status checked: `sudo systemctl status rpi-vision`
- [ ] Logs accessible: `tail -f /var/log/rpi-vision/app.log`

---

## WSL Server Setup

### 1. System Preparation
- [ ] WSL2 installed and running
- [ ] Ubuntu shell accessible
- [ ] Tailscale connected: `tailscale status`
- [ ] Note Tailscale IP: `tailscale ip -4`

### 2. GPU Testing
- [ ] NVIDIA driver visible: `nvidia-smi`
- [ ] GPU details displayed
- [ ] No errors in nvidia-smi output

### 3. Repository Setup
- [ ] Repository cloned: `git clone <url> ~/kebak_sorting`
- [ ] Changed to project directory: `cd ~/kebak_sorting`
- [ ] Scripts are executable: `chmod +x scripts/*.sh`

### 4. Environment Setup
- [ ] Conda environment created: `conda env create -f wsl/environment.yml`
- [ ] Environment activated: `conda activate wsl-vision`
- [ ] PyTorch with CUDA working: `python -c "import torch; print(torch.cuda.is_available())"`

### 5. Model Download
- [ ] Models downloaded: `python wsl/download_models.py`
- [ ] yolov8n.pt present: `ls -lh yolov8n.pt`
- [ ] yolov8s.pt present: `ls -lh yolov8s.pt`
- [ ] yolov8m.pt present: `ls -lh yolov8m.pt`

### 6. Configuration
- [ ] Config copied: `cp wsl/config.example.yml wsl/config.yml`
- [ ] GPU device set correctly (cuda:0)
- [ ] Model parameters adjusted if needed
- [ ] API settings configured
- [ ] Config syntax validated: `python -c "import yaml; yaml.safe_load(open('wsl/config.yml'))"`

### 7. Firewall Configuration
- [ ] UDP port opened: `sudo ufw allow 5000/udp`
- [ ] HTTP port opened: `sudo ufw allow 8000/tcp`
- [ ] Firewall status checked: `sudo ufw status`

### 8. Testing
- [ ] Manual run successful: `python wsl/main.py --config wsl/config.yml`
- [ ] API accessible: `curl http://localhost:8000/health`
- [ ] No errors in console output

### 9. Deployment
- [ ] Deployment script run: `sudo ./scripts/deploy_wsl.sh`
- [ ] Service enabled
- [ ] Service started
- [ ] Service status checked: `sudo systemctl status wsl-vision`
- [ ] Logs accessible: `tail -f /var/log/wsl-vision/app.log`

---

## Integration Testing

### 1. Network Connectivity
- [ ] RPi can ping WSL: `ping <wsl-tailscale-ip>`
- [ ] WSL can ping RPi: `ping <rpi-tailscale-ip>`
- [ ] Tailscale connection stable
- [ ] Latency acceptable (< 100ms)

### 2. UDP Communication
- [ ] RPi transmitting frames: Check RPi logs
- [ ] WSL receiving frames: Check WSL logs
- [ ] Frame rate stable
- [ ] No significant packet loss

### 3. Inference Pipeline
- [ ] Frames being processed on WSL
- [ ] Detections appearing in logs
- [ ] Inference time acceptable (< 100ms)
- [ ] GPU being utilized: `nvidia-smi`

### 4. API Functionality
- [ ] Health endpoint responding: `curl http://<wsl-ip>:8000/health`
- [ ] Stats endpoint working: `curl http://<wsl-ip>:8000/api/v1/stats`
- [ ] Latest detections available: `curl http://<wsl-ip>:8000/api/v1/detections/latest`

### 5. Dashboard Access
- [ ] Dashboard accessible: `http://<wsl-ip>:8000/dashboard`
- [ ] Page loads without errors
- [ ] WebSocket connects
- [ ] Live detections appearing
- [ ] Statistics updating
- [ ] No console errors

---

## Verification

### Performance Metrics
- [ ] Capture FPS: _____
- [ ] Network latency: _____ ms
- [ ] Inference time: _____ ms
- [ ] End-to-end latency: _____ ms
- [ ] GPU utilization: _____ %
- [ ] CPU usage (RPi): _____ %
- [ ] Memory usage (RPi): _____ MB
- [ ] Memory usage (WSL): _____ GB

### Quality Checks
- [ ] Camera images clear and focused
- [ ] Compression quality acceptable
- [ ] Detections accurate
- [ ] No significant false positives
- [ ] Confidence scores reasonable
- [ ] Dashboard visualization correct

### Reliability
- [ ] System runs for 1 hour without errors
- [ ] Services auto-restart on failure
- [ ] Logs rotating properly
- [ ] No memory leaks observed
- [ ] Network connection stable

---

## Production Readiness

### Security
- [ ] Tailscale authentication configured
- [ ] API CORS settings reviewed
- [ ] Default passwords changed
- [ ] Firewall rules appropriate
- [ ] SSH keys configured (not passwords)

### Monitoring
- [ ] Health check script tested: `sudo ./scripts/health_check.sh`
- [ ] Log rotation configured
- [ ] Disk space monitored
- [ ] Alert mechanisms in place

### Documentation
- [ ] Configuration documented
- [ ] Network topology documented
- [ ] Troubleshooting procedures reviewed
- [ ] Emergency contacts listed
- [ ] Backup procedures defined

### Backup
- [ ] Configuration files backed up
- [ ] Recovery procedure tested
- [ ] Model files backed up (if modified)

---

## Post-Deployment

### Week 1
- [ ] Monitor performance daily
- [ ] Check logs for errors
- [ ] Verify uptime
- [ ] Document any issues
- [ ] Fine-tune configuration

### Month 1
- [ ] Review performance metrics
- [ ] Optimize as needed
- [ ] Update documentation
- [ ] Plan improvements
- [ ] Backup configurations

---

## Troubleshooting Reference

If issues occur, check:
1. **Service status**: `sudo systemctl status <service>`
2. **Logs**: `sudo journalctl -u <service> -n 50`
3. **Resources**: `htop`, `nvidia-smi`
4. **Network**: `ping`, `tailscale status`
5. **Documentation**: See `docs/TROUBLESHOOTING.md`

---

## Quick Commands

### Start Everything
```bash
# On RPi
sudo systemctl start rpi-vision

# On WSL
sudo systemctl start wsl-vision
```

### Check Status
```bash
# On RPi
sudo ./scripts/health_check.sh

# On WSL
sudo ./scripts/health_check.sh
curl http://localhost:8000/health
```

### View Logs
```bash
# On RPi
sudo journalctl -u rpi-vision -f

# On WSL
sudo journalctl -u wsl-vision -f
```

---

## Sign-Off

### Raspberry Pi Deployment
- [ ] All checks passed
- [ ] System stable
- [ ] Deployed by: ________________
- [ ] Date: ________________
- [ ] Notes: ________________

### WSL Server Deployment
- [ ] All checks passed
- [ ] System stable
- [ ] Deployed by: ________________
- [ ] Date: ________________
- [ ] Notes: ________________

### Final System Verification
- [ ] End-to-end pipeline working
- [ ] Performance acceptable
- [ ] Documentation complete
- [ ] Team trained
- [ ] Support procedures in place

**System Status**: ☐ Development  ☐ Testing  ☐ **Production**

---

## Support

For issues during setup:
1. Review relevant documentation
2. Check troubleshooting guide
3. Verify all prerequisites
4. Test components individually
5. Review logs for specific errors

**Congratulations! Your distributed vision system is ready! 🎉**
