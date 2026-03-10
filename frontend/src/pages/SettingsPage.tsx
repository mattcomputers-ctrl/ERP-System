import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { settingsAPI, inventoryAPI } from '../services/api';
import type { ShipVia, Branding, QCTestDefinition, PackExtensionDefinition, Item, UOM } from '../types';

type SettingsTab = 'branding' | 'ship-vias' | 'uom' | 'qc-tests' | 'pack-extensions';

const SettingsPage: React.FC = () => {
  const [tab, setTab] = useState<SettingsTab>('branding');
  const [showShipViaForm, setShowShipViaForm] = useState(false);
  const [editingShipVia, setEditingShipVia] = useState<ShipVia | null>(null);
  const [shipViaForm, setShipViaForm] = useState({ name: '', carrier: '', account_number: '' });
  const [brandingForm, setBrandingForm] = useState({
    company_name: '', address_line1: '', address_line2: '', city: '', state: '', postal_code: '', country: 'US',
    phone: '', email: '', website: '', primary_color: '#1e40af',
  });

  // UOM state
  const [showUOMForm, setShowUOMForm] = useState(false);
  const [editingUOM, setEditingUOM] = useState<UOM | null>(null);
  const [uomForm, setUomForm] = useState({ name: '', abbreviation: '', category: 'weight' });

  // QC Test Definition state
  const [showQCTestForm, setShowQCTestForm] = useState(false);
  const [editingQCTest, setEditingQCTest] = useState<QCTestDefinition | null>(null);
  const [qcTestForm, setQcTestForm] = useState({ name: '', test_type: 'range', method: '', uom_id: null as number | null });

  // Pack Extension Definition state
  const [showPackExtForm, setShowPackExtForm] = useState(false);
  const [editingPackExt, setEditingPackExt] = useState<PackExtensionDefinition | null>(null);
  const [packExtForm, setPackExtForm] = useState({ code: '', name: '', description: '', materials: [] as { material_item_id: number; quantity_per_lb: string; uom_id: number | null }[] });
  const [materialForm, setMaterialForm] = useState({ material_item_id: 0, quantity_per_lb: '', uom_id: null as number | null });

  const queryClient = useQueryClient();

  // --- Data queries ---
  const { data: branding } = useQuery({ queryKey: ['branding'], queryFn: () => settingsAPI.getBranding() });
  const { data: shipVias } = useQuery({ queryKey: ['ship-vias'], queryFn: () => settingsAPI.listShipVias() });
  const { data: qcTestDefs } = useQuery({ queryKey: ['qc-test-definitions'], queryFn: () => inventoryAPI.listQCTestDefinitions() });
  const { data: packExtDefs } = useQuery({ queryKey: ['pack-extension-definitions'], queryFn: () => inventoryAPI.listPackExtensionDefinitions() });
  const { data: itemsList } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: uoms } = useQuery({ queryKey: ['uoms'], queryFn: () => inventoryAPI.listUOMs() });

  const items: Item[] = itemsList?.data || [];
  const uomList: UOM[] = uoms?.data || [];

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

  // --- Branding mutations ---
  const saveBranding = useMutation({
    mutationFn: (data: any) => settingsAPI.updateBranding(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['branding'] }); toast.success('Branding saved'); },
    onError: () => toast.error('Failed to save branding'),
  });

  // --- Ship Via mutations ---
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

  // --- UOM mutations ---
  const saveUOM = useMutation({
    mutationFn: (data: any) => editingUOM ? inventoryAPI.updateUOM(editingUOM.id, data) : inventoryAPI.createUOM(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['uoms'] }); closeUOMForm(); toast.success(editingUOM ? 'UOM updated' : 'UOM created'); },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to save UOM'),
  });

  const deleteUOM = useMutation({
    mutationFn: (id: number) => inventoryAPI.deleteUOM(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['uoms'] }); toast.success('UOM deleted'); },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to delete UOM'),
  });

  // --- QC Test Definition mutations ---
  const saveQCTest = useMutation({
    mutationFn: (data: any) => editingQCTest ? inventoryAPI.updateQCTestDefinition(editingQCTest.id, data) : inventoryAPI.createQCTestDefinition(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['qc-test-definitions'] }); closeQCTestForm(); toast.success(editingQCTest ? 'QC test updated' : 'QC test created'); },
    onError: () => toast.error('Failed to save QC test'),
  });

  const deleteQCTest = useMutation({
    mutationFn: (id: number) => inventoryAPI.deleteQCTestDefinition(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['qc-test-definitions'] }); toast.success('QC test deactivated'); },
  });

  // --- Pack Extension Definition mutations ---
  const savePackExt = useMutation({
    mutationFn: (data: any) => editingPackExt ? inventoryAPI.updatePackExtensionDefinition(editingPackExt.id, data) : inventoryAPI.createPackExtensionDefinition(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pack-extension-definitions'] }); closePackExtForm(); toast.success(editingPackExt ? 'Pack extension updated' : 'Pack extension created'); },
    onError: () => toast.error('Failed to save pack extension'),
  });

  const deletePackExt = useMutation({
    mutationFn: (id: number) => inventoryAPI.deletePackExtensionDefinition(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pack-extension-definitions'] }); toast.success('Pack extension deactivated'); },
  });

  // --- Form helpers ---
  const closeShipViaForm = () => { setShowShipViaForm(false); setEditingShipVia(null); setShipViaForm({ name: '', carrier: '', account_number: '' }); };
  const openEditShipVia = (sv: ShipVia) => {
    setEditingShipVia(sv);
    setShipViaForm({ name: sv.name, carrier: sv.carrier || '', account_number: sv.account_number || '' });
    setShowShipViaForm(true);
  };

  const closeUOMForm = () => { setShowUOMForm(false); setEditingUOM(null); setUomForm({ name: '', abbreviation: '', category: 'weight' }); };
  const openEditUOM = (u: UOM) => {
    setEditingUOM(u);
    setUomForm({ name: u.name, abbreviation: u.abbreviation, category: u.category });
    setShowUOMForm(true);
  };

  const closeQCTestForm = () => { setShowQCTestForm(false); setEditingQCTest(null); setQcTestForm({ name: '', test_type: 'range', method: '', uom_id: null }); };
  const openEditQCTest = (td: QCTestDefinition) => {
    setEditingQCTest(td);
    setQcTestForm({ name: td.name, test_type: td.test_type, method: td.method || '', uom_id: td.uom_id });
    setShowQCTestForm(true);
  };

  const closePackExtForm = () => { setShowPackExtForm(false); setEditingPackExt(null); setPackExtForm({ code: '', name: '', description: '', materials: [] }); setMaterialForm({ material_item_id: 0, quantity_per_lb: '', uom_id: null }); };
  const openEditPackExt = (pe: PackExtensionDefinition) => {
    setEditingPackExt(pe);
    setPackExtForm({
      code: pe.code, name: pe.name, description: pe.description || '',
      materials: pe.materials.map(m => ({ material_item_id: m.material_item_id, quantity_per_lb: String(m.quantity_per_lb), uom_id: m.uom_id })),
    });
    setShowPackExtForm(true);
  };

  const getUomName = (id: number | null) => {
    if (!id) return '-';
    const u = uomList.find(u => u.id === id);
    return u ? `${u.name} (${u.abbreviation})` : '-';
  };

  // --- Column definitions ---
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

  const uomColumns = [
    { header: 'Name', accessor: 'name' as keyof UOM },
    { header: 'Abbreviation', accessor: 'abbreviation' as keyof UOM },
    { header: 'Category', accessor: ((row: UOM) => <span className="badge-blue">{row.category}</span>) },
    { header: 'Actions', accessor: ((row: UOM) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openEditUOM(row); }}>Edit</button>
        <button className="text-sm text-red-600 hover:underline" onClick={(e) => { e.stopPropagation(); deleteUOM.mutate(row.id); }}>Delete</button>
      </div>
    )) },
  ];

  const qcTestColumns = [
    { header: 'Name', accessor: 'name' as keyof QCTestDefinition },
    { header: 'Type', accessor: ((row: QCTestDefinition) => <span className={row.test_type === 'pass_fail' ? 'badge-blue' : 'badge-yellow'}>{row.test_type === 'pass_fail' ? 'Pass/Fail' : 'Range'}</span>) },
    { header: 'Method', accessor: ((row: QCTestDefinition) => row.method || '-') },
    { header: 'UOM', accessor: ((row: QCTestDefinition) => getUomName(row.uom_id)) },
    { header: 'Actions', accessor: ((row: QCTestDefinition) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openEditQCTest(row); }}>Edit</button>
        <button className="text-sm text-red-600 hover:underline" onClick={(e) => { e.stopPropagation(); deleteQCTest.mutate(row.id); }}>Delete</button>
      </div>
    )) },
  ];

  const packExtColumns = [
    { header: 'Code', accessor: 'code' as keyof PackExtensionDefinition },
    { header: 'Name', accessor: 'name' as keyof PackExtensionDefinition },
    { header: 'Description', accessor: ((row: PackExtensionDefinition) => row.description || '-') },
    { header: 'Materials', accessor: ((row: PackExtensionDefinition) => `${row.materials?.length || 0} material(s)`) },
    { header: 'Actions', accessor: ((row: PackExtensionDefinition) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openEditPackExt(row); }}>Edit</button>
        <button className="text-sm text-red-600 hover:underline" onClick={(e) => { e.stopPropagation(); deletePackExt.mutate(row.id); }}>Delete</button>
      </div>
    )) },
  ];

  const tabs: { id: SettingsTab; label: string }[] = [
    { id: 'branding', label: 'Branding' },
    { id: 'ship-vias', label: 'Ship Vias' },
    { id: 'uom', label: 'Units of Measure' },
    { id: 'qc-tests', label: 'QC Tests' },
    { id: 'pack-extensions', label: 'Pack Extensions' },
  ];

  const getTabAction = () => {
    if (tab === 'ship-vias') return <button className="btn-primary" onClick={() => setShowShipViaForm(true)}>New Ship Via</button>;
    if (tab === 'uom') return <button className="btn-primary" onClick={() => setShowUOMForm(true)}>New UOM</button>;
    if (tab === 'qc-tests') return <button className="btn-primary" onClick={() => setShowQCTestForm(true)}>New QC Test</button>;
    if (tab === 'pack-extensions') return <button className="btn-primary" onClick={() => setShowPackExtForm(true)}>New Pack Extension</button>;
    return undefined;
  };

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Configure branding, shipping, units of measure, QC tests, and pack extensions"
        actions={getTabAction()}
      />

      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === t.id ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>{t.label}</button>
        ))}
      </div>

      {/* ======== BRANDING TAB ======== */}
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

      {/* ======== SHIP VIAS TAB ======== */}
      {tab === 'ship-vias' && (
        <div className="card">
          <DataTable columns={shipViaColumns} data={shipVias?.data || []} />
        </div>
      )}

      {/* ======== UNITS OF MEASURE TAB ======== */}
      {tab === 'uom' && (
        <div className="card">
          <DataTable columns={uomColumns} data={uomList} />
        </div>
      )}

      {/* ======== QC TESTS TAB ======== */}
      {tab === 'qc-tests' && (
        <div className="card">
          <DataTable columns={qcTestColumns} data={qcTestDefs?.data || []} />
        </div>
      )}

      {/* ======== PACK EXTENSIONS TAB ======== */}
      {tab === 'pack-extensions' && (
        <div className="card">
          <DataTable columns={packExtColumns} data={packExtDefs?.data || []} />
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

      {/* UOM Form Modal */}
      <Modal isOpen={showUOMForm} onClose={closeUOMForm} title={editingUOM ? 'Edit Unit of Measure' : 'New Unit of Measure'}>
        <form onSubmit={(e) => { e.preventDefault(); saveUOM.mutate(uomForm); }} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input className="input-field" value={uomForm.name} onChange={(e) => setUomForm({ ...uomForm, name: e.target.value })} required placeholder="e.g., Pound" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Abbreviation</label>
            <input className="input-field" value={uomForm.abbreviation} onChange={(e) => setUomForm({ ...uomForm, abbreviation: e.target.value })} required placeholder="e.g., LB" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Category</label>
            <select className="input-field" value={uomForm.category} onChange={(e) => setUomForm({ ...uomForm, category: e.target.value })}>
              <option value="weight">Weight</option>
              <option value="volume">Volume</option>
              <option value="count">Count</option>
              <option value="length">Length</option>
              <option value="area">Area</option>
              <option value="time">Time</option>
            </select>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={closeUOMForm}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saveUOM.isPending}>{editingUOM ? 'Save' : 'Create'}</button>
          </div>
        </form>
      </Modal>

      {/* QC Test Definition Form Modal */}
      <Modal isOpen={showQCTestForm} onClose={closeQCTestForm} title={editingQCTest ? 'Edit QC Test' : 'New QC Test'}>
        <form onSubmit={(e) => { e.preventDefault(); saveQCTest.mutate(qcTestForm); }} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Test Name</label>
            <input className="input-field" value={qcTestForm.name} onChange={(e) => setQcTestForm({ ...qcTestForm, name: e.target.value })} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Test Type</label>
            <select className="input-field" value={qcTestForm.test_type} onChange={(e) => setQcTestForm({ ...qcTestForm, test_type: e.target.value })}>
              <option value="pass_fail">Pass/Fail</option>
              <option value="range">Range (Min/Max)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Method</label>
            <input className="input-field" value={qcTestForm.method} onChange={(e) => setQcTestForm({ ...qcTestForm, method: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">UOM</label>
            <select className="input-field" value={qcTestForm.uom_id || ''} onChange={(e) => setQcTestForm({ ...qcTestForm, uom_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">-- None --</option>
              {uomList.map(u => <option key={u.id} value={u.id}>{u.name} ({u.abbreviation})</option>)}
            </select>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={closeQCTestForm}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saveQCTest.isPending}>{editingQCTest ? 'Save' : 'Create'}</button>
          </div>
        </form>
      </Modal>

      {/* Pack Extension Definition Form Modal */}
      <Modal isOpen={showPackExtForm} onClose={closePackExtForm} title={editingPackExt ? 'Edit Pack Extension' : 'New Pack Extension'} size="lg">
        <form onSubmit={(e) => {
          e.preventDefault();
          savePackExt.mutate({
            code: packExtForm.code,
            name: packExtForm.name,
            description: packExtForm.description || null,
            materials: packExtForm.materials.map(m => ({
              material_item_id: m.material_item_id,
              quantity_per_lb: Number(m.quantity_per_lb),
              uom_id: m.uom_id,
            })),
          });
        }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Extension Code</label>
              <input className="input-field" value={packExtForm.code} onChange={(e) => setPackExtForm({ ...packExtForm, code: e.target.value })} required disabled={!!editingPackExt} placeholder="e.g., -50" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input className="input-field" value={packExtForm.name} onChange={(e) => setPackExtForm({ ...packExtForm, name: e.target.value })} required placeholder="e.g., 5LB Can" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea className="input-field" rows={2} value={packExtForm.description} onChange={(e) => setPackExtForm({ ...packExtForm, description: e.target.value })} />
          </div>

          {/* Materials Section */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Packaging Materials (consumed per 1 LB of product)</h4>
            {packExtForm.materials.length > 0 && (
              <table className="w-full text-sm mb-3">
                <thead>
                  <tr className="border-b text-gray-500">
                    <th className="text-left py-1">Material</th>
                    <th className="text-right py-1">Qty per LB</th>
                    <th className="text-left py-1">UOM</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {packExtForm.materials.map((m, i) => {
                    const item = items.find(it => it.id === m.material_item_id);
                    const uom = uomList.find(u => u.id === m.uom_id);
                    return (
                      <tr key={i} className="border-b">
                        <td className="py-1">{item ? `${item.item_code} - ${item.name}` : `Item #${m.material_item_id}`}</td>
                        <td className="py-1 text-right">{m.quantity_per_lb}</td>
                        <td className="py-1">{uom ? uom.abbreviation : '-'}</td>
                        <td className="py-1">
                          <button type="button" className="text-red-500 text-xs" onClick={() => {
                            setPackExtForm({ ...packExtForm, materials: packExtForm.materials.filter((_, idx) => idx !== i) });
                          }}>Remove</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
            <div className="grid grid-cols-4 gap-2 items-end">
              <div>
                <label className="block text-xs mb-1">Material Item</label>
                <select className="input-field" value={materialForm.material_item_id || ''} onChange={(e) => setMaterialForm({ ...materialForm, material_item_id: Number(e.target.value) })}>
                  <option value="">-- Select --</option>
                  {items.filter(it => it.item_type === 'packaging' || it.item_type === 'raw_material' || it.item_type === 'consumable').map(it => (
                    <option key={it.id} value={it.id}>{it.item_code} - {it.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1">Qty per LB</label>
                <input type="number" step="0.000001" className="input-field" value={materialForm.quantity_per_lb} onChange={(e) => setMaterialForm({ ...materialForm, quantity_per_lb: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs mb-1">UOM</label>
                <select className="input-field" value={materialForm.uom_id || ''} onChange={(e) => setMaterialForm({ ...materialForm, uom_id: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">-- Select --</option>
                  {uomList.map(u => <option key={u.id} value={u.id}>{u.abbreviation}</option>)}
                </select>
              </div>
              <button type="button" className="btn-secondary text-sm" onClick={() => {
                if (!materialForm.material_item_id || !materialForm.quantity_per_lb) {
                  toast.error('Select a material and enter quantity');
                  return;
                }
                setPackExtForm({ ...packExtForm, materials: [...packExtForm.materials, { ...materialForm }] });
                setMaterialForm({ material_item_id: 0, quantity_per_lb: '', uom_id: null });
              }}>Add Material</button>
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={closePackExtForm}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={savePackExt.isPending}>{editingPackExt ? 'Save' : 'Create'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default SettingsPage;
