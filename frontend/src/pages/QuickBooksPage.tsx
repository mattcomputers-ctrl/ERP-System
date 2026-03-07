import React, { useState, useEffect, useCallback } from 'react';
import { quickbooksAPI } from '../services/api';
import type { QBSyncStatus, QBPendingSync } from '../types';

const QuickBooksPage: React.FC = () => {
  const [syncStatus, setSyncStatus] = useState<QBSyncStatus | null>(null);
  const [pending, setPending] = useState<QBPendingSync | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResults, setSyncResults] = useState<any[]>([]);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [previewEntity, setPreviewEntity] = useState({ type: 'customer', id: '' });
  const [previewXml, setPreviewXml] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const [statusRes, pendingRes] = await Promise.all([
        quickbooksAPI.getStatus(),
        quickbooksAPI.getPending(),
      ]);
      setSyncStatus(statusRes.data);
      setPending(pendingRes.data);
    } catch { /* ignore */ }
  }, []);

  const loadResults = useCallback(async () => {
    try {
      const res = await quickbooksAPI.getSyncResults();
      setSyncResults(res.data.results || []);
      setLastSync(res.data.last_sync);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadStatus();
    loadResults();
  }, [loadStatus, loadResults]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await quickbooksAPI.triggerSync();
      setSyncResults(res.data.results || []);
      setLastSync(new Date().toISOString());
      loadStatus();
    } catch { /* ignore */ }
    finally { setSyncing(false); }
  };

  const handlePreview = async () => {
    if (!previewEntity.id) return;
    try {
      const res = await quickbooksAPI.previewQbxml(previewEntity.type, parseInt(previewEntity.id));
      setPreviewXml(res.data.qbxml);
    } catch (err: any) {
      setPreviewXml(`Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">QuickBooks Enterprise Sync</h1>
          <p className="text-sm text-gray-500">Synchronize data with QuickBooks Desktop via qbXML</p>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="bg-primary-600 text-white px-4 py-2 rounded-md text-sm hover:bg-primary-700 disabled:opacity-50"
        >
          {syncing ? 'Syncing...' : 'Run Sync Now'}
        </button>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500 uppercase font-medium">Sync Status</div>
          <div className="mt-1 text-lg font-bold">
            {syncStatus?.enabled ? (
              <span className="text-green-600">Enabled</span>
            ) : (
              <span className="text-gray-400">Disabled</span>
            )}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            Interval: {syncStatus?.interval_seconds || 300}s
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500 uppercase font-medium">Pending Records</div>
          <div className="mt-1 text-2xl font-bold text-primary-600">{pending?.total || 0}</div>
          <div className="text-xs text-gray-400 mt-1">Awaiting sync to QB</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500 uppercase font-medium">Last Sync</div>
          <div className="mt-1 text-sm font-medium">
            {lastSync ? new Date(lastSync).toLocaleString() : 'Never'}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500 uppercase font-medium">Last Batch Size</div>
          <div className="mt-1 text-2xl font-bold">{syncResults.length}</div>
          <div className="text-xs text-gray-400 mt-1">Records processed</div>
        </div>
      </div>

      {/* Pending Breakdown */}
      {pending && pending.total > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <h2 className="text-sm font-semibold mb-3 text-gray-700">Pending Sync Breakdown</h2>
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Customers', count: pending.customers, color: 'text-blue-600' },
              { label: 'Vendors', count: pending.vendors, color: 'text-purple-600' },
              { label: 'Invoices', count: pending.invoices, color: 'text-green-600' },
              { label: 'Purchase Orders', count: pending.purchase_orders, color: 'text-orange-600' },
            ].map(item => (
              <div key={item.label} className="flex items-center gap-2">
                <span className={`text-xl font-bold ${item.color}`}>{item.count}</span>
                <span className="text-sm text-gray-600">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sync Results */}
      {syncResults.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700">Last Sync Results</h2>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entity</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name/Number</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">qbXML</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {syncResults.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm capitalize">{r.entity}</td>
                  <td className="px-4 py-3 text-sm">{r.id}</td>
                  <td className="px-4 py-3 text-sm">{r.name || r.number || '-'}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full text-xs">{r.action}</span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {r.qbxml_generated ? <span className="text-green-600">Generated</span> : <span className="text-gray-400">-</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* qbXML Preview */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-sm font-semibold mb-3 text-gray-700">qbXML Preview</h2>
        <div className="flex gap-3 mb-3">
          <select value={previewEntity.type} onChange={e => setPreviewEntity(p => ({ ...p, type: e.target.value }))} className="border rounded px-3 py-1.5 text-sm">
            <option value="customer">Customer</option>
            <option value="vendor">Vendor</option>
            <option value="invoice">Invoice</option>
            <option value="purchase_order">Purchase Order</option>
          </select>
          <input
            type="number"
            value={previewEntity.id}
            onChange={e => setPreviewEntity(p => ({ ...p, id: e.target.value }))}
            placeholder="Entity ID"
            className="border rounded px-3 py-1.5 text-sm w-32"
          />
          <button onClick={handlePreview} className="bg-gray-100 text-gray-700 px-4 py-1.5 rounded text-sm hover:bg-gray-200">
            Preview
          </button>
        </div>
        {previewXml && (
          <pre className="bg-gray-900 text-green-400 p-4 rounded text-xs overflow-x-auto max-h-96 whitespace-pre-wrap">{previewXml}</pre>
        )}
      </div>
    </div>
  );
};

export default QuickBooksPage;
