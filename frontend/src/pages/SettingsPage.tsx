import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { settingsAPI } from '../services/api';
import type { ShipVia, Branding } from '../types';

const SettingsPage: React.FC = () => {
  const [tab, setTab] = useState<'branding' | 'ship-vias' | 'price-lists'>('branding');
  const [showShipViaForm, setShowShipViaForm] = useState(false);
  const [editingShipVia, setEditingShipVia] = useState<ShipVia | null>(null);
  const [shipViaForm, setShipViaForm] = useState({ name: '', carrier: '', account_number: '' });
  const [brandingForm, setBrandingForm] = useState({
    company_name: '', address_line1: '', address_line2: '', city: '', state: '', postal_code: '', country: 'US',
    phone: '', email: '', website: '', primary_color: '#1e40af',
  });
  const queryClient = useQueryClient();

  const { data: branding } = useQuery({ queryKey: ['branding'], queryFn: () => settingsAPI.getBranding() });
  const { data: shipVias } = useQuery({ queryKey: ['ship-vias'], queryFn: () => settingsAPI.listShipVias() });

  useEffect(() => {
    if (branding?.data) {
      const b = branding.data;
      setBrandingForm({
        company_name: b.company_name || '', address_line1: b.address_line1 || '', address_line2: b.address_line2 || '',
        city: b.city || '', state: b.state || '', postal_code: b.postal_code || '', country: b.country || 'US',
        phone: b.phone || '', email: b.email || '', website: b.website || '', primary_color: b.primary_color || '#1e40af',
      });
    }
  }, [branding?.data]);

  const saveBranding = useMutation({
    mutationFn: (data: any) => settingsAPI.updateBranding(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['branding'] }); toast.success('Branding saved'); },
    onError: () => toast.error('Failed to save branding'),
  });

  const saveShipVia = useMutation({
    mutationFn: (data: any) => editingShipVia ? settingsAPI.updateShipVia(editingShipVia.id, data) : settingsAPI.createShipVia(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ship-vias'] }); closeShipViaForm(); toast.success(editingShipVia ? 'Ship Via updated' : 'Ship Via created'); },
    onError: () => toast.error('Failed to save Ship Via'),
  });

  const deleteShipVia = useMutation({
    mutationFn: (id: number) => settingsAPI.deleteShipVia(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ship-vias'] }); toast.success('Ship Via deleted'); },
    onError: () => toast.error('Failed to delete Ship Via'),
  });

  const closeShipViaForm = () => { setShowShipViaForm(false); setEditingShipVia(null); setShipViaForm({ name: '', carrier: '', account_number: '' }); };

  const openEditShipVia = (sv: ShipVia) => {
    setEditingShipVia(sv);
    setShipViaForm({ name: sv.name, carrier: sv.carrier || '', account_number: sv.account_number || '' });
    setShowShipViaForm(true);
  };

  const shipViaColumns = [
    { header: 'Name', accessor: 'name' as keyof ShipVia },
    { header: 'Carrier', accessor: ((row: ShipVia) => row.carrier || '-') },
    { header: 'Account #', accessor: ((row: ShipVia) => row.account_number || '-') },
    { header: 'Status', accessor: ((row: ShipVia) => <span className={row.is_active ? 'badge-green' : 'badge-red'}>{row.is_active ? 'Active' : 'Inactive'}</span>) },
    { header: 'Actions', accessor: ((row: ShipVia) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openEditShipVia(row); }}>Edit</button>
        <button className="text-sm text-red-600 hover:underline" onClick={(e) => { e.stopPropagation(); deleteShipVia.mutate(row.id); }}>Delete</button>
      </div>
    )) },
  ];

  const tabs = [
    { id: 'branding' as const, label: 'Branding' },
    { id: 'ship-vias' as const, label: 'Ship Vias' },
  ];

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Configure branding, shipping methods, and system preferences"
        actions={tab === 'ship-vias' ? <button className="btn-primary" onClick={() => setShowShipViaForm(true)}>New Ship Via</button> : undefined}
      />

      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === t.id ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>{t.label}</button>
        ))}
      </div>

      {tab === 'branding' && (
        <div className="card">
          <form onSubmit={(e) => { e.preventDefault(); saveBranding.mutate(brandingForm); }} className="space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Company Information</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Company Name</label>
                  <input className="input-field" value={brandingForm.company_name} onChange={(e) => setBrandingForm({ ...brandingForm, company_name: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Phone</label>
                  <input className="input-field" value={brandingForm.phone} onChange={(e) => setBrandingForm({ ...brandingForm, phone: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Email</label>
                  <input className="input-field" type="email" value={brandingForm.email} onChange={(e) => setBrandingForm({ ...brandingForm, email: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Website</label>
                  <input className="input-field" value={brandingForm.website} onChange={(e) => setBrandingForm({ ...brandingForm, website: e.target.value })} />
                </div>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Address</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Address Line 1</label>
                  <input className="input-field" value={brandingForm.address_line1} onChange={(e) => setBrandingForm({ ...brandingForm, address_line1: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Address Line 2</label>
                  <input className="input-field" value={brandingForm.address_line2} onChange={(e) => setBrandingForm({ ...brandingForm, address_line2: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">City</label>
                  <input className="input-field" value={brandingForm.city} onChange={(e) => setBrandingForm({ ...brandingForm, city: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">State</label>
                    <input className="input-field" value={brandingForm.state} onChange={(e) => setBrandingForm({ ...brandingForm, state: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Postal Code</label>
                    <input className="input-field" value={brandingForm.postal_code} onChange={(e) => setBrandingForm({ ...brandingForm, postal_code: e.target.value })} />
                  </div>
                </div>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Appearance</h3>
              <div className="flex items-center gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Primary Color</label>
                  <div className="flex items-center gap-2">
                    <input type="color" value={brandingForm.primary_color} onChange={(e) => setBrandingForm({ ...brandingForm, primary_color: e.target.value })} className="w-10 h-10 rounded cursor-pointer" />
                    <input className="input-field w-32" value={brandingForm.primary_color} onChange={(e) => setBrandingForm({ ...brandingForm, primary_color: e.target.value })} />
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-end">
              <button type="submit" className="btn-primary" disabled={saveBranding.isPending}>Save Branding</button>
            </div>
          </form>
        </div>
      )}

      {tab === 'ship-vias' && (
        <div className="card">
          <DataTable columns={shipViaColumns} data={shipVias?.data || []} />
        </div>
      )}

      {/* Ship Via Form Modal */}
      <Modal isOpen={showShipViaForm} onClose={closeShipViaForm} title={editingShipVia ? 'Edit Ship Via' : 'New Ship Via'}>
        <form onSubmit={(e) => { e.preventDefault(); saveShipVia.mutate(shipViaForm); }} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input className="input-field" value={shipViaForm.name} onChange={(e) => setShipViaForm({ ...shipViaForm, name: e.target.value })} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Carrier</label>
            <input className="input-field" value={shipViaForm.carrier} onChange={(e) => setShipViaForm({ ...shipViaForm, carrier: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Account Number</label>
            <input className="input-field" value={shipViaForm.account_number} onChange={(e) => setShipViaForm({ ...shipViaForm, account_number: e.target.value })} />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={closeShipViaForm}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saveShipVia.isPending}>{editingShipVia ? 'Save' : 'Create'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default SettingsPage;
