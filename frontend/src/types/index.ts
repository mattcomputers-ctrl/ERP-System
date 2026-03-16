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
  primary_uom_id: number | null;
  is_active: boolean;
  is_lot_tracked: boolean;
  reorder_level: number | null;
  safety_stock: number | null;
  tracking_type: string;
  max_shelf_life_days: number | null;
  does_not_expire: boolean;
  target_min_qty: number | null;
  master_recipe_id: number | null;
  current_fifo_cost: number | null;
  replacement_cost: number | null;
  lead_time_days: number | null;
  preferred_supplier_id: number | null;
  specific_gravity: number | null;
  density_lb_gal: number | null;
  voc_percent: number | null;
  boiling_point: string | null;
  flash_point: string | null;
  created_at: string;
}

export interface Lot {
  id: number;
  lot_number: string;
  item_id: number;
  pack_extension_id: number | null;
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

export interface InventorySummaryRow {
  warehouse_code: string;
  warehouse_name: string;
  warehouse_id: number | null;
  item_id: number;
  item_code: string;
  item_base_code: string;
  item_name: string;
  pack_extension_id: number | null;
  pack_extension_code: string | null;
  pack_extension_name: string | null;
  qty_on_hand: number;
  qty_allocated: number;
  uom_abbreviation: string;
  gl_group_name: string;
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
  credit_limit: number | null;
  sales_rep: string | null;
  default_ship_via_id: number | null;
  sales_tax_option_id: number | null;
  tax_exempt: boolean;
  tax_id_number: string | null;
  internal_memo: string | null;
  shipping_memo: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SalesTaxOption {
  id: number;
  name: string;
  description: string | null;
  qb_tax_code: string | null;
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

export interface DocumentTemplate {
  id: number;
  name: string;
  doc_type: string;
  description: string | null;
  layout_json: string;
  header_html: string | null;
  footer_html: string | null;
  is_default: boolean;
  is_active: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface GeneratedDocument {
  id: number;
  doc_type: string;
  reference_type: string;
  reference_id: number;
  template_id: number | null;
  file_path: string;
  file_name: string;
  generated_by: number | null;
  generated_at: string;
}

export interface COACertificate {
  id: number;
  certificate_number: string;
  lot_id: number;
  specification_id: number | null;
  customer_id: number | null;
  pdf_path: string | null;
  status: string;
  approved_by: number | null;
  approved_at: string | null;
  notes: string | null;
  created_by: number | null;
  created_at: string;
}

export interface QBSyncStatus {
  enabled: boolean;
  interval_seconds: number;
  is_running: boolean;
  last_sync: string | null;
  last_result_count: number;
}

export interface QBPendingSync {
  customers: number;
  vendors: number;
  invoices: number;
  purchase_orders: number;
  total: number;
}

// --- Item Active Recipes ---

export interface ItemActiveRecipe {
  id: number;
  item_id: number;
  formula_id: number;
  is_master: boolean;
  created_at: string;
}

// --- QC Test Definitions (Settings) ---

export interface QCTestDefinition {
  id: number;
  name: string;
  test_type: string;
  method: string | null;
  uom_id: number | null;
  is_active: boolean;
  created_at: string;
}

// --- Item QC Test Assignments ---

export interface ItemQCTestAssignment {
  id: number;
  item_id: number;
  qc_test_definition_id: number;
  target_value: number | null;
  min_value: number | null;
  max_value: number | null;
  created_at: string;
}

// --- Pack Extension Definitions (Settings) ---

export interface PackExtensionMaterial {
  id: number;
  pack_extension_id: number;
  material_item_id: number;
  quantity_per_lb: number;
  uom_id: number | null;
  created_at: string;
}

export interface PackExtensionDefinition {
  id: number;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  materials: PackExtensionMaterial[];
  created_at: string;
}

// --- Item Pack Extension Assignments ---

export interface ItemPackExtension {
  id: number;
  item_id: number;
  pack_extension_id: number;
  desired_fill_amount: number | null;
  fill_uom_id: number | null;
  created_at: string;
}

// --- UOM ---

export interface UOM {
  id: number;
  name: string;
  abbreviation: string;
  category: string;
}

// --- Recipes ---

export interface RecipeIngredient {
  id: number;
  item_id: number;
  sequence: number;
  weight_percent: number;
  notes: string | null;
}

export interface RecipeProcedureStep {
  id: number;
  sequence: number;
  step_type: string; // add_formula, instruction
  instruction_text: string | null;
}

export interface RecipeVersion {
  id: number;
  recipe_id: number;
  version_number: number;
  status: string; // draft, published
  comment: string | null;
  batch_size: number | null;
  batch_uom_id: number | null;
  expected_yield_percent: number;
  published_at: string | null;
  created_at: string;
  ingredients: RecipeIngredient[];
  procedure_steps: RecipeProcedureStep[];
}

export interface Recipe {
  id: number;
  product_item_id: number;
  description: string | null;
  is_active: boolean;
  versions: RecipeVersion[];
  created_at: string;
}

// --- Batch Tickets ---

export interface BatchTicketPackage {
  id: number;
  pack_extension_id: number;
  quantity: number;
}

export interface BatchTicketMaterial {
  id: number;
  item_id: number;
  planned_quantity: number;
  available_quantity: number | null;
  has_shortage: boolean;
}

export interface BatchTicket {
  id: number;
  ticket_number: string;
  ticket_type: string; // batch, repack
  recipe_id: number | null;
  recipe_version_id: number | null;
  item_id: number;
  planned_quantity: number;
  due_date: string | null;
  customer_id: number | null;
  status: string;
  has_shortage: boolean;
  shortage_override: boolean;
  shortage_details: string | null;
  notes: string | null;
  packages: BatchTicketPackage[];
  planned_materials: BatchTicketMaterial[];
  created_at: string;
}

// --- Batch Execution ---

export interface BatchExecutionConsumption {
  id: number;
  item_id: number;
  lot_id: number | null;
  planned_quantity: number | null;
  actual_quantity: number;
  unit_cost: number | null;
  total_cost: number | null;
}

export interface BatchExecutionOutput {
  id: number;
  item_id: number;
  lot_id: number | null;
  quantity: number;
  unit_cost: number | null;
  total_cost: number | null;
}

export interface BatchExecutionQCResult {
  id: number;
  execution_id: number;
  qc_test_definition_id: number;
  target_value: number | null;
  min_value: number | null;
  max_value: number | null;
  result_value: number | null;
  result_text: string | null;
  passed: boolean | null;
  tested_by: number | null;
  tested_at: string | null;
  notes: string | null;
}

export interface QCTestAssignment {
  assignment_id: number;
  qc_test_definition_id: number;
  test_name: string;
  test_type: string;
  method: string | null;
  target_value: number | null;
  min_value: number | null;
  max_value: number | null;
}

export interface BatchExecution {
  id: number;
  batch_ticket_id: number;
  status: string;
  actual_yield: number | null;
  yield_percent: number | null;
  started_at: string;
  completed_at: string | null;
  notes: string | null;
  consumptions: BatchExecutionConsumption[];
  outputs: BatchExecutionOutput[];
  qc_results: BatchExecutionQCResult[];
}
