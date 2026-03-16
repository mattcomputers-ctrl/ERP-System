import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { recipesAPI, inventoryAPI, salesAPI } from '../services/api';
import type { BatchTicket, Recipe, RecipeVersion, Item, Customer, PackExtensionDefinition } from '../types';

interface PackageRow {
  pack_extension_id: number;
  quantity: string;
}

const BatchTicketsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [ticketType, setTicketType] = useState<'batch' | 'repack'>('batch');
  const [filter, setFilter] = useState<string>('');

  // Form state
  const [formItemId, setFormItemId] = useState<number | null>(null);
  const [formRecipeId, setFormRecipeId] = useState<number | null>(null);
  const [formRecipeVersionId, setFormRecipeVersionId] = useState<number | null>(null);
  const [formQuantity, setFormQuantity] = useState('');
  const [formDueDate, setFormDueDate] = useState('');
  const [formCustomerId, setFormCustomerId] = useState<number | null>(null);
  const [formPackages, setFormPackages] = useState<PackageRow[]>([]);
  const [formNotes, setFormNotes] = useState('');
  const [formOverride, setFormOverride] = useState(false);

  // Detail view
  const [viewingTicket, setViewingTicket] = useState<BatchTicket | null>(null);

  const { data: tickets } = useQuery({
    queryKey: ['batch-tickets', filter],
    queryFn: () => recipesAPI.listBatchTickets(filter ? { ticket_type: filter } : undefined),
  });
  const { data: recipes } = useQuery({ queryKey: ['recipes'], queryFn: () => recipesAPI.list() });
  const { data: itemsList } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: customers } = useQuery({ queryKey: ['customers'], queryFn: () => salesAPI.listCustomers() });
  const { data: packExtDefs } = useQuery({ queryKey: ['pack-extension-definitions'], queryFn: () => inventoryAPI.listPackExtensionDefinitions() });

  const items: Item[] = itemsList?.data || [];
  const recipeList: Recipe[] = recipes?.data || [];
  const customerList: Customer[] = customers?.data || [];
  const packExts: PackExtensionDefinition[] = packExtDefs?.data || [];

  const getItemCode = (id: number) => items.find(i => i.id === id)?.item_code || '?';
  const getItemName = (id: number) => items.find(i => i.id === id)?.name || '?';
  const getCustomerName = (id: number | null) => id ? customerList.find(c => c.id === id)?.name || '?' : '-';

  // Get recipes for selected item
  const recipesForItem = formItemId ? recipeList.filter(r => r.product_item_id === formItemId) : [];
  const selectedRecipe = formRecipeId ? recipeList.find(r => r.id === formRecipeId) : null;
  const publishedVersions = selectedRecipe?.versions.filter(v => v.status === 'published') || [];

  const resetForm = () => {
    setFormItemId(null);
    setFormRecipeId(null);
    setFormRecipeVersionId(null);
    setFormQuantity('');
    setFormDueDate('');
    setFormCustomerId(null);
    setFormPackages([]);
    setFormNotes('');
    setFormOverride(false);
  };

  const createTicket = useMutation({
    mutationFn: (data: any) => recipesAPI.createBatchTicket(data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['batch-tickets'] });
      const ticket = res.data as BatchTicket;
      if (ticket.has_shortage && !ticket.shortage_override) {
        toast.error('Material shortage detected! Review shortage details or override.');
        setViewingTicket(ticket);
      } else {
        toast.success(`${ticketType === 'batch' ? 'Batch' : 'Repack'} ticket created`);
      }
      setShowForm(false);
      resetForm();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to create ticket'),
  });

  const handleCreate = () => {
    if (!formItemId || !formQuantity) {
      toast.error('Item and quantity are required');
      return;
    }
    createTicket.mutate({
      ticket_type: ticketType,
      recipe_id: formRecipeId,
      recipe_version_id: formRecipeVersionId,
      item_id: formItemId,
      planned_quantity: Number(formQuantity),
      due_date: formDueDate || null,
      customer_id: formCustomerId,
      shortage_override: formOverride,
      notes: formNotes || null,
      packages: formPackages.filter(p => p.pack_extension_id && p.quantity).map(p => ({
        pack_extension_id: p.pack_extension_id,
        quantity: Number(p.quantity),
      })),
    });
  };

  const statusColor = (s: string) => {
    switch (s) {
      case 'draft': return 'badge-yellow';
      case 'planned': return 'badge-blue';
      case 'in_progress': return 'badge-yellow';
      case 'completed': return 'badge-green';
      case 'cancelled': return 'badge-red';
      default: return '';
    }
  };

  const columns = [
    { header: 'Ticket #', accessor: 'ticket_number' as keyof BatchTicket },
    { header: 'Type', accessor: ((row: BatchTicket) => (
      <span className={row.ticket_type === 'batch' ? 'badge-blue' : 'badge-yellow'}>{row.ticket_type}</span>
    )) },
    { header: 'Item', accessor: ((row: BatchTicket) => getItemCode(row.item_id)) },
    { header: 'Description', accessor: ((row: BatchTicket) => getItemName(row.item_id)) },
    { header: 'Qty', accessor: ((row: BatchTicket) => Number(row.planned_quantity).toFixed(2)) },
    { header: 'Due Date', accessor: ((row: BatchTicket) => row.due_date ? new Date(row.due_date).toLocaleDateString() : '-') },
    { header: 'Customer', accessor: ((row: BatchTicket) => getCustomerName(row.customer_id)) },
    { header: 'Shortage', accessor: ((row: BatchTicket) => row.has_shortage
      ? <span className="badge-red">Yes{row.shortage_override ? ' (Override)' : ''}</span>
      : <span className="badge-green">No</span>
    ) },
    { header: 'Status', accessor: ((row: BatchTicket) => <span className={statusColor(row.status)}>{row.status}</span>) },
    { header: 'Actions', accessor: ((row: BatchTicket) => (
      <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); setViewingTicket(row); }}>View</button>
    )) },
  ];

  return (
    <div>
      <PageHeader
        title="Batch & Repack Tickets"
        subtitle="Plan batch production and repack operations"
        actions={
          <div className="flex gap-2">
            <button className="btn-primary" onClick={() => { setTicketType('batch'); resetForm(); setShowForm(true); }}>New Batch Ticket</button>
            <button className="btn-secondary" onClick={() => { setTicketType('repack'); resetForm(); setShowForm(true); }}>New Repack Ticket</button>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        {['', 'batch', 'repack'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-md text-sm ${filter === f ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
          >{f || 'All'}</button>
        ))}
      </div>

      <div className="card">
        <DataTable columns={columns} data={tickets?.data || []} />
      </div>

      {/* Create Ticket Modal */}
      <Modal isOpen={showForm} onClose={() => { setShowForm(false); resetForm(); }}
        title={ticketType === 'batch' ? 'New Batch Ticket' : 'New Repack Ticket'} size="xl"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Product Item</label>
              <select className="input-field" value={formItemId || ''} onChange={(e) => {
                setFormItemId(e.target.value ? Number(e.target.value) : null);
                setFormRecipeId(null);
                setFormRecipeVersionId(null);
              }}>
                <option value="">-- Select Item --</option>
                {items.filter(i => i.item_type === 'finished_good' || i.item_type === 'intermediate').map(i => (
                  <option key={i.id} value={i.id}>{i.item_code} - {i.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Quantity</label>
              <input type="number" step="0.01" className="input-field" value={formQuantity}
                onChange={(e) => setFormQuantity(e.target.value)} placeholder="How much to make" />
            </div>
          </div>

          {ticketType === 'batch' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Recipe</label>
                <select className="input-field" value={formRecipeId || ''} onChange={(e) => {
                  setFormRecipeId(e.target.value ? Number(e.target.value) : null);
                  setFormRecipeVersionId(null);
                }}>
                  <option value="">-- Select Recipe --</option>
                  {recipesForItem.map(r => (
                    <option key={r.id} value={r.id}>
                      {getItemCode(r.product_item_id)} ({r.versions.length} version{r.versions.length !== 1 ? 's' : ''})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Recipe Version</label>
                <select className="input-field" value={formRecipeVersionId || ''} onChange={(e) => setFormRecipeVersionId(e.target.value ? Number(e.target.value) : null)}>
                  <option value="">-- Select Version --</option>
                  {publishedVersions.map(v => (
                    <option key={v.id} value={v.id}>
                      .{String(v.version_number).padStart(2, '0')} (published)
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Due Date</label>
              <input type="date" className="input-field" value={formDueDate} onChange={(e) => setFormDueDate(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Customer</label>
              <select className="input-field" value={formCustomerId || ''} onChange={(e) => setFormCustomerId(e.target.value ? Number(e.target.value) : null)}>
                <option value="">-- None --</option>
                {customerList.map(c => <option key={c.id} value={c.id}>{c.code} - {c.name}</option>)}
              </select>
            </div>
          </div>

          {/* Packages */}
          <div>
            <label className="block text-sm font-medium mb-1">Packages</label>
            {formPackages.map((pkg, idx) => (
              <div key={idx} className="flex gap-2 mb-2 items-center">
                <select className="input-field flex-1" value={pkg.pack_extension_id || ''}
                  onChange={(e) => {
                    const newPkgs = [...formPackages];
                    newPkgs[idx] = { ...newPkgs[idx], pack_extension_id: Number(e.target.value) };
                    setFormPackages(newPkgs);
                  }}>
                  <option value="">-- Select Pack --</option>
                  {packExts.map(pe => <option key={pe.id} value={pe.id}>{pe.code} - {pe.name}</option>)}
                </select>
                <input type="number" className="input-field w-28" placeholder="Qty" value={pkg.quantity}
                  onChange={(e) => {
                    const newPkgs = [...formPackages];
                    newPkgs[idx] = { ...newPkgs[idx], quantity: e.target.value };
                    setFormPackages(newPkgs);
                  }} />
                <button className="text-red-500 text-xs" onClick={() => setFormPackages(formPackages.filter((_, i) => i !== idx))}>Remove</button>
              </div>
            ))}
            <button type="button" className="text-sm text-blue-600 hover:underline"
              onClick={() => setFormPackages([...formPackages, { pack_extension_id: 0, quantity: '' }])}>
              + Add Package
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Notes</label>
            <textarea className="input-field" rows={2} value={formNotes} onChange={(e) => setFormNotes(e.target.value)} />
          </div>

          <div className="flex items-center gap-2">
            <input type="checkbox" id="shortage_override" checked={formOverride}
              onChange={(e) => setFormOverride(e.target.checked)} />
            <label htmlFor="shortage_override" className="text-sm">Override material shortage (if any)</label>
          </div>

          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => { setShowForm(false); resetForm(); }}>Cancel</button>
            <button type="button" className="btn-primary" onClick={handleCreate} disabled={createTicket.isPending}>
              Create Ticket
            </button>
          </div>
        </div>
      </Modal>

      {/* Detail View Modal */}
      <Modal isOpen={!!viewingTicket} onClose={() => setViewingTicket(null)}
        title={viewingTicket ? `Ticket: ${viewingTicket.ticket_number}` : ''} size="xl"
      >
        {viewingTicket && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div><span className="font-medium text-gray-500">Type:</span> <span className={viewingTicket.ticket_type === 'batch' ? 'badge-blue' : 'badge-yellow'}>{viewingTicket.ticket_type}</span></div>
              <div><span className="font-medium text-gray-500">Status:</span> <span className={statusColor(viewingTicket.status)}>{viewingTicket.status}</span></div>
              <div><span className="font-medium text-gray-500">Item:</span> {getItemCode(viewingTicket.item_id)} - {getItemName(viewingTicket.item_id)}</div>
              <div><span className="font-medium text-gray-500">Quantity:</span> {Number(viewingTicket.planned_quantity).toFixed(2)}</div>
              <div><span className="font-medium text-gray-500">Due:</span> {viewingTicket.due_date ? new Date(viewingTicket.due_date).toLocaleDateString() : '-'}</div>
              <div><span className="font-medium text-gray-500">Customer:</span> {getCustomerName(viewingTicket.customer_id)}</div>
            </div>

            {viewingTicket.has_shortage && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <h4 className="text-sm font-semibold text-red-800 mb-2">Material Shortage</h4>
                {viewingTicket.shortage_details && (
                  <table className="w-full text-sm">
                    <thead><tr className="text-red-600"><th className="text-left">Item</th><th className="text-right">Required</th><th className="text-right">Available</th><th className="text-right">Short</th></tr></thead>
                    <tbody>
                      {JSON.parse(viewingTicket.shortage_details).map((s: any, i: number) => (
                        <tr key={i} className="border-t border-red-100">
                          <td>{s.item_code}</td>
                          <td className="text-right">{s.required.toFixed(2)}</td>
                          <td className="text-right">{s.available.toFixed(2)}</td>
                          <td className="text-right text-red-600 font-semibold">{s.short.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {viewingTicket.shortage_override && (
                  <p className="text-xs text-red-600 mt-2 font-medium">Override active - proceeding despite shortage.</p>
                )}
              </div>
            )}

            {viewingTicket.planned_materials.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Planned Materials</h4>
                <table className="w-full text-sm">
                  <thead><tr className="border-b text-gray-500"><th className="text-left py-1">Item</th><th className="text-right py-1">Planned</th><th className="text-right py-1">Available</th><th className="py-1">Status</th></tr></thead>
                  <tbody>
                    {viewingTicket.planned_materials.map(m => (
                      <tr key={m.id} className="border-b">
                        <td className="py-1">{getItemCode(m.item_id)} - {getItemName(m.item_id)}</td>
                        <td className="py-1 text-right">{Number(m.planned_quantity).toFixed(2)}</td>
                        <td className="py-1 text-right">{m.available_quantity != null ? Number(m.available_quantity).toFixed(2) : '-'}</td>
                        <td className="py-1">{m.has_shortage ? <span className="badge-red">Short</span> : <span className="badge-green">OK</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {viewingTicket.packages.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Packages</h4>
                <table className="w-full text-sm">
                  <thead><tr className="border-b text-gray-500"><th className="text-left py-1">Pack Extension</th><th className="text-right py-1">Quantity</th></tr></thead>
                  <tbody>
                    {viewingTicket.packages.map(p => {
                      const pe = packExts.find(e => e.id === p.pack_extension_id);
                      return (
                        <tr key={p.id} className="border-b">
                          <td className="py-1">{pe ? `${pe.code} - ${pe.name}` : `Pack #${p.pack_extension_id}`}</td>
                          <td className="py-1 text-right">{Number(p.quantity).toFixed(2)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default BatchTicketsPage;
