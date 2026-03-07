import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import { manufacturingAPI } from '../services/api';
import { getStatusColor, formatNumber } from '../utils/helpers';
import type { Formula, ProductionOrder } from '../types';

const ManufacturingPage: React.FC = () => {
  const [tab, setTab] = useState<'production' | 'formulas'>('production');

  const { data: prodOrders } = useQuery({ queryKey: ['prod-orders'], queryFn: () => manufacturingAPI.listProductionOrders() });
  const { data: formulas } = useQuery({ queryKey: ['formulas'], queryFn: () => manufacturingAPI.listFormulas() });

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
  ];

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
    </div>
  );
};

export default ManufacturingPage;
