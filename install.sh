#!/bin/bash
set -euo pipefail

# BatchFlow ERP - Ubuntu Server Installer
# Supports Ubuntu 22.04+ (Jammy) and newer

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
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

print_banner() {
    echo ""
    echo "=============================================="
    echo "    BatchFlow ERP - Ubuntu Server Installer"
    echo "    Batch Manufacturing ERP System"
    echo "=============================================="
    echo ""
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This installer must be run as root (use sudo)"
        exit 1
    fi
}

check_ubuntu() {
    if ! grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
        log_warn "This installer is designed for Ubuntu Server."
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
    log_ok "Ubuntu detected"
}

generate_password() {
    openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 20
}

install_system_dependencies() {
    log_info "Updating package lists..."
    apt-get update -qq

    log_info "Installing system dependencies..."
    apt-get install -y -qq \
        postgresql postgresql-contrib \
        python3 python3-pip python3-venv \
        nginx \
        curl \
        openssl \
        git \
        build-essential \
        libpq-dev \
        > /dev/null 2>&1

    # Install Node.js 20 LTS
    if ! command -v node &> /dev/null; then
        log_info "Installing Node.js 20 LTS..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
        apt-get install -y -qq nodejs > /dev/null 2>&1
    fi

    log_ok "System dependencies installed"
}

create_system_user() {
    if ! id "$BATCHFLOW_USER" &>/dev/null; then
        log_info "Creating system user: $BATCHFLOW_USER"
        useradd --system --home "$BATCHFLOW_HOME" --shell /bin/false "$BATCHFLOW_USER"
    fi
    log_ok "System user ready"
}

setup_directories() {
    log_info "Creating directories..."
    mkdir -p "$BATCHFLOW_HOME"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR/uploads"
    mkdir -p "$DATA_DIR/backups"

    chown -R "$BATCHFLOW_USER:$BATCHFLOW_USER" "$LOG_DIR" "$DATA_DIR"
    log_ok "Directories created"
}

setup_database() {
    DB_PASSWORD=$(generate_password)
    log_info "Configuring PostgreSQL..."

    # Create user if not exists, then always set password to match what we write to .db_password
    sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$BATCHFLOW_DB_USER'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE USER $BATCHFLOW_DB_USER WITH PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "ALTER USER $BATCHFLOW_DB_USER WITH PASSWORD '$DB_PASSWORD';"

    # Drop and recreate database to ensure clean state on re-install
    if sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$BATCHFLOW_DB'" | grep -q 1; then
        log_info "Dropping existing database for clean re-install..."
        sudo -u postgres psql -c "DROP DATABASE $BATCHFLOW_DB;"
    fi
    sudo -u postgres psql -c "CREATE DATABASE $BATCHFLOW_DB OWNER $BATCHFLOW_DB_USER;"

    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $BATCHFLOW_DB TO $BATCHFLOW_DB_USER;"

    log_ok "PostgreSQL configured (database: $BATCHFLOW_DB)"
    echo "$DB_PASSWORD" > "$BATCHFLOW_HOME/.db_password"
    chmod 600 "$BATCHFLOW_HOME/.db_password"
}

install_backend() {
    log_info "Installing backend application..."



    # Clean previous install to ensure fresh files and venv
    if [ -d "$BATCHFLOW_HOME/backend" ]; then
        log_info "Removing previous backend installation..."
        rm -rf "$BATCHFLOW_HOME/backend"
    fi

    cp -r "$INSTALL_DIR/backend" "$BATCHFLOW_HOME/backend"

    cd "$BATCHFLOW_HOME/backend"
    python3 -m venv venv
    source venv/bin/activate
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    deactivate

    # Generate secure secret key
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(cat "$BATCHFLOW_HOME/.db_password")

    cat > "$BATCHFLOW_HOME/backend/.env" << EOF
APP_NAME=BatchFlow ERP
DEBUG=false
DATABASE_URL=postgresql://$BATCHFLOW_DB_USER:$DB_PASSWORD@localhost:5432/$BATCHFLOW_DB
SECRET_KEY=$SECRET_KEY
CORS_ORIGINS=http://localhost,http://localhost:80,https://localhost,https://localhost:443
UPLOAD_DIR=$DATA_DIR/uploads
LOG_DIR=$LOG_DIR
EOF

    chmod 600 "$BATCHFLOW_HOME/backend/.env"

    # Initialize database and seed data
    log_info "Initializing database schema..."
    cd "$BATCHFLOW_HOME/backend"
    source venv/bin/activate
    python -c "from app.core.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)"
    python seed_data.py
    deactivate

    chown -R "$BATCHFLOW_USER:$BATCHFLOW_USER" "$BATCHFLOW_HOME/backend"
    log_ok "Backend installed and database initialized"
}

install_frontend() {
    log_info "Building frontend application..."



    # Clean previous install
    if [ -d "$BATCHFLOW_HOME/frontend" ]; then
        log_info "Removing previous frontend installation..."
        rm -rf "$BATCHFLOW_HOME/frontend"
    fi
    rm -rf "$BATCHFLOW_HOME/static"

    cp -r "$INSTALL_DIR/frontend" "$BATCHFLOW_HOME/frontend"

    cd "$BATCHFLOW_HOME/frontend"
    npm install --silent 2>/dev/null
    npm run build 2>/dev/null

    # Move built assets to nginx serving directory
    mkdir -p "$BATCHFLOW_HOME/static"
    cp -r dist/* "$BATCHFLOW_HOME/static/"

    chown -R "$BATCHFLOW_USER:$BATCHFLOW_USER" "$BATCHFLOW_HOME/frontend" "$BATCHFLOW_HOME/static"
    log_ok "Frontend built"
}

configure_systemd() {
    log_info "Creating systemd service..."

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
ExecStart=$BATCHFLOW_HOME/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5
StandardOutput=append:$LOG_DIR/batchflow.log
StandardError=append:$LOG_DIR/batchflow-error.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable batchflow
    systemctl start batchflow

    # Verify the service started and API is responding
    sleep 3
    if ! systemctl is-active --quiet batchflow; then
        log_error "BatchFlow service failed to start. Check logs:"
        log_error "  sudo journalctl -u batchflow -n 30"
        log_error "  cat $LOG_DIR/batchflow-error.log"
        exit 1
    fi
    if ! curl -sf http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        log_warn "API server not responding yet on port 8000. Check: sudo systemctl status batchflow"
    else
        log_ok "BatchFlow service started and API is healthy"
    fi
}

configure_nginx() {
    log_info "Configuring Nginx..."

    cat > /etc/nginx/sites-available/batchflow << 'EOF'
server {
    listen 80;
    server_name _;

    root /opt/batchflow/static;
    index index.html;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }

    # Frontend SPA
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
}
EOF

    ln -sf /etc/nginx/sites-available/batchflow /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    nginx -t && systemctl reload nginx
    log_ok "Nginx configured"
}

setup_ssl() {
    log_info "Generating self-signed SSL certificate..."

    mkdir -p /etc/nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/batchflow.key \
        -out /etc/nginx/ssl/batchflow.crt \
        -subj "/CN=batchflow.local/O=BatchFlow ERP" \
        > /dev/null 2>&1

    cat > /etc/nginx/sites-available/batchflow-ssl << 'EOF'
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
EOF

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

print_summary() {
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo "=============================================="
    echo "    BatchFlow ERP Installation Complete!"
    echo "=============================================="
    echo ""
    echo "  Access URL:    http://$SERVER_IP"
    echo "  API Docs:      http://$SERVER_IP/api/docs"
    echo ""
    echo "  Default Admin Account:"
    echo "    Username: admin"
    echo "    Password: admin123"
    echo ""
    echo "  IMPORTANT: Change the admin password after first login!"
    echo ""
    echo "  Service Management:"
    echo "    sudo systemctl status batchflow"
    echo "    sudo systemctl restart batchflow"
    echo "    sudo journalctl -u batchflow -f"
    echo ""
    echo "  Logs: $LOG_DIR/"
    echo "  Config: $BATCHFLOW_HOME/backend/.env"
    echo "  Database: $BATCHFLOW_DB (PostgreSQL)"
    echo ""
    echo "=============================================="
}

# --- Main Installation Flow ---
main() {
    print_banner
    check_root
    check_ubuntu

    log_info "Starting BatchFlow ERP installation..."
    echo ""

    install_system_dependencies
    create_system_user
    setup_directories
    setup_database
    install_backend
    install_frontend
    configure_systemd
    configure_nginx
    setup_ssl
    setup_logrotate

    print_summary
}

main "$@"
