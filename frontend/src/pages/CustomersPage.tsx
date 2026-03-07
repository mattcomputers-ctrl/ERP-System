import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { salesAPI, settingsAPI } from '../services/api';
import type { Customer, ShipTo } from '../types';

const emptyCustomer = {
  code: '', name: '', contact_name: '', email: '', phone: '',
  billing_address_line1: '', billing_address_line2: '', billing_city: '', billing_state: '', billing_postal_code: '', billing_country: 'US',
  payment_terms: 'Net 30', tax_exempt: false,
};

const emptyShipTo = {
  customer_id: 0, name: '', address_line1: '', address_line2: '', city: '', state: '', postal_code: '', country: 'US',
  contact_name: '', phone: '', is_default: false,
};

const CustomersPage: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [form, setForm] = useState(emptyCustomer);
  const [showShipTos, setShowShipTos] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [showShipToForm, setShowShipToForm] = useState(false);
  const [shipToForm, setShipToForm] = useState(emptyShipTo);
  const [editingShipTo, setEditingShipTo] = useState<ShipTo | null>(null);
  const queryClient = useQueryClient();

  const { data: customers } = useQuery({ queryKey: ['customers'], queryFn: () => salesAPI.listCustomers() });

  const { data: shipTos } = useQuery({
    queryKey: ['ship-tos', selectedCustomer?.id],
    queryFn: () => settingsAPI.listShipTos({ customer_id: selectedCustomer!.id }),
    enabled: !!selectedCustomer && showShipTos,
  });

  const saveCust = useMutation({
    mutationFn: (data: any) => editingCustomer ? salesAPI.updateCustomer(editingCustomer.id, data) : salesAPI.createCustomer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] });
      closeForm();
      toast.success(editingCustomer ? 'Customer updated' : 'Customer created');
    },
    onError: () => toast.error('Failed to save customer'),
  });

  const saveShipTo = useMutation({
    mutationFn: (data: any) => editingShipTo ? settingsAPI.updateShipTo(editingShipTo.id, data) : settingsAPI.createShipTo(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ship-tos', selectedCustomer?.id] });
      setShowShipToForm(false);
      setEditingShipTo(null);
      setShipToForm(emptyShipTo);
      toast.success(editingShipTo ? 'Ship-To updated' : 'Ship-To created');
    },
    onError: () => toast.error('Failed to save Ship-To'),
  });

  const closeForm = () => { setShowForm(false); setEditingCustomer(null); setForm(emptyCustomer); };

  const openEdit = (c: Customer) => {
    setEditingCustomer(c);
    setForm({
      code: c.code, name: c.name, contact_name: c.contact_name || '', email: c.email || '', phone: c.phone || '',
      billing_address_line1: c.billing_address_line1 || '', billing_address_line2: c.billing_address_line2 || '',
      billing_city: c.billing_city || '', billing_state: c.billing_state || '', billing_postal_code: c.billing_postal_code || '',
      billing_country: c.billing_country || 'US', payment_terms: c.payment_terms || '', tax_exempt: c.tax_exempt,
    });
    setShowForm(true);
  };

  const openShipTos = (c: Customer) => { setSelectedCustomer(c); setShowShipTos(true); };

  const openShipToEdit = (st: ShipTo) => {
    setEditingShipTo(st);
    setShipToForm({
      customer_id: st.customer_id, name: st.name, address_line1: st.address_line1 || '', address_line2: st.address_line2 || '',
      city: st.city || '', state: st.state || '', postal_code: st.postal_code || '', country: st.country || 'US',
      contact_name: st.contact_name || '', phone: st.phone || '', is_default: st.is_default,
    });
    setShowShipToForm(true);
  };

  const columns = [
    { header: 'Code', accessor: 'code' as keyof Customer },
    { header: 'Name', accessor: 'name' as keyof Customer },
    { header: 'Contact', accessor: 'contact_name' as keyof Customer },
    { header: 'Email', accessor: 'email' as keyof Customer },
    { header: 'Phone', accessor: 'phone' as keyof Customer },
    { header: 'Terms', accessor: 'payment_terms' as keyof Customer },
    { header: 'Status', accessor: ((row: Customer) => <span className={row.is_active ? 'badge-green' : 'badge-red'}>{row.is_active ? 'Active' : 'Inactive'}</span>) },
    { header: 'Actions', accessor: ((row: Customer) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openEdit(row); }}>Edit</button>
        <button className="text-sm text-purple-600 hover:underline" onClick={(e) => { e.stopPropagation(); openShipTos(row); }}>Ship-To</button>
      </div>
    )) },
  ];

  const F = (label: string, field: string, props: any = {}) => (
    <div>
      <label className="block text-sm font-medium mb-1">{label}</label>
      <input className="input-field" value={(form as any)[field]} onChange={(e) => setForm({ ...form, [field]: e.target.value })} {...props} />
    </div>
  );

  return (
    <div>
      <PageHeader title="Customers" subtitle="Manage customers and ship-to addresses" actions={<button className="btn-primary" onClick={() => setShowForm(true)}>New Customer</button>} />
      <div className="card"><DataTable columns={columns} data={customers?.data || []} /></div>

      {/* Customer Create/Edit */}
      <Modal isOpen={showForm} onClose={closeForm} title={editingCustomer ? 'Edit Customer' : 'New Customer'} size="xl">
        <form onSubmit={(e) => { e.preventDefault(); saveCust.mutate(form); }} className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {F('Code', 'code', { required: true, disabled: !!editingCustomer })}
            {F('Name', 'name', { required: true })}
            {F('Contact Name', 'contact_name')}
            {F('Email', 'email', { type: 'email' })}
            {F('Phone', 'phone')}
            {F('Payment Terms', 'payment_terms')}
          </div>
          <h3 className="text-sm font-semibold text-gray-700 mt-4">Billing Address</h3>
          <div className="grid grid-cols-3 gap-4">
            {F('Address Line 1', 'billing_address_line1')}
            {F('Address Line 2', 'billing_address_line2')}
            {F('City', 'billing_city')}
            {F('State', 'billing_state')}
            {F('Postal Code', 'billing_postal_code')}
            {F('Country', 'billing_country')}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <input type="checkbox" id="tax_exempt" checked={form.tax_exempt} onChange={(e) => setForm({ ...form, tax_exempt: e.target.checked })} />
            <label htmlFor="tax_exempt" className="text-sm">Tax Exempt</label>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={closeForm}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saveCust.isPending}>{editingCustomer ? 'Save' : 'Create'}</button>
          </div>
        </form>
      </Modal>

      {/* Ship-To List */}
      <Modal isOpen={showShipTos} onClose={() => { setShowShipTos(false); setSelectedCustomer(null); }} title={`Ship-To Addresses - ${selectedCustomer?.name || ''}`} size="xl">
        <div className="space-y-4">
          <div className="flex justify-end">
            <button className="btn-primary text-sm" onClick={() => { setShipToForm({ ...emptyShipTo, customer_id: selectedCustomer!.id }); setEditingShipTo(null); setShowShipToForm(true); }}>Add Ship-To</button>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {(shipTos?.data || []).length === 0 ? (
              <p className="text-gray-500 text-sm py-4 text-center">No ship-to addresses.</p>
            ) : (
              <table className="w-full text-sm">
                <thead><tr className="border-b"><th className="text-left py-2">Name</th><th className="text-left py-2">Address</th><th className="text-left py-2">City</th><th className="text-left py-2">State</th><th className="text-left py-2">Default</th><th className="py-2"></th></tr></thead>
                <tbody>
                  {(shipTos?.data || []).map((st: ShipTo) => (
                    <tr key={st.id} className="border-b">
                      <td className="py-2">{st.name}</td>
                      <td className="py-2">{st.address_line1}</td>
                      <td className="py-2">{st.city}</td>
                      <td className="py-2">{st.state}</td>
                      <td className="py-2">{st.is_default ? <span className="badge-green">Yes</span> : '-'}</td>
                      <td className="py-2"><button className="text-blue-600 hover:underline text-xs" onClick={() => openShipToEdit(st)}>Edit</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </Modal>

      {/* Ship-To Create/Edit */}
      <Modal isOpen={showShipToForm} onClose={() => { setShowShipToForm(false); setEditingShipTo(null); }} title={editingShipTo ? 'Edit Ship-To' : 'New Ship-To'}>
        <form onSubmit={(e) => { e.preventDefault(); saveShipTo.mutate(shipToForm); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium mb-1">Name</label><input className="input-field" value={shipToForm.name} onChange={(e) => setShipToForm({ ...shipToForm, name: e.target.value })} required /></div>
            <div><label className="block text-sm font-medium mb-1">Contact</label><input className="input-field" value={shipToForm.contact_name} onChange={(e) => setShipToForm({ ...shipToForm, contact_name: e.target.value })} /></div>
            <div><label className="block text-sm font-medium mb-1">Address Line 1</label><input className="input-field" value={shipToForm.address_line1} onChange={(e) => setShipToForm({ ...shipToForm, address_line1: e.target.value })} /></div>
            <div><label className="block text-sm font-medium mb-1">Address Line 2</label><input className="input-field" value={shipToForm.address_line2} onChange={(e) => setShipToForm({ ...shipToForm, address_line2: e.target.value })} /></div>
            <div><label className="block text-sm font-medium mb-1">City</label><input className="input-field" value={shipToForm.city} onChange={(e) => setShipToForm({ ...shipToForm, city: e.target.value })} /></div>
            <div><label className="block text-sm font-medium mb-1">State</label><input className="input-field" value={shipToForm.state} onChange={(e) => setShipToForm({ ...shipToForm, state: e.target.value })} /></div>
            <div><label className="block text-sm font-medium mb-1">Postal Code</label><input className="input-field" value={shipToForm.postal_code} onChange={(e) => setShipToForm({ ...shipToForm, postal_code: e.target.value })} /></div>
            <div><label className="block text-sm font-medium mb-1">Phone</label><input className="input-field" value={shipToForm.phone} onChange={(e) => setShipToForm({ ...shipToForm, phone: e.target.value })} /></div>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="ship_to_default" checked={shipToForm.is_default} onChange={(e) => setShipToForm({ ...shipToForm, is_default: e.target.checked })} />
            <label htmlFor="ship_to_default" className="text-sm">Default Ship-To</label>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setShowShipToForm(false)}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saveShipTo.isPending}>{editingShipTo ? 'Save' : 'Create'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default CustomersPage;
