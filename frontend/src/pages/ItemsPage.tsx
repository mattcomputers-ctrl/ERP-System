import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { inventoryAPI, glGroupsAPI, purchasingAPI, manufacturingAPI } from '../services/api';
import { formatCurrency } from '../utils/helpers';
import type {
  Item, GLGroup, Vendor, Formula, QCTestDefinition,
  ItemActiveRecipe, ItemQCTestAssignment, PackExtensionDefinition,
  ItemPackExtension, UOM,
} from '../types';

type ItemTab = 'general' | 'technical' | 'qc-tests' | 'pack-extensions';

const ItemsPage: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | null>(null);
  const [activeTab, setActiveTab] = useState<ItemTab>('general');
  const queryClient = useQueryClient();

  // --- Header fields (always visible in modal) ---
  const [headerForm, setHeaderForm] = useState({
    item_code: '', name: '', description: '',
    item_type: 'raw_material', primary_uom_id: null as number | null,
  });

  // --- General tab state ---
  const [generalForm, setGeneralForm] = useState({
    gl_group_id: null as number | null,
    tracking_type: 'inventory_lot',
    max_shelf_life_days: null as number | null,
    does_not_expire: false,
    target_min_qty: null as number | null,
    replacement_cost: null as number | null,
    lead_time_days: null as number | null,
    preferred_supplier_id: null as number | null,
  });

  // --- Technical/Safety tab state ---
  const [techForm, setTechForm] = useState({
    specific_gravity: null as number | null,
    density_lb_gal: null as number | null,
    voc_percent: null as number | null,
    boiling_point: '',
    flash_point: '',
  });

  // --- QC Tests tab state ---
  const [qcAddForm, setQcAddForm] = useState({
    qc_test_definition_id: 0,
    target_value: '' as string,
    min_value: '' as string,
    max_value: '' as string,
  });

  // --- Pack Extensions tab state ---
  const [peAddForm, setPeAddForm] = useState({
    pack_extension_id: 0,
    desired_fill_amount: '' as string,
    fill_uom_id: null as number | null,
  });

  // --- Data queries ---
  const { data: items } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: glGroups } = useQuery({ queryKey: ['gl-groups'], queryFn: () => glGroupsAPI.list() });
  const { data: vendors } = useQuery({ queryKey: ['vendors'], queryFn: () => purchasingAPI.listVendors() });
  const { data: formulas } = useQuery({ queryKey: ['formulas'], queryFn: () => manufacturingAPI.listFormulas() });
  const { data: uoms } = useQuery({ queryKey: ['uoms'], queryFn: () => inventoryAPI.listUOMs() });
  const { data: qcTestDefs } = useQuery({ queryKey: ['qc-test-definitions'], queryFn: () => inventoryAPI.listQCTestDefinitions() });
  const { data: packExtDefs } = useQuery({ queryKey: ['pack-extension-definitions'], queryFn: () => inventoryAPI.listPackExtensionDefinitions() });

  // Item-specific queries (only when editing an existing item)
  const { data: activeRecipes } = useQuery({
    queryKey: ['active-recipes', editingItem?.id],
    queryFn: () => inventoryAPI.listActiveRecipes(editingItem!.id),
    enabled: !!editingItem && showForm,
  });
  const { data: itemQCTests } = useQuery({
    queryKey: ['item-qc-tests', editingItem?.id],
    queryFn: () => inventoryAPI.listItemQCTests(editingItem!.id),
    enabled: !!editingItem && showForm && activeTab === 'qc-tests',
  });
  const { data: itemPackExts } = useQuery({
    queryKey: ['item-pack-extensions', editingItem?.id],
    queryFn: () => inventoryAPI.listItemPackExtensions(editingItem!.id),
    enabled: !!editingItem && showForm && activeTab === 'pack-extensions',
  });

  // --- Active recipes state ---
  const [recipeSelections, setRecipeSelections] = useState<{ formula_id: number; is_master: boolean }[]>([]);

  useEffect(() => {
    if (activeRecipes?.data) {
      setRecipeSelections(activeRecipes.data.map((r: ItemActiveRecipe) => ({
        formula_id: r.formula_id, is_master: r.is_master,
      })));
    }
  }, [activeRecipes?.data]);

  // --- Populate forms when editing ---
  useEffect(() => {
    if (editingItem) {
      setHeaderForm({
        item_code: editingItem.item_code,
        name: editingItem.name,
        description: editingItem.description || '',
        item_type: editingItem.item_type,
        primary_uom_id: editingItem.primary_uom_id,
      });
      setGeneralForm({
        gl_group_id: editingItem.gl_group_id,
        tracking_type: editingItem.tracking_type || 'inventory_lot',
        max_shelf_life_days: editingItem.max_shelf_life_days,
        does_not_expire: editingItem.does_not_expire || false,
        target_min_qty: editingItem.target_min_qty,
        replacement_cost: editingItem.replacement_cost,
        lead_time_days: editingItem.lead_time_days,
        preferred_supplier_id: editingItem.preferred_supplier_id,
      });
      setTechForm({
        specific_gravity: editingItem.specific_gravity,
        density_lb_gal: editingItem.density_lb_gal,
        voc_percent: editingItem.voc_percent,
        boiling_point: editingItem.boiling_point || '',
        flash_point: editingItem.flash_point || '',
      });
    }
  }, [editingItem]);

  // Auto-calculate density from SG
  useEffect(() => {
    if (techForm.specific_gravity != null && techForm.specific_gravity > 0) {
      setTechForm(f => ({ ...f, density_lb_gal: Math.round(Number(f.specific_gravity) * 8.345404 * 1000000) / 1000000 }));
    }
  }, [techForm.specific_gravity]);

  // --- Mutations ---
  const saveItem = useMutation({
    mutationFn: (data: any) => editingItem ? inventoryAPI.updateItem(editingItem.id, data) : inventoryAPI.createItem(data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      if (!editingItem) {
        // After creating, switch to editing so user can use all tabs
        setEditingItem(res.data);
        toast.success('Item created');
      } else {
        inventoryAPI.getItem(editingItem.id).then(r => setEditingItem(r.data));
        toast.success('Item updated');
      }
    },
    onError: () => toast.error('Failed to save item'),
  });

  const saveActiveRecipes = useMutation({
    mutationFn: ({ itemId, recipes }: { itemId: number; recipes: any[] }) => inventoryAPI.setActiveRecipes(itemId, recipes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-recipes', editingItem?.id] });
      toast.success('Active recipes updated');
    },
    onError: () => toast.error('Failed to update active recipes'),
  });

  const addItemQCTest = useMutation({
    mutationFn: ({ itemId, data }: { itemId: number; data: any }) => inventoryAPI.addItemQCTest(itemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item-qc-tests', editingItem?.id] });
      setQcAddForm({ qc_test_definition_id: 0, target_value: '', min_value: '', max_value: '' });
      toast.success('QC test added');
    },
    onError: () => toast.error('Failed to add QC test'),
  });

  const removeItemQCTest = useMutation({
    mutationFn: ({ itemId, assignmentId }: { itemId: number; assignmentId: number }) => inventoryAPI.removeItemQCTest(itemId, assignmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item-qc-tests', editingItem?.id] });
      toast.success('QC test removed');
    },
  });

  const addItemPackExt = useMutation({
    mutationFn: ({ itemId, data }: { itemId: number; data: any }) => inventoryAPI.addItemPackExtension(itemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item-pack-extensions', editingItem?.id] });
      setPeAddForm({ pack_extension_id: 0, desired_fill_amount: '', fill_uom_id: null });
      toast.success('Pack extension added');
    },
    onError: () => toast.error('Failed to add pack extension'),
  });

  const updateItemPackExt = useMutation({
    mutationFn: ({ itemId, ipeId, data }: { itemId: number; ipeId: number; data: any }) => inventoryAPI.updateItemPackExtension(itemId, ipeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item-pack-extensions', editingItem?.id] });
      toast.success('Pack extension updated');
    },
  });

  const removeItemPackExt = useMutation({
    mutationFn: ({ itemId, ipeId }: { itemId: number; ipeId: number }) => inventoryAPI.removeItemPackExtension(itemId, ipeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item-pack-extensions', editingItem?.id] });
      toast.success('Pack extension removed');
    },
  });

  // --- Helpers ---
  const resetForm = () => {
    setHeaderForm({ item_code: '', name: '', description: '', item_type: 'raw_material', primary_uom_id: null });
    setGeneralForm({ gl_group_id: null, tracking_type: 'inventory_lot', max_shelf_life_days: null, does_not_expire: false, target_min_qty: null, replacement_cost: null, lead_time_days: null, preferred_supplier_id: null });
    setTechForm({ specific_gravity: null, density_lb_gal: null, voc_percent: null, boiling_point: '', flash_point: '' });
    setQcAddForm({ qc_test_definition_id: 0, target_value: '', min_value: '', max_value: '' });
    setPeAddForm({ pack_extension_id: 0, desired_fill_amount: '', fill_uom_id: null });
    setRecipeSelections([]);
  };

  const closeForm = () => { setShowForm(false); setEditingItem(null); setActiveTab('general'); resetForm(); };

  const openNew = () => { resetForm(); setEditingItem(null); setActiveTab('general'); setShowForm(true); };

  const openEdit = (item: Item) => { setEditingItem(item); setActiveTab('general'); setShowForm(true); };

  const handleSave = () => {
    const data = { ...headerForm, ...generalForm, ...techForm };
    saveItem.mutate(data);
  };

  const glGroupList: GLGroup[] = glGroups?.data || [];
  const vendorList: Vendor[] = vendors?.data || [];
  const formulaList: Formula[] = formulas?.data || [];
  const uomList: UOM[] = uoms?.data || [];
  const qcTestDefList: QCTestDefinition[] = qcTestDefs?.data || [];
  const packExtDefList: PackExtensionDefinition[] = packExtDefs?.data || [];
  const itemFormulas = formulaList.filter(f => f.product_item_id === editingItem?.id && f.is_active);
  const itemQCTestList: ItemQCTestAssignment[] = itemQCTests?.data || [];
  const itemPackExtList: ItemPackExtension[] = itemPackExts?.data || [];

  const isExistingItem = !!editingItem;

  const columns = [
    { header: 'Code', accessor: 'item_code' as keyof Item },
    { header: 'Name', accessor: 'name' as keyof Item },
    { header: 'Type', accessor: ((row: Item) => <span className="badge-blue">{row.item_type.replace('_', ' ')}</span>) },
    { header: 'Lot Tracked', accessor: ((row: Item) => row.is_lot_tracked ? 'Yes' : 'No') },
    { header: 'Status', accessor: ((row: Item) => <span className={row.is_active ? 'badge-green' : 'badge-red'}>{row.is_active ? 'Active' : 'Inactive'}</span>) },
    { header: 'Actions', accessor: ((row: Item) => (
      <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openEdit(row); }}>Edit</button>
    )) },
  ];

  const tabs: { id: ItemTab; label: string }[] = [
    { id: 'general', label: 'General' },
    { id: 'technical', label: 'Technical/Safety' },
    { id: 'qc-tests', label: 'QC Tests' },
    { id: 'pack-extensions', label: 'Pack Extensions' },
  ];

  const getUomAbbrev = (id: number | null) => {
    if (!id) return '';
    const u = uomList.find(u => u.id === id);
    return u ? u.abbreviation : '';
  };

  return (
    <div>
      <PageHeader title="Items" subtitle="Manage items, recipes, QC tests, and pack extensions" actions={<button className="btn-primary" onClick={openNew}>New Item</button>} />
      <div className="card"><DataTable columns={columns} data={items?.data || []} /></div>

      {/* Item Setup Modal */}
      <Modal isOpen={showForm} onClose={closeForm} title={editingItem ? 'Edit Item' : 'New Item'} size="xl">
        {/* Header Section - Item Code, Description, UOM */}
        <div className="border rounded-lg p-4 mb-4 bg-gray-50">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-500 font-medium mb-1">Item Code</label>
              <input className="input-field" value={headerForm.item_code} onChange={(e) => setHeaderForm({ ...headerForm, item_code: e.target.value })} required disabled={isExistingItem} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 font-medium mb-1">Description</label>
              <input className="input-field" value={headerForm.name} onChange={(e) => setHeaderForm({ ...headerForm, name: e.target.value })} required />
            </div>
            <div>
              <label className="block text-xs text-gray-500 font-medium mb-1">UOM</label>
              <select className="input-field" value={headerForm.primary_uom_id || ''} onChange={(e) => setHeaderForm({ ...headerForm, primary_uom_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">-- Select --</option>
                {uomList.map(u => <option key={u.id} value={u.id}>{u.name} ({u.abbreviation})</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border rounded-lg">
          <div className="flex gap-1 bg-gray-100 rounded-t-lg p-1">
            {tabs.map(t => {
              const disabled = !isExistingItem && (t.id === 'qc-tests' || t.id === 'pack-extensions');
              return (
                <button key={t.id} onClick={() => !disabled && setActiveTab(t.id)} disabled={disabled}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === t.id ? 'bg-white shadow-sm text-gray-900' : disabled ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:text-gray-700'}`}>
                  {t.label}
                </button>
              );
            })}
          </div>

          <div className="p-4" style={{ minHeight: '400px' }}>
            {/* ======== GENERAL TAB ======== */}
            <div style={{ display: activeTab === 'general' ? 'block' : 'none' }}>
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Type</label>
                    <select className="input-field" value={headerForm.item_type} onChange={(e) => setHeaderForm({ ...headerForm, item_type: e.target.value })}>
                      <option value="raw_material">Raw Material</option><option value="finished_good">Finished Good</option>
                      <option value="packaging">Packaging</option><option value="intermediate">Intermediate</option><option value="consumable">Consumable</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">GL Group Assignment</label>
                    <select className="input-field" value={generalForm.gl_group_id || ''} onChange={(e) => setGeneralForm({ ...generalForm, gl_group_id: e.target.value ? Number(e.target.value) : null })}>
                      <option value="">-- None --</option>
                      {glGroupList.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Tracking</label>
                    <select className="input-field" value={generalForm.tracking_type} onChange={(e) => setGeneralForm({ ...generalForm, tracking_type: e.target.value })}>
                      <option value="inventory_lot">Inventory with Lot Tracing</option>
                      <option value="inventory_no_lot">Inventory with No Lot Tracing</option>
                      <option value="not_inventoried">Not Inventoried</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Maximum Shelf Life (days)</label>
                    <div className="flex items-center gap-3">
                      <input type="number" className="input-field flex-1" value={generalForm.max_shelf_life_days ?? ''} onChange={(e) => setGeneralForm({ ...generalForm, max_shelf_life_days: e.target.value ? Number(e.target.value) : null })} disabled={generalForm.does_not_expire} />
                      <label className="flex items-center gap-1 text-sm whitespace-nowrap">
                        <input type="checkbox" checked={generalForm.does_not_expire} onChange={(e) => setGeneralForm({ ...generalForm, does_not_expire: e.target.checked, max_shelf_life_days: e.target.checked ? null : generalForm.max_shelf_life_days })} />
                        Does not expire
                      </label>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Target Minimum Qty on Hand</label>
                    <input type="number" step="0.0001" className="input-field" value={generalForm.target_min_qty ?? ''} onChange={(e) => setGeneralForm({ ...generalForm, target_min_qty: e.target.value ? Number(e.target.value) : null })} />
                  </div>
                </div>

                {/* Active Recipes (only for existing items) */}
                {isExistingItem && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Active Recipe(s)</label>
                    {itemFormulas.length === 0 ? (
                      <p className="text-gray-500 text-sm">No formulas available for this item.</p>
                    ) : (
                      <div className="space-y-2">
                        {itemFormulas.map(f => {
                          const isSelected = recipeSelections.some(r => r.formula_id === f.id);
                          const isMaster = recipeSelections.find(r => r.formula_id === f.id)?.is_master || false;
                          return (
                            <div key={f.id} className="flex items-center gap-3 border rounded p-2">
                              <input type="checkbox" checked={isSelected} onChange={(e) => {
                                if (e.target.checked) {
                                  setRecipeSelections([...recipeSelections, { formula_id: f.id, is_master: recipeSelections.length === 0 }]);
                                } else {
                                  setRecipeSelections(recipeSelections.filter(r => r.formula_id !== f.id));
                                }
                              }} />
                              <span className="flex-1 text-sm">{f.code} - {f.name}</span>
                              {isSelected && (
                                <label className="flex items-center gap-1 text-xs">
                                  <input type="radio" name="master_recipe" checked={isMaster} onChange={() => {
                                    setRecipeSelections(recipeSelections.map(r => ({ ...r, is_master: r.formula_id === f.id })));
                                  }} />
                                  Master
                                </label>
                              )}
                            </div>
                          );
                        })}
                        <button type="button" className="btn-secondary text-sm" onClick={() => {
                          if (recipeSelections.length > 0 && !recipeSelections.some(r => r.is_master)) {
                            toast.error('Please designate one master recipe');
                            return;
                          }
                          saveActiveRecipes.mutate({ itemId: editingItem!.id, recipes: recipeSelections });
                        }} disabled={saveActiveRecipes.isPending}>
                          Save Active Recipes
                        </button>
                      </div>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Current FIFO Cost (per UOM)</label>
                    <input type="text" className="input-field bg-gray-100" value={editingItem?.current_fifo_cost != null ? formatCurrency(editingItem.current_fifo_cost) : '-'} disabled />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Replacement Cost (per UOM)</label>
                    <input type="number" step="0.000001" className="input-field" value={generalForm.replacement_cost ?? ''} onChange={(e) => setGeneralForm({ ...generalForm, replacement_cost: e.target.value ? Number(e.target.value) : null })} />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Lead Time (days)</label>
                    <input type="number" className="input-field" value={generalForm.lead_time_days ?? ''} onChange={(e) => setGeneralForm({ ...generalForm, lead_time_days: e.target.value ? Number(e.target.value) : null })} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Preferred Supplier</label>
                    <select className="input-field" value={generalForm.preferred_supplier_id || ''} onChange={(e) => setGeneralForm({ ...generalForm, preferred_supplier_id: e.target.value ? Number(e.target.value) : null })}>
                      <option value="">-- None --</option>
                      {vendorList.map(v => <option key={v.id} value={v.id}>{v.code} - {v.name}</option>)}
                    </select>
                  </div>
                </div>
              </div>
            </div>

            {/* ======== TECHNICAL/SAFETY TAB ======== */}
            <div style={{ display: activeTab === 'technical' ? 'block' : 'none' }}>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Specific Gravity</label>
                    <input type="number" step="0.000001" className="input-field" value={techForm.specific_gravity ?? ''} onChange={(e) => setTechForm({ ...techForm, specific_gravity: e.target.value ? Number(e.target.value) : null })} />
                    {editingItem?.master_recipe_id && <p className="text-xs text-gray-400 mt-1">May be calculated from master recipe</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Density (lb/gal)</label>
                    <input type="number" step="0.000001" className="input-field bg-gray-100" value={techForm.density_lb_gal ?? ''} disabled />
                    <p className="text-xs text-gray-400 mt-1">Calculated from specific gravity (SG x 8.345)</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">VOC %</label>
                    <input type="number" step="0.0001" className="input-field" value={techForm.voc_percent ?? ''} onChange={(e) => setTechForm({ ...techForm, voc_percent: e.target.value ? Number(e.target.value) : null })} />
                    {editingItem?.master_recipe_id && <p className="text-xs text-gray-400 mt-1">May be calculated from master recipe</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Boiling Point</label>
                    <input type="text" className="input-field" value={techForm.boiling_point} onChange={(e) => setTechForm({ ...techForm, boiling_point: e.target.value })} placeholder="e.g., 212°F" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Flash Point</label>
                    <input type="text" className="input-field" value={techForm.flash_point} onChange={(e) => setTechForm({ ...techForm, flash_point: e.target.value })} placeholder="e.g., 140°F" />
                  </div>
                </div>
              </div>
            </div>

            {/* ======== QC TESTS TAB ======== */}
            <div style={{ display: activeTab === 'qc-tests' ? 'block' : 'none' }}>
              {isExistingItem && (
                <div className="space-y-4">
                  {itemQCTestList.length === 0 ? (
                    <p className="text-gray-500 text-sm">No QC tests assigned to this item.</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-gray-500">
                          <th className="text-left py-2">Test Name</th>
                          <th className="text-left py-2">Type</th>
                          <th className="text-right py-2">Target</th>
                          <th className="text-right py-2">Min</th>
                          <th className="text-right py-2">Max</th>
                          <th className="text-left py-2">UOM</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {itemQCTestList.map((iqt) => {
                          const def = qcTestDefList.find(d => d.id === iqt.qc_test_definition_id);
                          return (
                            <tr key={iqt.id} className="border-b">
                              <td className="py-2">{def?.name || `Test #${iqt.qc_test_definition_id}`}</td>
                              <td className="py-2"><span className={def?.test_type === 'pass_fail' ? 'badge-blue' : 'badge-yellow'}>{def?.test_type === 'pass_fail' ? 'Pass/Fail' : 'Range'}</span></td>
                              <td className="py-2 text-right">{iqt.target_value ?? '-'}</td>
                              <td className="py-2 text-right">{iqt.min_value ?? '-'}</td>
                              <td className="py-2 text-right">{iqt.max_value ?? '-'}</td>
                              <td className="py-2">{def?.uom_id ? getUomAbbrev(def.uom_id) || '-' : '-'}</td>
                              <td className="py-2">
                                <button className="text-red-500 text-xs hover:underline" onClick={() => removeItemQCTest.mutate({ itemId: editingItem!.id, assignmentId: iqt.id })}>Remove</button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}

                  <hr />
                  <p className="text-sm font-medium">Add QC Test</p>
                  <form onSubmit={(e) => {
                    e.preventDefault();
                    if (!qcAddForm.qc_test_definition_id) return;
                    addItemQCTest.mutate({
                      itemId: editingItem!.id,
                      data: {
                        qc_test_definition_id: qcAddForm.qc_test_definition_id,
                        target_value: qcAddForm.target_value ? Number(qcAddForm.target_value) : null,
                        min_value: qcAddForm.min_value ? Number(qcAddForm.min_value) : null,
                        max_value: qcAddForm.max_value ? Number(qcAddForm.max_value) : null,
                      },
                    });
                  }} className="grid grid-cols-5 gap-3 items-end">
                    <div>
                      <label className="block text-xs mb-1">Test</label>
                      <select className="input-field" value={qcAddForm.qc_test_definition_id || ''} onChange={(e) => setQcAddForm({ ...qcAddForm, qc_test_definition_id: Number(e.target.value) })} required>
                        <option value="">-- Select --</option>
                        {qcTestDefList.filter(d => !itemQCTestList.some(iqt => iqt.qc_test_definition_id === d.id)).map(d => (
                          <option key={d.id} value={d.id}>{d.name} ({d.test_type === 'pass_fail' ? 'P/F' : 'Range'})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs mb-1">Target</label>
                      <input type="number" step="any" className="input-field" value={qcAddForm.target_value} onChange={(e) => setQcAddForm({ ...qcAddForm, target_value: e.target.value })} />
                    </div>
                    <div>
                      <label className="block text-xs mb-1">Min</label>
                      <input type="number" step="any" className="input-field" value={qcAddForm.min_value} onChange={(e) => setQcAddForm({ ...qcAddForm, min_value: e.target.value })} />
                    </div>
                    <div>
                      <label className="block text-xs mb-1">Max</label>
                      <input type="number" step="any" className="input-field" value={qcAddForm.max_value} onChange={(e) => setQcAddForm({ ...qcAddForm, max_value: e.target.value })} />
                    </div>
                    <button type="submit" className="btn-primary text-sm" disabled={addItemQCTest.isPending}>Add</button>
                  </form>
                </div>
              )}
            </div>

            {/* ======== PACK EXTENSIONS TAB ======== */}
            <div style={{ display: activeTab === 'pack-extensions' ? 'block' : 'none' }}>
              {isExistingItem && (
                <div className="space-y-4">
                  {itemPackExtList.length === 0 ? (
                    <p className="text-gray-500 text-sm">No pack extensions assigned to this item.</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-gray-500">
                          <th className="text-left py-2">Extension Code</th>
                          <th className="text-left py-2">Name</th>
                          <th className="text-right py-2">Desired Fill Amount</th>
                          <th className="text-left py-2">Fill UOM</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {itemPackExtList.map((ipe) => {
                          const def = packExtDefList.find(d => d.id === ipe.pack_extension_id);
                          return (
                            <tr key={ipe.id} className="border-b">
                              <td className="py-2 font-mono">{def?.code || '-'}</td>
                              <td className="py-2">{def?.name || '-'}</td>
                              <td className="py-2 text-right">
                                <input type="number" step="0.0001" className="input-field w-28 text-right inline-block" value={ipe.desired_fill_amount ?? ''} onChange={(e) => {
                                  updateItemPackExt.mutate({
                                    itemId: editingItem!.id, ipeId: ipe.id,
                                    data: { desired_fill_amount: e.target.value ? Number(e.target.value) : null },
                                  });
                                }} />
                              </td>
                              <td className="py-2">{getUomAbbrev(ipe.fill_uom_id) || '-'}</td>
                              <td className="py-2">
                                <button className="text-red-500 text-xs hover:underline" onClick={() => removeItemPackExt.mutate({ itemId: editingItem!.id, ipeId: ipe.id })}>Remove</button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}

                  <hr />
                  <p className="text-sm font-medium">Add Pack Extension</p>
                  <form onSubmit={(e) => {
                    e.preventDefault();
                    if (!peAddForm.pack_extension_id) return;
                    addItemPackExt.mutate({
                      itemId: editingItem!.id,
                      data: {
                        pack_extension_id: peAddForm.pack_extension_id,
                        desired_fill_amount: peAddForm.desired_fill_amount ? Number(peAddForm.desired_fill_amount) : null,
                        fill_uom_id: peAddForm.fill_uom_id,
                      },
                    });
                  }} className="grid grid-cols-4 gap-3 items-end">
                    <div>
                      <label className="block text-xs mb-1">Pack Extension</label>
                      <select className="input-field" value={peAddForm.pack_extension_id || ''} onChange={(e) => setPeAddForm({ ...peAddForm, pack_extension_id: Number(e.target.value) })} required>
                        <option value="">-- Select --</option>
                        {packExtDefList.filter(d => !itemPackExtList.some(ipe => ipe.pack_extension_id === d.id)).map(d => (
                          <option key={d.id} value={d.id}>{d.code} - {d.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs mb-1">Desired Fill Amount</label>
                      <input type="number" step="0.0001" className="input-field" value={peAddForm.desired_fill_amount} onChange={(e) => setPeAddForm({ ...peAddForm, desired_fill_amount: e.target.value })} />
                    </div>
                    <div>
                      <label className="block text-xs mb-1">Fill UOM</label>
                      <select className="input-field" value={peAddForm.fill_uom_id || ''} onChange={(e) => setPeAddForm({ ...peAddForm, fill_uom_id: e.target.value ? Number(e.target.value) : null })}>
                        <option value="">-- Select --</option>
                        {uomList.map(u => <option key={u.id} value={u.id}>{u.abbreviation}</option>)}
                      </select>
                    </div>
                    <button type="submit" className="btn-primary text-sm" disabled={addItemPackExt.isPending}>Add</button>
                  </form>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Save / Cancel buttons */}
        <div className="flex justify-end gap-3 mt-4 pt-4 border-t">
          <button type="button" className="btn-secondary" onClick={closeForm}>Close</button>
          <button type="button" className="btn-primary" onClick={handleSave} disabled={saveItem.isPending}>
            {editingItem ? 'Save' : 'Create'}
          </button>
        </div>
      </Modal>
    </div>
  );
};

export default ItemsPage;
