import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import PageHeader from '../components/common/PageHeader';
import StatCard from '../components/common/StatCard';
import { reportsAPI, inventoryAPI, salesAPI, manufacturingAPI } from '../services/api';
import { formatCurrency } from '../utils/helpers';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const DashboardPage: React.FC = () => {
  const { data: items } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const { data: salesOrders } = useQuery({ queryKey: ['sales-orders'], queryFn: () => salesAPI.listOrders() });
  const { data: prodOrders } = useQuery({ queryKey: ['prod-orders'], queryFn: () => manufacturingAPI.listProductionOrders() });
  const { data: glReport } = useQuery({ queryKey: ['inv-gl'], queryFn: () => reportsAPI.inventoryByGLGroup() });
  const { data: salesReport } = useQuery({ queryKey: ['sales-cust'], queryFn: () => reportsAPI.salesByCustomer() });

  const activeItems = items?.data?.length || 0;
  const openSO = salesOrders?.data?.filter((o: any) => !['closed', 'cancelled'].includes(o.status)).length || 0;
  const activeProd = prodOrders?.data?.filter((o: any) => ['planned', 'released', 'in_production'].includes(o.status)).length || 0;
  const totalInventoryValue = glReport?.data?.reduce((sum: number, g: any) => sum + (g.total_value || 0), 0) || 0;

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Overview of your batch manufacturing operations" />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Active Items" value={activeItems} color="blue" />
        <StatCard title="Open Sales Orders" value={openSO} color="green" />
        <StatCard title="Active Production" value={activeProd} color="yellow" />
        <StatCard title="Inventory Value" value={formatCurrency(totalInventoryValue)} color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Inventory Value by GL Group</h3>
          <div className="h-64">
            {glReport?.data && glReport.data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={glReport.data} dataKey="total_value" nameKey="gl_group_name" cx="50%" cy="50%" outerRadius={80} label>
                    {glReport.data.map((_: any, i: number) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">No inventory data yet</div>
            )}
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Sales by Customer</h3>
          <div className="h-64">
            {salesReport?.data && salesReport.data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={salesReport.data.slice(0, 10)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="customer_name" tick={{ fontSize: 11 }} />
                  <YAxis />
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Bar dataKey="total_revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">No sales data yet</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
