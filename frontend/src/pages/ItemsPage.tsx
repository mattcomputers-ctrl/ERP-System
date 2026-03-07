import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { inventoryAPI, qualityAPI, manufacturingAPI, settingsAPI } from '../services/api';
import { formatCurrency } from '../utils/helpers';
import type { Item, ItemAlias, QCSpecification, Formula } from '../types';

const emptyItem = { item_code: '', name: '', item_type: 'raw_material', description: '', is_lot_tracked: true };

const ItemsPage: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | null>(null);
  const [form, setForm] = useState(emptyItem);
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [activeTab, setActiveTab] = useState<'aliases' | 'qc' | 'formulas' | 'pricing'>('aliases');
  const [showDetail, setShowDetail] = useState(false);
  const [aliasForm, setAliasForm] = useState({ alias_code: '', alias_name: '', alias_type: 'internal', notes: '' });
  const queryClient = useQueryClient();

  const { data: items } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: aliases } = useQuery({
    queryKey: ['aliases', selectedItem?.id], queryFn: () => inventoryAPI.listAliases(selectedItem!.id),
    enabled: !!selectedItem && showDetail && activeTab === 'aliases',
  });
  const { data: specs } = useQuery({
    queryKey: ['qc-specs', selectedItem?.id], queryFn: () => qualityAPI.listSpecifications({ item_id: selectedItem!.id }),
    enabled: !!selectedItem && showDetail && activeTab === 'qc',
  });
  const { data: formulas } = useQuery({
    queryKey: ['item-formulas'], queryFn: () => manufacturingAPI.listFormulas(),
    enabled: !!selectedItem && showDetail && activeTab === 'formulas',
  });
  const { data: priceLists } = useQuery({
    queryKey: ['price-lists', selectedItem?.id], queryFn: () => settingsAPI.listPriceLists({ item_id: selectedItem!.id }),
    enabled: !!selectedItem && showDetail && activeTab === 'pricing',
  });

  const saveItem = useMutation({
    mutationFn: (data: any) => editingItem ? inventoryAPI.updateItem(editingItem.id, data) : inventoryAPI.createItem(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['items'] }); closeForm(); toast.success(editingItem ? 'Item updated' : 'Item created'); },
    onError: () => toast.error('Failed to save item'),
  });

  const createAlias = useMutation({
    mutationFn: (data: any) => inventoryAPI.createAlias(selectedItem!.id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['aliases', selectedItem?.id] }); setAliasForm({ alias_code: '', alias_name: '', alias_type: 'internal', notes: '' }); toast.success('Alias created'); },
    onError: () => toast.error('Failed to create alias'),
  });

  const deleteAlias = useMutation({
    mutationFn: (aliasId: number) => inventoryAPI.deleteAlias(selectedItem!.id, aliasId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['aliases', selectedItem?.id] }); toast.success('Alias deleted'); },
  });

  const closeForm = () => { setShowForm(false); setEditingItem(null); setForm(emptyItem); };

  const openEdit = (item: Item) => {
    setEditingItem(item);
    setForm({ item_code: item.item_code, name: item.name, item_type: item.item_type, description: item.description || '', is_lot_tracked: item.is_lot_tracked });
    setShowForm(true);
  };

  const openDetail = (item: Item) => { setSelectedItem(item); setActiveTab('aliases'); setShowDetail(true); };

  const itemFormulas: Formula[] = (formulas?.data || []).filter((f: Formula) => f.product_item_id === selectedItem?.id);

  const columns = [
    { header: 'Code', accessor: 'item_code' as keyof Item },
    { header: 'Name', accessor: 'name' as keyof Item },
    { header: 'Type', accessor: ((row: Item) => <span className="badge-blue">{row.item_type.replace('_', ' ')}</span>) },
    { header: 'Lot Tracked', accessor: ((row: Item) => row.is_lot_tracked ? 'Yes' : 'No') },
    { header: 'Status', accessor: ((row: Item) => <span className={row.is_active ? 'badge-green' : 'badge-red'}>{row.is_active ? 'Active' : 'Inactive'}</span>) },
    { header: 'Actions', accessor: ((row: Item) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openEdit(row); }}>Edit</button>
        <button className="text-sm text-purple-600 hover:underline" onClick={(e) => { e.stopPropagation(); openDetail(row); }}>Details</button>
      </div>
    )) },
  ];

  const tabs = [
    { id: 'aliases' as const, label: 'Aliases' },
    { id: 'qc' as const, label: 'QC Specs' },
    { id: 'formulas' as const, label: 'Formulas' },
    { id: 'pricing' as const, label: 'Pricing' },
  ];

  return (
    <div>
      <PageHeader title="Items" subtitle="Manage items, aliases, QC specs, formulas, and pricing" actions={<button className="btn-primary" onClick={() => setShowForm(true)}>New Item</button>} />
      <div className="card"><DataTable columns={columns} data={items?.data || []} /></div>

      {/* Create/Edit Item */}
      <Modal isOpen={showForm} onClose={closeForm} title={editingItem ? 'Edit Item' : 'New Item'}>
        <form onSubmit={(e) => { e.preventDefault(); saveItem.mutate(form); }} className="space-y-4">
          <div><label className="block text-sm font-medium mb-1">Item Code</label><input className="input-field" value={form.item_code} onChange={(e) => setForm({ ...form, item_code: e.target.value })} required disabled={!!editingItem} /></div>
          <div><label className="block text-sm font-medium mb-1">Name</label><input className="input-field" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
          <div><label className="block text-sm font-medium mb-1">Type</label>
            <select className="input-field" value={form.item_type} onChange={(e) => setForm({ ...form, item_type: e.target.value })}>
              <option value="raw_material">Raw Material</option><option value="finished_good">Finished Good</option>
              <option value="packaging">Packaging</option><option value="intermediate">Intermediate</option><option value="consumable">Consumable</option>
            </select>
          </div>
          <div><label className="block text-sm font-medium mb-1">Description</label><textarea className="input-field" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="lot_tracked" checked={form.is_lot_tracked} onChange={(e) => setForm({ ...form, is_lot_tracked: e.target.checked })} />
            <label htmlFor="lot_tracked" className="text-sm">Lot Tracked</label>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={closeForm}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saveItem.isPending}>{editingItem ? 'Save' : 'Create'}</button>
          </div>
        </form>
      </Modal>

      {/* Item Detail */}
      <Modal isOpen={showDetail} onClose={() => { setShowDetail(false); setSelectedItem(null); }} title={`${selectedItem?.item_code} - ${selectedItem?.name || ''}`} size="xl">
        <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
          {tabs.map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === t.id ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>{t.label}</button>
          ))}
        </div>

        {activeTab === 'aliases' && (
          <div className="space-y-4">
            <div className="max-h-48 overflow-y-auto">
              {(aliases?.data || []).length === 0 ? <p className="text-gray-500 text-sm">No aliases.</p> : (
                <table className="w-full text-sm">
                  <thead><tr className="border-b"><th className="text-left py-1">Code</th><th className="text-left py-1">Name</th><th className="text-left py-1">Type</th><th></th></tr></thead>
                  <tbody>{(aliases?.data || []).map((a: ItemAlias) => (
                    <tr key={a.id} className="border-b"><td className="py-1">{a.alias_code}</td><td className="py-1">{a.alias_name || '-'}</td><td className="py-1"><span className="badge-blue">{a.alias_type}</span></td><td className="py-1"><button className="text-red-500 text-xs" onClick={() => deleteAlias.mutate(a.id)}>Remove</button></td></tr>
                  ))}</tbody>
                </table>
              )}
            </div>
            <hr />
            <form onSubmit={(e) => { e.preventDefault(); createAlias.mutate(aliasForm); }} className="space-y-3">
              <p className="text-sm font-medium">Add Alias</p>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="block text-xs mb-1">Code</label><input className="input-field" value={aliasForm.alias_code} onChange={(e) => setAliasForm({ ...aliasForm, alias_code: e.target.value })} required /></div>
                <div><label className="block text-xs mb-1">Name</label><input className="input-field" value={aliasForm.alias_name} onChange={(e) => setAliasForm({ ...aliasForm, alias_name: e.target.value })} /></div>
                <div><label className="block text-xs mb-1">Type</label>
                  <select className="input-field" value={aliasForm.alias_type} onChange={(e) => setAliasForm({ ...aliasForm, alias_type: e.target.value })}>
                    <option value="internal">Internal</option><option value="customer">Customer</option><option value="vendor">Vendor</option><option value="regulatory">Regulatory</option><option value="legacy">Legacy</option>
                  </select>
                </div>
                <div><label className="block text-xs mb-1">Notes</label><input className="input-field" value={aliasForm.notes} onChange={(e) => setAliasForm({ ...aliasForm, notes: e.target.value })} /></div>
              </div>
              <button type="submit" className="btn-primary text-sm">Add Alias</button>
            </form>
          </div>
        )}

        {activeTab === 'qc' && (
          <div className="space-y-3">
            {(specs?.data || []).length === 0 ? <p className="text-gray-500 text-sm">No QC specifications for this item.</p> : (
              (specs?.data || []).map((spec: QCSpecification) => (
                <div key={spec.id} className="border rounded-lg p-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium">{spec.name}</span>
                    <span className="badge-blue text-xs">{spec.spec_type}</span>
                  </div>
                  {spec.tests?.length > 0 && (
                    <table className="w-full text-sm">
                      <thead><tr className="border-b text-gray-500"><th className="text-left py-1">Test</th><th className="text-left py-1">Method</th><th className="text-right py-1">Target</th><th className="text-right py-1">Min</th><th className="text-right py-1">Max</th><th className="text-left py-1">UOM</th></tr></thead>
                      <tbody>{spec.tests.map(t => (
                        <tr key={t.id} className="border-b"><td className="py-1">{t.test_name}</td><td className="py-1">{t.test_method || '-'}</td><td className="py-1 text-right">{t.target_value ?? '-'}</td><td className="py-1 text-right">{t.min_value ?? '-'}</td><td className="py-1 text-right">{t.max_value ?? '-'}</td><td className="py-1">{t.uom || '-'}</td></tr>
                      ))}</tbody>
                    </table>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'formulas' && (
          <div className="space-y-3">
            {itemFormulas.length === 0 ? <p className="text-gray-500 text-sm">No formulas for this item.</p> : (
              itemFormulas.map(f => {
                const currentVersion = f.versions?.find(v => v.is_current);
                return (
                  <div key={f.id} className="border rounded-lg p-3">
                    <div className="flex justify-between items-center mb-2">
                      <div><span className="font-medium">{f.code}</span> - {f.name}</div>
                      <span className={f.is_active ? 'badge-green' : 'badge-red'}>{f.is_active ? 'Active' : 'Inactive'}</span>
                    </div>
                    {currentVersion && (
                      <div className="text-sm text-gray-600">
                        <div>Version {currentVersion.version_number} | Batch Size: {currentVersion.batch_size} | Yield: {currentVersion.expected_yield_percent}%</div>
                        <div>{currentVersion.ingredients?.length || 0} ingredients</div>
                        {currentVersion.instructions && (
                          <div className="mt-2 bg-gray-50 p-2 rounded text-xs">
                            <span className="font-medium">Instructions:</span>
                            <pre className="whitespace-pre-wrap mt-1">{currentVersion.instructions}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        {activeTab === 'pricing' && (
          <div className="space-y-3">
            {(priceLists?.data || []).length === 0 ? <p className="text-gray-500 text-sm">No pricing data for this item.</p> : (
              <table className="w-full text-sm">
                <thead><tr className="border-b"><th className="text-left py-1">Type</th><th className="text-left py-1">Entity ID</th><th className="text-right py-1">Price</th><th className="text-right py-1">Min Qty</th><th className="text-left py-1">Status</th></tr></thead>
                <tbody>{(priceLists?.data || []).map((pl: any) => (
                  <tr key={pl.id} className="border-b"><td className="py-1"><span className="badge-blue">{pl.price_type}</span></td><td className="py-1">{pl.entity_id}</td><td className="py-1 text-right">{formatCurrency(pl.unit_price)}</td><td className="py-1 text-right">{pl.min_quantity}</td><td className="py-1">{pl.is_active ? <span className="badge-green">Active</span> : <span className="badge-red">Inactive</span>}</td></tr>
                ))}</tbody>
              </table>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ItemsPage;
