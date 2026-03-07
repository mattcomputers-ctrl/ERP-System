import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { purchasingAPI, inventoryAPI, settingsAPI } from '../services/api';
import { getStatusColor, formatDate, formatCurrency } from '../utils/helpers';
import type { PurchaseOrder, Vendor, Item, ShipVia } from '../types';

interface POLine { item_id: number; line_number: number; quantity_ordered: number; unit_price: number; }

const PurchasingPage: React.FC = () => {
  const [showCreateOrder, setShowCreateOrder] = useState(false);
  const [showOrderDetail, setShowOrderDetail] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<PurchaseOrder | null>(null);
  const [orderForm, setOrderForm] = useState({ vendor_id: 0, ship_via_id: null as number | null, expected_delivery_date: '', notes: '' });
  const [orderLines, setOrderLines] = useState<POLine[]>([{ item_id: 0, line_number: 1, quantity_ordered: 0, unit_price: 0 }]);
  const queryClient = useQueryClient();

  const { data: orders } = useQuery({ queryKey: ['purchase-orders'], queryFn: () => purchasingAPI.listOrders() });
  const { data: vendors } = useQuery({ queryKey: ['vendors'], queryFn: () => purchasingAPI.listVendors() });
  const { data: items } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: shipVias } = useQuery({ queryKey: ['ship-vias'], queryFn: () => settingsAPI.listShipVias() });

  const createOrder = useMutation({
    mutationFn: (data: any) => purchasingAPI.createOrder(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['purchase-orders'] }); setShowCreateOrder(false); resetForm(); toast.success('Purchase order created'); },
    onError: () => toast.error('Failed to create purchase order'),
  });

  const updateOrder = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => purchasingAPI.updateOrder(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['purchase-orders'] }); toast.success('Order updated'); },
    onError: () => toast.error('Failed to update order'),
  });

  const resetForm = () => {
    setOrderForm({ vendor_id: 0, ship_via_id: null, expected_delivery_date: '', notes: '' });
    setOrderLines([{ item_id: 0, line_number: 1, quantity_ordered: 0, unit_price: 0 }]);
  };

  const addLine = () => setOrderLines([...orderLines, { item_id: 0, line_number: orderLines.length + 1, quantity_ordered: 0, unit_price: 0 }]);
  const removeLine = (idx: number) => setOrderLines(orderLines.filter((_, i) => i !== idx).map((l, i) => ({ ...l, line_number: i + 1 })));
  const updateLine = (idx: number, field: string, value: any) => setOrderLines(orderLines.map((l, i) => i === idx ? { ...l, [field]: value } : l));

  const handleSubmitOrder = () => {
    const validLines = orderLines.filter(l => l.item_id > 0 && l.quantity_ordered > 0);
    if (validLines.length === 0) { toast.error('Add at least one line item'); return; }
    createOrder.mutate({ ...orderForm, lines: validLines });
  };

  const vendorList: Vendor[] = vendors?.data || [];
  const itemList: Item[] = items?.data || [];
  const shipViaList: ShipVia[] = shipVias?.data || [];
  const subtotal = orderLines.reduce((s, l) => s + l.quantity_ordered * l.unit_price, 0);

  const orderColumns = [
    { header: 'PO #', accessor: 'po_number' as keyof PurchaseOrder },
    { header: 'Vendor', accessor: ((row: PurchaseOrder) => { const v = vendorList.find(v => v.id === row.vendor_id); return v?.name || '-'; }) },
    { header: 'Date', accessor: ((row: PurchaseOrder) => formatDate(row.order_date)) },
    { header: 'Expected', accessor: ((row: PurchaseOrder) => formatDate(row.expected_delivery_date)) },
    { header: 'Status', accessor: ((row: PurchaseOrder) => <span className={getStatusColor(row.status)}>{row.status}</span>) },
    { header: 'Total', accessor: ((row: PurchaseOrder) => formatCurrency(row.total_amount)) },
    { header: 'Actions', accessor: ((row: PurchaseOrder) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); setSelectedOrder(row); setShowOrderDetail(true); }}>View</button>
        {row.status === 'draft' && <button className="text-sm text-green-600 hover:underline" onClick={(e) => { e.stopPropagation(); updateOrder.mutate({ id: row.id, data: { status: 'approved' } }); }}>Approve</button>}
        {row.status === 'approved' && <button className="text-sm text-purple-600 hover:underline" onClick={(e) => { e.stopPropagation(); updateOrder.mutate({ id: row.id, data: { status: 'sent' } }); }}>Mark Sent</button>}
      </div>
    )) },
  ];

  return (
    <div>
      <PageHeader title="Purchase Orders" subtitle="Create and manage purchase orders" actions={<button className="btn-primary" onClick={() => setShowCreateOrder(true)}>New PO</button>} />
      <div className="card"><DataTable columns={orderColumns} data={orders?.data || []} /></div>

      {/* Create PO */}
      <Modal isOpen={showCreateOrder} onClose={() => { setShowCreateOrder(false); resetForm(); }} title="New Purchase Order" size="xl">
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Vendor</label>
              <select className="input-field" value={orderForm.vendor_id} onChange={(e) => {
                const vid = Number(e.target.value);
                const vendor = vendorList.find(v => v.id === vid);
                setOrderForm({ ...orderForm, vendor_id: vid, ship_via_id: vendor?.default_ship_via_id || null });
              }} required>
                <option value={0}>Select vendor...</option>
                {vendorList.map(v => <option key={v.id} value={v.id}>{v.code} - {v.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Ship Via</label>
              <select className="input-field" value={orderForm.ship_via_id || ''} onChange={(e) => setOrderForm({ ...orderForm, ship_via_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">-- Select --</option>
                {shipViaList.map(sv => <option key={sv.id} value={sv.id}>{sv.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Expected Delivery</label>
              <input type="date" className="input-field" value={orderForm.expected_delivery_date} onChange={(e) => setOrderForm({ ...orderForm, expected_delivery_date: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Notes</label>
            <input className="input-field" value={orderForm.notes} onChange={(e) => setOrderForm({ ...orderForm, notes: e.target.value })} />
          </div>
          <h3 className="text-sm font-semibold text-gray-700">Line Items</h3>
          <table className="w-full text-sm">
            <thead><tr className="border-b"><th className="text-left py-1">#</th><th className="text-left py-1">Item</th><th className="text-right py-1">Qty</th><th className="text-right py-1">Price</th><th className="text-right py-1">Total</th><th></th></tr></thead>
            <tbody>
              {orderLines.map((line, idx) => (
                <tr key={idx} className="border-b">
                  <td className="py-1">{line.line_number}</td>
                  <td className="py-1">
                    <select className="input-field text-sm" value={line.item_id} onChange={(e) => updateLine(idx, 'item_id', Number(e.target.value))}>
                      <option value={0}>Select...</option>
                      {itemList.map(i => <option key={i.id} value={i.id}>{i.item_code} - {i.name}</option>)}
                    </select>
                  </td>
                  <td className="py-1"><input type="number" step="0.01" className="input-field text-sm text-right w-24" value={line.quantity_ordered || ''} onChange={(e) => updateLine(idx, 'quantity_ordered', Number(e.target.value))} /></td>
                  <td className="py-1"><input type="number" step="0.01" className="input-field text-sm text-right w-24" value={line.unit_price || ''} onChange={(e) => updateLine(idx, 'unit_price', Number(e.target.value))} /></td>
                  <td className="py-1 text-right">{formatCurrency(line.quantity_ordered * line.unit_price)}</td>
                  <td className="py-1"><button className="text-red-500 text-xs" onClick={() => removeLine(idx)}>X</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex justify-between items-center">
            <button type="button" className="text-sm text-blue-600 hover:underline" onClick={addLine}>+ Add Line</button>
            <div className="text-right font-semibold">Subtotal: {formatCurrency(subtotal)}</div>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => { setShowCreateOrder(false); resetForm(); }}>Cancel</button>
            <button type="button" className="btn-primary" onClick={handleSubmitOrder} disabled={createOrder.isPending}>Create PO</button>
          </div>
        </div>
      </Modal>

      {/* PO Detail */}
      <Modal isOpen={showOrderDetail} onClose={() => { setShowOrderDetail(false); setSelectedOrder(null); }} title={`PO ${selectedOrder?.po_number || ''}`} size="lg">
        {selectedOrder && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div><span className="text-gray-500">Vendor:</span> {vendorList.find(v => v.id === selectedOrder.vendor_id)?.name}</div>
              <div><span className="text-gray-500">Status:</span> <span className={getStatusColor(selectedOrder.status)}>{selectedOrder.status}</span></div>
              <div><span className="text-gray-500">Total:</span> {formatCurrency(selectedOrder.total_amount)}</div>
            </div>
            <table className="w-full text-sm">
              <thead><tr className="border-b"><th className="text-left py-1">Item</th><th className="text-right py-1">Ordered</th><th className="text-right py-1">Received</th><th className="text-right py-1">Price</th><th className="text-right py-1">Total</th></tr></thead>
              <tbody>{selectedOrder.lines?.map(l => {
                const item = itemList.find(i => i.id === l.item_id);
                return <tr key={l.id} className="border-b"><td className="py-1">{item ? `${item.item_code} - ${item.name}` : `Item #${l.item_id}`}</td><td className="py-1 text-right">{l.quantity_ordered}</td><td className="py-1 text-right">{l.quantity_received}</td><td className="py-1 text-right">{formatCurrency(l.unit_price)}</td><td className="py-1 text-right">{formatCurrency(l.line_total)}</td></tr>;
              })}</tbody>
            </table>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default PurchasingPage;
