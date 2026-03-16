import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { inventoryAPI } from '../services/api';
import type { InventorySummaryRow, Item, Warehouse, PackExtensionDefinition } from '../types';

type InventoryTab = 'on-hand' | 'adjustments';

const InventoryPage: React.FC = () => {
  const [tab, setTab] = useState<InventoryTab>('on-hand');
  const [warehouseFilter, setWarehouseFilter] = useState<string>('');
  const [showAdjustForm, setShowAdjustForm] = useState(false);
  const [adjForm, setAdjForm] = useState({
    item_id: 0,
    pack_extension_id: null as number | null,
    warehouse_id: null as number | null,
    quantity: '',
    unit_cost: '',
    reason: '',
  });

  const queryClient = useQueryClient();

  // --- Data queries ---
  const { data: summary } = useQuery({
    queryKey: ['inventory-summary', warehouseFilter],
    queryFn: () => inventoryAPI.getInventorySummary(warehouseFilter ? { warehouse_id: Number(warehouseFilter) } : undefined),
  });
  const { data: items } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: () => inventoryAPI.listWarehouses() });
  const { data: transactions } = useQuery({
    queryKey: ['inventory-transactions'],
    queryFn: () => inventoryAPI.listTransactions({ transaction_type: 'adjustment' }),
    enabled: tab === 'adjustments',
  });
  const { data: packExtDefs } = useQuery({ queryKey: ['pack-extension-definitions'], queryFn: () => inventoryAPI.listPackExtensionDefinitions() });

  const summaryRows: InventorySummaryRow[] = summary?.data || [];
  const itemList: Item[] = items?.data || [];
  const warehouseList: Warehouse[] = warehouses?.data || [];
  const packExtList: PackExtensionDefinition[] = packExtDefs?.data || [];
  const txnList = transactions?.data || [];

  // Get available pack extensions for selected item
  const selectedItem = itemList.find(i => i.id === adjForm.item_id);
  const itemPackExts = selectedItem
    ? packExtList.filter(pe => {
        // Show all pack extensions that are assigned to this item
        // For simplicity, show all active pack extensions
        return pe.is_active;
      })
    : [];

  // --- Mutations ---
  const createAdjustment = useMutation({
    mutationFn: (data: any) => inventoryAPI.createAdjustment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-summary'] });
      queryClient.invalidateQueries({ queryKey: ['inventory-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['lots'] });
      setShowAdjustForm(false);
      setAdjForm({ item_id: 0, pack_extension_id: null, warehouse_id: null, quantity: '', unit_cost: '', reason: '' });
      toast.success('Adjustment created');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to create adjustment'),
  });

  const handleAdjustSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!adjForm.item_id) { toast.error('Select an item'); return; }
    if (!adjForm.quantity) { toast.error('Enter a quantity'); return; }
    createAdjustment.mutate({
      item_id: adjForm.item_id,
      pack_extension_id: adjForm.pack_extension_id || null,
      warehouse_id: adjForm.warehouse_id || null,
      quantity: Number(adjForm.quantity),
      unit_cost: adjForm.unit_cost ? Number(adjForm.unit_cost) : null,
      reason: adjForm.reason || null,
    });
  };

  // --- Column definitions ---
  const adjustmentColumns = [
    { header: 'Date', accessor: ((row: any) => {
      const d = new Date(row.created_at);
      return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }) },
    { header: 'Item', accessor: ((row: any) => {
      const item = itemList.find(i => i.id === row.item_id);
      return item ? `${item.item_code} - ${item.name}` : `Item #${row.item_id}`;
    }) },
    { header: 'Quantity', accessor: ((row: any) => (
      <span className={Number(row.quantity) >= 0 ? 'text-green-600' : 'text-red-600'}>
        {Number(row.quantity) >= 0 ? '+' : ''}{Number(row.quantity).toFixed(2)}
      </span>
    )) },
    { header: 'Unit Cost', accessor: ((row: any) => row.unit_cost != null ? `$${Number(row.unit_cost).toFixed(4)}` : '-') },
    { header: 'Reason', accessor: ((row: any) => row.notes || '-') },
  ];

  const tabs: { id: InventoryTab; label: string }[] = [
    { id: 'on-hand', label: 'On Hand' },
    { id: 'adjustments', label: 'Adjustments' },
  ];

  return (
    <div>
      <PageHeader
        title="Inventory"
        subtitle="View current inventory levels and make adjustments"
        actions={
          tab === 'adjustments'
            ? <button className="btn-primary" onClick={() => setShowAdjustForm(true)}>New Adjustment</button>
            : undefined
        }
      />

      <div className="flex items-center gap-4 mb-4">
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === t.id ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>{t.label}</button>
          ))}
        </div>

        {tab === 'on-hand' && (
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-500">Warehouse:</label>
            <select className="input-field w-48" value={warehouseFilter} onChange={(e) => setWarehouseFilter(e.target.value)}>
              <option value="">All Warehouses</option>
              {warehouseList.map(w => <option key={w.id} value={w.id}>{w.code} - {w.name}</option>)}
            </select>
          </div>
        )}
      </div>

      {/* ======== ON HAND TAB ======== */}
      {tab === 'on-hand' && (
        <div className="card">
          {summaryRows.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">No inventory on hand.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="table-header">Warehouse</th>
                    <th className="table-header">Item Code</th>
                    <th className="table-header">Description</th>
                    <th className="table-header">Qty on Hand</th>
                    <th className="table-header">GL Group</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {summaryRows.map((row, i) => (
                    <tr key={i}>
                      <td className="table-cell">{row.warehouse_name}</td>
                      <td className="table-cell font-mono">{row.item_code}</td>
                      <td className="table-cell">
                        {row.item_name}
                        {row.pack_extension_name && <span className="text-gray-400 text-xs ml-1">({row.pack_extension_name})</span>}
                      </td>
                      <td className="table-cell">
                        {row.qty_on_hand.toFixed(2)} <span className="text-gray-400 text-xs">{row.uom_abbreviation}</span>
                      </td>
                      <td className="table-cell">{row.gl_group_name || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ======== ADJUSTMENTS TAB ======== */}
      {tab === 'adjustments' && (
        <div className="card">
          {txnList.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">No adjustments recorded.</p>
          ) : (
            <DataTable columns={adjustmentColumns} data={txnList} />
          )}
        </div>
      )}

      {/* Adjustment Form Modal */}
      <Modal isOpen={showAdjustForm} onClose={() => setShowAdjustForm(false)} title="New Inventory Adjustment">
        <form onSubmit={handleAdjustSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Item</label>
            <select className="input-field" value={adjForm.item_id || ''} onChange={(e) => setAdjForm({ ...adjForm, item_id: Number(e.target.value), pack_extension_id: null })} required>
              <option value="">-- Select Item --</option>
              {itemList.filter(i => i.is_active).map(i => (
                <option key={i.id} value={i.id}>{i.item_code} - {i.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Pack Extension (optional)</label>
            <select className="input-field" value={adjForm.pack_extension_id || ''} onChange={(e) => setAdjForm({ ...adjForm, pack_extension_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">Bulk (no extension)</option>
              {itemPackExts.map(pe => (
                <option key={pe.id} value={pe.id}>{pe.code} - {pe.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Warehouse</label>
            <select className="input-field" value={adjForm.warehouse_id || ''} onChange={(e) => setAdjForm({ ...adjForm, warehouse_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">-- Select Warehouse --</option>
              {warehouseList.map(w => (
                <option key={w.id} value={w.id}>{w.code} - {w.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Quantity</label>
              <input type="number" step="0.0001" className="input-field" value={adjForm.quantity} onChange={(e) => setAdjForm({ ...adjForm, quantity: e.target.value })} required placeholder="Positive to add, negative to remove" />
              <p className="text-xs text-gray-400 mt-1">Use negative values to reduce inventory</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Unit Cost</label>
              <input type="number" step="0.000001" className="input-field" value={adjForm.unit_cost} onChange={(e) => setAdjForm({ ...adjForm, unit_cost: e.target.value })} placeholder="Optional" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Reason</label>
            <textarea className="input-field" rows={2} value={adjForm.reason} onChange={(e) => setAdjForm({ ...adjForm, reason: e.target.value })} placeholder="Reason for adjustment" />
          </div>

          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setShowAdjustForm(false)}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={createAdjustment.isPending}>Create Adjustment</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default InventoryPage;
