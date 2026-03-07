import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import { reportsAPI } from '../services/api';
import { formatCurrency, formatNumber, downloadBlob } from '../utils/helpers';

const reportTypes = [
  { id: 'inv-lot', label: 'Inventory by Lot' },
  { id: 'fifo', label: 'FIFO Valuation' },
  { id: 'inv-gl', label: 'Inventory by GL Group' },
  { id: 'batch', label: 'Batch History' },
  { id: 'qc', label: 'QC Results' },
  { id: 'sales-cust', label: 'Sales by Customer' },
  { id: 'sales-gl', label: 'Sales by GL Group' },
  { id: 'purch', label: 'Purchases by Vendor' },
] as const;

const ReportsPage: React.FC = () => {
  const [selected, setSelected] = useState<string>('inv-lot');

  const { data: invLot } = useQuery({ queryKey: ['rpt-inv-lot'], queryFn: () => reportsAPI.inventoryByLot(), enabled: selected === 'inv-lot' });
  const { data: fifo } = useQuery({ queryKey: ['rpt-fifo'], queryFn: () => reportsAPI.fifoValuation(), enabled: selected === 'fifo' });
  const { data: invGl } = useQuery({ queryKey: ['rpt-inv-gl'], queryFn: () => reportsAPI.inventoryByGLGroup(), enabled: selected === 'inv-gl' });
  const { data: batch } = useQuery({ queryKey: ['rpt-batch'], queryFn: () => reportsAPI.batchHistory(), enabled: selected === 'batch' });
  const { data: qc } = useQuery({ queryKey: ['rpt-qc'], queryFn: () => reportsAPI.qcResultsByLot(), enabled: selected === 'qc' });
  const { data: salesCust } = useQuery({ queryKey: ['rpt-sales-cust'], queryFn: () => reportsAPI.salesByCustomer(), enabled: selected === 'sales-cust' });
  const { data: salesGl } = useQuery({ queryKey: ['rpt-sales-gl'], queryFn: () => reportsAPI.salesByGLGroup(), enabled: selected === 'sales-gl' });
  const { data: purch } = useQuery({ queryKey: ['rpt-purch'], queryFn: () => reportsAPI.purchasesByVendor(), enabled: selected === 'purch' });

  const handleExportCSV = async () => {
    const { data } = await reportsAPI.exportInventoryCSV();
    downloadBlob(data, 'inventory_report.csv');
  };

  const renderReport = () => {
    switch (selected) {
      case 'inv-lot':
        return <DataTable columns={[
          { header: 'Lot #', accessor: 'lot_number' },
          { header: 'Item Code', accessor: 'item_code' },
          { header: 'Item', accessor: 'item_name' },
          { header: 'Qty', accessor: (r: any) => formatNumber(r.quantity_on_hand) },
          { header: 'Status', accessor: 'status' },
        ]} data={invLot?.data || []} />;
      case 'fifo':
        return <DataTable columns={[
          { header: 'Item Code', accessor: 'item_code' },
          { header: 'Item', accessor: 'item_name' },
          { header: 'Total Qty', accessor: (r: any) => formatNumber(r.total_quantity) },
          { header: 'Total Value', accessor: (r: any) => formatCurrency(r.total_value) },
        ]} data={fifo?.data || []} />;
      case 'inv-gl':
        return <DataTable columns={[
          { header: 'GL Group', accessor: 'gl_group_name' },
          { header: 'Total Qty', accessor: (r: any) => formatNumber(r.total_quantity) },
          { header: 'Total Value', accessor: (r: any) => formatCurrency(r.total_value) },
          { header: 'Item Count', accessor: 'item_count' },
        ]} data={invGl?.data || []} />;
      case 'batch':
        return <DataTable columns={[
          { header: 'Order #', accessor: 'order_number' },
          { header: 'Formula', accessor: 'formula' },
          { header: 'Planned', accessor: (r: any) => formatNumber(r.planned_quantity) },
          { header: 'Actual', accessor: (r: any) => r.actual_quantity ? formatNumber(r.actual_quantity) : '-' },
          { header: 'Yield %', accessor: (r: any) => r.yield_percent ? `${formatNumber(r.yield_percent)}%` : '-' },
          { header: 'Status', accessor: 'status' },
        ]} data={batch?.data || []} />;
      case 'qc':
        return <DataTable columns={[
          { header: 'Lot #', accessor: 'lot_number' },
          { header: 'Test', accessor: 'test_name' },
          { header: 'Value', accessor: (r: any) => r.result_value != null ? formatNumber(r.result_value) : '-' },
          { header: 'Passed', accessor: (r: any) => r.passed != null ? (r.passed ? 'Pass' : 'Fail') : '-' },
        ]} data={qc?.data || []} />;
      case 'sales-cust':
        return <DataTable columns={[
          { header: 'Customer', accessor: 'customer_name' },
          { header: 'Orders', accessor: 'order_count' },
          { header: 'Revenue', accessor: (r: any) => formatCurrency(r.total_revenue) },
        ]} data={salesCust?.data || []} />;
      case 'sales-gl':
        return <DataTable columns={[
          { header: 'GL Group', accessor: 'gl_group' },
          { header: 'Total Sales', accessor: (r: any) => formatCurrency(r.total_sales) },
        ]} data={salesGl?.data || []} />;
      case 'purch':
        return <DataTable columns={[
          { header: 'Vendor', accessor: 'vendor_name' },
          { header: 'Orders', accessor: 'order_count' },
          { header: 'Total', accessor: (r: any) => formatCurrency(r.total_purchases) },
        ]} data={purch?.data || []} />;
      default:
        return null;
    }
  };

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Generate and export reports"
        actions={<button className="btn-secondary" onClick={handleExportCSV}>Export Inventory CSV</button>}
      />
      <div className="flex gap-6">
        <div className="w-56 flex-shrink-0">
          <div className="card p-2">
            {reportTypes.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelected(r.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${selected === r.id ? 'bg-primary-50 text-primary-700 font-medium' : 'text-gray-600 hover:bg-gray-50'}`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 card">{renderReport()}</div>
      </div>
    </div>
  );
};

export default ReportsPage;
