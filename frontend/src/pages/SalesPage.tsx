import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { salesAPI } from '../services/api';
import { getStatusColor, formatDate, formatCurrency } from '../utils/helpers';
import type { SalesOrder, Customer } from '../types';

const SalesPage: React.FC = () => {
  const [tab, setTab] = useState<'orders' | 'customers'>('orders');
  const [showCreateCustomer, setShowCreateCustomer] = useState(false);
  const [custForm, setCustForm] = useState({ code: '', name: '', contact_name: '', email: '', phone: '', payment_terms: 'Net 30' });
  const queryClient = useQueryClient();

  const { data: orders } = useQuery({ queryKey: ['sales-orders'], queryFn: () => salesAPI.listOrders() });
  const { data: customers } = useQuery({ queryKey: ['customers'], queryFn: () => salesAPI.listCustomers() });

  const createCustomer = useMutation({
    mutationFn: (data: any) => salesAPI.createCustomer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] });
      setShowCreateCustomer(false);
      toast.success('Customer created');
    },
    onError: () => toast.error('Failed to create customer'),
  });

  const orderColumns = [
    { header: 'Order #', accessor: 'order_number' as keyof SalesOrder },
    { header: 'Date', accessor: ((row: SalesOrder) => formatDate(row.order_date)) },
    { header: 'Ship Date', accessor: ((row: SalesOrder) => formatDate(row.requested_ship_date)) },
    { header: 'Status', accessor: ((row: SalesOrder) => <span className={getStatusColor(row.status)}>{row.status}</span>) },
    { header: 'Total', accessor: ((row: SalesOrder) => formatCurrency(row.total_amount)) },
  ];

  const customerColumns = [
    { header: 'Code', accessor: 'code' as keyof Customer },
    { header: 'Name', accessor: 'name' as keyof Customer },
    { header: 'Contact', accessor: 'contact_name' as keyof Customer },
    { header: 'Email', accessor: 'email' as keyof Customer },
    { header: 'Phone', accessor: 'phone' as keyof Customer },
    { header: 'Status', accessor: ((row: Customer) => <span className={row.is_active ? 'badge-green' : 'badge-red'}>{row.is_active ? 'Active' : 'Inactive'}</span>) },
  ];

  return (
    <div>
      <PageHeader
        title="Sales Management"
        subtitle="Manage customers, sales orders, shipments, and invoices"
        actions={
          <button className="btn-primary" onClick={() => setShowCreateCustomer(true)}>New Customer</button>
        }
      />

      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {(['orders', 'customers'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <div className="card">
        {tab === 'orders' && <DataTable columns={orderColumns} data={orders?.data || []} />}
        {tab === 'customers' && <DataTable columns={customerColumns} data={customers?.data || []} />}
      </div>

      <Modal isOpen={showCreateCustomer} onClose={() => setShowCreateCustomer(false)} title="Create Customer">
        <form onSubmit={(e) => { e.preventDefault(); createCustomer.mutate(custForm); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Code</label>
              <input className="input-field" value={custForm.code} onChange={(e) => setCustForm({ ...custForm, code: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input className="input-field" value={custForm.name} onChange={(e) => setCustForm({ ...custForm, name: e.target.value })} required />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Contact</label>
              <input className="input-field" value={custForm.contact_name} onChange={(e) => setCustForm({ ...custForm, contact_name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input className="input-field" type="email" value={custForm.email} onChange={(e) => setCustForm({ ...custForm, email: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Phone</label>
              <input className="input-field" value={custForm.phone} onChange={(e) => setCustForm({ ...custForm, phone: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Payment Terms</label>
              <input className="input-field" value={custForm.payment_terms} onChange={(e) => setCustForm({ ...custForm, payment_terms: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setShowCreateCustomer(false)}>Cancel</button>
            <button type="submit" className="btn-primary">Create</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default SalesPage;
