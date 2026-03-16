import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { recipesAPI, inventoryAPI } from '../services/api';
import type { BatchTicket, BatchExecution, Item, Lot, QCTestAssignment, BatchExecutionQCResult } from '../types';

interface ConsumptionEntry {
  item_id: number;
  lot_id: number | null;
  actual_quantity: string;
  planned_quantity: number;
}

interface QCEntry {
  qc_test_definition_id: number;
  test_name: string;
  test_type: string;
  method: string | null;
  target_value: number | null;
  min_value: number | null;
  max_value: number | null;
  result_value: string;
  result_text: string;
  passed: boolean | null;
  notes: string;
}

type ExecutionStep = 'consume' | 'qc' | 'complete';

const BatchExecutionPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedTicket, setSelectedTicket] = useState<BatchTicket | null>(null);
  const [execution, setExecution] = useState<BatchExecution | null>(null);
  const [showExecute, setShowExecute] = useState(false);
  const [executionStep, setExecutionStep] = useState<ExecutionStep>('consume');

  // Consumption form
  const [consumptions, setConsumptions] = useState<ConsumptionEntry[]>([]);

  // QC form
  const [qcEntries, setQcEntries] = useState<QCEntry[]>([]);
  const [qcTestsLoaded, setQcTestsLoaded] = useState(false);

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

  const loadQCTests = async (ticketId: number, existingResults?: BatchExecutionQCResult[]) => {
    try {
      const res = await recipesAPI.getExecutionQCTests(ticketId);
      const tests: QCTestAssignment[] = res.data;
      setQcEntries(tests.map(t => {
        const existing = existingResults?.find(r => r.qc_test_definition_id === t.qc_test_definition_id);
        return {
          qc_test_definition_id: t.qc_test_definition_id,
          test_name: t.test_name,
          test_type: t.test_type,
          method: t.method,
          target_value: t.target_value,
          min_value: t.min_value,
          max_value: t.max_value,
          result_value: existing?.result_value != null ? String(existing.result_value) : '',
          result_text: existing?.result_text || '',
          passed: existing?.passed ?? null,
          notes: existing?.notes || '',
        };
      }));
      setQcTestsLoaded(true);
    } catch {
      setQcEntries([]);
      setQcTestsLoaded(true);
    }
  };

  const startExecution = useMutation({
    mutationFn: (ticketId: number) => recipesAPI.startExecution(ticketId, {}),
    onSuccess: (res) => {
      const exec = res.data as BatchExecution;
      setExecution(exec);
      if (selectedTicket) {
        setConsumptions(selectedTicket.planned_materials.map(m => ({
          item_id: m.item_id,
          lot_id: null,
          actual_quantity: String(Number(m.planned_quantity).toFixed(4)),
          planned_quantity: Number(m.planned_quantity),
        })));
        loadQCTests(selectedTicket.id);
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
      if (selectedTicket) {
        loadQCTests(selectedTicket.id, exec.qc_results);
      }
    },
    onError: () => {
      setExecution(null);
      if (selectedTicket) {
        setConsumptions(selectedTicket.planned_materials.map(m => ({
          item_id: m.item_id,
          lot_id: null,
          actual_quantity: String(Number(m.planned_quantity).toFixed(4)),
          planned_quantity: Number(m.planned_quantity),
        })));
        loadQCTests(selectedTicket.id);
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
      setExecutionStep('qc');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to record consumption'),
  });

  const saveQCResults = useMutation({
    mutationFn: () => {
      if (!selectedTicket) throw new Error('No ticket');
      return recipesAPI.recordExecutionQCResults(selectedTicket.id, {
        results: qcEntries.map(e => ({
          qc_test_definition_id: e.qc_test_definition_id,
          target_value: e.target_value,
          min_value: e.min_value,
          max_value: e.max_value,
          result_value: e.result_value ? Number(e.result_value) : null,
          result_text: e.result_text || null,
          passed: e.passed,
          notes: e.notes || null,
        })),
      });
    },
    onSuccess: () => {
      toast.success('QC results saved');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to save QC results'),
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
      setQcTestsLoaded(false);
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to complete execution'),
  });

  const createCOA = useMutation({
    mutationFn: () => {
      if (!selectedTicket) throw new Error('No ticket');
      return recipesAPI.createCOAFromExecution(selectedTicket.id, {
        customer_id: selectedTicket.customer_id || undefined,
      });
    },
    onSuccess: (res) => {
      toast.success(`COA created: ${res.data.certificate_number}`);
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to create COA'),
  });

  const openExecution = (ticket: BatchTicket) => {
    setSelectedTicket(ticket);
    setShowExecute(true);
    setExecutionStep('consume');
    setQcTestsLoaded(false);
    setQcEntries([]);
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
      loadQCTests(ticket.id);
    }
  };

  const getAvailableLots = (itemId: number) =>
    lotList.filter(l => l.item_id === itemId && Number(l.quantity_on_hand) > 0 && l.status === 'available');

  // Auto-calculate pass/fail for QC entries
  const updateQCResult = (idx: number, value: string) => {
    const newEntries = [...qcEntries];
    const entry = { ...newEntries[idx], result_value: value };
    if (value && entry.test_type === 'range') {
      const numVal = Number(value);
      if (entry.min_value != null && entry.max_value != null) {
        entry.passed = numVal >= entry.min_value && numVal <= entry.max_value;
      } else if (entry.min_value != null) {
        entry.passed = numVal >= entry.min_value;
      } else if (entry.max_value != null) {
        entry.passed = numVal <= entry.max_value;
      }
    }
    newEntries[idx] = entry;
    setQcEntries(newEntries);
  };

  const updateQCPassFail = (idx: number, passed: boolean) => {
    const newEntries = [...qcEntries];
    newEntries[idx] = { ...newEntries[idx], passed };
    setQcEntries(newEntries);
  };

  const allQCPassed = qcEntries.length > 0 && qcEntries.every(e => e.passed === true);
  const anyQCFailed = qcEntries.some(e => e.passed === false);
  const qcComplete = qcEntries.length > 0 && qcEntries.every(e => e.passed !== null);

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

  const stepTabs: { id: ExecutionStep; label: string }[] = [
    { id: 'consume', label: '1. Consumption' },
    { id: 'qc', label: '2. QC Check' },
    { id: 'complete', label: '3. Output & Complete' },
  ];

  return (
    <div>
      <PageHeader
        title="Batch / Repack Execution"
        subtitle="Execute batch and repack tickets - record consumption, QC results, and output"
      />
      <div className="card">
        <DataTable columns={columns} data={executableTickets} />
      </div>

      {/* Execution Modal */}
      <Modal isOpen={showExecute} onClose={() => { setShowExecute(false); setSelectedTicket(null); setExecution(null); setQcTestsLoaded(false); }}
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
                <p className="text-gray-500 mb-3">Start execution to record consumption, QC results, and output.</p>
                <button className="btn-primary" onClick={() => startExecution.mutate(selectedTicket.id)}
                  disabled={startExecution.isPending}>
                  Start Execution
                </button>
              </div>
            )}

            {/* Step tabs */}
            {(execution || selectedTicket.status === 'in_progress') && (
              <>
                <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
                  {stepTabs.map(t => (
                    <button key={t.id} onClick={() => setExecutionStep(t.id)}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                        executionStep === t.id ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >{t.label}</button>
                  ))}
                </div>

                {/* ===== STEP 1: CONSUMPTION ===== */}
                {executionStep === 'consume' && (
                  <div className="space-y-4">
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
                            <td className="py-2">{getItemCode(c.item_id)} - {getItemName(c.item_id)}</td>
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
                    <div className="flex justify-end">
                      <button className="btn-primary text-sm" onClick={() => recordConsumption.mutate()}
                        disabled={recordConsumption.isPending}>
                        Record Consumption & Next
                      </button>
                    </div>
                  </div>
                )}

                {/* ===== STEP 2: QC CHECK ===== */}
                {executionStep === 'qc' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-gray-700">Quality Control Check</h4>
                      {qcComplete && (
                        <div className={`text-sm font-semibold ${allQCPassed ? 'text-green-600' : 'text-red-600'}`}>
                          {allQCPassed ? 'All tests PASSED' : 'Some tests FAILED'}
                        </div>
                      )}
                    </div>

                    {!qcTestsLoaded ? (
                      <p className="text-gray-400 text-sm text-center py-4">Loading QC tests...</p>
                    ) : qcEntries.length === 0 ? (
                      <div className="bg-gray-50 rounded-lg p-6 text-center">
                        <p className="text-gray-500 text-sm">No QC tests assigned to this item.</p>
                        <p className="text-gray-400 text-xs mt-1">Assign QC tests in the Item Setup to enable QC checks during execution.</p>
                        <button className="btn-secondary text-sm mt-3" onClick={() => setExecutionStep('complete')}>
                          Skip to Output
                        </button>
                      </div>
                    ) : (
                      <>
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b text-gray-500">
                              <th className="text-left py-2">Test</th>
                              <th className="text-left py-2">Method</th>
                              <th className="text-center py-2">Target</th>
                              <th className="text-center py-2">Min</th>
                              <th className="text-center py-2">Max</th>
                              <th className="text-center py-2">Result</th>
                              <th className="text-center py-2 w-24">Pass/Fail</th>
                            </tr>
                          </thead>
                          <tbody>
                            {qcEntries.map((entry, idx) => (
                              <tr key={idx} className={`border-b ${entry.passed === false ? 'bg-red-50' : entry.passed === true ? 'bg-green-50' : ''}`}>
                                <td className="py-2 font-medium">{entry.test_name}</td>
                                <td className="py-2 text-gray-500">{entry.method || '-'}</td>
                                <td className="py-2 text-center text-gray-500">{entry.target_value != null ? entry.target_value : '-'}</td>
                                <td className="py-2 text-center text-gray-500">{entry.min_value != null ? entry.min_value : '-'}</td>
                                <td className="py-2 text-center text-gray-500">{entry.max_value != null ? entry.max_value : '-'}</td>
                                <td className="py-2 text-center">
                                  {entry.test_type === 'range' ? (
                                    <input
                                      type="number" step="0.001"
                                      className="input-field w-28 text-center"
                                      value={entry.result_value}
                                      onChange={(e) => updateQCResult(idx, e.target.value)}
                                      placeholder="Enter value"
                                    />
                                  ) : (
                                    <input
                                      type="text"
                                      className="input-field w-28 text-center"
                                      value={entry.result_text}
                                      onChange={(e) => {
                                        const newEntries = [...qcEntries];
                                        newEntries[idx] = { ...newEntries[idx], result_text: e.target.value };
                                        setQcEntries(newEntries);
                                      }}
                                      placeholder="Result"
                                    />
                                  )}
                                </td>
                                <td className="py-2 text-center">
                                  {entry.test_type === 'pass_fail' ? (
                                    <div className="flex gap-1 justify-center">
                                      <button
                                        className={`px-2 py-1 rounded text-xs font-medium ${entry.passed === true ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-green-100'}`}
                                        onClick={() => updateQCPassFail(idx, true)}
                                      >Pass</button>
                                      <button
                                        className={`px-2 py-1 rounded text-xs font-medium ${entry.passed === false ? 'bg-red-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-red-100'}`}
                                        onClick={() => updateQCPassFail(idx, false)}
                                      >Fail</button>
                                    </div>
                                  ) : (
                                    entry.passed === true ? (
                                      <span className="badge-green">Pass</span>
                                    ) : entry.passed === false ? (
                                      <span className="badge-red">Fail</span>
                                    ) : (
                                      <span className="text-gray-400">-</span>
                                    )
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>

                        {anyQCFailed && (
                          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
                            One or more QC tests have failed. Review results before proceeding.
                          </div>
                        )}

                        <div className="flex justify-between">
                          <button className="btn-secondary text-sm" onClick={() => setExecutionStep('consume')}>
                            Back to Consumption
                          </button>
                          <div className="flex gap-2">
                            <button className="btn-primary text-sm" onClick={() => saveQCResults.mutate()}
                              disabled={saveQCResults.isPending}>
                              Save QC Results
                            </button>
                            <button
                              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                              onClick={() => {
                                saveQCResults.mutate();
                                setExecutionStep('complete');
                              }}
                            >
                              Save & Next
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {/* ===== STEP 3: OUTPUT & COMPLETE ===== */}
                {executionStep === 'complete' && (
                  <div className="space-y-4">
                    <h4 className="text-sm font-semibold text-gray-700">Record Output & Complete Execution</h4>

                    {/* QC Summary */}
                    {qcEntries.length > 0 && (
                      <div className={`rounded-lg p-3 text-sm border ${allQCPassed ? 'bg-green-50 border-green-200' : anyQCFailed ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'}`}>
                        <div className="flex items-center justify-between">
                          <span className="font-medium">
                            QC Status: {allQCPassed ? 'All Passed' : anyQCFailed ? 'Has Failures' : 'Incomplete'}
                          </span>
                          <span className="text-xs">
                            {qcEntries.filter(e => e.passed === true).length}/{qcEntries.length} passed
                          </span>
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">Output Lot Number</label>
                        <input className="input-field" value={outputLotNumber} onChange={(e) => setOutputLotNumber(e.target.value)} />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">Output Quantity (Yield)</label>
                        <input type="number" step="0.01" className="input-field" value={outputQuantity}
                          onChange={(e) => setOutputQuantity(e.target.value)} />
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
                        <input className="input-field" value={outputNotes} onChange={(e) => setOutputNotes(e.target.value)} />
                      </div>
                    </div>

                    <div className="flex justify-between">
                      <button className="btn-secondary text-sm" onClick={() => setExecutionStep('qc')}>
                        Back to QC Check
                      </button>
                      <div className="flex gap-2">
                        {execution?.status === 'completed' && qcEntries.length > 0 && (
                          <button
                            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                            onClick={() => createCOA.mutate()}
                            disabled={createCOA.isPending}
                          >
                            Create COA
                          </button>
                        )}
                        {execution?.status !== 'completed' && (
                          <button
                            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                            onClick={() => completeExecution.mutate()}
                            disabled={completeExecution.isPending || !outputLotNumber || !outputQuantity}
                          >
                            Complete Execution
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default BatchExecutionPage;
