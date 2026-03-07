#!/bin/bash
set -euo pipefail

# BatchFlow ERP - Install & Update Script
# Automatically detects fresh install vs update and acts accordingly.
#
# Usage:
#   Fresh install:  sudo ./setup.sh
#   Update:         sudo ./setup.sh
#   Update (skip frontend build):  sudo ./setup.sh --backend-only
#   Update (skip backend):         sudo ./setup.sh --frontend-only
#   Force full reinstall:          sudo ./setup.sh --force-install
#   Run DB migrations only:        sudo ./setup.sh --migrate-only

INSTALL_DIR=$(cd "$(dirname "$0")" && pwd)
BATCHFLOW_HOME="/opt/batchflow"
BATCHFLOW_USER="batchflow"
BATCHFLOW_DB="batchflow_erp"
BATCHFLOW_DB_USER="batchflow"
LOG_DIR="/var/log/batchflow"
DATA_DIR="/var/lib/batchflow"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[  OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }
log_step()  { echo -e "\n${CYAN}── $1 ──${NC}"; }

# ───────────────────────────────────────────────
# Argument parsing
# ───────────────────────────────────────────────
MODE=""               # auto-detected: "install" or "update"
FORCE_INSTALL=false
BACKEND_ONLY=false
FRONTEND_ONLY=false
MIGRATE_ONLY=false
SKIP_DEPS=false
SKIP_DB_BACKUP=false

for arg in "$@"; do
    case $arg in
        --force-install)  FORCE_INSTALL=true ;;
        --backend-only)   BACKEND_ONLY=true ;;
        --frontend-only)  FRONTEND_ONLY=true ;;
        --migrate-only)   MIGRATE_ONLY=true ;;
        --skip-deps)      SKIP_DEPS=true ;;
        --skip-backup)    SKIP_DB_BACKUP=true ;;
        --help|-h)
            echo "BatchFlow ERP Setup - Install & Updater"
            echo ""
            echo "Usage: sudo $0 [options]"
            echo ""
            echo "Options:"
            echo "  --force-install   Force a full install even if already installed"
            echo "  --backend-only    Only update backend (skip frontend build)"
            echo "  --frontend-only   Only update frontend (skip backend)"
            echo "  --migrate-only    Only run database migrations"
            echo "  --skip-deps       Skip system dependency installation (faster updates)"
            echo "  --skip-backup     Skip database backup before update"
            echo "  -h, --help        Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $arg (use --help)"
            exit 1
            ;;
    esac
done

# ───────────────────────────────────────────────
# Pre-flight checks
# ───────────────────────────────────────────────
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

detect_mode() {
    if [[ "$FORCE_INSTALL" == true ]]; then
        MODE="install"
    elif [[ -f "$BATCHFLOW_HOME/backend/.env" ]] && systemctl list-unit-files | grep -q batchflow; then
        MODE="update"
    else
        MODE="install"
    fi
}

generate_password() {
    openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 20
}

get_installed_version() {
    if [[ -f "$BATCHFLOW_HOME/.version" ]]; then
        cat "$BATCHFLOW_HOME/.version"
    else
        echo "unknown"
    fi
}

get_source_version() {
    # Try to get version from the source config, fallback to git
    local ver
    ver=$(python3 -c "
import sys
sys.path.insert(0, '$INSTALL_DIR/backend')
try:
    from app.core.config import Settings
    print(Settings().APP_VERSION)
except:
    print('unknown')
" 2>/dev/null || echo "unknown")

    if [[ "$ver" == "unknown" ]] && command -v git &>/dev/null && [[ -d "$INSTALL_DIR/.git" ]]; then
        ver=$(git -C "$INSTALL_DIR" describe --tags --always 2>/dev/null || git -C "$INSTALL_DIR" rev-parse --short HEAD 2>/dev/null || echo "dev")
    fi
    echo "$ver"
}

# ───────────────────────────────────────────────
# Install-only functions (fresh install)
# ───────────────────────────────────────────────
install_system_dependencies() {
    if [[ "$SKIP_DEPS" == true ]]; then
        log_info "Skipping system dependencies (--skip-deps)"
        return
    fi

    log_step "Installing system dependencies"
    apt-get update -qq

    apt-get install -y -qq \
        postgresql postgresql-contrib \
        python3 python3-pip python3-venv \
        nginx curl openssl git \
        build-essential libpq-dev \
        > /dev/null 2>&1

    # Node.js 20 LTS
    if ! command -v node &>/dev/null; then
        log_info "Installing Node.js 20 LTS..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
        apt-get install -y -qq nodejs > /dev/null 2>&1
    fi

    log_ok "System dependencies installed"
}

create_system_user() {
    if ! id "$BATCHFLOW_USER" &>/dev/null; then
        useradd --system --home "$BATCHFLOW_HOME" --shell /bin/false "$BATCHFLOW_USER"
    fi
}

setup_directories() {
    mkdir -p "$BATCHFLOW_HOME"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR/uploads/pdfs"
    mkdir -p "$DATA_DIR/backups"
    chown -R "$BATCHFLOW_USER:$BATCHFLOW_USER" "$LOG_DIR" "$DATA_DIR"
}

setup_database_fresh() {
    log_step "Setting up PostgreSQL database"
    DB_PASSWORD=$(generate_password)

    sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$BATCHFLOW_DB_USER'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE USER $BATCHFLOW_DB_USER WITH PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "ALTER USER $BATCHFLOW_DB_USER WITH PASSWORD '$DB_PASSWORD';"

    if sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$BATCHFLOW_DB'" | grep -q 1; then
        log_info "Dropping existing database for clean install..."
        sudo -u postgres psql -c "DROP DATABASE $BATCHFLOW_DB;"
    fi
    sudo -u postgres psql -c "CREATE DATABASE $BATCHFLOW_DB OWNER $BATCHFLOW_DB_USER;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $BATCHFLOW_DB TO $BATCHFLOW_DB_USER;"

    echo "$DB_PASSWORD" > "$BATCHFLOW_HOME/.db_password"
    chmod 600 "$BATCHFLOW_HOME/.db_password"
    log_ok "PostgreSQL database created"
}

configure_systemd() {
    log_step "Configuring systemd service"

    cat > /etc/systemd/system/batchflow.service << EOF
[Unit]
Description=BatchFlow ERP API Server
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$BATCHFLOW_USER
Group=$BATCHFLOW_USER
WorkingDirectory=$BATCHFLOW_HOME/backend
Environment=PATH=$BATCHFLOW_HOME/backend/venv/bin:/usr/bin
ExecStart=$BATCHFLOW_HOME/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=append:$LOG_DIR/batchflow.log
StandardError=append:$LOG_DIR/batchflow-error.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable batchflow
    log_ok "Systemd service configured"
}

configure_nginx() {
    log_step "Configuring Nginx"

    cat > /etc/nginx/sites-available/batchflow << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    root /opt/batchflow/static;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        client_max_body_size 50M;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
}
NGINXEOF

    ln -sf /etc/nginx/sites-available/batchflow /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    nginx -t && systemctl reload nginx
    log_ok "Nginx configured"
}

setup_ssl() {
    log_step "Generating self-signed SSL certificate"

    mkdir -p /etc/nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/batchflow.key \
        -out /etc/nginx/ssl/batchflow.crt \
        -subj "/CN=batchflow.local/O=BatchFlow ERP" \
        > /dev/null 2>&1

    cat > /etc/nginx/sites-available/batchflow-ssl << 'SSLEOF'
server {
    listen 443 ssl;
    server_name _;

    ssl_certificate /etc/nginx/ssl/batchflow.crt;
    ssl_certificate_key /etc/nginx/ssl/batchflow.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    root /opt/batchflow/static;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}

server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
SSLEOF

    log_ok "SSL certificate generated (self-signed)"
}

setup_logrotate() {
    cat > /etc/logrotate.d/batchflow << EOF
$LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
    log_ok "Log rotation configured"
}

# ───────────────────────────────────────────────
# Shared functions (used by both install & update)
# ───────────────────────────────────────────────
deploy_backend() {
    log_step "Deploying backend"

    local IS_FRESH=false
    if [[ ! -d "$BATCHFLOW_HOME/backend/venv" ]]; then
        IS_FRESH=true
    fi

    # Preserve .env during update
    local ENV_BACKUP=""
    if [[ -f "$BATCHFLOW_HOME/backend/.env" ]]; then
        ENV_BACKUP=$(cat "$BATCHFLOW_HOME/backend/.env")
    fi

    # Sync source files (preserve venv and .env)
    if [[ "$IS_FRESH" == true ]]; then
        rm -rf "$BATCHFLOW_HOME/backend"
        cp -r "$INSTALL_DIR/backend" "$BATCHFLOW_HOME/backend"
    else
        # Update only source code, not venv or .env
        log_info "Syncing backend source files..."
        rsync -a --delete \
            --exclude='venv/' \
            --exclude='.env' \
            --exclude='__pycache__/' \
            --exclude='*.pyc' \
            "$INSTALL_DIR/backend/" "$BATCHFLOW_HOME/backend/"
    fi

    # Restore .env if we had one
    if [[ -n "$ENV_BACKUP" ]]; then
        echo "$ENV_BACKUP" > "$BATCHFLOW_HOME/backend/.env"
        chmod 600 "$BATCHFLOW_HOME/backend/.env"
    fi

    # Setup venv if fresh
    cd "$BATCHFLOW_HOME/backend"
    if [[ "$IS_FRESH" == true ]]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Install/update dependencies
    log_info "Installing Python dependencies..."
    source venv/bin/activate
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    deactivate

    # Generate .env on fresh install
    if [[ -z "$ENV_BACKUP" ]]; then
        SECRET_KEY=$(openssl rand -hex 32)
        DB_PASSWORD=$(cat "$BATCHFLOW_HOME/.db_password")
        SERVER_IP=$(hostname -I | awk '{print $1}')

        cat > "$BATCHFLOW_HOME/backend/.env" << ENVEOF
APP_NAME=BatchFlow ERP
DEBUG=false
DATABASE_URL=postgresql://$BATCHFLOW_DB_USER:$DB_PASSWORD@localhost:5432/$BATCHFLOW_DB
SECRET_KEY=$SECRET_KEY
CORS_ORIGINS=http://localhost,http://localhost:80,https://localhost,https://localhost:443,http://$SERVER_IP,http://$SERVER_IP:80
UPLOAD_DIR=$DATA_DIR/uploads
LOG_DIR=$LOG_DIR
ENVEOF
        chmod 600 "$BATCHFLOW_HOME/backend/.env"
    fi

    chown -R "$BATCHFLOW_USER:$BATCHFLOW_USER" "$BATCHFLOW_HOME/backend"
    log_ok "Backend deployed"
}

run_migrations() {
    log_step "Running database migrations"
    cd "$BATCHFLOW_HOME/backend"
    source venv/bin/activate

    if [[ "$MODE" == "install" ]]; then
        # Fresh install: create all tables directly
        log_info "Creating database schema..."
        python -c "from app.core.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)"

        # Mark alembic as current so future migrations work
        if [[ -f alembic.ini ]]; then
            alembic stamp head 2>/dev/null || true
        fi

        # Seed data
        if [[ -f seed_data.py ]]; then
            log_info "Loading seed data..."
            python seed_data.py
        fi
    else
        # Update: run alembic migrations
        if [[ -f alembic.ini ]]; then
            log_info "Running Alembic migrations..."
            alembic upgrade head 2>&1 || {
                log_warn "Alembic migration failed. Falling back to create_all..."
                python -c "from app.core.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)"
                alembic stamp head 2>/dev/null || true
            }
        else
            # No alembic - just ensure tables exist
            python -c "from app.core.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)"
        fi
    fi

    # Verify app loads
    if ! python -c "from app.main import app; print('App verified')" 2>&1; then
        log_error "Application failed to load after migration"
        deactivate
        exit 1
    fi

    deactivate
    log_ok "Database migrations complete"
}

deploy_frontend() {
    log_step "Deploying frontend"

    local IS_FRESH=false
    if [[ ! -d "$BATCHFLOW_HOME/frontend/node_modules" ]]; then
        IS_FRESH=true
    fi

    if [[ "$IS_FRESH" == true ]]; then
        rm -rf "$BATCHFLOW_HOME/frontend"
        cp -r "$INSTALL_DIR/frontend" "$BATCHFLOW_HOME/frontend"
    else
        # Sync source files, preserve node_modules
        rsync -a --delete \
            --exclude='node_modules/' \
            --exclude='dist/' \
            "$INSTALL_DIR/frontend/" "$BATCHFLOW_HOME/frontend/"
    fi

    cd "$BATCHFLOW_HOME/frontend"

    log_info "Installing npm packages..."
    npm install --silent 2>/dev/null

    log_info "Building frontend..."
    npm run build 2>/dev/null

    mkdir -p "$BATCHFLOW_HOME/static"
    cp -r dist/* "$BATCHFLOW_HOME/static/"

    chown -R "$BATCHFLOW_USER:$BATCHFLOW_USER" "$BATCHFLOW_HOME/frontend" "$BATCHFLOW_HOME/static"
    log_ok "Frontend built and deployed"
}

backup_database() {
    if [[ "$SKIP_DB_BACKUP" == true ]]; then
        log_info "Skipping database backup (--skip-backup)"
        return
    fi

    mkdir -p "$DATA_DIR/backups"
    local BACKUP_FILE="$DATA_DIR/backups/batchflow_pre_update_$(date +%Y%m%d_%H%M%S).sql.gz"
    log_info "Backing up database..."

    if sudo -u postgres pg_dump "$BATCHFLOW_DB" 2>/dev/null | gzip > "$BACKUP_FILE"; then
        chmod 640 "$BACKUP_FILE"
        log_ok "Database backed up to $BACKUP_FILE"
    else
        log_warn "Database backup failed (this is OK for fresh installs)"
    fi
}

start_services() {
    log_step "Starting services"

    # Clear old logs
    > "$LOG_DIR/batchflow.log" 2>/dev/null || true
    > "$LOG_DIR/batchflow-error.log" 2>/dev/null || true

    systemctl daemon-reload
    systemctl restart batchflow

    # Wait for API to become healthy
    log_info "Waiting for API to start..."
    local retries=10
    while (( retries > 0 )); do
        if curl -sf http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
            log_ok "API is healthy"
            break
        fi
        retries=$((retries - 1))
        sleep 2
    done

    if (( retries == 0 )); then
        log_warn "API not responding yet. Check: sudo journalctl -u batchflow -n 30"
    fi

    systemctl reload nginx 2>/dev/null || true
    log_ok "Services started"
}

save_version() {
    local VERSION
    VERSION=$(get_source_version)
    echo "$VERSION" > "$BATCHFLOW_HOME/.version"
    echo "$(date -Iseconds)" > "$BATCHFLOW_HOME/.last_updated"
}

# ───────────────────────────────────────────────
# Main flows
# ───────────────────────────────────────────────
do_fresh_install() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     BatchFlow ERP - Fresh Installation       ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
    echo ""

    install_system_dependencies
    create_system_user
    setup_directories
    setup_database_fresh
    deploy_backend
    run_migrations
    deploy_frontend
    configure_systemd
    configure_nginx
    setup_ssl
    setup_logrotate
    start_services
    save_version

    local SERVER_IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Installation Complete!                    ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Access URL:    http://$SERVER_IP"
    echo "  API Docs:      http://$SERVER_IP/api/docs"
    echo ""
    echo "  Default Login:"
    echo "    Username: admin"
    echo "    Password: admin123"
    echo ""
    echo "  IMPORTANT: Change the admin password after first login!"
    echo ""
    echo "  Commands:"
    echo "    sudo systemctl status batchflow     # Check status"
    echo "    sudo systemctl restart batchflow     # Restart API"
    echo "    sudo journalctl -u batchflow -f      # Follow logs"
    echo "    sudo $0                              # Update later"
    echo ""
}

do_update() {
    local CUR_VER NEW_VER
    CUR_VER=$(get_installed_version)
    NEW_VER=$(get_source_version)

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     BatchFlow ERP - Update                   ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Current version: $CUR_VER"
    echo "  New version:     $NEW_VER"
    echo ""

    # Pre-update backup
    backup_database

    # Stop service for clean update
    log_step "Stopping BatchFlow service"
    systemctl stop batchflow 2>/dev/null || true
    log_ok "Service stopped"

    # Update components based on flags
    if [[ "$FRONTEND_ONLY" == true ]]; then
        deploy_frontend
    elif [[ "$BACKEND_ONLY" == true ]]; then
        deploy_backend
        run_migrations
    else
        deploy_backend
        run_migrations
        deploy_frontend
    fi

    # Restart
    start_services
    save_version

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Update Complete!                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Updated: $CUR_VER -> $NEW_VER"
    echo "  Database backup saved before update."
    echo ""
}

do_migrate_only() {
    echo ""
    echo -e "${CYAN}── Running database migrations only ──${NC}"
    echo ""

    systemctl stop batchflow 2>/dev/null || true
    backup_database
    run_migrations
    systemctl start batchflow

    log_ok "Migrations applied and service restarted"
}

# ───────────────────────────────────────────────
# Entry point
# ───────────────────────────────────────────────
main() {
    check_root
    detect_mode

    if [[ "$MIGRATE_ONLY" == true ]]; then
        do_migrate_only
    elif [[ "$MODE" == "install" ]]; then
        do_fresh_install
    else
        do_update
    fi
}

main "$@"
