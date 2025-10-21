#!/bin/bash

# Cloudflare Tunnel Deployment Script for MailQueryWithMCP
# This script sets up and manages Cloudflare Tunnel for the unified HTTP server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TUNNEL_NAME="mailquery-mcp"
CONFIG_FILE="cloudflare-tunnel-config.yml"
SERVICE_FILE="cloudflared.service"
UNIFIED_SERVER="entrypoints/production/unified_http_server.py"

echo -e "${GREEN}MailQueryWithMCP Cloudflare Tunnel Deployment Script${NC}"
echo "=================================================="

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if cloudflared is installed
check_cloudflared() {
    if ! command -v cloudflared &> /dev/null; then
        print_error "cloudflared is not installed!"
        echo "Please install cloudflared first:"
        echo "  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared"
        echo "  chmod +x cloudflared"
        echo "  sudo mv cloudflared /usr/local/bin/"
        exit 1
    fi
    print_status "cloudflared is installed ($(cloudflared --version))"
}

# Login to Cloudflare (if not already logged in)
cloudflare_login() {
    if [ ! -f "$HOME/.cloudflared/cert.pem" ]; then
        print_warning "Not logged in to Cloudflare. Starting login process..."
        cloudflared tunnel login
    else
        print_status "Already logged in to Cloudflare"
    fi
}

# Create tunnel if it doesn't exist
create_tunnel() {
    if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
        print_status "Tunnel '$TUNNEL_NAME' already exists"
    else
        print_warning "Creating new tunnel '$TUNNEL_NAME'..."
        cloudflared tunnel create "$TUNNEL_NAME"
        print_status "Tunnel created successfully"
    fi

    # Get tunnel credentials file
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
    CRED_FILE="$HOME/.cloudflared/${TUNNEL_ID}.json"

    if [ ! -f "$CRED_FILE" ]; then
        print_error "Credentials file not found at $CRED_FILE"
        exit 1
    fi

    # Update config file with correct credentials path
    sed -i "s|credentials-file:.*|credentials-file: $CRED_FILE|" "$CONFIG_FILE"
    print_status "Updated config with credentials file: $CRED_FILE"
}

# Configure DNS
configure_dns() {
    echo ""
    print_warning "DNS Configuration Required!"
    echo "Please add the following CNAME record to your DNS:"
    echo ""
    echo "  Name: mailquery-mcp (or your preferred subdomain)"
    echo "  Target: ${TUNNEL_ID}.cfargotunnel.com"
    echo ""
    echo "You can do this through:"
    echo "1. Cloudflare Dashboard > DNS"
    echo "2. Or run: cloudflared tunnel route dns $TUNNEL_NAME mailquery-mcp.yourdomain.com"
    echo ""
    read -p "Press Enter when DNS is configured..."
}

# Start the unified HTTP server
start_unified_server() {
    print_status "Checking unified HTTP server..."

    # Check if already running
    if pgrep -f "$UNIFIED_SERVER" > /dev/null; then
        print_status "Unified HTTP server is already running"
    else
        print_warning "Starting unified HTTP server..."
        cd /home/kimghw/MailQueryWithMCP
        nohup python3 "$UNIFIED_SERVER" > logs/unified_server.log 2>&1 &
        sleep 3

        if pgrep -f "$UNIFIED_SERVER" > /dev/null; then
            print_status "Unified HTTP server started successfully"
        else
            print_error "Failed to start unified HTTP server"
            echo "Check logs/unified_server.log for details"
            exit 1
        fi
    fi
}

# Install systemd service
install_service() {
    print_status "Installing systemd service..."

    # Copy service file
    sudo cp "$SERVICE_FILE" /etc/systemd/system/

    # Reload systemd
    sudo systemctl daemon-reload

    # Enable and start service
    sudo systemctl enable cloudflared.service
    sudo systemctl restart cloudflared.service

    # Check status
    if sudo systemctl is-active --quiet cloudflared.service; then
        print_status "Cloudflare Tunnel service is running"
    else
        print_error "Failed to start Cloudflare Tunnel service"
        echo "Check logs with: sudo journalctl -u cloudflared -f"
        exit 1
    fi
}

# Test the tunnel
test_tunnel() {
    print_status "Testing tunnel connection..."

    # Wait for tunnel to establish
    sleep 5

    # Get tunnel info
    cloudflared tunnel info "$TUNNEL_NAME"

    echo ""
    print_status "Tunnel is active!"
    echo ""
    echo "Your application should now be accessible at:"
    echo "  https://mailquery-mcp.yourdomain.com"
    echo ""
    echo "Useful commands:"
    echo "  View tunnel status: cloudflared tunnel info $TUNNEL_NAME"
    echo "  View service logs: sudo journalctl -u cloudflared -f"
    echo "  Restart service: sudo systemctl restart cloudflared"
    echo "  Stop service: sudo systemctl stop cloudflared"
}

# Main execution
main() {
    case "${1:-deploy}" in
        deploy)
            check_cloudflared
            cloudflare_login
            create_tunnel
            configure_dns
            start_unified_server
            install_service
            test_tunnel
            ;;
        start)
            start_unified_server
            sudo systemctl start cloudflared
            print_status "Services started"
            ;;
        stop)
            sudo systemctl stop cloudflared
            pkill -f "$UNIFIED_SERVER" || true
            print_status "Services stopped"
            ;;
        restart)
            $0 stop
            $0 start
            ;;
        status)
            echo "Unified HTTP Server:"
            pgrep -f "$UNIFIED_SERVER" && echo "  Running" || echo "  Stopped"
            echo ""
            echo "Cloudflare Tunnel:"
            sudo systemctl status cloudflared --no-pager
            ;;
        logs)
            echo "Showing Cloudflare Tunnel logs (Ctrl+C to exit)..."
            sudo journalctl -u cloudflared -f
            ;;
        *)
            echo "Usage: $0 {deploy|start|stop|restart|status|logs}"
            echo ""
            echo "  deploy  - Full deployment (login, create tunnel, configure DNS, start services)"
            echo "  start   - Start the HTTP server and tunnel"
            echo "  stop    - Stop all services"
            echo "  restart - Restart all services"
            echo "  status  - Show service status"
            echo "  logs    - Show tunnel logs"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"