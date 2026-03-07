# BatchFlow ERP - System Architecture

## Overview

BatchFlow ERP is a modern, web-based Enterprise Resource Planning system designed for batch-based manufacturing companies (ink, chemical, coatings, food, nutraceutical, and pharmaceutical manufacturers).

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+ / FastAPI |
| **Frontend** | React 18 + TypeScript |
| **Database** | PostgreSQL 15+ |
| **API** | REST (OpenAPI/Swagger) |
| **Authentication** | JWT with refresh tokens |
| **Web Server** | Nginx (reverse proxy) |
| **Process Manager** | systemd |
| **QB Integration** | qbXML via background sync service |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    Browser (React UI)                │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS
┌──────────────────────┴──────────────────────────────┐
│                  Nginx Reverse Proxy                 │
│                  (SSL Termination)                   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│              FastAPI Application Server              │
│  ┌─────────┬──────────┬──────────┬───────────────┐  │
│  │  Auth   │ Inventory│  Sales   │ Manufacturing │  │
│  │ Module  │  Module  │  Module  │    Module     │  │
│  ├─────────┼──────────┼──────────┼───────────────┤  │
│  │Purchase │    QC    │Reporting │   GL/Acctg    │  │
│  │ Module  │  Module  │  Module  │    Module     │  │
│  └─────────┴──────────┴──────────┴───────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
┌─────────┴──────────┐  ┌──────────┴──────────┐
│    PostgreSQL DB   │  │  QuickBooks Desktop  │
│  (Data + Schema)   │  │   Sync Service       │
└────────────────────┘  └─────────────────────┘
```

## Module Structure

### Core Modules
1. **Authentication & Authorization** - JWT auth, user groups, granular permissions
2. **GL Groups** - Accounting classification and QuickBooks mapping
3. **Inventory Management** - FIFO costing, lot tracking, warehouses, bins
4. **Sales Order Management** - Customers, orders, shipments, invoices
5. **Purchase Order Management** - Vendors, POs, receiving, vendor invoices
6. **Batch Manufacturing** - Formulas, production orders, batch processing
7. **Quality Control** - Specifications, testing, lot release/hold/reject
8. **Lot Traceability** - Full genealogy, forward/backward trace, recall reports
9. **Reporting** - Configurable reports, CSV/Excel export, dashboards
10. **QuickBooks Sync** - Background sync with QB Desktop via qbXML

## API Design

- All endpoints follow RESTful conventions
- Versioned API: `/api/v1/`
- OpenAPI/Swagger documentation at `/api/docs`
- Consistent error response format
- Pagination on list endpoints
- Filtering and sorting support

## Security

- Passwords hashed with bcrypt
- JWT access tokens (15-minute expiry)
- JWT refresh tokens (7-day expiry)
- Role-based access control (RBAC)
- CORS configuration
- SQL injection prevention via ORM
- XSS prevention via React
- CSRF protection

## Database

- PostgreSQL with Alembic migrations
- Full referential integrity
- Indexed for common query patterns
- Audit trails on critical tables
- FIFO cost layer management
