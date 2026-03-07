#!/bin/bash
set -euo pipefail

# BatchFlow ERP - Database Backup Script
# Run via cron: 0 2 * * * /opt/batchflow/scripts/backup.sh

BACKUP_DIR="/var/lib/batchflow/backups"
DB_NAME="batchflow_erp"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

sudo -u postgres pg_dump "$DB_NAME" | gzip > "$BACKUP_FILE"
chmod 640 "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE"

# Clean old backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "Old backups cleaned (retention: ${RETENTION_DAYS} days)"
