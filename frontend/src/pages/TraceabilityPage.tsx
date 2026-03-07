import React, { useState } from 'react';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import { traceabilityAPI } from '../services/api';

const TraceabilityPage: React.FC = () => {
  const [lotId, setLotId] = useState('');
  const [genealogy, setGenealogy] = useState<any>(null);
  const [recallImpact, setRecallImpact] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const searchGenealogy = async () => {
    if (!lotId) return;
    setLoading(true);
    try {
      const { data } = await traceabilityAPI.getLotGenealogy(parseInt(lotId));
      setGenealogy(data);
      setRecallImpact(null);
    } catch {
      toast.error('Failed to load genealogy');
    } finally {
      setLoading(false);
    }
  };

  const searchRecall = async () => {
    if (!lotId) return;
    setLoading(true);
    try {
      const { data } = await traceabilityAPI.getRecallImpact(parseInt(lotId));
      setRecallImpact(data);
    } catch {
      toast.error('Failed to load recall impact');
    } finally {
      setLoading(false);
    }
  };

  const renderTree = (node: any, depth = 0) => {
    if (!node) return null;
    return (
      <div style={{ marginLeft: depth * 24 }} className="border-l-2 border-gray-200 pl-4 py-1">
        {node.lot_number && (
          <div className="text-sm">
            <span className="font-medium">{node.lot_number}</span>
            {node.item_name && <span className="text-gray-500 ml-2">({node.item_name})</span>}
            {node.quantity_used && <span className="text-gray-400 ml-2">Qty: {node.quantity_used}</span>}
            {node.customer && <span className="badge-blue ml-2">{node.customer}</span>}
          </div>
        )}
        {node.type === 'purchase_receipt' && (
          <div className="text-sm text-gray-500">Purchase Receipt - Qty: {node.quantity}</div>
        )}
        {node.type === 'shipment' && (
          <div className="text-sm">
            <span className="badge-green">Shipped</span>
            <span className="ml-2">{node.shipment_number}</span>
            {node.customer && <span className="ml-2 text-gray-500">to {node.customer}</span>}
          </div>
        )}
        {node.sources?.map((s: any, i: number) => <React.Fragment key={i}>{renderTree(s, depth + 1)}</React.Fragment>)}
        {node.destinations?.map((d: any, i: number) => <React.Fragment key={i}>{renderTree(d, depth + 1)}</React.Fragment>)}
      </div>
    );
  };

  return (
    <div>
      <PageHeader title="Lot Traceability" subtitle="Trace lot genealogy and analyze recall impact" />

      <div className="card mb-6">
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Lot ID</label>
            <input
              className="input-field"
              placeholder="Enter lot ID"
              value={lotId}
              onChange={(e) => setLotId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && searchGenealogy()}
            />
          </div>
          <button className="btn-primary" onClick={searchGenealogy} disabled={loading}>
            {loading ? 'Searching...' : 'Trace Genealogy'}
          </button>
          <button className="btn-danger" onClick={searchRecall} disabled={loading}>Recall Analysis</button>
        </div>
      </div>

      {genealogy && (
        <div className="card mb-6">
          <h3 className="text-lg font-semibold mb-4">
            Lot Genealogy: {genealogy.lot?.lot_number}
            {genealogy.lot?.item_name && <span className="text-gray-500 font-normal ml-2">({genealogy.lot.item_name})</span>}
          </h3>
          {genealogy.sources?.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Raw Material Sources (Backward Trace)</h4>
              {genealogy.sources.map((s: any, i: number) => <React.Fragment key={i}>{renderTree(s)}</React.Fragment>)}
            </div>
          )}
          {genealogy.destinations?.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Destinations (Forward Trace)</h4>
              {genealogy.destinations.map((d: any, i: number) => <React.Fragment key={i}>{renderTree(d)}</React.Fragment>)}
            </div>
          )}
          {!genealogy.sources?.length && !genealogy.destinations?.length && (
            <p className="text-gray-500">No genealogy data found for this lot.</p>
          )}
        </div>
      )}

      {recallImpact && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Recall Impact Analysis</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-700">Affected Lots</p>
              <p className="text-2xl font-bold text-red-800">{recallImpact.affected_lot_count}</p>
            </div>
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <p className="text-sm text-orange-700">Affected Customers</p>
              <p className="text-2xl font-bold text-orange-800">{recallImpact.affected_customer_count}</p>
            </div>
          </div>
          {recallImpact.affected_lots?.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium mb-2">Affected Lots</h4>
              <div className="flex flex-wrap gap-2">
                {recallImpact.affected_lots.map((l: string) => <span key={l} className="badge-red">{l}</span>)}
              </div>
            </div>
          )}
          {recallImpact.affected_customers?.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2">Affected Customers</h4>
              <div className="flex flex-wrap gap-2">
                {recallImpact.affected_customers.map((c: string) => <span key={c} className="badge-yellow">{c}</span>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TraceabilityPage;
