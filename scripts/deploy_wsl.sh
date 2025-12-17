#!/bin/bash
# Deployment script for WSL YOLO Inference Server

set -e

echo "================================================"
echo "WSL YOLO Inference Server Deployment"
echo "================================================"

# Configuration
INSTALL_DIR="/opt/wsl-vision"
SERVICE_NAME="wsl-vision"
LOG_DIR="/var/log/wsl-vision"
CONDA_ENV="wsl-vision"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

echo -e "${GREEN}Step 1: Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

echo -e "${GREEN}Step 2: Copying application files...${NC}"
cp -r wsl/* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/main.py"

echo -e "${GREEN}Step 3: Setting up configuration...${NC}"
if [ ! -f "$INSTALL_DIR/config.yml" ]; then
    cp "$INSTALL_DIR/config.example.yml" "$INSTALL_DIR/config.yml"
    echo -e "${YELLOW}Configuration file created. Please edit $INSTALL_DIR/config.yml${NC}"
else
    echo -e "${YELLOW}Configuration file already exists${NC}"
fi

echo -e "${GREEN}Step 4: Downloading YOLO models...${NC}"
read -p "Download YOLO models now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo -u $SUDO_USER bash << EOF
        source ~/miniconda3/etc/profile.d/conda.sh
        conda activate ${CONDA_ENV}
        cd "$INSTALL_DIR"
        python download_models.py
EOF
    echo -e "${GREEN}Models downloaded${NC}"
else
    echo -e "${YELLOW}Skipping model download. Run 'python download_models.py' later${NC}"
fi

echo -e "${GREEN}Step 5: Creating systemd service...${NC}"
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=WSL Multi-Model YOLO Inference Server
After=network.target

[Service]
Type=simple
User=$SUDO_USER
Group=$SUDO_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=/home/$SUDO_USER/miniconda3/envs/${CONDA_ENV}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="CUDA_VISIBLE_DEVICES=0"
ExecStart=/home/$SUDO_USER/miniconda3/envs/${CONDA_ENV}/bin/python main.py --config config.yml
Restart=always
RestartSec=10
StandardOutput=append:${LOG_DIR}/stdout.log
StandardError=append:${LOG_DIR}/stderr.log

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}Step 6: Enabling and starting service...${NC}"
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}.service

read -p "Start the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl start ${SERVICE_NAME}.service
    echo -e "${GREEN}Service started${NC}"
    sleep 2
    systemctl status ${SERVICE_NAME}.service
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Service name: ${SERVICE_NAME}"
echo "Install directory: ${INSTALL_DIR}"
echo "Log directory: ${LOG_DIR}"
echo "Dashboard URL: http://localhost:8000/dashboard"
echo ""
echo "Useful commands:"
echo "  sudo systemctl start ${SERVICE_NAME}     - Start the service"
echo "  sudo systemctl stop ${SERVICE_NAME}      - Stop the service"
echo "  sudo systemctl restart ${SERVICE_NAME}   - Restart the service"
echo "  sudo systemctl status ${SERVICE_NAME}    - Check service status"
echo "  sudo journalctl -u ${SERVICE_NAME} -f   - View live logs"
echo "  tail -f ${LOG_DIR}/app.log              - View application logs"
echo ""
echo "API endpoints:"
echo "  http://localhost:8000/health            - Health check"
echo "  http://localhost:8000/api/v1/stats      - Statistics"
echo "  http://localhost:8000/dashboard         - Web dashboard"
echo ""
echo -e "${YELLOW}Don't forget to:${NC}"
echo "  1. Edit $INSTALL_DIR/config.yml with your settings"
echo "  2. Verify GPU is accessible (nvidia-smi)"
echo "  3. Open firewall ports if needed (5000 UDP, 8000 TCP)"
echo ""
