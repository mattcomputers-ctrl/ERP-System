import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { recipesAPI, inventoryAPI } from '../services/api';
import type { BatchTicket, BatchExecution, Item, Lot } from '../types';

interface ConsumptionEntry {
  item_id: number;
  lot_id: number | null;
  actual_quantity: string;
  planned_quantity: number;
}

const BatchExecutionPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedTicket, setSelectedTicket] = useState<BatchTicket | null>(null);
  const [execution, setExecution] = useState<BatchExecution | null>(null);
  const [showExecute, setShowExecute] = useState(false);

  // Consumption form
  const [consumptions, setConsumptions] = useState<ConsumptionEntry[]>([]);

  // Output form
  const [showComplete, setShowComplete] = useState(false);
  const [outputLotNumber, setOutputLotNumber] = useState('');
  const [outputQuantity, setOutputQuantity] = useState('');
  const [outputWarehouseId, setOutputWarehouseId] = useState<number | null>(null);
  const [outputNotes, setOutputNotes] = useState('');

  const { data: tickets } = useQuery({
    queryKey: ['batch-tickets-executable'],
    queryFn: () => recipesAPI.listBatchTickets(),
  });
  const { data: itemsList } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: lots } = useQuery({ queryKey: ['lots'], queryFn: () => inventoryAPI.listLots() });
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: () => inventoryAPI.listWarehouses() });

  const items: Item[] = itemsList?.data || [];
  const lotList: Lot[] = lots?.data || [];

  const getItemCode = (id: number) => items.find(i => i.id === id)?.item_code || '?';
  const getItemName = (id: number) => items.find(i => i.id === id)?.name || '?';

  // Filter tickets that can be executed (draft/planned/in_progress)
  const executableTickets: BatchTicket[] = (tickets?.data || []).filter(
    (t: BatchTicket) => ['draft', 'planned', 'in_progress'].includes(t.status)
  );

  const startExecution = useMutation({
    mutationFn: (ticketId: number) => recipesAPI.startExecution(ticketId, {}),
    onSuccess: (res) => {
      const exec = res.data as BatchExecution;
      setExecution(exec);
      // Pre-populate consumptions from planned materials
      if (selectedTicket) {
        setConsumptions(selectedTicket.planned_materials.map(m => ({
          item_id: m.item_id,
          lot_id: null,
          actual_quantity: String(Number(m.planned_quantity).toFixed(4)),
          planned_quantity: Number(m.planned_quantity),
        })));
      }
      queryClient.invalidateQueries({ queryKey: ['batch-tickets-executable'] });
      toast.success('Execution started');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to start execution'),
  });

  const loadExecution = useMutation({
    mutationFn: (ticketId: number) => recipesAPI.getExecution(ticketId),
    onSuccess: (res) => {
      const exec = res.data as BatchExecution;
      setExecution(exec);
      setConsumptions(exec.consumptions.map(c => ({
        item_id: c.item_id,
        lot_id: c.lot_id,
        actual_quantity: String(Number(c.actual_quantity).toFixed(4)),
        planned_quantity: Number(c.planned_quantity || 0),
      })));
    },
    onError: () => {
      // No execution yet
      setExecution(null);
      if (selectedTicket) {
        setConsumptions(selectedTicket.planned_materials.map(m => ({
          item_id: m.item_id,
          lot_id: null,
          actual_quantity: String(Number(m.planned_quantity).toFixed(4)),
          planned_quantity: Number(m.planned_quantity),
        })));
      }
    },
  });

  const recordConsumption = useMutation({
    mutationFn: () => {
      if (!selectedTicket) throw new Error('No ticket');
      const validConsumptions = consumptions.filter(c => c.lot_id && Number(c.actual_quantity) > 0);
      return recipesAPI.recordConsumption(selectedTicket.id, {
        consumptions: validConsumptions.map(c => ({
          item_id: c.item_id,
          lot_id: c.lot_id!,
          actual_quantity: Number(c.actual_quantity),
        })),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lots'] });
      toast.success('Consumption recorded');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to record consumption'),
  });

  const completeExecution = useMutation({
    mutationFn: () => {
      if (!selectedTicket) throw new Error('No ticket');
      return recipesAPI.completeExecution(selectedTicket.id, {
        output: {
          lot_number: outputLotNumber,
          quantity: Number(outputQuantity),
          warehouse_id: outputWarehouseId,
        },
        notes: outputNotes || null,
      });
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['batch-tickets-executable'] });
      queryClient.invalidateQueries({ queryKey: ['lots'] });
      toast.success(`Batch completed! Yield: ${res.data.yield_percent.toFixed(1)}%`);
      setShowExecute(false);
      setShowComplete(false);
      setSelectedTicket(null);
      setExecution(null);
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to complete execution'),
  });

  const openExecution = (ticket: BatchTicket) => {
    setSelectedTicket(ticket);
    setShowExecute(true);
    if (ticket.status === 'in_progress') {
      loadExecution.mutate(ticket.id);
    } else {
      setExecution(null);
      setConsumptions(ticket.planned_materials.map(m => ({
        item_id: m.item_id,
        lot_id: null,
        actual_quantity: String(Number(m.planned_quantity).toFixed(4)),
        planned_quantity: Number(m.planned_quantity),
      })));
    }
  };

  const getAvailableLots = (itemId: number) =>
    lotList.filter(l => l.item_id === itemId && Number(l.quantity_on_hand) > 0 && l.status === 'available');

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
    { header: 'Item', accessor: ((row: BatchTicket) => `${getItemCode(row.item_id)} - ${getItemName(row.item_id)}`) },
    { header: 'Qty', accessor: ((row: BatchTicket) => Number(row.planned_quantity).toFixed(2)) },
    { header: 'Due', accessor: ((row: BatchTicket) => row.due_date ? new Date(row.due_date).toLocaleDateString() : '-') },
    { header: 'Status', accessor: ((row: BatchTicket) => <span className={statusColor(row.status)}>{row.status}</span>) },
    { header: 'Actions', accessor: ((row: BatchTicket) => (
      <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openExecution(row); }}>
        {row.status === 'in_progress' ? 'Continue' : 'Execute'}
      </button>
    )) },
  ];

  return (
    <div>
      <PageHeader
        title="Batch / Repack Execution"
        subtitle="Execute batch and repack tickets - record consumption and output"
      />
      <div className="card">
        <DataTable columns={columns} data={executableTickets} />
      </div>

      {/* Execution Modal */}
      <Modal isOpen={showExecute} onClose={() => { setShowExecute(false); setSelectedTicket(null); setExecution(null); }}
        title={selectedTicket ? `Execute: ${selectedTicket.ticket_number}` : ''} size="xl"
      >
        {selectedTicket && (
          <div className="space-y-4">
            {/* Ticket info */}
            <div className="grid grid-cols-3 gap-4 text-sm bg-gray-50 p-3 rounded">
              <div><span className="font-medium text-gray-500">Item:</span> {getItemCode(selectedTicket.item_id)} - {getItemName(selectedTicket.item_id)}</div>
              <div><span className="font-medium text-gray-500">Planned Qty:</span> {Number(selectedTicket.planned_quantity).toFixed(2)}</div>
              <div><span className="font-medium text-gray-500">Status:</span> <span className={statusColor(selectedTicket.status)}>{selectedTicket.status}</span></div>
            </div>

            {/* Start execution if not started */}
            {selectedTicket.status !== 'in_progress' && !execution && (
              <div className="text-center py-4">
                <p className="text-gray-500 mb-3">Start execution to record consumption and output.</p>
                <button className="btn-primary" onClick={() => startExecution.mutate(selectedTicket.id)}
                  disabled={startExecution.isPending}>
                  Start Execution
                </button>
              </div>
            )}

            {/* Consumption entry */}
            {(execution || selectedTicket.status === 'in_progress') && (
              <>
                <h4 className="text-sm font-semibold text-gray-700">Material Consumption</h4>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-gray-500">
                      <th className="text-left py-2">Item</th>
                      <th className="text-left py-2">Lot</th>
                      <th className="text-right py-2">Planned</th>
                      <th className="text-right py-2">Actual</th>
                    </tr>
                  </thead>
                  <tbody>
                    {consumptions.map((c, idx) => (
                      <tr key={idx} className="border-b">
                        <td className="py-2">{getItemCode(c.item_id)}</td>
                        <td className="py-2">
                          <select className="input-field w-48" value={c.lot_id || ''}
                            onChange={(e) => {
                              const newC = [...consumptions];
                              newC[idx] = { ...newC[idx], lot_id: e.target.value ? Number(e.target.value) : null };
                              setConsumptions(newC);
                            }}>
                            <option value="">-- Select Lot --</option>
                            {getAvailableLots(c.item_id).map(l => (
                              <option key={l.id} value={l.id}>{l.lot_number} (Avail: {Number(l.quantity_on_hand).toFixed(2)})</option>
                            ))}
                          </select>
                        </td>
                        <td className="py-2 text-right text-gray-500">{c.planned_quantity.toFixed(2)}</td>
                        <td className="py-2 text-right">
                          <input type="number" step="0.01" className="input-field w-28 text-right"
                            value={c.actual_quantity}
                            onChange={(e) => {
                              const newC = [...consumptions];
                              newC[idx] = { ...newC[idx], actual_quantity: e.target.value };
                              setConsumptions(newC);
                            }} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="flex gap-2">
                  <button className="btn-primary text-sm" onClick={() => recordConsumption.mutate()}
                    disabled={recordConsumption.isPending}>
                    Record Consumption
                  </button>
                  <button className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                    onClick={() => setShowComplete(true)}>
                    Complete &amp; Record Output
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </Modal>

      {/* Complete Output Modal */}
      <Modal isOpen={showComplete} onClose={() => setShowComplete(false)} title="Record Output & Complete">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Output Lot Number</label>
            <input className="input-field" value={outputLotNumber} onChange={(e) => setOutputLotNumber(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Output Quantity (Yield)</label>
            <input type="number" step="0.01" className="input-field" value={outputQuantity}
              onChange={(e) => setOutputQuantity(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Output Warehouse</label>
            <select className="input-field" value={outputWarehouseId || ''} onChange={(e) => setOutputWarehouseId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">-- Select --</option>
              {(warehouses?.data || []).map((w: any) => (
                <option key={w.id} value={w.id}>{w.code} - {w.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Notes</label>
            <textarea className="input-field" rows={2} value={outputNotes} onChange={(e) => setOutputNotes(e.target.value)} />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => setShowComplete(false)}>Cancel</button>
            <button type="button" className="btn-primary" onClick={() => completeExecution.mutate()}
              disabled={completeExecution.isPending || !outputLotNumber || !outputQuantity}>
              Complete Execution
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default BatchExecutionPage;
