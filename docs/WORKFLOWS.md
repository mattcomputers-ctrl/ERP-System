# BatchFlow ERP - Example Workflows

## 1. Raw Material Purchasing

### Workflow Steps:

1. **Create Purchase Order**
   ```
   POST /api/v1/purchasing/orders
   {
     "vendor_id": 1,
     "expected_delivery_date": "2026-04-15",
     "lines": [
       {"item_id": 1, "line_number": 1, "quantity_ordered": 500, "unit_price": 3.50},
       {"item_id": 2, "line_number": 2, "quantity_ordered": 300, "unit_price": 1.25}
     ]
   }
   ```

2. **Approve Purchase Order**
   ```
   PUT /api/v1/purchasing/orders/1
   { "status": "approved" }
   ```

3. **Send to Vendor** - Update status to "sent"

---

## 2. Purchase Order Receiving

1. **Receive Materials Against PO**
   ```
   POST /api/v1/purchasing/receipts
   {
     "purchase_order_id": 1,
     "lines": [
       {
         "purchase_order_line_id": 1,
         "item_id": 1,
         "lot_number": "RM-TIO2-20260315-A",
         "quantity_received": 500,
         "warehouse_id": 2,
         "location_id": 4,
         "vendor_lot_number": "VL-88234",
         "qc_hold": true
       }
     ]
   }
   ```

   This automatically:
   - Creates lot record
   - Creates FIFO cost layer at PO unit price
   - Updates PO received quantities
   - Creates inventory transaction
   - Sets lot status to "on_hold" for QC

---

## 3. QC Inspection

1. **Record Test Results**
   ```
   POST /api/v1/quality/results/batch
   {
     "lot_id": 1,
     "specification_id": 1,
     "results": [
       {"test_id": 1, "result_value": 99.7, "notes": "Good purity"},
       {"test_id": 2, "result_value": 0.24},
       {"test_id": 3, "result_value": 0.28}
     ]
   }
   ```

   Results are automatically compared to spec min/max values.

2. **Release Lot** (if all tests pass)
   ```
   POST /api/v1/quality/lot-disposition
   { "lot_id": 1, "action": "release", "notes": "All tests passed" }
   ```

---

## 4. Production Batch Creation

1. **Create Production Order**
   ```
   POST /api/v1/manufacturing/production-orders
   {
     "formula_id": 1,
     "formula_version_id": 1,
     "planned_quantity": 200,
     "planned_start_date": "2026-04-01",
     "output_warehouse_id": 1,
     "output_location_id": 1
   }
   ```

   Planned consumptions auto-calculated by scaling formula ingredients:
   - Formula batch size: 100 kg
   - Planned quantity: 200 kg
   - Scale factor: 2x
   - TiO2 planned: 60 kg, CaCO3: 40 kg, Resin: 70 kg, Solvent: 30 L

2. **Release for Production**
   ```
   PUT /api/v1/manufacturing/production-orders/1
   { "status": "released" }
   ```

---

## 5. Batch Production Completion

1. **Record Material Consumption**
   ```
   POST /api/v1/manufacturing/production-orders/1/consume
   [
     {"item_id": 1, "lot_id": 1, "actual_quantity": 60},
     {"item_id": 2, "lot_id": 2, "actual_quantity": 40},
     {"item_id": 3, "lot_id": 3, "actual_quantity": 70},
     {"item_id": 4, "lot_id": 4, "actual_quantity": 30}
   ]
   ```

   This:
   - Reduces lot quantities
   - Consumes FIFO cost layers
   - Creates consumption inventory transactions
   - Calculates total input cost

2. **Record Production Output**
   ```
   POST /api/v1/manufacturing/production-orders/1/output
   {
     "lot_number": "FG-PWC-20260401-001",
     "quantity": 196,
     "warehouse_id": 1,
     "location_id": 1
   }
   ```

   This:
   - Creates finished goods lot
   - Calculates unit cost from total input costs
   - Creates FIFO cost layer for output
   - Sets yield percent (196/200 = 98%)
   - Completes production order

---

## 6. Finished Goods QC Release

1. **Run QC Tests on FG Lot**
   ```
   POST /api/v1/quality/results/batch
   {
     "lot_id": 5,
     "specification_id": 2,
     "results": [
       {"test_id": 4, "result_value": 87},
       {"test_id": 5, "result_value": 11.3},
       {"test_id": 6, "result_value": 8.6},
       {"test_id": 7, "result_value": 82}
     ]
   }
   ```

2. **Release for Sale**
   ```
   POST /api/v1/quality/lot-disposition
   { "lot_id": 5, "action": "release" }
   ```

---

## 7. Sales Order Fulfillment

1. **Create Sales Order**
   ```
   POST /api/v1/sales/orders
   {
     "customer_id": 1,
     "requested_ship_date": "2026-04-10",
     "shipping_method": "LTL Freight",
     "lines": [
       {"item_id": 9, "line_number": 1, "quantity_ordered": 100, "unit_price": 12.50, "tax_rate": 7}
     ]
   }
   ```

2. **Confirm Order**
   ```
   PUT /api/v1/sales/orders/1
   { "status": "confirmed" }
   ```

3. **Ship Order**
   ```
   POST /api/v1/sales/shipments
   {
     "sales_order_id": 1,
     "carrier": "FreightCo",
     "tracking_number": "FC-123456",
     "lines": [
       {"sales_order_line_id": 1, "lot_id": 5, "quantity_shipped": 100}
     ]
   }
   ```

4. **Generate Invoice**
   ```
   POST /api/v1/sales/orders/1/invoice
   ```

---

## 8. Lot Traceability Search

### Forward Trace (Raw Material -> Customers)
```
GET /api/v1/traceability/lot/1/genealogy
```
Shows: RM lot -> Production order -> FG lot -> Shipment -> Customer

### Recall Impact Analysis
```
GET /api/v1/traceability/lot/1/recall-impact
```
Returns: affected lots, affected customers

---

## 9. GL Group Accounting Export

1. **View Inventory by GL Group**
   ```
   GET /api/v1/reports/inventory/by-gl-group
   ```
   Returns totals per GL group (Raw Materials, Finished Goods, etc.)

2. **View Sales by GL Group**
   ```
   GET /api/v1/reports/sales/by-gl-group
   ```
   Revenue categorized by GL group for accounting

3. **Sync to QuickBooks**
   GL account mappings ensure that:
   - Inventory values map to correct asset accounts
   - Sales revenue maps to correct income accounts
   - COGS maps to correct expense accounts

---

## Complete Order-to-Cash Flow

```
Purchase Order -> Receive -> QC Inspect -> Release ->
Production Order -> Consume Materials -> Record Output -> QC FG -> Release ->
Sales Order -> Ship -> Invoice -> QuickBooks Sync
```

Each step maintains:
- Full lot traceability
- FIFO cost layers
- GL Group accounting classification
- Audit trail via inventory transactions
