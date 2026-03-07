import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { inventoryAPI } from '../services/api';
import { getStatusColor, formatDate } from '../utils/helpers';
import type { Item, Lot } from '../types';

const InventoryPage: React.FC = () => {
  const [tab, setTab] = useState<'items' | 'lots' | 'warehouses'>('items');
  const [showCreateItem, setShowCreateItem] = useState(false);
  const [itemForm, setItemForm] = useState({ item_code: '', name: '', item_type: 'raw_material', description: '' });
  const queryClient = useQueryClient();

  const { data: items, isLoading: itemsLoading } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: lots } = useQuery({ queryKey: ['lots'], queryFn: () => inventoryAPI.listLots() });
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: () => inventoryAPI.listWarehouses() });

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
  ];

  const lotColumns = [
    { header: 'Lot #', accessor: 'lot_number' as keyof Lot },
    { header: 'Qty On Hand', accessor: ((row: Lot) => row.quantity_on_hand.toFixed(2)) },
    { header: 'Allocated', accessor: ((row: Lot) => row.quantity_allocated.toFixed(2)) },
    { header: 'Status', accessor: ((row: Lot) => <span className={getStatusColor(row.status)}>{row.status}</span>) },
    { header: 'Expiration', accessor: ((row: Lot) => formatDate(row.expiration_date)) },
    { header: 'Received', accessor: ((row: Lot) => formatDate(row.received_date)) },
  ];

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
        {tab === 'items' && <DataTable columns={itemColumns} data={items?.data || []} />}
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
    </div>
  );
};

export default InventoryPage;
