#!/bin/bash

# Cloudflared Installation Script
# Installs cloudflared for Cloudflare Tunnel support

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Cloudflared Installation Script${NC}"
echo "=================================="

# Detect system architecture
ARCH=$(uname -m)
OS=$(uname -s | tr '[:upper:]' '[:lower:]')

echo "Detected: OS=$OS, Architecture=$ARCH"

# Determine download URL based on architecture
case "$ARCH" in
    x86_64)
        DOWNLOAD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        ;;
    aarch64|arm64)
        DOWNLOAD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
        ;;
    armv7l)
        DOWNLOAD_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-armhf"
        ;;
    *)
        echo -e "${RED}Unsupported architecture: $ARCH${NC}"
        exit 1
        ;;
esac

# Method 1: Install via package manager (recommended)
echo -e "\n${YELLOW}Installation Options:${NC}"
echo "1) Install via package manager (requires sudo)"
echo "2) Download binary to local directory (no sudo)"
echo "3) Exit"

read -p "Choose option (1-3): " choice

case $choice in
    1)
        echo -e "\n${GREEN}Installing via package manager...${NC}"

        # Try different package managers
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            echo "Using apt package manager..."

            # Add cloudflare gpg key
            sudo mkdir -p --mode=0755 /usr/share/keyrings
            curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

            # Add repository
            echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

            # Update and install
            sudo apt-get update
            sudo apt-get install -y cloudflared

        elif command -v yum &> /dev/null; then
            # RHEL/CentOS/Fedora
            echo "Using yum package manager..."
            sudo rpm -ivh https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm

        elif command -v pacman &> /dev/null; then
            # Arch Linux
            echo "Using pacman package manager..."
            sudo pacman -S cloudflared

        else
            echo -e "${RED}No supported package manager found${NC}"
            echo "Falling back to binary download..."
            choice=2
        fi
        ;;

    2)
        echo -e "\n${GREEN}Downloading cloudflared binary...${NC}"

        # Download to local bin directory
        LOCAL_BIN="$HOME/.local/bin"
        mkdir -p "$LOCAL_BIN"

        echo "Downloading from: $DOWNLOAD_URL"
        curl -L "$DOWNLOAD_URL" -o "$LOCAL_BIN/cloudflared"
        chmod +x "$LOCAL_BIN/cloudflared"

        # Check if .local/bin is in PATH
        if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
            echo -e "\n${YELLOW}Note: Add $LOCAL_BIN to your PATH${NC}"
            echo "Add this line to your ~/.bashrc or ~/.zshrc:"
            echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
            echo ""
            echo "Then reload your shell:"
            echo "  source ~/.bashrc"
        fi

        CLOUDFLARED_PATH="$LOCAL_BIN/cloudflared"
        ;;

    3)
        echo "Installation cancelled."
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

# Verify installation
echo -e "\n${GREEN}Verifying installation...${NC}"

if [ "$choice" = "1" ]; then
    CLOUDFLARED_PATH="cloudflared"
elif [ "$choice" = "2" ]; then
    CLOUDFLARED_PATH="$LOCAL_BIN/cloudflared"
fi

if command -v $CLOUDFLARED_PATH &> /dev/null || [ -x "$CLOUDFLARED_PATH" ]; then
    echo -e "${GREEN}✓ Cloudflared installed successfully!${NC}"
    $CLOUDFLARED_PATH --version
    echo ""
    echo "Next steps:"
    echo "1. Run: cloudflared tunnel login"
    echo "2. Create tunnel: cloudflared tunnel create mailquery-mcp"
    echo "3. Run deployment script: ./deploy-cloudflare-tunnel.sh deploy"
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi

# Optional: Install as systemd service
if [ "$choice" = "1" ]; then
    echo ""
    read -p "Install cloudflared as systemd service? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo cloudflared service install
        echo -e "${GREEN}✓ Systemd service installed${NC}"
        echo "Control service with:"
        echo "  sudo systemctl start cloudflared"
        echo "  sudo systemctl stop cloudflared"
        echo "  sudo systemctl status cloudflared"
    fi
fi

echo -e "\n${GREEN}Installation complete!${NC}"