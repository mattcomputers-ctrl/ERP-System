# BatchFlow ERP - Deployment Guide

## Prerequisites

- Ubuntu Server 22.04 LTS or newer
- Minimum 2 GB RAM, 20 GB disk space
- Root or sudo access
- Internet connection (for package installation)

## Quick Start

```bash
git clone <repository-url> /tmp/batchflow
cd /tmp/batchflow
sudo ./install.sh
```

The installer will:
1. Install PostgreSQL, Python 3, Node.js 20, Nginx
2. Create system user and directories
3. Configure PostgreSQL database
4. Install Python dependencies in a virtualenv
5. Build React frontend
6. Configure systemd service
7. Set up Nginx reverse proxy
8. Generate self-signed SSL certificate
9. Seed database with initial data

## Post-Installation

### Access the System
- HTTP: `http://<server-ip>`
- HTTPS: `https://<server-ip>` (self-signed cert)
- API Docs: `http://<server-ip>/api/docs`

### Default Credentials
- Username: `admin`
- Password: `admin123`

**Change the admin password immediately after first login.**

### Service Management

```bash
# Check status
sudo systemctl status batchflow

# Restart
sudo systemctl restart batchflow

# View logs
sudo journalctl -u batchflow -f
tail -f /var/log/batchflow/batchflow.log
```

### Configuration

Edit `/opt/batchflow/backend/.env` to customize settings, then restart:

```bash
sudo systemctl restart batchflow
```

### SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Database Backup

Manual backup:
```bash
sudo -u postgres pg_dump batchflow_erp > backup.sql
```

Automated (add to crontab):
```bash
sudo crontab -e
# Add: 0 2 * * * /opt/batchflow/scripts/backup.sh
```

### Upgrading

```bash
cd /path/to/new-version
sudo ./scripts/upgrade.sh
```

## Directory Structure

```
/opt/batchflow/           # Application home
  backend/                # Python/FastAPI backend
  frontend/               # React source
  static/                 # Built frontend assets
/var/log/batchflow/       # Application logs
/var/lib/batchflow/       # Data files
  uploads/                # Uploaded files
  backups/                # Database backups
```

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u batchflow --no-pager -n 50
```

### Database connection issues
```bash
sudo -u postgres psql -c "\\l"  # List databases
sudo systemctl status postgresql
```

### Nginx errors
```bash
sudo nginx -t           # Test configuration
sudo tail -f /var/log/nginx/error.log
```
