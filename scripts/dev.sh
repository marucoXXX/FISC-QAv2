#!/bin/bash

# FISC-QAv2 Development Environment Script
# Usage: ./scripts/dev.sh [start|stop|status|restart]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Java path for Datastore Emulator
export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_datastore() {
    curl -s http://localhost:8081/ > /dev/null 2>&1
}

check_backend() {
    curl -s http://localhost:8000/docs > /dev/null 2>&1
}

check_frontend() {
    curl -s http://localhost:5173/ > /dev/null 2>&1
}

start_datastore() {
    if check_datastore; then
        log_warn "Datastore Emulator already running"
        return 0
    fi
    log_info "Starting Datastore Emulator..."
    gcloud beta emulators datastore start \
        --project=fisc-qav2-dev \
        --host-port=localhost:8081 \
        --data-dir="$PROJECT_ROOT/.datastore" \
        > /tmp/fisc-qav2-datastore.log 2>&1 &

    # Wait for startup
    for i in {1..30}; do
        if check_datastore; then
            log_info "Datastore Emulator started"
            return 0
        fi
        sleep 1
    done
    log_error "Datastore Emulator failed to start"
    return 1
}

start_backend() {
    if check_backend; then
        log_warn "Backend already running"
        return 0
    fi
    log_info "Starting Backend..."
    cd "$PROJECT_ROOT"
    source backend/.venv/bin/activate
    PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/backend" uvicorn backend.app.main:app --reload --port 8000 \
        > /tmp/fisc-qav2-backend.log 2>&1 &

    # Wait for startup
    for i in {1..30}; do
        if check_backend; then
            log_info "Backend started"
            return 0
        fi
        sleep 1
    done
    log_error "Backend failed to start"
    return 1
}

start_frontend() {
    if check_frontend; then
        log_warn "Frontend already running"
        return 0
    fi
    log_info "Starting Frontend..."
    cd "$PROJECT_ROOT/frontend"
    npm run dev > /tmp/fisc-qav2-frontend.log 2>&1 &

    # Wait for startup
    for i in {1..30}; do
        if check_frontend; then
            log_info "Frontend started"
            return 0
        fi
        sleep 1
    done
    log_error "Frontend failed to start"
    return 1
}

stop_all() {
    log_info "Stopping all services..."
    # Datastore Emulator: graceful shutdown via HTTP API
    curl -s -X POST http://localhost:8081/shutdown 2>/dev/null || true
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    sleep 2
    log_info "All services stopped"
}

status() {
    echo ""
    echo "=== FISC-QAv2 Development Services ==="
    echo ""

    if check_datastore; then
        echo -e "Datastore Emulator : ${GREEN}Running${NC} (http://localhost:8081)"
    else
        echo -e "Datastore Emulator : ${RED}Stopped${NC}"
    fi

    if check_backend; then
        echo -e "Backend API        : ${GREEN}Running${NC} (http://localhost:8000)"
    else
        echo -e "Backend API        : ${RED}Stopped${NC}"
    fi

    if check_frontend; then
        echo -e "Frontend           : ${GREEN}Running${NC} (http://localhost:5173)"
    else
        echo -e "Frontend           : ${RED}Stopped${NC}"
    fi

    echo ""
}

start_all() {
    log_info "Starting all services..."
    start_datastore
    start_backend
    start_frontend
    echo ""
    status
}

case "${1:-}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        start_all
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
