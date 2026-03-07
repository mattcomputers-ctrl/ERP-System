import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { salesAPI, inventoryAPI, settingsAPI } from '../services/api';
import { getStatusColor, formatDate, formatCurrency } from '../utils/helpers';
import type { SalesOrder, Customer, Item, ShipTo, ShipVia } from '../types';

interface OrderLine { item_id: number; line_number: number; quantity_ordered: number; unit_price: number; tax_rate: number; }

const SalesPage: React.FC = () => {
  const [showCreateOrder, setShowCreateOrder] = useState(false);
  const [showOrderDetail, setShowOrderDetail] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<SalesOrder | null>(null);
  const [showPickList, setShowPickList] = useState(false);
  const [pickListData, setPickListData] = useState<any>(null);
  const [orderForm, setOrderForm] = useState({ customer_id: 0, ship_to_id: null as number | null, ship_via_id: null as number | null, requested_ship_date: '', notes: '' });
  const [orderLines, setOrderLines] = useState<OrderLine[]>([{ item_id: 0, line_number: 1, quantity_ordered: 0, unit_price: 0, tax_rate: 0 }]);
  const queryClient = useQueryClient();

  const { data: orders } = useQuery({ queryKey: ['sales-orders'], queryFn: () => salesAPI.listOrders() });
  const { data: customers } = useQuery({ queryKey: ['customers'], queryFn: () => salesAPI.listCustomers() });
  const { data: items } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: shipVias } = useQuery({ queryKey: ['ship-vias'], queryFn: () => settingsAPI.listShipVias() });
  const { data: shipTos } = useQuery({
    queryKey: ['ship-tos', orderForm.customer_id],
    queryFn: () => settingsAPI.listShipTos({ customer_id: orderForm.customer_id }),
    enabled: orderForm.customer_id > 0,
  });

  const createOrder = useMutation({
    mutationFn: (data: any) => salesAPI.createOrder(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['sales-orders'] }); setShowCreateOrder(false); resetOrderForm(); toast.success('Order created'); },
    onError: () => toast.error('Failed to create order'),
  });

  const createInvoice = useMutation({
    mutationFn: (orderId: number) => salesAPI.createInvoice(orderId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['sales-orders'] }); toast.success('Invoice created'); },
    onError: () => toast.error('Failed to create invoice'),
  });

  const createPackingList = useMutation({
    mutationFn: (orderId: number) => salesAPI.createPackingList(orderId),
    onSuccess: (res) => { toast.success(`Packing list ${res.data.packing_list_number} created`); },
    onError: () => toast.error('Failed to create packing list'),
  });

  const resetOrderForm = () => {
    setOrderForm({ customer_id: 0, ship_to_id: null, ship_via_id: null, requested_ship_date: '', notes: '' });
    setOrderLines([{ item_id: 0, line_number: 1, quantity_ordered: 0, unit_price: 0, tax_rate: 0 }]);
  };

  const addLine = () => setOrderLines([...orderLines, { item_id: 0, line_number: orderLines.length + 1, quantity_ordered: 0, unit_price: 0, tax_rate: 0 }]);
  const removeLine = (idx: number) => setOrderLines(orderLines.filter((_, i) => i !== idx).map((l, i) => ({ ...l, line_number: i + 1 })));
  const updateLine = (idx: number, field: string, value: any) => setOrderLines(orderLines.map((l, i) => i === idx ? { ...l, [field]: value } : l));

  const handleSubmitOrder = () => {
    const validLines = orderLines.filter(l => l.item_id > 0 && l.quantity_ordered > 0);
    if (validLines.length === 0) { toast.error('Add at least one line item'); return; }
    createOrder.mutate({ ...orderForm, lines: validLines });
  };

  const loadPickList = async (orderId: number) => {
    try {
      const res = await salesAPI.getPickList(orderId);
      setPickListData(res.data);
      setShowPickList(true);
    } catch { toast.error('Failed to load pick list'); }
  };

  const custList: Customer[] = customers?.data || [];
  const itemList: Item[] = items?.data || [];
  const shipViaList: ShipVia[] = shipVias?.data || [];
  const shipToList: ShipTo[] = shipTos?.data || [];
  const subtotal = orderLines.reduce((s, l) => s + l.quantity_ordered * l.unit_price, 0);

  const orderColumns = [
    { header: 'Order #', accessor: 'order_number' as keyof SalesOrder },
    { header: 'Customer', accessor: ((row: SalesOrder) => { const c = custList.find(c => c.id === row.customer_id); return c?.name || '-'; }) },
    { header: 'Date', accessor: ((row: SalesOrder) => formatDate(row.order_date)) },
    { header: 'Ship Date', accessor: ((row: SalesOrder) => formatDate(row.requested_ship_date)) },
    { header: 'Status', accessor: ((row: SalesOrder) => <span className={getStatusColor(row.status)}>{row.status}</span>) },
    { header: 'Total', accessor: ((row: SalesOrder) => formatCurrency(row.total_amount)) },
    { header: 'Actions', accessor: ((row: SalesOrder) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); setSelectedOrder(row); setShowOrderDetail(true); }}>View</button>
        <button className="text-sm text-green-600 hover:underline" onClick={(e) => { e.stopPropagation(); loadPickList(row.id); }}>Pick List</button>
      </div>
    )) },
  ];

  return (
    <div>
      <PageHeader title="Sales Orders" subtitle="Create and manage sales orders" actions={<button className="btn-primary" onClick={() => setShowCreateOrder(true)}>New Order</button>} />
      <div className="card"><DataTable columns={orderColumns} data={orders?.data || []} /></div>

      {/* Create Order */}
      <Modal isOpen={showCreateOrder} onClose={() => { setShowCreateOrder(false); resetOrderForm(); }} title="New Sales Order" size="xl">
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Customer</label>
              <select className="input-field" value={orderForm.customer_id} onChange={(e) => setOrderForm({ ...orderForm, customer_id: Number(e.target.value), ship_to_id: null })} required>
                <option value={0}>Select customer...</option>
                {custList.map(c => <option key={c.id} value={c.id}>{c.code} - {c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Ship To</label>
              <select className="input-field" value={orderForm.ship_to_id || ''} onChange={(e) => setOrderForm({ ...orderForm, ship_to_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">-- Select --</option>
                {shipToList.map(st => <option key={st.id} value={st.id}>{st.name} - {st.city}, {st.state}</option>)}
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
              <label className="block text-sm font-medium mb-1">Requested Ship Date</label>
              <input type="date" className="input-field" value={orderForm.requested_ship_date} onChange={(e) => setOrderForm({ ...orderForm, requested_ship_date: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">Notes</label>
              <input className="input-field" value={orderForm.notes} onChange={(e) => setOrderForm({ ...orderForm, notes: e.target.value })} />
            </div>
          </div>
          <h3 className="text-sm font-semibold text-gray-700">Line Items</h3>
          <table className="w-full text-sm">
            <thead><tr className="border-b"><th className="text-left py-1">#</th><th className="text-left py-1">Item</th><th className="text-right py-1">Qty</th><th className="text-right py-1">Price</th><th className="text-right py-1">Tax %</th><th className="text-right py-1">Total</th><th></th></tr></thead>
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
                  <td className="py-1"><input type="number" step="0.01" className="input-field text-sm text-right w-20" value={line.tax_rate || ''} onChange={(e) => updateLine(idx, 'tax_rate', Number(e.target.value))} /></td>
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
            <button type="button" className="btn-secondary" onClick={() => { setShowCreateOrder(false); resetOrderForm(); }}>Cancel</button>
            <button type="button" className="btn-primary" onClick={handleSubmitOrder} disabled={createOrder.isPending}>Create Order</button>
          </div>
        </div>
      </Modal>

      {/* Order Detail */}
      <Modal isOpen={showOrderDetail} onClose={() => { setShowOrderDetail(false); setSelectedOrder(null); }} title={`Order ${selectedOrder?.order_number || ''}`} size="lg">
        {selectedOrder && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div><span className="text-gray-500">Customer:</span> {custList.find(c => c.id === selectedOrder.customer_id)?.name}</div>
              <div><span className="text-gray-500">Status:</span> <span className={getStatusColor(selectedOrder.status)}>{selectedOrder.status}</span></div>
              <div><span className="text-gray-500">Total:</span> {formatCurrency(selectedOrder.total_amount)}</div>
            </div>
            <table className="w-full text-sm">
              <thead><tr className="border-b"><th className="text-left py-1">Item</th><th className="text-right py-1">Ordered</th><th className="text-right py-1">Shipped</th><th className="text-right py-1">Price</th><th className="text-right py-1">Total</th></tr></thead>
              <tbody>{selectedOrder.lines?.map(l => {
                const item = itemList.find(i => i.id === l.item_id);
                return <tr key={l.id} className="border-b"><td className="py-1">{item ? `${item.item_code} - ${item.name}` : `Item #${l.item_id}`}</td><td className="py-1 text-right">{l.quantity_ordered}</td><td className="py-1 text-right">{l.quantity_shipped}</td><td className="py-1 text-right">{formatCurrency(l.unit_price)}</td><td className="py-1 text-right">{formatCurrency(l.line_total)}</td></tr>;
              })}</tbody>
            </table>
            <div className="flex gap-3 justify-end">
              {selectedOrder.status !== 'invoiced' && selectedOrder.status !== 'cancelled' && (
                <>
                  <button className="btn-secondary text-sm" onClick={() => createPackingList.mutate(selectedOrder.id)}>Generate Packing List</button>
                  <button className="btn-primary text-sm" onClick={() => createInvoice.mutate(selectedOrder.id)}>Generate Invoice</button>
                </>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* Pick List */}
      <Modal isOpen={showPickList} onClose={() => { setShowPickList(false); setPickListData(null); }} title={`Pick List - ${pickListData?.order_number || ''}`} size="lg">
        {pickListData && (
          <div className="space-y-4">
            <div className="text-sm"><span className="text-gray-500">Customer:</span> {pickListData.customer_name} | <span className="text-gray-500">Ship Date:</span> {pickListData.requested_ship_date ? formatDate(pickListData.requested_ship_date) : '-'}</div>
            {pickListData.items?.map((item: any, idx: number) => (
              <div key={idx} className="border rounded-lg p-3">
                <div className="flex justify-between mb-2">
                  <span className="font-medium">{item.item_code} - {item.item_name}</span>
                  <span className="text-sm">Pick: <strong>{item.quantity_to_pick}</strong></span>
                </div>
                {item.lot_suggestions?.length > 0 ? (
                  <table className="w-full text-xs">
                    <thead><tr className="border-b"><th className="text-left py-1">Lot #</th><th className="text-right py-1">Available</th><th className="text-right py-1">Pick Qty</th><th className="text-left py-1">Expiration</th></tr></thead>
                    <tbody>{item.lot_suggestions.map((lot: any, li: number) => (
                      <tr key={li} className="border-b"><td className="py-1">{lot.lot_number}</td><td className="py-1 text-right">{lot.available_qty}</td><td className="py-1 text-right font-medium">{lot.suggested_pick_qty}</td><td className="py-1">{lot.expiration_date ? formatDate(lot.expiration_date) : '-'}</td></tr>
                    ))}</tbody>
                  </table>
                ) : <p className="text-xs text-red-500">No available lots</p>}
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SalesPage;
