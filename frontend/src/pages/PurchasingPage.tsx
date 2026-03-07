import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { purchasingAPI } from '../services/api';
import { getStatusColor, formatDate, formatCurrency } from '../utils/helpers';
import type { PurchaseOrder, Vendor } from '../types';

const PurchasingPage: React.FC = () => {
  const [tab, setTab] = useState<'orders' | 'vendors'>('orders');
  const [showCreateVendor, setShowCreateVendor] = useState(false);
  const [vendorForm, setVendorForm] = useState({ code: '', name: '', contact_name: '', email: '', phone: '', payment_terms: 'Net 30' });
  const queryClient = useQueryClient();

  const { data: orders } = useQuery({ queryKey: ['purchase-orders'], queryFn: () => purchasingAPI.listOrders() });
  const { data: vendors } = useQuery({ queryKey: ['vendors'], queryFn: () => purchasingAPI.listVendors() });

  const createVendor = useMutation({
    mutationFn: (data: any) => purchasingAPI.createVendor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      setShowCreateVendor(false);
      toast.success('Vendor created');
    },
    onError: () => toast.error('Failed to create vendor'),
  });

  const orderColumns = [
    { header: 'PO #', accessor: 'po_number' as keyof PurchaseOrder },
    { header: 'Date', accessor: ((row: PurchaseOrder) => formatDate(row.order_date)) },
    { header: 'Expected', accessor: ((row: PurchaseOrder) => formatDate(row.expected_delivery_date)) },
    { header: 'Status', accessor: ((row: PurchaseOrder) => <span className={getStatusColor(row.status)}>{row.status}</span>) },
    { header: 'Total', accessor: ((row: PurchaseOrder) => formatCurrency(row.total_amount)) },
  ];

  const vendorColumns = [
    { header: 'Code', accessor: 'code' as keyof Vendor },
    { header: 'Name', accessor: 'name' as keyof Vendor },
    { header: 'Contact', accessor: 'contact_name' as keyof Vendor },
    { header: 'Email', accessor: 'email' as keyof Vendor },
    { header: 'Phone', accessor: 'phone' as keyof Vendor },
  ];

  return (
    <div>
      <PageHeader
        title="Purchasing"
        subtitle="Manage vendors, purchase orders, and receiving"
        actions={<button className="btn-primary" onClick={() => setShowCreateVendor(true)}>New Vendor</button>}
      />

      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {(['orders', 'vendors'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {t === 'orders' ? 'Purchase Orders' : 'Vendors'}
          </button>
        ))}
      </div>

      <div className="card">
        {tab === 'orders' && <DataTable columns={orderColumns} data={orders?.data || []} />}
        {tab === 'vendors' && <DataTable columns={vendorColumns} data={vendors?.data || []} />}
      </div>

      <Modal isOpen={showCreateVendor} onClose={() => setShowCreateVendor(false)} title="Create Vendor">
        <form onSubmit={(e) => { e.preventDefault(); createVendor.mutate(vendorForm); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Code</label>
              <input className="input-field" value={vendorForm.code} onChange={(e) => setVendorForm({ ...vendorForm, code: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input className="input-field" value={vendorForm.name} onChange={(e) => setVendorForm({ ...vendorForm, name: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Contact</label>
              <input className="input-field" value={vendorForm.contact_name} onChange={(e) => setVendorForm({ ...vendorForm, contact_name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input className="input-field" type="email" value={vendorForm.email} onChange={(e) => setVendorForm({ ...vendorForm, email: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Phone</label>
              <input className="input-field" value={vendorForm.phone} onChange={(e) => setVendorForm({ ...vendorForm, phone: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Payment Terms</label>
              <input className="input-field" value={vendorForm.payment_terms} onChange={(e) => setVendorForm({ ...vendorForm, payment_terms: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setShowCreateVendor(false)}>Cancel</button>
            <button type="submit" className="btn-primary">Create</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default PurchasingPage;
