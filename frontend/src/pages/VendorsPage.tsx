import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { purchasingAPI, settingsAPI } from '../services/api';
import type { Vendor, ShipVia } from '../types';

const emptyVendor = {
  code: '', name: '', contact_name: '', email: '', phone: '',
  address_line1: '', address_line2: '', city: '', state: '', postal_code: '', country: 'US',
  remit_address_line1: '', remit_address_line2: '', remit_city: '', remit_state: '', remit_postal_code: '', remit_country: 'US',
  payment_terms: 'Net 30', default_ship_via_id: null as number | null,
};

const VendorsPage: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
  const [form, setForm] = useState(emptyVendor);
  const queryClient = useQueryClient();

  const { data: vendors } = useQuery({ queryKey: ['vendors'], queryFn: () => purchasingAPI.listVendors() });
  const { data: shipVias } = useQuery({ queryKey: ['ship-vias'], queryFn: () => settingsAPI.listShipVias() });

  const saveVendor = useMutation({
    mutationFn: (data: any) => editingVendor ? purchasingAPI.updateVendor(editingVendor.id, data) : purchasingAPI.createVendor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      closeForm();
      toast.success(editingVendor ? 'Vendor updated' : 'Vendor created');
    },
    onError: () => toast.error('Failed to save vendor'),
  });

  const closeForm = () => { setShowForm(false); setEditingVendor(null); setForm(emptyVendor); };

  const openEdit = (v: Vendor) => {
    setEditingVendor(v);
    setForm({
      code: v.code, name: v.name, contact_name: v.contact_name || '', email: v.email || '', phone: v.phone || '',
      address_line1: v.address_line1 || '', address_line2: v.address_line2 || '', city: v.city || '', state: v.state || '', postal_code: v.postal_code || '', country: v.country || 'US',
      remit_address_line1: v.remit_address_line1 || '', remit_address_line2: v.remit_address_line2 || '', remit_city: v.remit_city || '', remit_state: v.remit_state || '', remit_postal_code: v.remit_postal_code || '', remit_country: v.remit_country || 'US',
      payment_terms: v.payment_terms || '', default_ship_via_id: v.default_ship_via_id,
    });
    setShowForm(true);
  };

  const shipViaList: ShipVia[] = shipVias?.data || [];

  const columns = [
    { header: 'Code', accessor: 'code' as keyof Vendor },
    { header: 'Name', accessor: 'name' as keyof Vendor },
    { header: 'Contact', accessor: 'contact_name' as keyof Vendor },
    { header: 'Email', accessor: 'email' as keyof Vendor },
    { header: 'Phone', accessor: 'phone' as keyof Vendor },
    { header: 'Terms', accessor: 'payment_terms' as keyof Vendor },
    { header: 'Ship Via', accessor: ((row: Vendor) => {
      const sv = shipViaList.find(s => s.id === row.default_ship_via_id);
      return sv ? sv.name : '-';
    }) },
    { header: 'Actions', accessor: ((row: Vendor) => (
      <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openEdit(row); }}>Edit</button>
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
      <PageHeader title="Vendors" subtitle="Manage vendors and remit-to addresses" actions={<button className="btn-primary" onClick={() => setShowForm(true)}>New Vendor</button>} />
      <div className="card"><DataTable columns={columns} data={vendors?.data || []} /></div>

      <Modal isOpen={showForm} onClose={closeForm} title={editingVendor ? 'Edit Vendor' : 'New Vendor'} size="xl">
        <form onSubmit={(e) => { e.preventDefault(); saveVendor.mutate(form); }} className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {F('Code', 'code', { required: true, disabled: !!editingVendor })}
            {F('Name', 'name', { required: true })}
            {F('Contact Name', 'contact_name')}
            {F('Email', 'email', { type: 'email' })}
            {F('Phone', 'phone')}
            {F('Payment Terms', 'payment_terms')}
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Default Ship Via</label>
            <select className="input-field" value={form.default_ship_via_id || ''} onChange={(e) => setForm({ ...form, default_ship_via_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">-- None --</option>
              {shipViaList.map(sv => <option key={sv.id} value={sv.id}>{sv.name}</option>)}
            </select>
          </div>
          <h3 className="text-sm font-semibold text-gray-700">Office Address</h3>
          <div className="grid grid-cols-3 gap-4">
            {F('Address Line 1', 'address_line1')}
            {F('Address Line 2', 'address_line2')}
            {F('City', 'city')}
            {F('State', 'state')}
            {F('Postal Code', 'postal_code')}
            {F('Country', 'country')}
          </div>
          <h3 className="text-sm font-semibold text-gray-700">Remit-To Address</h3>
          <div className="grid grid-cols-3 gap-4">
            {F('Address Line 1', 'remit_address_line1')}
            {F('Address Line 2', 'remit_address_line2')}
            {F('City', 'remit_city')}
            {F('State', 'remit_state')}
            {F('Postal Code', 'remit_postal_code')}
            {F('Country', 'remit_country')}
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={closeForm}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saveVendor.isPending}>{editingVendor ? 'Save' : 'Create'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default VendorsPage;
