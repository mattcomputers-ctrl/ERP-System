"""Initial migration - all tables

Revision ID: f13dbf42ab10
Revises:
Create Date: 2026-03-07 17:16:42.396918
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f13dbf42ab10'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Users & Auth ---
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('user_groups',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('user_group_associations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('assigned_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )

    op.create_table('group_permissions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('module', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('allowed', sa.Boolean(), server_default='true'),
    )

    # --- GL Groups ---
    op.create_table('gl_groups',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('gl_account_mappings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('gl_group_id', sa.Integer(), sa.ForeignKey('gl_groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('account_type', sa.String(50), nullable=False),
        sa.Column('account_name', sa.String(200), nullable=False),
        sa.Column('account_number', sa.String(50), nullable=True),
        sa.Column('qb_account_ref', sa.String(200), nullable=True),
    )

    # --- Settings ---
    op.create_table('ship_vias',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('carrier', sa.String(100), nullable=True),
        sa.Column('account_number', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('branding',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('company_name', sa.String(255), nullable=False, server_default='My Company'),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), server_default='US'),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('logo_path', sa.String(500), nullable=True),
        sa.Column('primary_color', sa.String(7), server_default='#1e40af'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Inventory ---
    op.create_table('units_of_measure',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('abbreviation', sa.String(10), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
    )

    op.create_table('uom_conversions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('from_uom_id', sa.Integer(), sa.ForeignKey('units_of_measure.id'), nullable=False),
        sa.Column('to_uom_id', sa.Integer(), sa.ForeignKey('units_of_measure.id'), nullable=False),
        sa.Column('factor', sa.Numeric(18, 8), nullable=False),
    )

    op.create_table('warehouses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(20), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
    )

    op.create_table('locations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
    )

    op.create_table('items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('item_code', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('item_type', sa.String(30), nullable=False),
        sa.Column('gl_group_id', sa.Integer(), sa.ForeignKey('gl_groups.id'), nullable=True),
        sa.Column('primary_uom_id', sa.Integer(), sa.ForeignKey('units_of_measure.id'), nullable=True),
        sa.Column('reorder_level', sa.Numeric(18, 4), nullable=True),
        sa.Column('safety_stock', sa.Numeric(18, 4), nullable=True),
        sa.Column('is_lot_tracked', sa.Boolean(), server_default='true'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('item_aliases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('alias_code', sa.String(100), nullable=False, index=True),
        sa.Column('alias_name', sa.String(255), nullable=True),
        sa.Column('alias_type', sa.String(30), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('pack_components',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('pack_item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('component_item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('sequence', sa.Integer(), server_default='0'),
        sa.Column('uom_id', sa.Integer(), sa.ForeignKey('units_of_measure.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('lots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('lot_number', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('quantity_on_hand', sa.Numeric(18, 4), server_default='0'),
        sa.Column('quantity_allocated', sa.Numeric(18, 4), server_default='0'),
        sa.Column('quantity_on_hold', sa.Numeric(18, 4), server_default='0'),
        sa.Column('status', sa.String(30), server_default='available'),
        sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('vendor_lot_number', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('fifo_cost_layers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=True),
        sa.Column('quantity_remaining', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit_cost', sa.Numeric(18, 6), nullable=False),
        sa.Column('total_cost', sa.Numeric(18, 4), nullable=False),
        sa.Column('received_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
    )

    op.create_table('inventory_transactions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('transaction_type', sa.String(30), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=True),
        sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit_cost', sa.Numeric(18, 6), nullable=True),
        sa.Column('total_cost', sa.Numeric(18, 4), nullable=True),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('gl_group_id', sa.Integer(), sa.ForeignKey('gl_groups.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('price_lists',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('price_type', sa.String(20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('min_quantity', sa.Numeric(18, 4), server_default='0'),
        sa.Column('effective_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('price_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('price_list_id', sa.Integer(), sa.ForeignKey('price_lists.id'), nullable=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('price_type', sa.String(20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('old_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('new_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('changed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )

    # --- Sales ---
    op.create_table('customers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('billing_address_line1', sa.String(255), nullable=True),
        sa.Column('billing_address_line2', sa.String(255), nullable=True),
        sa.Column('billing_city', sa.String(100), nullable=True),
        sa.Column('billing_state', sa.String(100), nullable=True),
        sa.Column('billing_postal_code', sa.String(20), nullable=True),
        sa.Column('billing_country', sa.String(100), server_default='US'),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), server_default='US'),
        sa.Column('payment_terms', sa.String(50), nullable=True),
        sa.Column('tax_exempt', sa.Boolean(), server_default='false'),
        sa.Column('qb_list_id', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('ship_tos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), server_default='US'),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='false'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('sales_orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_number', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('ship_to_id', sa.Integer(), sa.ForeignKey('ship_tos.id'), nullable=True),
        sa.Column('ship_via_id', sa.Integer(), sa.ForeignKey('ship_vias.id'), nullable=True),
        sa.Column('order_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('requested_ship_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(30), server_default='draft'),
        sa.Column('shipping_method', sa.String(100), nullable=True),
        sa.Column('shipping_address', sa.Text(), nullable=True),
        sa.Column('subtotal', sa.Numeric(18, 4), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(18, 4), server_default='0'),
        sa.Column('total_amount', sa.Numeric(18, 4), server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('sales_order_lines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sales_order_id', sa.Integer(), sa.ForeignKey('sales_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('quantity_ordered', sa.Numeric(18, 4), nullable=False),
        sa.Column('quantity_shipped', sa.Numeric(18, 4), server_default='0'),
        sa.Column('unit_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('tax_rate', sa.Numeric(8, 4), server_default='0'),
        sa.Column('line_total', sa.Numeric(18, 4), nullable=False),
        sa.Column('allocated_lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=True),
    )

    op.create_table('shipments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('shipment_number', sa.String(50), nullable=False, unique=True),
        sa.Column('sales_order_id', sa.Integer(), sa.ForeignKey('sales_orders.id'), nullable=False),
        sa.Column('ship_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('carrier', sa.String(100), nullable=True),
        sa.Column('tracking_number', sa.String(200), nullable=True),
        sa.Column('status', sa.String(30), server_default='pending'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('shipment_lines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('shipment_id', sa.Integer(), sa.ForeignKey('shipments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sales_order_line_id', sa.Integer(), sa.ForeignKey('sales_order_lines.id'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=True),
        sa.Column('quantity_shipped', sa.Numeric(18, 4), nullable=False),
    )

    op.create_table('invoices',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('invoice_number', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('sales_order_id', sa.Integer(), sa.ForeignKey('sales_orders.id'), nullable=False),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('invoice_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(30), server_default='draft'),
        sa.Column('subtotal', sa.Numeric(18, 4), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(18, 4), server_default='0'),
        sa.Column('total_amount', sa.Numeric(18, 4), server_default='0'),
        sa.Column('pdf_path', sa.String(500), nullable=True),
        sa.Column('qb_txn_id', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('invoice_lines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('line_total', sa.Numeric(18, 4), nullable=False),
        sa.Column('gl_group_id', sa.Integer(), sa.ForeignKey('gl_groups.id'), nullable=True),
    )

    op.create_table('packing_lists',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('packing_list_number', sa.String(50), nullable=False, unique=True),
        sa.Column('sales_order_id', sa.Integer(), sa.ForeignKey('sales_orders.id'), nullable=False),
        sa.Column('shipment_id', sa.Integer(), sa.ForeignKey('shipments.id'), nullable=True),
        sa.Column('created_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('pdf_path', sa.String(500), nullable=True),
    )

    # --- Purchasing ---
    op.create_table('vendors',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), server_default='US'),
        sa.Column('remit_address_line1', sa.String(255), nullable=True),
        sa.Column('remit_address_line2', sa.String(255), nullable=True),
        sa.Column('remit_city', sa.String(100), nullable=True),
        sa.Column('remit_state', sa.String(100), nullable=True),
        sa.Column('remit_postal_code', sa.String(20), nullable=True),
        sa.Column('remit_country', sa.String(100), server_default='US'),
        sa.Column('payment_terms', sa.String(50), nullable=True),
        sa.Column('default_ship_via_id', sa.Integer(), sa.ForeignKey('ship_vias.id'), nullable=True),
        sa.Column('qb_list_id', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('purchase_orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('po_number', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('vendor_id', sa.Integer(), sa.ForeignKey('vendors.id'), nullable=False),
        sa.Column('ship_via_id', sa.Integer(), sa.ForeignKey('ship_vias.id'), nullable=True),
        sa.Column('order_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expected_delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(30), server_default='draft'),
        sa.Column('subtotal', sa.Numeric(18, 4), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(18, 4), server_default='0'),
        sa.Column('total_amount', sa.Numeric(18, 4), server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('pdf_path', sa.String(500), nullable=True),
        sa.Column('qb_txn_id', sa.String(200), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('purchase_order_lines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('purchase_order_id', sa.Integer(), sa.ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('quantity_ordered', sa.Numeric(18, 4), nullable=False),
        sa.Column('quantity_received', sa.Numeric(18, 4), server_default='0'),
        sa.Column('unit_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('line_total', sa.Numeric(18, 4), nullable=False),
    )

    op.create_table('receipts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('receipt_number', sa.String(50), nullable=False, unique=True),
        sa.Column('purchase_order_id', sa.Integer(), sa.ForeignKey('purchase_orders.id'), nullable=False),
        sa.Column('receipt_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', sa.String(30), server_default='received'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('receipt_lines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('receipt_id', sa.Integer(), sa.ForeignKey('receipts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('purchase_order_line_id', sa.Integer(), sa.ForeignKey('purchase_order_lines.id'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=True),
        sa.Column('quantity_received', sa.Numeric(18, 4), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('qc_status', sa.String(30), server_default='pending'),
    )

    # --- Manufacturing ---
    op.create_table('formulas',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('product_item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('formula_versions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('formula_id', sa.Integer(), sa.ForeignKey('formulas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('batch_size', sa.Numeric(18, 4), nullable=False),
        sa.Column('batch_uom_id', sa.Integer(), sa.ForeignKey('units_of_measure.id'), nullable=True),
        sa.Column('expected_yield_percent', sa.Numeric(8, 4), server_default='100'),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('reverted_from_version_id', sa.Integer(), sa.ForeignKey('formula_versions.id'), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('formula_ingredients',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('formula_version_id', sa.Integer(), sa.ForeignKey('formula_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 6), nullable=False),
        sa.Column('uom_id', sa.Integer(), sa.ForeignKey('units_of_measure.id'), nullable=True),
        sa.Column('percentage', sa.Numeric(8, 4), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    op.create_table('production_orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_number', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('formula_id', sa.Integer(), sa.ForeignKey('formulas.id'), nullable=False),
        sa.Column('formula_version_id', sa.Integer(), sa.ForeignKey('formula_versions.id'), nullable=False),
        sa.Column('planned_quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('actual_quantity', sa.Numeric(18, 4), nullable=True),
        sa.Column('planned_start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(30), server_default='planned'),
        sa.Column('output_lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=True),
        sa.Column('output_warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id'), nullable=True),
        sa.Column('output_location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('yield_percent', sa.Numeric(8, 4), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('production_consumptions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('production_order_id', sa.Integer(), sa.ForeignKey('production_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=True),
        sa.Column('planned_quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('actual_quantity', sa.Numeric(18, 4), nullable=True),
        sa.Column('unit_cost', sa.Numeric(18, 6), nullable=True),
        sa.Column('total_cost', sa.Numeric(18, 4), nullable=True),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table('production_outputs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('production_order_id', sa.Integer(), sa.ForeignKey('production_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False),
        sa.Column('lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit_cost', sa.Numeric(18, 6), nullable=True),
        sa.Column('total_cost', sa.Numeric(18, 4), nullable=True),
        sa.Column('produced_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Quality ---
    op.create_table('qc_specifications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=True),
        sa.Column('spec_type', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('qc_tests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('specification_id', sa.Integer(), sa.ForeignKey('qc_specifications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('test_name', sa.String(200), nullable=False),
        sa.Column('test_method', sa.String(200), nullable=True),
        sa.Column('target_value', sa.Numeric(18, 6), nullable=True),
        sa.Column('min_value', sa.Numeric(18, 6), nullable=True),
        sa.Column('max_value', sa.Numeric(18, 6), nullable=True),
        sa.Column('uom', sa.String(50), nullable=True),
        sa.Column('is_required', sa.Boolean(), server_default='true'),
        sa.Column('sequence', sa.Integer(), server_default='0'),
    )

    op.create_table('qc_results',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=False),
        sa.Column('specification_id', sa.Integer(), sa.ForeignKey('qc_specifications.id'), nullable=False),
        sa.Column('test_id', sa.Integer(), sa.ForeignKey('qc_tests.id'), nullable=False),
        sa.Column('result_value', sa.Numeric(18, 6), nullable=True),
        sa.Column('result_text', sa.String(500), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('tested_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('tested_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    # --- Documents ---
    op.create_table('document_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('doc_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('layout_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('header_html', sa.Text(), nullable=True),
        sa.Column('footer_html', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='false'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('generated_documents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('doc_type', sa.String(50), nullable=False),
        sa.Column('reference_type', sa.String(50), nullable=False),
        sa.Column('reference_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('document_templates.id'), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('generated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('coa_certificates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('certificate_number', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('lot_id', sa.Integer(), sa.ForeignKey('lots.id'), nullable=False),
        sa.Column('specification_id', sa.Integer(), sa.ForeignKey('qc_specifications.id'), nullable=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('pdf_path', sa.String(500), nullable=True),
        sa.Column('status', sa.String(30), server_default='draft'),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('coa_certificates')
    op.drop_table('generated_documents')
    op.drop_table('document_templates')
    op.drop_table('qc_results')
    op.drop_table('qc_tests')
    op.drop_table('qc_specifications')
    op.drop_table('production_outputs')
    op.drop_table('production_consumptions')
    op.drop_table('production_orders')
    op.drop_table('formula_ingredients')
    op.drop_table('formula_versions')
    op.drop_table('formulas')
    op.drop_table('receipt_lines')
    op.drop_table('receipts')
    op.drop_table('purchase_order_lines')
    op.drop_table('purchase_orders')
    op.drop_table('vendors')
    op.drop_table('packing_lists')
    op.drop_table('invoice_lines')
    op.drop_table('invoices')
    op.drop_table('shipment_lines')
    op.drop_table('shipments')
    op.drop_table('sales_order_lines')
    op.drop_table('sales_orders')
    op.drop_table('ship_tos')
    op.drop_table('customers')
    op.drop_table('price_history')
    op.drop_table('price_lists')
    op.drop_table('inventory_transactions')
    op.drop_table('fifo_cost_layers')
    op.drop_table('lots')
    op.drop_table('pack_components')
    op.drop_table('item_aliases')
    op.drop_table('items')
    op.drop_table('locations')
    op.drop_table('warehouses')
    op.drop_table('uom_conversions')
    op.drop_table('units_of_measure')
    op.drop_table('branding')
    op.drop_table('ship_vias')
    op.drop_table('gl_account_mappings')
    op.drop_table('gl_groups')
    op.drop_table('group_permissions')
    op.drop_table('user_group_associations')
    op.drop_table('user_groups')
    op.drop_table('users')
