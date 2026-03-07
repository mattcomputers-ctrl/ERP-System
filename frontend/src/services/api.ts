import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = useAuthStore.getState().refreshToken;
      if (refreshToken) {
        try {
          const response = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
          const { access_token, refresh_token } = response.data;
          useAuthStore.getState().setTokens(access_token, refresh_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch {
          useAuthStore.getState().logout();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// --- Auth ---
export const authAPI = {
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me'),
};

// --- Users ---
export const usersAPI = {
  list: () => api.get('/users'),
  create: (data: any) => api.post('/users', data),
  update: (id: number, data: any) => api.put(`/users/${id}`, data),
  listGroups: () => api.get('/users/groups/'),
  createGroup: (data: any) => api.post('/users/groups/', data),
  setGroupPermissions: (groupId: number, permissions: any[]) => api.put(`/users/groups/${groupId}/permissions`, { permissions }),
  getGroupPermissions: (groupId: number) => api.get(`/users/groups/${groupId}/permissions`),
  addUserToGroup: (groupId: number, userId: number) => api.post(`/users/groups/${groupId}/users/${userId}`),
  removeUserFromGroup: (groupId: number, userId: number) => api.delete(`/users/groups/${groupId}/users/${userId}`),
};

// --- GL Groups ---
export const glGroupsAPI = {
  list: () => api.get('/gl-groups'),
  create: (data: any) => api.post('/gl-groups', data),
  update: (id: number, data: any) => api.put(`/gl-groups/${id}`, data),
  setMappings: (id: number, mappings: any[]) => api.put(`/gl-groups/${id}/mappings`, mappings),
};

// --- Inventory ---
export const inventoryAPI = {
  listItems: (params?: any) => api.get('/inventory/items', { params }),
  createItem: (data: any) => api.post('/inventory/items', data),
  getItem: (id: number) => api.get(`/inventory/items/${id}`),
  updateItem: (id: number, data: any) => api.put(`/inventory/items/${id}`, data),
  listWarehouses: () => api.get('/inventory/warehouses'),
  createWarehouse: (data: any) => api.post('/inventory/warehouses', data),
  listLocations: (warehouseId?: number) => api.get('/inventory/locations', { params: { warehouse_id: warehouseId } }),
  createLocation: (data: any) => api.post('/inventory/locations', data),
  listLots: (params?: any) => api.get('/inventory/lots', { params }),
  getLot: (id: number) => api.get(`/inventory/lots/${id}`),
  listTransactions: (params?: any) => api.get('/inventory/transactions', { params }),
  createAdjustment: (data: any) => api.post('/inventory/adjustments', data),
  createTransfer: (data: any) => api.post('/inventory/transfers', data),
  listUOMs: () => api.get('/inventory/uoms'),
  createUOM: (data: any) => api.post('/inventory/uoms', data),
  getValuation: (itemId?: number) => api.get('/inventory/valuation', { params: { item_id: itemId } }),
  // Aliases
  listAliases: (itemId: number) => api.get(`/inventory/items/${itemId}/aliases`),
  createAlias: (itemId: number, data: any) => api.post(`/inventory/items/${itemId}/aliases`, data),
  updateAlias: (itemId: number, aliasId: number, data: any) => api.put(`/inventory/items/${itemId}/aliases/${aliasId}`, data),
  deleteAlias: (itemId: number, aliasId: number) => api.delete(`/inventory/items/${itemId}/aliases/${aliasId}`),
  lookupByAlias: (code: string, type?: string) => api.get('/inventory/alias-lookup', { params: { alias_code: code, alias_type: type } }),
  // Pack Components
  listPackComponents: (itemId: number) => api.get(`/inventory/items/${itemId}/pack-components`),
  setPackComponents: (itemId: number, data: any) => api.put(`/inventory/items/${itemId}/pack-components`, data),
  addPackComponent: (itemId: number, data: any) => api.post(`/inventory/items/${itemId}/pack-components`, data),
  deletePackComponent: (itemId: number, componentId: number) => api.delete(`/inventory/items/${itemId}/pack-components/${componentId}`),
  assemblePack: (data: any) => api.post('/inventory/packs/assemble', data),
  disassemblePack: (data: any) => api.post('/inventory/packs/disassemble', data),
};

// --- Sales ---
export const salesAPI = {
  listCustomers: () => api.get('/sales/customers'),
  createCustomer: (data: any) => api.post('/sales/customers', data),
  getCustomer: (id: number) => api.get(`/sales/customers/${id}`),
  updateCustomer: (id: number, data: any) => api.put(`/sales/customers/${id}`, data),
  listOrders: (params?: any) => api.get('/sales/orders', { params }),
  createOrder: (data: any) => api.post('/sales/orders', data),
  getOrder: (id: number) => api.get(`/sales/orders/${id}`),
  updateOrder: (id: number, data: any) => api.put(`/sales/orders/${id}`, data),
  createShipment: (data: any) => api.post('/sales/shipments', data),
  createInvoice: (orderId: number) => api.post(`/sales/orders/${orderId}/invoice`),
};

// --- Purchasing ---
export const purchasingAPI = {
  listVendors: () => api.get('/purchasing/vendors'),
  createVendor: (data: any) => api.post('/purchasing/vendors', data),
  getVendor: (id: number) => api.get(`/purchasing/vendors/${id}`),
  updateVendor: (id: number, data: any) => api.put(`/purchasing/vendors/${id}`, data),
  listOrders: (params?: any) => api.get('/purchasing/orders', { params }),
  createOrder: (data: any) => api.post('/purchasing/orders', data),
  getOrder: (id: number) => api.get(`/purchasing/orders/${id}`),
  updateOrder: (id: number, data: any) => api.put(`/purchasing/orders/${id}`, data),
  receiveOrder: (data: any) => api.post('/purchasing/receipts', data),
};

// --- Manufacturing ---
export const manufacturingAPI = {
  listFormulas: () => api.get('/manufacturing/formulas'),
  createFormula: (data: any) => api.post('/manufacturing/formulas', data),
  getFormula: (id: number) => api.get(`/manufacturing/formulas/${id}`),
  addVersion: (formulaId: number, data: any) => api.post(`/manufacturing/formulas/${formulaId}/versions`, data),
  listVersions: (formulaId: number) => api.get(`/manufacturing/formulas/${formulaId}/versions`),
  revertVersion: (formulaId: number, versionId: number, reason: string) => api.post(`/manufacturing/formulas/${formulaId}/versions/${versionId}/revert`, { reason }),
  listProductionOrders: (params?: any) => api.get('/manufacturing/production-orders', { params }),
  createProductionOrder: (data: any) => api.post('/manufacturing/production-orders', data),
  getProductionOrder: (id: number) => api.get(`/manufacturing/production-orders/${id}`),
  updateProductionOrder: (id: number, data: any) => api.put(`/manufacturing/production-orders/${id}`, data),
  recordConsumption: (id: number, data: any[]) => api.post(`/manufacturing/production-orders/${id}/consume`, data),
  recordOutput: (id: number, data: any) => api.post(`/manufacturing/production-orders/${id}/output`, data),
};

// --- Quality ---
export const qualityAPI = {
  listSpecifications: (params?: any) => api.get('/quality/specifications', { params }),
  createSpecification: (data: any) => api.post('/quality/specifications', data),
  getSpecification: (id: number) => api.get(`/quality/specifications/${id}`),
  listResults: (params?: any) => api.get('/quality/results', { params }),
  recordResult: (data: any) => api.post('/quality/results', data),
  recordBatchResults: (data: any) => api.post('/quality/results/batch', data),
  setLotDisposition: (data: any) => api.post('/quality/lot-disposition', data),
};

// --- Traceability ---
export const traceabilityAPI = {
  getLotGenealogy: (lotId: number) => api.get(`/traceability/lot/${lotId}/genealogy`),
  getRecallImpact: (lotId: number) => api.get(`/traceability/lot/${lotId}/recall-impact`),
};

// --- Reports ---
export const reportsAPI = {
  inventoryByLot: (params?: any) => api.get('/reports/inventory/by-lot', { params }),
  fifoValuation: (params?: any) => api.get('/reports/inventory/fifo-valuation', { params }),
  inventoryByGLGroup: () => api.get('/reports/inventory/by-gl-group'),
  batchHistory: (params?: any) => api.get('/reports/manufacturing/batch-history', { params }),
  qcResultsByLot: (params?: any) => api.get('/reports/quality/results-by-lot', { params }),
  salesByCustomer: () => api.get('/reports/sales/by-customer'),
  salesByGLGroup: () => api.get('/reports/sales/by-gl-group'),
  purchasesByVendor: () => api.get('/reports/purchasing/by-vendor'),
  exportInventoryCSV: () => api.get('/reports/export/inventory-csv', { responseType: 'blob' }),
};
