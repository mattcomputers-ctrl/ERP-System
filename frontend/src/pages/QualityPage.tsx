import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import { qualityAPI } from '../services/api';

const QualityPage: React.FC = () => {
  const [tab, setTab] = useState<'specifications' | 'results'>('specifications');

  const { data: specs } = useQuery({ queryKey: ['qc-specs'], queryFn: () => qualityAPI.listSpecifications() });
  const { data: results } = useQuery({ queryKey: ['qc-results'], queryFn: () => qualityAPI.listResults() });

  const specColumns = [
    { header: 'Name', accessor: 'name' },
    { header: 'Type', accessor: ((row: any) => <span className="badge-blue">{row.spec_type.replace('_', ' ')}</span>) },
    { header: 'Tests', accessor: ((row: any) => row.tests?.length || 0) },
    { header: 'Status', accessor: ((row: any) => <span className={row.is_active ? 'badge-green' : 'badge-red'}>{row.is_active ? 'Active' : 'Inactive'}</span>) },
  ];

  const resultColumns = [
    { header: 'Lot ID', accessor: 'lot_id' },
    { header: 'Test ID', accessor: 'test_id' },
    { header: 'Value', accessor: ((row: any) => row.result_value ?? row.result_text ?? '-') },
    { header: 'Result', accessor: ((row: any) => row.passed != null ? <span className={row.passed ? 'badge-green' : 'badge-red'}>{row.passed ? 'Pass' : 'Fail'}</span> : <span className="badge-gray">Pending</span>) },
    { header: 'Tested', accessor: ((row: any) => row.tested_at ? new Date(row.tested_at).toLocaleDateString() : '-') },
  ];

  return (
    <div>
      <PageHeader title="Quality Control" subtitle="Manage QC specifications, testing, and lot disposition" />

      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {(['specifications', 'results'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <div className="card">
        {tab === 'specifications' && <DataTable columns={specColumns} data={specs?.data || []} />}
        {tab === 'results' && <DataTable columns={resultColumns} data={results?.data || []} />}
      </div>
    </div>
  );
};

export default QualityPage;
