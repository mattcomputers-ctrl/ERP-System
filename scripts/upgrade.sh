#!/bin/bash
set -euo pipefail

# BatchFlow ERP - Upgrade Script

BATCHFLOW_HOME="/opt/batchflow"
BATCHFLOW_USER="batchflow"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ $EUID -ne 0 ]]; then
    log_error "Must be run as root"
    exit 1
fi

INSTALL_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "=============================================="
echo "    BatchFlow ERP - Upgrade"
echo "=============================================="

# Backup database
log_info "Creating database backup..."
BACKUP_FILE="/var/lib/batchflow/backups/batchflow_$(date +%Y%m%d_%H%M%S).sql"
sudo -u postgres pg_dump batchflow_erp > "$BACKUP_FILE"
log_ok "Database backed up to $BACKUP_FILE"

# Stop services
log_info "Stopping services..."
systemctl stop batchflow

# Update backend
log_info "Updating backend..."
cp -r "$INSTALL_DIR/backend/"* "$BATCHFLOW_HOME/backend/"
cd "$BATCHFLOW_HOME/backend"
source venv/bin/activate
pip install --quiet -r requirements.txt
deactivate

# Update frontend
log_info "Building frontend..."
cp -r "$INSTALL_DIR/frontend/"* "$BATCHFLOW_HOME/frontend/"
cd "$BATCHFLOW_HOME/frontend"
npm install --silent 2>/dev/null
npm run build 2>/dev/null
cp -r dist/* "$BATCHFLOW_HOME/static/"

# Fix permissions
chown -R "$BATCHFLOW_USER:$BATCHFLOW_USER" "$BATCHFLOW_HOME"

# Restart services
log_info "Restarting services..."
systemctl start batchflow
systemctl reload nginx

log_ok "Upgrade complete!"
echo ""
echo "If you encounter issues, restore the database backup:"
echo "  sudo -u postgres psql batchflow_erp < $BACKUP_FILE"
