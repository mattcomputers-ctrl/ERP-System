import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { manufacturingAPI } from '../services/api';
import { getStatusColor, formatNumber } from '../utils/helpers';
import type { Formula, FormulaVersion, ProductionOrder } from '../types';

const ManufacturingPage: React.FC = () => {
  const [tab, setTab] = useState<'production' | 'formulas'>('production');
  const [selectedFormula, setSelectedFormula] = useState<Formula | null>(null);
  const [showVersions, setShowVersions] = useState(false);
  const [showRevert, setShowRevert] = useState(false);
  const [revertTargetId, setRevertTargetId] = useState<number | null>(null);
  const [revertReason, setRevertReason] = useState('');
  const queryClient = useQueryClient();

  const { data: prodOrders } = useQuery({ queryKey: ['prod-orders'], queryFn: () => manufacturingAPI.listProductionOrders() });
  const { data: formulas } = useQuery({ queryKey: ['formulas'], queryFn: () => manufacturingAPI.listFormulas() });

  const { data: versions } = useQuery({
    queryKey: ['formula-versions', selectedFormula?.id],
    queryFn: () => manufacturingAPI.listVersions(selectedFormula!.id),
    enabled: !!selectedFormula && showVersions,
  });

  const revertVersion = useMutation({
    mutationFn: () => manufacturingAPI.revertVersion(selectedFormula!.id, revertTargetId!, revertReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['formula-versions', selectedFormula?.id] });
      queryClient.invalidateQueries({ queryKey: ['formulas'] });
      setShowRevert(false);
      setRevertReason('');
      setRevertTargetId(null);
      toast.success('Version reverted successfully');
    },
    onError: () => toast.error('Failed to revert version'),
  });

  const prodColumns = [
    { header: 'Order #', accessor: 'order_number' as keyof ProductionOrder },
    { header: 'Planned Qty', accessor: ((row: ProductionOrder) => formatNumber(row.planned_quantity)) },
    { header: 'Actual Qty', accessor: ((row: ProductionOrder) => row.actual_quantity ? formatNumber(row.actual_quantity) : '-') },
    { header: 'Yield %', accessor: ((row: ProductionOrder) => row.yield_percent ? `${formatNumber(row.yield_percent)}%` : '-') },
    { header: 'Status', accessor: ((row: ProductionOrder) => <span className={getStatusColor(row.status)}>{row.status.replace('_', ' ')}</span>) },
  ];

  const formulaColumns = [
    { header: 'Code', accessor: 'code' as keyof Formula },
    { header: 'Name', accessor: 'name' as keyof Formula },
    { header: 'Versions', accessor: ((row: Formula) => row.versions?.length || 0) },
    { header: 'Status', accessor: ((row: Formula) => <span className={row.is_active ? 'badge-green' : 'badge-red'}>{row.is_active ? 'Active' : 'Inactive'}</span>) },
    { header: 'Actions', accessor: ((row: Formula) => (
      <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); setSelectedFormula(row); setShowVersions(true); }}>
        Version History
      </button>
    )) },
  ];

  const versionList: FormulaVersion[] = versions?.data || [];

  return (
    <div>
      <PageHeader title="Manufacturing" subtitle="Manage formulas, production orders, and batch processing" />

      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {(['production', 'formulas'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {t === 'production' ? 'Production Orders' : 'Formulas'}
          </button>
        ))}
      </div>

      <div className="card">
        {tab === 'production' && <DataTable columns={prodColumns} data={prodOrders?.data || []} />}
        {tab === 'formulas' && <DataTable columns={formulaColumns} data={formulas?.data || []} />}
      </div>

      {/* Version History Modal */}
      <Modal isOpen={showVersions} onClose={() => { setShowVersions(false); setSelectedFormula(null); }} title={`Version History - ${selectedFormula?.code || ''}`}>
        <div className="space-y-3">
          {versionList.length === 0 ? (
            <p className="text-gray-500 text-sm">No versions found.</p>
          ) : (
            <div className="max-h-96 overflow-y-auto space-y-2">
              {versionList.map((v: FormulaVersion) => (
                <div key={v.id} className={`p-3 rounded-lg border ${v.is_current ? 'border-blue-300 bg-blue-50' : 'border-gray-200'}`}>
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">Version {v.version_number}</span>
                        {v.is_current && <span className="badge-green text-xs">Current</span>}
                        {v.reverted_from_version_id && <span className="badge-yellow text-xs">Reverted</span>}
                      </div>
                      <div className="text-sm text-gray-600 mt-1">
                        Batch Size: {formatNumber(v.batch_size)} | Yield: {formatNumber(v.expected_yield_percent)}%
                      </div>
                      {v.change_reason && (
                        <div className="text-sm text-gray-500 mt-1 italic">Reason: {v.change_reason}</div>
                      )}
                      <div className="text-xs text-gray-400 mt-1">
                        {v.ingredients?.length || 0} ingredients
                        {v.reverted_from_version_id && ` | Reverted from v${versionList.find((vv: FormulaVersion) => vv.id === v.reverted_from_version_id)?.version_number || '?'}`}
                      </div>
                    </div>
                    {!v.is_current && (
                      <button
                        className="text-sm text-orange-600 hover:underline whitespace-nowrap"
                        onClick={() => { setRevertTargetId(v.id); setShowRevert(true); }}
                      >
                        Revert to this
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>

      {/* Revert Confirmation Modal */}
      <Modal isOpen={showRevert} onClose={() => { setShowRevert(false); setRevertReason(''); setRevertTargetId(null); }} title="Revert Formula Version">
        <form onSubmit={(e) => { e.preventDefault(); revertVersion.mutate(); }} className="space-y-4">
          <p className="text-sm text-gray-600">
            This will create a new version based on the selected version. The current version will be deactivated.
          </p>
          <div>
            <label className="block text-sm font-medium mb-1">Reason for Revert <span className="text-red-500">*</span></label>
            <textarea
              className="input-field"
              rows={3}
              value={revertReason}
              onChange={(e) => setRevertReason(e.target.value)}
              placeholder="Explain why this version is being reverted..."
              required
            />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={() => { setShowRevert(false); setRevertReason(''); }}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={revertVersion.isPending || !revertReason.trim()}>
              {revertVersion.isPending ? 'Reverting...' : 'Confirm Revert'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default ManufacturingPage;
