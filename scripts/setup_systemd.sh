#!/bin/bash
# Setup systemd services for vision system

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================================"
echo "Systemd Service Setup"
echo "================================================"

read -p "Setup for (1) Raspberry Pi or (2) WSL Server? " -n 1 -r
echo

if [[ $REPLY == "1" ]]; then
    echo -e "${GREEN}Setting up Raspberry Pi service...${NC}"
    bash scripts/deploy_rpi.sh
elif [[ $REPLY == "2" ]]; then
    echo -e "${GREEN}Setting up WSL Server service...${NC}"
    bash scripts/deploy_wsl.sh
else
    echo "Invalid option"
    exit 1
fi
