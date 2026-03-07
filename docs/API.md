# BatchFlow ERP - API Reference

Base URL: `/api/v1`

Interactive documentation: `/api/docs` (Swagger UI)

## Authentication

### POST /api/v1/auth/login
Login with username and password. Returns JWT access and refresh tokens.

```json
Request: { "username": "admin", "password": "admin123" }
Response: { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
```

### POST /api/v1/auth/refresh
Refresh an expired access token.

### GET /api/v1/auth/me
Get current authenticated user info.

All other endpoints require `Authorization: Bearer <access_token>` header.

---

## Users & Permissions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /users | List users |
| POST | /users | Create user |
| GET | /users/{id} | Get user |
| PUT | /users/{id} | Update user |
| GET | /users/groups/ | List groups |
| POST | /users/groups/ | Create group |
| PUT | /users/groups/{id}/permissions | Set group permissions |
| GET | /users/groups/{id}/permissions | Get group permissions |
| POST | /users/groups/{gid}/users/{uid} | Add user to group |
| DELETE | /users/groups/{gid}/users/{uid} | Remove user from group |

---

## GL Groups

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /gl-groups | List GL groups |
| POST | /gl-groups | Create GL group with account mappings |
| GET | /gl-groups/{id} | Get GL group |
| PUT | /gl-groups/{id} | Update GL group |
| PUT | /gl-groups/{id}/mappings | Set account mappings |

---

## Inventory

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /inventory/items | List items (filter: item_type, is_active) |
| POST | /inventory/items | Create item |
| GET | /inventory/items/{id} | Get item |
| PUT | /inventory/items/{id} | Update item |
| GET | /inventory/warehouses | List warehouses |
| POST | /inventory/warehouses | Create warehouse |
| GET | /inventory/locations | List locations |
| POST | /inventory/locations | Create location |
| GET | /inventory/lots | List lots (filter: item_id, status) |
| GET | /inventory/lots/{id} | Get lot |
| GET | /inventory/transactions | List transactions |
| POST | /inventory/adjustments | Create inventory adjustment |
| POST | /inventory/transfers | Transfer inventory between locations |
| GET | /inventory/uoms | List units of measure |
| POST | /inventory/uoms | Create UOM |
| GET | /inventory/valuation | Get FIFO valuation |

---

## Sales

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /sales/customers | List customers |
| POST | /sales/customers | Create customer |
| GET | /sales/customers/{id} | Get customer |
| PUT | /sales/customers/{id} | Update customer |
| GET | /sales/orders | List sales orders |
| POST | /sales/orders | Create sales order with lines |
| GET | /sales/orders/{id} | Get sales order |
| PUT | /sales/orders/{id} | Update sales order |
| POST | /sales/shipments | Create shipment |
| POST | /sales/orders/{id}/invoice | Generate invoice from order |

---

## Purchasing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /purchasing/vendors | List vendors |
| POST | /purchasing/vendors | Create vendor |
| GET | /purchasing/vendors/{id} | Get vendor |
| PUT | /purchasing/vendors/{id} | Update vendor |
| GET | /purchasing/orders | List purchase orders |
| POST | /purchasing/orders | Create purchase order |
| GET | /purchasing/orders/{id} | Get purchase order |
| PUT | /purchasing/orders/{id} | Update purchase order |
| POST | /purchasing/receipts | Receive against purchase order |

---

## Manufacturing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /manufacturing/formulas | List formulas |
| POST | /manufacturing/formulas | Create formula with initial version |
| GET | /manufacturing/formulas/{id} | Get formula |
| POST | /manufacturing/formulas/{id}/versions | Add formula version |
| GET | /manufacturing/production-orders | List production orders |
| POST | /manufacturing/production-orders | Create production order |
| GET | /manufacturing/production-orders/{id} | Get production order |
| PUT | /manufacturing/production-orders/{id} | Update production order |
| POST | /manufacturing/production-orders/{id}/consume | Record material consumption |
| POST | /manufacturing/production-orders/{id}/output | Record production output |

---

## Quality Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /quality/specifications | List QC specifications |
| POST | /quality/specifications | Create QC specification with tests |
| GET | /quality/specifications/{id} | Get specification |
| GET | /quality/results | List QC results |
| POST | /quality/results | Record single QC result |
| POST | /quality/results/batch | Record batch QC results |
| POST | /quality/lot-disposition | Set lot disposition (release/hold/reject) |

---

## Traceability

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /traceability/lot/{id}/genealogy | Get full lot genealogy tree |
| GET | /traceability/lot/{id}/recall-impact | Analyze recall impact |

---

## Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /reports/inventory/by-lot | Inventory by lot |
| GET | /reports/inventory/fifo-valuation | FIFO valuation report |
| GET | /reports/inventory/by-gl-group | Inventory by GL group |
| GET | /reports/manufacturing/batch-history | Batch production history |
| GET | /reports/quality/results-by-lot | QC results by lot |
| GET | /reports/sales/by-customer | Sales by customer |
| GET | /reports/sales/by-gl-group | Sales by GL group |
| GET | /reports/purchasing/by-vendor | Purchases by vendor |
| GET | /reports/export/inventory-csv | Export inventory as CSV |
