import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import Layout from './components/layout/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ItemsPage from './pages/ItemsPage';
import InventoryPage from './pages/InventoryPage';
import CustomersPage from './pages/CustomersPage';
import SalesPage from './pages/SalesPage';
import VendorsPage from './pages/VendorsPage';
import PurchasingPage from './pages/PurchasingPage';
import ManufacturingPage from './pages/ManufacturingPage';
import RecipesPage from './pages/RecipesPage';
import BatchTicketsPage from './pages/BatchTicketsPage';
import BatchExecutionPage from './pages/BatchExecutionPage';
import QualityPage from './pages/QualityPage';
import TraceabilityPage from './pages/TraceabilityPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';
import AdminPage from './pages/AdminPage';
import DocumentsPage from './pages/DocumentsPage';
import QuickBooksPage from './pages/QuickBooksPage';

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
        <Route path="items" element={<ItemsPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="customers" element={<CustomersPage />} />
        <Route path="sales" element={<SalesPage />} />
        <Route path="vendors" element={<VendorsPage />} />
        <Route path="purchasing" element={<PurchasingPage />} />
        <Route path="manufacturing" element={<ManufacturingPage />} />
        <Route path="recipes" element={<RecipesPage />} />
        <Route path="batch-tickets" element={<BatchTicketsPage />} />
        <Route path="batch-execution" element={<BatchExecutionPage />} />
        <Route path="quality" element={<QualityPage />} />
        <Route path="traceability" element={<TraceabilityPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="quickbooks" element={<QuickBooksPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
    </Routes>
  );
};

export default App;
