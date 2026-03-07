export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface GLGroup {
  id: number;
  name: string;
  description: string | null;
  account_mappings: GLAccountMapping[];
  created_at: string;
}

export interface GLAccountMapping {
  id: number;
  gl_group_id: number;
  account_type: string;
  account_name: string;
  account_number: string | null;
  qb_account_ref: string | null;
}

export interface Item {
  id: number;
  item_code: string;
  name: string;
  description: string | null;
  item_type: string;
  gl_group_id: number | null;
  is_active: boolean;
  is_lot_tracked: boolean;
  reorder_level: number | null;
  safety_stock: number | null;
  created_at: string;
}

export interface Lot {
  id: number;
  lot_number: string;
  item_id: number;
  warehouse_id: number | null;
  location_id: number | null;
  quantity_on_hand: number;
  quantity_allocated: number;
  quantity_on_hold: number;
  status: string;
  expiration_date: string | null;
  received_date: string | null;
  vendor_lot_number: string | null;
  created_at: string;
}

export interface Warehouse {
  id: number;
  code: string;
  name: string;
  address: string | null;
  is_active: boolean;
}

export interface Customer {
  id: number;
  code: string;
  name: string;
  contact_name: string | null;
  email: string | null;
  phone: string | null;
  billing_address_line1: string | null;
  billing_address_line2: string | null;
  billing_city: string | null;
  billing_state: string | null;
  billing_postal_code: string | null;
  billing_country: string;
  payment_terms: string | null;
  tax_exempt: boolean;
  is_active: boolean;
  created_at: string;
}

export interface ShipTo {
  id: number;
  customer_id: number;
  name: string;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string;
  contact_name: string | null;
  phone: string | null;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Vendor {
  id: number;
  code: string;
  name: string;
  contact_name: string | null;
  email: string | null;
  phone: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string;
  remit_address_line1: string | null;
  remit_address_line2: string | null;
  remit_city: string | null;
  remit_state: string | null;
  remit_postal_code: string | null;
  remit_country: string;
  payment_terms: string | null;
  default_ship_via_id: number | null;
  is_active: boolean;
  created_at: string;
}

export interface ShipVia {
  id: number;
  name: string;
  carrier: string | null;
  account_number: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SalesOrder {
  id: number;
  order_number: string;
  customer_id: number;
  ship_to_id: number | null;
  ship_via_id: number | null;
  order_date: string;
  requested_ship_date: string | null;
  status: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  notes: string | null;
  lines: SalesOrderLine[];
  created_at: string;
}

export interface SalesOrderLine {
  id: number;
  item_id: number;
  line_number: number;
  quantity_ordered: number;
  quantity_shipped: number;
  unit_price: number;
  tax_rate: number;
  line_total: number;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  vendor_id: number;
  ship_via_id: number | null;
  order_date: string;
  expected_delivery_date: string | null;
  status: string;
  subtotal: number;
  total_amount: number;
  notes: string | null;
  lines: PurchaseOrderLine[];
  created_at: string;
}

export interface PurchaseOrderLine {
  id: number;
  item_id: number;
  line_number: number;
  quantity_ordered: number;
  quantity_received: number;
  unit_price: number;
  line_total: number;
}

export interface Formula {
  id: number;
  code: string;
  name: string;
  product_item_id: number;
  description: string | null;
  is_active: boolean;
  versions: FormulaVersion[];
  created_at: string;
}

export interface FormulaVersion {
  id: number;
  formula_id: number;
  version_number: number;
  batch_size: number;
  expected_yield_percent: number;
  instructions: string | null;
  is_current: boolean;
  change_reason: string | null;
  reverted_from_version_id: number | null;
  ingredients: FormulaIngredient[];
}

export interface FormulaIngredient {
  id: number;
  item_id: number;
  sequence: number;
  quantity: number;
  percentage: number | null;
}

export interface ProductionOrder {
  id: number;
  order_number: string;
  formula_id: number;
  formula_version_id: number;
  planned_quantity: number;
  actual_quantity: number | null;
  status: string;
  yield_percent: number | null;
  created_at: string;
}

export interface QCSpecification {
  id: number;
  name: string;
  item_id: number | null;
  spec_type: string;
  is_active: boolean;
  tests: QCTest[];
}

export interface QCTest {
  id: number;
  test_name: string;
  test_method: string | null;
  target_value: number | null;
  min_value: number | null;
  max_value: number | null;
  uom: string | null;
}

export interface ItemAlias {
  id: number;
  item_id: number;
  alias_code: string;
  alias_name: string | null;
  alias_type: string | null;
  reference_id: number | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PackComponent {
  id: number;
  pack_item_id: number;
  component_item_id: number;
  quantity: number;
  sequence: number;
  uom_id: number | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface UserGroup {
  id: number;
  name: string;
  description: string | null;
}

export interface PriceList {
  id: number;
  item_id: number;
  price_type: string;
  entity_id: number;
  unit_price: number;
  min_quantity: number;
  effective_date: string;
  expiration_date: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PriceHistory {
  id: number;
  item_id: number;
  price_type: string;
  entity_id: number;
  old_price: number | null;
  new_price: number;
  changed_at: string;
}

export interface Branding {
  id: number;
  company_name: string;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  logo_path: string | null;
  primary_color: string;
  updated_at: string;
}
