# BatchFlow ERP - Database Schema

## Entity Relationship Overview

```
Users ──┬── UserGroupAssociations ──── UserGroups ──── GroupPermissions
        │
GLGroups ──── GLAccountMappings
   │
Items ──┬── Lots ──┬── FIFOCostLayers
   │    │          ├── InventoryTransactions
   │    │          ├── QCResults
   │    │          ├── ProductionConsumptions
   │    │          ├── ProductionOutputs
   │    │          └── ShipmentLines
   │    │
   │    ├── FormulaIngredients
   │    └── SalesOrderLines / PurchaseOrderLines
   │
Warehouses ──── Locations
   │
Formulas ──── FormulaVersions ──── FormulaIngredients
   │
ProductionOrders ──┬── ProductionConsumptions
                   └── ProductionOutputs
   │
QCSpecifications ──── QCTests ──── QCResults
   │
Customers ──── SalesOrders ──┬── SalesOrderLines
                             ├── Shipments ──── ShipmentLines
                             └── Invoices ──── InvoiceLines
   │
Vendors ──── PurchaseOrders ──┬── PurchaseOrderLines
                              └── Receipts ──── ReceiptLines
```

## Key Tables

### Users & Auth
| Table | Purpose |
|-------|---------|
| users | User accounts with auth credentials |
| user_groups | Named permission groups |
| user_group_associations | Many-to-many user/group link |
| group_permissions | Module+action permission grants |

### Accounting
| Table | Purpose |
|-------|---------|
| gl_groups | Accounting classification categories |
| gl_account_mappings | Map GL groups to account numbers |

### Inventory
| Table | Purpose |
|-------|---------|
| items | Master item/product records |
| lots | Individual lot instances with quantities |
| fifo_cost_layers | FIFO costing layers per item/lot |
| inventory_transactions | All inventory movements (audit trail) |
| warehouses | Physical warehouse locations |
| locations | Bins/locations within warehouses |
| units_of_measure | UOM definitions |
| uom_conversions | UOM conversion factors |

### Sales
| Table | Purpose |
|-------|---------|
| customers | Customer master records |
| sales_orders | Sales order headers |
| sales_order_lines | Sales order line items |
| shipments | Shipment records |
| shipment_lines | Shipped lot/qty details |
| invoices | Customer invoices |
| invoice_lines | Invoice line items with GL group ref |

### Purchasing
| Table | Purpose |
|-------|---------|
| vendors | Vendor master records |
| purchase_orders | PO headers |
| purchase_order_lines | PO line items |
| receipts | Receipt records |
| receipt_lines | Received lot/qty details |

### Manufacturing
| Table | Purpose |
|-------|---------|
| formulas | Formula/BOM master |
| formula_versions | Versioned formula definitions |
| formula_ingredients | Ingredients per version |
| production_orders | Batch production orders |
| production_consumptions | Raw material consumption records |
| production_outputs | Finished goods output records |

### Quality
| Table | Purpose |
|-------|---------|
| qc_specifications | QC spec templates per item |
| qc_tests | Individual test definitions |
| qc_results | Actual test results per lot |

## Indexes

Key indexes are defined on:
- All primary keys (auto)
- `users.username`, `users.email`
- `items.item_code`
- `lots.lot_number`
- `sales_orders.order_number`
- `purchase_orders.po_number`
- `production_orders.order_number`
- `customers.code`, `vendors.code`
- `invoices.invoice_number`
- All foreign key columns

## FIFO Costing

The `fifo_cost_layers` table maintains cost layers:
- New layer created on receipt/production output
- `quantity_remaining` decremented on consumption/shipment
- Oldest layers consumed first (FIFO ordering by `received_date`)
- Cost flows through production to finished goods
