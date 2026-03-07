# BatchFlow ERP

A modern, web-based Enterprise Resource Planning system for batch-based manufacturing companies (ink, chemical, coatings, food, nutraceutical, and pharmaceutical manufacturers).

## Features

- **User Management** - Users, groups, granular permissions (create/read/update/delete/approve/export per module)
- **GL Groups** - Accounting classification with QuickBooks account mapping
- **Inventory Management** - FIFO costing, lot tracking, multiple warehouses, bin locations, UOM conversions
- **Sales Orders** - Customer management, order workflow, shipments, invoicing
- **Purchase Orders** - Vendor management, PO workflow, receiving with lot creation
- **Batch Manufacturing** - Formula/BOM management, versioning, batch scaling, production orders
- **Quality Control** - QC specifications, test definitions, lot-level results, disposition (release/hold/reject)
- **Lot Traceability** - Full genealogy (backward to raw materials, forward to customers), recall analysis
- **Reporting** - Inventory valuation, batch history, QC reports, sales/purchasing analysis, CSV export
- **QuickBooks Desktop Sync** - qbXML-based sync for customers, vendors, invoices, POs

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | React 18 / TypeScript / Tailwind CSS |
| Database | PostgreSQL 15+ |
| API | REST (OpenAPI/Swagger) |
| Auth | JWT (access + refresh tokens) |
| Web Server | Nginx |
| Charts | Recharts |

## Quick Start

### Ubuntu Server Installation

```bash
sudo ./install.sh
```

This installs all dependencies, configures PostgreSQL, builds the application, and starts services. Access at `http://<server-ip>`.

### Development Setup

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Set DATABASE_URL in .env
python seed_data.py
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Default Login
- Username: `admin`
- Password: `admin123`

## Project Structure

```
├── install.sh                  # Ubuntu automated installer
├── backend/
│   ├── app/
│   │   ├── api/routes/         # API endpoints
│   │   ├── core/               # Config, database, security
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   └── migrations/         # Alembic migrations
│   ├── tests/                  # API tests
│   ├── seed_data.py            # Initial data seeder
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API client
│   │   ├── store/              # State management
│   │   ├── types/              # TypeScript types
│   │   └── utils/              # Helpers
│   └── package.json
├── quickbooks-sync/            # QB Desktop sync module
├── scripts/                    # Upgrade, backup scripts
├── config/                     # Configuration templates
└── docs/                       # Documentation
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [API Reference](docs/API.md)
- [Database Schema](docs/DATABASE.md)
- [Example Workflows](docs/WORKFLOWS.md)

## API Endpoints

Interactive API documentation available at `/api/docs` when the server is running.

Key endpoint groups:
- `/api/v1/auth/` - Authentication
- `/api/v1/users/` - Users & permissions
- `/api/v1/gl-groups/` - GL group accounting
- `/api/v1/inventory/` - Items, lots, warehouses, transactions
- `/api/v1/sales/` - Customers, orders, shipments, invoices
- `/api/v1/purchasing/` - Vendors, POs, receiving
- `/api/v1/manufacturing/` - Formulas, production orders
- `/api/v1/quality/` - QC specs, results, lot disposition
- `/api/v1/traceability/` - Lot genealogy, recall analysis
- `/api/v1/reports/` - All reports and exports

## License

Proprietary - All rights reserved.
