import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import Layout from './components/layout/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import InventoryPage from './pages/InventoryPage';
import SalesPage from './pages/SalesPage';
import PurchasingPage from './pages/PurchasingPage';
import ManufacturingPage from './pages/ManufacturingPage';
import QualityPage from './pages/QualityPage';
import TraceabilityPage from './pages/TraceabilityPage';
import ReportsPage from './pages/ReportsPage';
import AdminPage from './pages/AdminPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="sales" element={<SalesPage />} />
        <Route path="purchasing" element={<PurchasingPage />} />
        <Route path="manufacturing" element={<ManufacturingPage />} />
        <Route path="quality" element={<QualityPage />} />
        <Route path="traceability" element={<TraceabilityPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
    </Routes>
  );
};

export default App;
