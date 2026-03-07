import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { inventoryAPI } from '../services/api';
import { getStatusColor, formatDate } from '../utils/helpers';
import type { Item, Lot, ItemAlias, PackComponent } from '../types';

const InventoryPage: React.FC = () => {
  const [tab, setTab] = useState<'items' | 'lots' | 'warehouses'>('items');
  const [showCreateItem, setShowCreateItem] = useState(false);
  const [itemForm, setItemForm] = useState({ item_code: '', name: '', item_type: 'raw_material', description: '' });
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [showAliases, setShowAliases] = useState(false);
  const [showPackComponents, setShowPackComponents] = useState(false);
  const [aliasForm, setAliasForm] = useState({ alias_code: '', alias_name: '', alias_type: 'internal', notes: '' });
  const [packForm, setPackForm] = useState({ component_item_id: 0, quantity: 0, sequence: 0, notes: '' });
  const queryClient = useQueryClient();

  const { data: items } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: lots } = useQuery({ queryKey: ['lots'], queryFn: () => inventoryAPI.listLots() });
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: () => inventoryAPI.listWarehouses() });

  const { data: aliases } = useQuery({
    queryKey: ['aliases', selectedItem?.id],
    queryFn: () => inventoryAPI.listAliases(selectedItem!.id),
    enabled: !!selectedItem && showAliases,
  });

  const { data: packComponents } = useQuery({
    queryKey: ['pack-components', selectedItem?.id],
    queryFn: () => inventoryAPI.listPackComponents(selectedItem!.id),
    enabled: !!selectedItem && showPackComponents,
  });

  const createItem = useMutation({
    mutationFn: (data: any) => inventoryAPI.createItem(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      setShowCreateItem(false);
      setItemForm({ item_code: '', name: '', item_type: 'raw_material', description: '' });
      toast.success('Item created');
    },
    onError: () => toast.error('Failed to create item'),
  });

  const createAlias = useMutation({
    mutationFn: (data: any) => inventoryAPI.createAlias(selectedItem!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['aliases', selectedItem?.id] });
      setAliasForm({ alias_code: '', alias_name: '', alias_type: 'internal', notes: '' });
      toast.success('Alias created');
    },
    onError: () => toast.error('Failed to create alias'),
  });

  const deleteAlias = useMutation({
    mutationFn: (aliasId: number) => inventoryAPI.deleteAlias(selectedItem!.id, aliasId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['aliases', selectedItem?.id] });
      toast.success('Alias deleted');
    },
  });

  const addPackComponent = useMutation({
    mutationFn: (data: any) => inventoryAPI.addPackComponent(selectedItem!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pack-components', selectedItem?.id] });
      setPackForm({ component_item_id: 0, quantity: 0, sequence: 0, notes: '' });
      toast.success('Component added');
    },
    onError: () => toast.error('Failed to add component'),
  });

  const deletePackComponent = useMutation({
    mutationFn: (componentId: number) => inventoryAPI.deletePackComponent(selectedItem!.id, componentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pack-components', selectedItem?.id] });
      toast.success('Component removed');
    },
  });

  const tabs = [
    { id: 'items', label: 'Items' },
    { id: 'lots', label: 'Lots' },
    { id: 'warehouses', label: 'Warehouses' },
  ] as const;

  const itemColumns = [
    { header: 'Code', accessor: 'item_code' as keyof Item },
    { header: 'Name', accessor: 'name' as keyof Item },
    { header: 'Type', accessor: ((row: Item) => <span className="badge-blue">{row.item_type.replace('_', ' ')}</span>) },
    { header: 'Lot Tracked', accessor: ((row: Item) => row.is_lot_tracked ? 'Yes' : 'No') },
    { header: 'Status', accessor: ((row: Item) => <span className={row.is_active ? 'badge-green' : 'badge-red'}>{row.is_active ? 'Active' : 'Inactive'}</span>) },
    { header: 'Actions', accessor: ((row: Item) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); setSelectedItem(row); setShowAliases(true); }}>Aliases</button>
        <button className="text-sm text-purple-600 hover:underline" onClick={(e) => { e.stopPropagation(); setSelectedItem(row); setShowPackComponents(true); }}>Pack</button>
      </div>
    )) },
  ];

  const lotColumns = [
    { header: 'Lot #', accessor: 'lot_number' as keyof Lot },
    { header: 'Qty On Hand', accessor: ((row: Lot) => row.quantity_on_hand.toFixed(2)) },
    { header: 'Allocated', accessor: ((row: Lot) => row.quantity_allocated.toFixed(2)) },
    { header: 'Status', accessor: ((row: Lot) => <span className={getStatusColor(row.status)}>{row.status}</span>) },
    { header: 'Expiration', accessor: ((row: Lot) => formatDate(row.expiration_date)) },
    { header: 'Received', accessor: ((row: Lot) => formatDate(row.received_date)) },
  ];

  const allItems = items?.data || [];

  return (
    <div>
      <PageHeader
        title="Inventory Management"
        subtitle="Manage items, lots, and warehouses"
        actions={
          <button className="btn-primary" onClick={() => setShowCreateItem(true)}>New Item</button>
        }
      />

      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === t.id ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="card">
        {tab === 'items' && <DataTable columns={itemColumns} data={allItems} />}
        {tab === 'lots' && <DataTable columns={lotColumns} data={lots?.data || []} />}
        {tab === 'warehouses' && (
          <DataTable
            columns={[
              { header: 'Code', accessor: 'code' },
              { header: 'Name', accessor: 'name' },
              { header: 'Address', accessor: 'address' },
              { header: 'Status', accessor: (row: any) => <span className={row.is_active ? 'badge-green' : 'badge-red'}>{row.is_active ? 'Active' : 'Inactive'}</span> },
            ]}
            data={warehouses?.data || []}
          />
        )}
      </div>

      {/* Create Item Modal */}
      <Modal isOpen={showCreateItem} onClose={() => setShowCreateItem(false)} title="Create New Item">
        <form onSubmit={(e) => { e.preventDefault(); createItem.mutate(itemForm); }} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Item Code</label>
            <input className="input-field" value={itemForm.item_code} onChange={(e) => setItemForm({ ...itemForm, item_code: e.target.value })} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input className="input-field" value={itemForm.name} onChange={(e) => setItemForm({ ...itemForm, name: e.target.value })} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Type</label>
            <select className="input-field" value={itemForm.item_type} onChange={(e) => setItemForm({ ...itemForm, item_type: e.target.value })}>
              <option value="raw_material">Raw Material</option>
              <option value="finished_good">Finished Good</option>
              <option value="packaging">Packaging</option>
              <option value="intermediate">Intermediate</option>
              <option value="consumable">Consumable</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea className="input-field" rows={3} value={itemForm.description} onChange={(e) => setItemForm({ ...itemForm, description: e.target.value })} />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setShowCreateItem(false)}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={createItem.isPending}>Create</button>
          </div>
        </form>
      </Modal>

      {/* Aliases Modal */}
      <Modal isOpen={showAliases} onClose={() => { setShowAliases(false); setSelectedItem(null); }} title={`Aliases - ${selectedItem?.item_code || ''}`}>
        <div className="space-y-4">
          <div className="max-h-60 overflow-y-auto">
            {(aliases?.data || []).length === 0 ? (
              <p className="text-gray-500 text-sm">No aliases defined.</p>
            ) : (
              <table className="w-full text-sm">
                <thead><tr className="border-b"><th className="text-left py-1">Code</th><th className="text-left py-1">Name</th><th className="text-left py-1">Type</th><th className="py-1"></th></tr></thead>
                <tbody>
                  {(aliases?.data || []).map((a: ItemAlias) => (
                    <tr key={a.id} className="border-b">
                      <td className="py-1">{a.alias_code}</td>
                      <td className="py-1">{a.alias_name || '-'}</td>
                      <td className="py-1"><span className="badge-blue">{a.alias_type}</span></td>
                      <td className="py-1"><button className="text-red-500 hover:underline text-xs" onClick={() => deleteAlias.mutate(a.id)}>Remove</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <hr />
          <form onSubmit={(e) => { e.preventDefault(); createAlias.mutate(aliasForm); }} className="space-y-3">
            <p className="text-sm font-medium">Add Alias</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs mb-1">Alias Code</label>
                <input className="input-field" value={aliasForm.alias_code} onChange={(e) => setAliasForm({ ...aliasForm, alias_code: e.target.value })} required />
              </div>
              <div>
                <label className="block text-xs mb-1">Alias Name</label>
                <input className="input-field" value={aliasForm.alias_name} onChange={(e) => setAliasForm({ ...aliasForm, alias_name: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs mb-1">Type</label>
                <select className="input-field" value={aliasForm.alias_type} onChange={(e) => setAliasForm({ ...aliasForm, alias_type: e.target.value })}>
                  <option value="internal">Internal</option>
                  <option value="customer">Customer</option>
                  <option value="vendor">Vendor</option>
                  <option value="regulatory">Regulatory</option>
                  <option value="legacy">Legacy</option>
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1">Notes</label>
                <input className="input-field" value={aliasForm.notes} onChange={(e) => setAliasForm({ ...aliasForm, notes: e.target.value })} />
              </div>
            </div>
            <button type="submit" className="btn-primary text-sm" disabled={createAlias.isPending}>Add Alias</button>
          </form>
        </div>
      </Modal>

      {/* Pack Components Modal */}
      <Modal isOpen={showPackComponents} onClose={() => { setShowPackComponents(false); setSelectedItem(null); }} title={`Pack Components - ${selectedItem?.item_code || ''}`}>
        <div className="space-y-4">
          <div className="max-h-60 overflow-y-auto">
            {(packComponents?.data || []).length === 0 ? (
              <p className="text-gray-500 text-sm">No pack components defined.</p>
            ) : (
              <table className="w-full text-sm">
                <thead><tr className="border-b"><th className="text-left py-1">Seq</th><th className="text-left py-1">Component</th><th className="text-left py-1">Qty</th><th className="py-1"></th></tr></thead>
                <tbody>
                  {(packComponents?.data || []).map((c: PackComponent) => {
                    const compItem = allItems.find((i: Item) => i.id === c.component_item_id);
                    return (
                      <tr key={c.id} className="border-b">
                        <td className="py-1">{c.sequence}</td>
                        <td className="py-1">{compItem ? `${compItem.item_code} - ${compItem.name}` : `Item #${c.component_item_id}`}</td>
                        <td className="py-1">{c.quantity}</td>
                        <td className="py-1"><button className="text-red-500 hover:underline text-xs" onClick={() => deletePackComponent.mutate(c.id)}>Remove</button></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
          <hr />
          <form onSubmit={(e) => { e.preventDefault(); addPackComponent.mutate(packForm); }} className="space-y-3">
            <p className="text-sm font-medium">Add Component</p>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs mb-1">Component Item</label>
                <select className="input-field" value={packForm.component_item_id} onChange={(e) => setPackForm({ ...packForm, component_item_id: Number(e.target.value) })} required>
                  <option value={0}>Select item...</option>
                  {allItems.filter((i: Item) => i.id !== selectedItem?.id).map((i: Item) => (
                    <option key={i.id} value={i.id}>{i.item_code} - {i.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1">Quantity</label>
                <input type="number" step="0.0001" className="input-field" value={packForm.quantity || ''} onChange={(e) => setPackForm({ ...packForm, quantity: Number(e.target.value) })} required />
              </div>
              <div>
                <label className="block text-xs mb-1">Sequence</label>
                <input type="number" className="input-field" value={packForm.sequence} onChange={(e) => setPackForm({ ...packForm, sequence: Number(e.target.value) })} />
              </div>
            </div>
            <button type="submit" className="btn-primary text-sm" disabled={addPackComponent.isPending}>Add Component</button>
          </form>
        </div>
      </Modal>
    </div>
  );
};

export default InventoryPage;
