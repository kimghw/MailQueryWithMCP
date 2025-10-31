#!/bin/bash

# Cloudflare Manager for MailQueryWithMCP
# Combined cloudflared installation and tunnel deployment script
# - Installs cloudflared if not present
# - Manages unified server and Cloudflare tunnel
# - Smart management of services with interactive menu

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TUNNEL_NAME="mailquery-mcp"
CONFIG_FILE="cloudflare-tunnel-config.yml"
SERVICE_FILE="cloudflared.service"
UNIFIED_SERVER_SCRIPT="entrypoints/production/run_unified_http.sh"
UNIFIED_SERVER_PROCESS="unified_http_server.py"
PROJECT_DIR="/home/kimghw/MailQueryWithMCP"
LOG_DIR="$PROJECT_DIR/logs"
UNIFIED_PID_FILE="/tmp/unified_server.pid"

echo -e "${GREEN}MailQueryWithMCP Cloudflare Manager${NC}"
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

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# ==================== INSTALLATION FUNCTIONS ====================

# Install cloudflared
install_cloudflared() {
    echo -e "\n${GREEN}Installing cloudflared...${NC}"
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
            return 1
            ;;
    esac

    echo -e "\n${YELLOW}Installation Options:${NC}"
    echo "1) Install via package manager (requires sudo)"
    echo "2) Download binary to local directory (no sudo)"
    echo "3) Cancel"

    read -p "Choose option (1-3): " install_choice

    case $install_choice in
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
                install_choice=2
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
                export PATH="$HOME/.local/bin:$PATH"
            fi

            CLOUDFLARED_PATH="$LOCAL_BIN/cloudflared"
            ;;

        3)
            echo "Installation cancelled."
            return 1
            ;;

        *)
            echo -e "${RED}Invalid option${NC}"
            return 1
            ;;
    esac

    # Verify installation
    echo -e "\n${GREEN}Verifying installation...${NC}"

    if [ "$install_choice" = "1" ]; then
        CLOUDFLARED_PATH="cloudflared"
    elif [ "$install_choice" = "2" ]; then
        CLOUDFLARED_PATH="$LOCAL_BIN/cloudflared"
    fi

    if command -v $CLOUDFLARED_PATH &> /dev/null || [ -x "$CLOUDFLARED_PATH" ]; then
        echo -e "${GREEN}✓ Cloudflared installed successfully!${NC}"
        $CLOUDFLARED_PATH --version

        # Set global variable
        CLOUDFLARED_BIN="$CLOUDFLARED_PATH"

        # Optional: Install as systemd service
        if [ "$install_choice" = "1" ]; then
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

        return 0
    else
        echo -e "${RED}✗ Installation failed${NC}"
        return 1
    fi
}

# Check if cloudflared is installed
check_cloudflared() {
    # Check in PATH first
    if command -v cloudflared &> /dev/null; then
        CLOUDFLARED_BIN="cloudflared"
        print_status "cloudflared is installed ($(cloudflared --version))"
        return 0
    fi

    # Check in ~/.local/bin
    if [ -x "$HOME/.local/bin/cloudflared" ]; then
        CLOUDFLARED_BIN="$HOME/.local/bin/cloudflared"
        print_status "cloudflared is installed ($($CLOUDFLARED_BIN --version))"
        export PATH="$HOME/.local/bin:$PATH"
        return 0
    fi

    print_error "cloudflared is not installed!"
    echo ""
    read -p "Would you like to install cloudflared now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if install_cloudflared; then
            return 0
        fi
    fi

    echo ""
    echo "Manual installation:"
    echo "  mkdir -p ~/.local/bin"
    echo "  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ~/.local/bin/cloudflared"
    echo "  chmod +x ~/.local/bin/cloudflared"
    exit 1
}

# ==================== SERVICE MANAGEMENT FUNCTIONS ====================

# Check unified server status
check_unified_status() {
    if [ -f "$UNIFIED_PID_FILE" ]; then
        PID=$(cat "$UNIFIED_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            if ps -p "$PID" -o comm= | grep -q python; then
                return 0  # Running
            fi
        fi
        # PID file exists but process is dead, cleanup
        rm -f "$UNIFIED_PID_FILE"
    fi

    # Double check with pgrep
    if pgrep -f "$UNIFIED_SERVER_PROCESS" > /dev/null; then
        # Update PID file
        pgrep -f "$UNIFIED_SERVER_PROCESS" | head -1 > "$UNIFIED_PID_FILE"
        return 0  # Running
    fi

    return 1  # Not running
}

# Start the unified HTTP server
start_unified_server() {
    if check_unified_status; then
        print_status "Unified HTTP server is already running (PID: $(cat $UNIFIED_PID_FILE))"
        return 0
    fi

    print_warning "Starting unified HTTP server..."

    # Ensure log directory exists
    mkdir -p "$LOG_DIR"

    cd "$PROJECT_DIR"

    # Use the production startup script
    print_info "Using production startup script: $UNIFIED_SERVER_SCRIPT"
    nohup bash "$UNIFIED_SERVER_SCRIPT" > "$LOG_DIR/unified_server.log" 2>&1 &

    UNIFIED_PID=$!
    echo $UNIFIED_PID > "$UNIFIED_PID_FILE"

    sleep 3

    if check_unified_status; then
        print_status "Unified HTTP server started successfully (PID: $UNIFIED_PID)"
        return 0
    else
        print_error "Failed to start unified HTTP server"
        echo "Check $LOG_DIR/unified_server.log for details"
        rm -f "$UNIFIED_PID_FILE"
        return 1
    fi
}

# Stop unified server
stop_unified_server() {
    if [ -f "$UNIFIED_PID_FILE" ]; then
        PID=$(cat "$UNIFIED_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            sleep 2
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID" 2>/dev/null || true
            fi
        fi
        rm -f "$UNIFIED_PID_FILE"
    fi

    # Backup kill by process name
    pkill -f "$UNIFIED_SERVER_PROCESS" 2>/dev/null || true

    print_status "Unified HTTP server stopped"
}

# Start Quick Tunnel in background
start_quick_tunnel_background() {
    QUICK_PID_FILE="/tmp/quick_tunnel.pid"
    QUICK_LOG_FILE="$LOG_DIR/quick_tunnel.log"

    # Check if already running
    if [ -f "$QUICK_PID_FILE" ]; then
        PID=$(cat "$QUICK_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_status "Quick Tunnel이 이미 실행 중입니다 (PID: $PID)"
            print_info "로그 확인: tail -f $QUICK_LOG_FILE"

            # Try to extract URL from log
            URL=$(grep -o "https://.*\.trycloudflare\.com" "$QUICK_LOG_FILE" 2>/dev/null | tail -1)
            if [ -n "$URL" ]; then
                print_status "접속 URL: $URL"
                # Update .env redirect URIs even if already running
                update_env_redirect_uris "$URL"
            fi
            return 0
        fi
        rm -f "$QUICK_PID_FILE"
    fi

    # Ensure cloudflared exists
    if [ -z "$CLOUDFLARED_BIN" ]; then
        check_cloudflared
    fi

    # Start Quick Tunnel in background
    print_warning "Quick Tunnel을 백그라운드로 시작합니다..."
    mkdir -p "$LOG_DIR"

    nohup $CLOUDFLARED_BIN tunnel --url http://localhost:8000 > "$QUICK_LOG_FILE" 2>&1 &
    QUICK_PID=$!
    echo $QUICK_PID > "$QUICK_PID_FILE"

    # Wait for URL to appear in log
    print_info "Quick Tunnel URL 대기 중..."
    for i in {1..10}; do
        sleep 2
        URL=$(grep -o "https://.*\.trycloudflare\.com" "$QUICK_LOG_FILE" 2>/dev/null | tail -1)
        if [ -n "$URL" ]; then
            print_status "Quick Tunnel 시작 성공! (PID: $QUICK_PID)"
            echo ""
            echo "==================================="
            echo "접속 URL: ${GREEN}$URL${NC}"
            echo "==================================="
            echo ""

            # Update .env redirect URIs
            update_env_redirect_uris "$URL"

            print_info "로그 확인: tail -f $QUICK_LOG_FILE"
            return 0
        fi
    done

    print_error "Quick Tunnel 시작 실패"
    print_info "로그 확인: cat $QUICK_LOG_FILE"
    return 1
}

# Update .env redirect URIs with tunnel URL
update_env_redirect_uris() {
    local TUNNEL_URL=$1
    local ENV_FILE="$PROJECT_DIR/.env"

    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env 파일이 없습니다"
        return 1
    fi

    print_info ".env 파일의 Redirect URIs 업데이트 중..."

    # Update DCR_OAUTH_REDIRECT_URI
    if grep -q "^DCR_OAUTH_REDIRECT_URI=" "$ENV_FILE"; then
        sed -i "s|^DCR_OAUTH_REDIRECT_URI=.*|DCR_OAUTH_REDIRECT_URI=$TUNNEL_URL/oauth/azure_callback|" "$ENV_FILE"
        print_status "DCR_OAUTH_REDIRECT_URI 업데이트됨"
    else
        echo "DCR_OAUTH_REDIRECT_URI=$TUNNEL_URL/oauth/azure_callback" >> "$ENV_FILE"
        print_status "DCR_OAUTH_REDIRECT_URI 추가됨"
    fi

    # Update AUTO_REGISTER_OAUTH_REDIRECT_URI
    if grep -q "^AUTO_REGISTER_OAUTH_REDIRECT_URI=" "$ENV_FILE"; then
        sed -i "s|^AUTO_REGISTER_OAUTH_REDIRECT_URI=.*|AUTO_REGISTER_OAUTH_REDIRECT_URI=$TUNNEL_URL/enrollment/callback|" "$ENV_FILE"
        print_status "AUTO_REGISTER_OAUTH_REDIRECT_URI 업데이트됨"
    else
        echo "AUTO_REGISTER_OAUTH_REDIRECT_URI=$TUNNEL_URL/enrollment/callback" >> "$ENV_FILE"
        print_status "AUTO_REGISTER_OAUTH_REDIRECT_URI 추가됨"
    fi

    echo ""
    echo "  ${GREEN}✓${NC} DCR_OAUTH_REDIRECT_URI=$TUNNEL_URL/oauth/azure_callback"
    echo "  ${GREEN}✓${NC} AUTO_REGISTER_OAUTH_REDIRECT_URI=$TUNNEL_URL/enrollment/callback"
    echo ""
    print_warning "서버를 재시작하여 변경사항을 적용하세요"
}

# Stop Quick Tunnel
stop_quick_tunnel() {
    QUICK_PID_FILE="/tmp/quick_tunnel.pid"

    if [ -f "$QUICK_PID_FILE" ]; then
        PID=$(cat "$QUICK_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            sleep 2
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID" 2>/dev/null || true
            fi
            print_status "Quick Tunnel 중지됨 (PID: $PID)"
        fi
        rm -f "$QUICK_PID_FILE"
    else
        # Backup: kill by process pattern
        pkill -f "cloudflared.*tunnel.*--url" 2>/dev/null || true
    fi
}

# ==================== UI FUNCTIONS ====================

# Interactive menu function
interactive_menu() {
    echo ""
    echo "=== 현재 서비스 상태 ==="
    echo ""

    UNIFIED_RUNNING=false
    QUICK_RUNNING=false

    # Check unified status
    echo "┌─────────────────────────────────────────────────────────────────────────┐"
    echo "│ Unified Server                                                          │"
    echo "├─────────────────────────────────────────────────────────────────────────┤"
    if check_unified_status; then
        UNIFIED_RUNNING=true
        PID=$(cat $UNIFIED_PID_FILE)
        echo "│ 상태: 실행 중 (PID: $PID)"
        echo "│"
        echo "│ 로컬 엔드포인트:"
        echo "│   • Mail Query:  http://localhost:8000/mail-query/"
        echo "│   • Enrollment:  http://localhost:8000/enrollment/"
        echo "│   • OneNote:     http://localhost:8000/onenote/"
        echo "│   • Health:      http://localhost:8000/health"
    else
        echo "│ 상태: 중지됨"
    fi
    echo "└─────────────────────────────────────────────────────────────────────────┘"
    echo ""

    # Check Quick Tunnel status
    QUICK_PID_FILE="/tmp/quick_tunnel.pid"

    # Check both PID file and actual cloudflared process
    CLOUDFLARED_PID=""
    if [ -f "$QUICK_PID_FILE" ] && ps -p "$(cat $QUICK_PID_FILE)" > /dev/null 2>&1; then
        CLOUDFLARED_PID=$(cat "$QUICK_PID_FILE")
    else
        # Check if cloudflared tunnel is running without PID file
        CLOUDFLARED_PID=$(pgrep -f "cloudflared.*tunnel.*--url" 2>/dev/null | head -1)
    fi

    echo "┌─────────────────────────────────────────────────────────────────────────┐"
    echo "│ Quick Tunnel (무료)                                                     │"
    echo "├─────────────────────────────────────────────────────────────────────────┤"
    if [ -n "$CLOUDFLARED_PID" ]; then
        QUICK_RUNNING=true
        echo "│ 상태: 실행 중 (PID: $CLOUDFLARED_PID)"

        # Try to get URL from log file first
        QUICK_LOG_FILE="$LOG_DIR/quick_tunnel.log"
        TUNNEL_URL=""
        if [ -f "$QUICK_LOG_FILE" ]; then
            TUNNEL_URL=$(grep -o "https://.*\.trycloudflare\.com" "$QUICK_LOG_FILE" 2>/dev/null | tail -1)
        fi

        # Try to get URL from metrics endpoint
        if [ -z "$TUNNEL_URL" ]; then
            TUNNEL_URL=$(curl -s http://127.0.0.1:20241/metrics 2>/dev/null | grep "userHostname=" | grep -o "https://[^\"]*\.trycloudflare\.com" | head -1)
        fi

        if [ -n "$TUNNEL_URL" ]; then
            echo "│"
            echo "│ 공개 URL:"
            echo "│   $TUNNEL_URL"
            echo "│"
            echo "│ MCP 서버 엔드포인트:"
            echo "│   • Mail Query:  $TUNNEL_URL/mail-query/"
            echo "│   • Enrollment:  $TUNNEL_URL/enrollment/"
            echo "│   • OneNote:     $TUNNEL_URL/onenote/"
            echo "│"
            echo "│ OAuth Redirect URIs:"
            echo "│   • Enrollment:  $TUNNEL_URL/enrollment/callback"
            echo "│   • Azure DCR:   $TUNNEL_URL/oauth/azure_callback"
            echo "│"
            echo "│ Health Check:"
            echo "│   $TUNNEL_URL/health"
        else
            echo "│ 터널 URL 확인 중... (잠시만 기다려주세요)"
        fi
    else
        echo "│ 상태: 중지됨"
    fi
    echo "└─────────────────────────────────────────────────────────────────────────┘"

    echo ""
    echo "=== 실행 옵션 ==="
    echo ""
    echo "1) Unified Server 시작/중지"
    echo "2) Quick Tunnel 시작 (무료, 임시 URL)"
    echo "3) Quick Tunnel 백그라운드 시작"
    echo "4) Quick Tunnel 중지"
    echo "5) 상태 확인"
    echo "6) 로그 보기"
    echo "7) cloudflared 설치/재설치"
    echo "0) 종료"
    echo ""

    read -p "선택하세요: " choice

    case $choice in
        1)
            # Unified Server 토글
            if [ "$UNIFIED_RUNNING" = true ]; then
                print_warning "Unified Server를 중지합니다..."
                stop_unified_server
            else
                print_warning "Unified Server를 시작합니다..."
                start_unified_server
            fi
            ;;
        2)
            # Quick Tunnel 포그라운드 시작
            if [ "$QUICK_RUNNING" = true ]; then
                print_warning "Quick Tunnel이 이미 실행 중입니다"
                QUICK_LOG_FILE="$LOG_DIR/quick_tunnel.log"
                URL=$(grep -o "https://.*\.trycloudflare\.com" "$QUICK_LOG_FILE" 2>/dev/null | tail -1)
                if [ -n "$URL" ]; then
                    echo "접속 URL: ${GREEN}$URL${NC}"
                fi
            else
                # Check cloudflared
                if [ -z "$CLOUDFLARED_BIN" ]; then
                    check_cloudflared
                fi

                # Unified 서버 확인 및 시작
                if [ "$UNIFIED_RUNNING" = false ]; then
                    print_warning "Unified Server를 먼저 시작합니다..."
                    start_unified_server
                    if [ $? -ne 0 ]; then
                        print_error "Unified Server 시작 실패"
                        return 1
                    fi
                fi

                # Quick Tunnel 시작
                echo ""
                print_status "Quick Tunnel을 시작합니다 (무료)..."
                print_info "임시 도메인이 생성됩니다. Ctrl+C로 종료할 수 있습니다."
                echo ""

                # Quick Tunnel 실행 (foreground)
                $CLOUDFLARED_BIN tunnel --url http://localhost:8000
            fi
            ;;
        3)
            # Quick Tunnel 백그라운드 시작
            if [ "$QUICK_RUNNING" = true ]; then
                print_warning "Quick Tunnel이 이미 실행 중입니다"
                QUICK_LOG_FILE="$LOG_DIR/quick_tunnel.log"
                URL=$(grep -o "https://.*\.trycloudflare\.com" "$QUICK_LOG_FILE" 2>/dev/null | tail -1)
                if [ -n "$URL" ]; then
                    echo "접속 URL: ${GREEN}$URL${NC}"
                fi
            else
                # Check cloudflared
                if [ -z "$CLOUDFLARED_BIN" ]; then
                    check_cloudflared
                fi

                # Unified 서버 확인 및 시작
                if [ "$UNIFIED_RUNNING" = false ]; then
                    print_warning "Unified Server를 먼저 시작합니다..."
                    start_unified_server
                    if [ $? -ne 0 ]; then
                        print_error "Unified Server 시작 실패"
                        return 1
                    fi
                fi

                # Quick Tunnel 백그라운드 시작
                start_quick_tunnel_background
            fi
            ;;
        4)
            # Quick Tunnel 중지
            if [ "$QUICK_RUNNING" = true ]; then
                stop_quick_tunnel
            else
                print_warning "Quick Tunnel이 실행 중이지 않습니다"
            fi
            ;;
        5)
            detailed_status
            ;;
        6)
            echo ""
            echo "로그 옵션:"
            echo "1) Unified server logs"
            echo "2) Quick Tunnel logs"
            echo "3) Both (화면 분할)"
            read -p "Choice (1-3): " log_choice

            case $log_choice in
                1)
                    tail -f "$LOG_DIR/unified_server.log"
                    ;;
                2)
                    if [ -f "$LOG_DIR/quick_tunnel.log" ]; then
                        tail -f "$LOG_DIR/quick_tunnel.log"
                    else
                        print_warning "Quick Tunnel이 실행된 적이 없습니다"
                    fi
                    ;;
                3)
                    if command -v tmux &> /dev/null; then
                        tmux new-session \; \
                            send-keys "tail -f $LOG_DIR/unified_server.log" C-m \; \
                            split-window -h \; \
                            send-keys "tail -f $LOG_DIR/quick_tunnel.log" C-m \;
                    else
                        print_error "tmux not installed. Install with: sudo apt install tmux"
                    fi
                    ;;
            esac
            ;;
        7)
            # Install/Reinstall cloudflared
            install_cloudflared
            ;;
        0)
            echo "종료합니다."
            exit 0
            ;;
        *)
            print_error "잘못된 선택입니다"
            ;;
    esac

    echo ""
    show_access_info

    # Automatically show menu again
    echo ""
    interactive_menu
}

# Show access information
show_access_info() {
    if check_unified_status; then
        print_status "Unified Server is active!"
        echo ""
        echo "Access points:"
        echo "  Local: http://localhost:8000"

        # Check if Quick Tunnel is running
        QUICK_PID_FILE="/tmp/quick_tunnel.pid"
        if [ -f "$QUICK_PID_FILE" ] && ps -p "$(cat $QUICK_PID_FILE)" > /dev/null 2>&1; then
            QUICK_LOG_FILE="$LOG_DIR/quick_tunnel.log"
            URL=$(grep -o "https://.*\.trycloudflare\.com" "$QUICK_LOG_FILE" 2>/dev/null | tail -1)
            if [ -n "$URL" ]; then
                echo "  Tunnel: $URL"
            fi
        fi

        echo ""
        echo "Logs:"
        echo "  Unified server: tail -f $LOG_DIR/unified_server.log"

        if [ -f "$QUICK_PID_FILE" ] && ps -p "$(cat $QUICK_PID_FILE)" > /dev/null 2>&1; then
            echo "  Quick Tunnel: tail -f $LOG_DIR/quick_tunnel.log"
        fi
    fi
}

# Detailed status
detailed_status() {
    echo ""
    echo "=== Service Status ==="
    echo ""

    echo "Unified HTTP Server:"
    if check_unified_status; then
        PID=$(cat "$UNIFIED_PID_FILE")
        echo "  Status: ${GREEN}RUNNING${NC}"
        echo "  PID: $PID"
        echo "  Memory: $(ps -o rss= -p $PID | awk '{print int($1/1024) "MB"}' 2>/dev/null || echo "N/A")"
        echo "  Uptime: $(ps -o etime= -p $PID 2>/dev/null || echo "N/A")"
    else
        echo "  Status: ${RED}STOPPED${NC}"
    fi

    echo ""
    echo "Quick Tunnel (무료):"
    QUICK_PID_FILE="/tmp/quick_tunnel.pid"

    # Check both PID file and actual cloudflared process
    CLOUDFLARED_PID=""
    if [ -f "$QUICK_PID_FILE" ] && ps -p "$(cat $QUICK_PID_FILE)" > /dev/null 2>&1; then
        CLOUDFLARED_PID=$(cat "$QUICK_PID_FILE")
    else
        # Check if cloudflared tunnel is running without PID file
        CLOUDFLARED_PID=$(pgrep -f "cloudflared.*tunnel.*--url" 2>/dev/null | head -1)
    fi

    if [ -n "$CLOUDFLARED_PID" ]; then
        echo "  Status: ${GREEN}RUNNING${NC}"
        echo "  PID: $CLOUDFLARED_PID"

        # Try to get URL from log file
        QUICK_LOG_FILE="$LOG_DIR/quick_tunnel.log"
        TUNNEL_URL=""
        if [ -f "$QUICK_LOG_FILE" ]; then
            TUNNEL_URL=$(grep -o "https://.*\.trycloudflare\.com" "$QUICK_LOG_FILE" 2>/dev/null | tail -1)
        fi

        # Try to get URL from metrics endpoint
        if [ -z "$TUNNEL_URL" ]; then
            TUNNEL_URL=$(curl -s http://127.0.0.1:20241/metrics 2>/dev/null | grep "userHostname=" | grep -o "https://[^\"]*\.trycloudflare\.com" | head -1)
        fi

        if [ -n "$TUNNEL_URL" ]; then
            echo ""
            echo "  ${BLUE}공개 URL:${NC}"
            echo "    $TUNNEL_URL"
            echo ""
            echo "  ${BLUE}MCP 서버 엔드포인트:${NC}"
            echo "    Mail Query:  $TUNNEL_URL/mail-query/"
            echo "    Enrollment:  $TUNNEL_URL/enrollment/"
            echo "    OneNote:     $TUNNEL_URL/onenote/"
            echo ""
            echo "  ${BLUE}OAuth Redirect URIs:${NC}"
            echo "    Enrollment:  $TUNNEL_URL/enrollment/callback"
            echo "    Azure DCR:   $TUNNEL_URL/oauth/azure_callback"
            echo ""
            echo "  ${BLUE}Health Check:${NC}"
            echo "    $TUNNEL_URL/health"
        else
            echo "  Note: 터널 URL 확인 중..."
        fi
    else
        echo "  Status: ${RED}STOPPED${NC}"
    fi

    echo ""
    echo "Cloudflared:"
    if command -v cloudflared &> /dev/null; then
        echo "  Status: ${GREEN}INSTALLED${NC}"
        echo "  Version: $(cloudflared --version 2>&1 | head -1)"
        echo "  Path: $(which cloudflared)"
    elif [ -x "$HOME/.local/bin/cloudflared" ]; then
        echo "  Status: ${GREEN}INSTALLED${NC}"
        echo "  Version: $($HOME/.local/bin/cloudflared --version 2>&1 | head -1)"
        echo "  Path: $HOME/.local/bin/cloudflared"
    else
        echo "  Status: ${RED}NOT INSTALLED${NC}"
    fi

    echo ""

    # Check connectivity
    if check_unified_status; then
        echo "=== Connectivity Test ==="
        echo -n "  Local endpoint (http://localhost:8000/health): "
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
            echo "${GREEN}OK${NC}"
        else
            echo "${RED}FAILED${NC}"
        fi

        # Quick Tunnel URL test if running
        QUICK_PID_FILE="/tmp/quick_tunnel.pid"
        if [ -f "$QUICK_PID_FILE" ] && ps -p "$(cat $QUICK_PID_FILE)" > /dev/null 2>&1; then
            QUICK_LOG_FILE="$LOG_DIR/quick_tunnel.log"
            URL=$(grep -o "https://.*\.trycloudflare\.com" "$QUICK_LOG_FILE" 2>/dev/null | tail -1)
            if [ -n "$URL" ]; then
                echo -n "  Tunnel endpoint ($URL/health): "
                if curl -s -o /dev/null -w "%{http_code}" "$URL/health" | grep -q "200"; then
                    echo "${GREEN}OK${NC}"
                else
                    echo "${YELLOW}PENDING${NC} (터널이 아직 준비 중일 수 있습니다)"
                fi
            fi
        fi
    fi
}

# ==================== MAIN EXECUTION ====================

# Main execution
main() {
    # First, check if cloudflared is installed
    if ! command -v cloudflared &> /dev/null && [ ! -x "$HOME/.local/bin/cloudflared" ]; then
        CLOUDFLARED_BIN=""
    else
        check_cloudflared > /dev/null 2>&1
    fi

    # If no arguments, run interactive menu
    if [ $# -eq 0 ]; then
        interactive_menu
        return
    fi

    case "${1}" in
        install)
            install_cloudflared
            ;;
        menu)
            interactive_menu
            ;;
        status)
            detailed_status
            ;;
        quick)
            # Quick Tunnel - 무료 임시 도메인 (명령줄 버전)
            print_info "Quick Tunnel 시작 중 (무료, 임시 도메인)..."

            # cloudflared 확인
            check_cloudflared

            # Unified 서버 시작
            if ! check_unified_status; then
                print_warning "Unified Server를 먼저 시작합니다..."
                start_unified_server
                if [ $? -ne 0 ]; then
                    print_error "Unified Server 시작 실패"
                    exit 1
                fi
            else
                print_status "Unified Server가 이미 실행 중입니다"
            fi

            echo ""
            print_status "Quick Tunnel을 시작합니다..."
            print_info "아래 URL로 접속할 수 있습니다 (Ctrl+C로 종료)"
            echo ""

            # Quick Tunnel 실행
            $CLOUDFLARED_BIN tunnel --url http://localhost:8000
            ;;
        logs)
            echo "Select log to view:"
            echo "1) Unified server logs"
            echo "2) Quick Tunnel logs"
            echo "3) Both (in split screen with tmux)"
            read -p "Choice (1-3): " choice

            case $choice in
                1)
                    tail -f "$LOG_DIR/unified_server.log"
                    ;;
                2)
                    if [ -f "$LOG_DIR/quick_tunnel.log" ]; then
                        tail -f "$LOG_DIR/quick_tunnel.log"
                    else
                        print_warning "Quick Tunnel이 실행된 적이 없습니다"
                    fi
                    ;;
                3)
                    if command -v tmux &> /dev/null; then
                        tmux new-session \; \
                            send-keys "tail -f $LOG_DIR/unified_server.log" C-m \; \
                            split-window -h \; \
                            send-keys "tail -f $LOG_DIR/quick_tunnel.log" C-m \;
                    else
                        print_error "tmux not installed. Install with: sudo apt install tmux"
                    fi
                    ;;
            esac
            ;;
        help|--help|-h)
            echo "Usage: $0 [command]"
            echo ""
            echo "MailQueryWithMCP Cloudflare Manager"
            echo "Complete solution for cloudflared installation and tunnel management"
            echo ""
            echo "Without arguments: Interactive menu"
            echo ""
            echo "Commands:"
            echo "  install        - Install cloudflared"
            echo "  menu           - Show interactive menu"
            echo "  quick          - Quick Tunnel 시작 (무료, 임시 도메인)"
            echo "  status         - Show detailed service status"
            echo "  logs           - View service logs"
            echo "  help           - Show this help message"
            echo ""
            echo "Features:"
            echo "  • Automatic cloudflared installation"
            echo "  • Unified HTTP server management"
            echo "  • Quick Tunnel for instant public access"
            echo "  • Real-time status monitoring"
            echo "  • Integrated log viewing"
            echo ""
            echo "Examples:"
            echo "  $0              # Interactive menu"
            echo "  $0 install      # Install cloudflared"
            echo "  $0 quick        # 무료 터널로 빠른 시작"
            echo "  $0 status       # 상태 확인"
            exit 0
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            echo "Or run '$0' without arguments for interactive menu"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"