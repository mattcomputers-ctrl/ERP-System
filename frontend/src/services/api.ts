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
  updateUOM: (id: number, data: any) => api.put(`/inventory/uoms/${id}`, data),
  deleteUOM: (id: number) => api.delete(`/inventory/uoms/${id}`),
  getValuation: (itemId?: number) => api.get('/inventory/valuation', { params: { item_id: itemId } }),
  getInventorySummary: (params?: any) => api.get('/inventory/summary', { params }),
  listAliases: (itemId: number) => api.get(`/inventory/items/${itemId}/aliases`),
  createAlias: (itemId: number, data: any) => api.post(`/inventory/items/${itemId}/aliases`, data),
  updateAlias: (aliasId: number, data: any) => api.put(`/inventory/aliases/${aliasId}`, data),
  deleteAlias: (_itemId: number, aliasId: number) => api.delete(`/inventory/aliases/${aliasId}`),
  lookupByAlias: (code: string, type?: string) => api.get('/inventory/aliases/lookup', { params: { alias_code: code, alias_type: type } }),
  listPackComponents: (itemId: number) => api.get(`/inventory/items/${itemId}/pack-components`),
  setPackComponents: (itemId: number, data: any) => api.put(`/inventory/items/${itemId}/pack-components`, data),
  addPackComponent: (itemId: number, data: any) => api.post(`/inventory/items/${itemId}/pack-components`, data),
  deletePackComponent: (_itemId: number, componentId: number) => api.delete(`/inventory/pack-components/${componentId}`),
  assemblePack: (data: any) => api.post('/inventory/packs/assemble', data),
  disassemblePack: (data: any) => api.post('/inventory/packs/disassemble', data),
  // Active Recipes
  listActiveRecipes: (itemId: number) => api.get(`/inventory/items/${itemId}/active-recipes`),
  setActiveRecipes: (itemId: number, recipes: any[]) => api.put(`/inventory/items/${itemId}/active-recipes`, recipes),
  // QC Test Definitions (Settings)
  listQCTestDefinitions: () => api.get('/inventory/qc-test-definitions'),
  createQCTestDefinition: (data: any) => api.post('/inventory/qc-test-definitions', data),
  updateQCTestDefinition: (id: number, data: any) => api.put(`/inventory/qc-test-definitions/${id}`, data),
  deleteQCTestDefinition: (id: number) => api.delete(`/inventory/qc-test-definitions/${id}`),
  // Item QC Test Assignments
  listItemQCTests: (itemId: number) => api.get(`/inventory/items/${itemId}/qc-tests`),
  addItemQCTest: (itemId: number, data: any) => api.post(`/inventory/items/${itemId}/qc-tests`, data),
  updateItemQCTest: (itemId: number, assignmentId: number, data: any) => api.put(`/inventory/items/${itemId}/qc-tests/${assignmentId}`, data),
  removeItemQCTest: (itemId: number, assignmentId: number) => api.delete(`/inventory/items/${itemId}/qc-tests/${assignmentId}`),
  // Pack Extension Definitions (Settings)
  listPackExtensionDefinitions: () => api.get('/inventory/pack-extension-definitions'),
  createPackExtensionDefinition: (data: any) => api.post('/inventory/pack-extension-definitions', data),
  updatePackExtensionDefinition: (id: number, data: any) => api.put(`/inventory/pack-extension-definitions/${id}`, data),
  deletePackExtensionDefinition: (id: number) => api.delete(`/inventory/pack-extension-definitions/${id}`),
  // Item Pack Extensions
  listItemPackExtensions: (itemId: number) => api.get(`/inventory/items/${itemId}/pack-extensions`),
  addItemPackExtension: (itemId: number, data: any) => api.post(`/inventory/items/${itemId}/pack-extensions`, data),
  updateItemPackExtension: (itemId: number, ipeId: number, data: any) => api.put(`/inventory/items/${itemId}/pack-extensions/${ipeId}`, data),
  removeItemPackExtension: (itemId: number, ipeId: number) => api.delete(`/inventory/items/${itemId}/pack-extensions/${ipeId}`),
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
  getPickList: (orderId: number) => api.get(`/sales/orders/${orderId}/pick-list`),
  createShipment: (data: any) => api.post('/sales/shipments', data),
  createInvoice: (orderId: number) => api.post(`/sales/orders/${orderId}/invoice`),
  createPackingList: (orderId: number) => api.post(`/sales/orders/${orderId}/packing-list`),
  getInvoice: (invoiceId: number) => api.get(`/sales/invoices/${invoiceId}`),
  listInvoices: (params?: any) => api.get('/sales/invoices', { params }),
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

// --- Settings ---
export const settingsAPI = {
  listShipVias: () => api.get('/settings/ship-vias'),
  createShipVia: (data: any) => api.post('/settings/ship-vias', data),
  updateShipVia: (id: number, data: any) => api.put(`/settings/ship-vias/${id}`, data),
  deleteShipVia: (id: number) => api.delete(`/settings/ship-vias/${id}`),
  getBranding: () => api.get('/settings/branding'),
  updateBranding: (data: any) => api.put('/settings/branding', data),
  listPriceLists: (params?: any) => api.get('/settings/price-lists', { params }),
  createPriceList: (data: any) => api.post('/settings/price-lists', data),
  updatePriceList: (id: number, data: any) => api.put(`/settings/price-lists/${id}`, data),
  listPriceHistory: (params?: any) => api.get('/settings/price-history', { params }),
  listShipTos: (params?: any) => api.get('/settings/ship-tos', { params }),
  createShipTo: (data: any) => api.post('/settings/ship-tos', data),
  getShipTo: (id: number) => api.get(`/settings/ship-tos/${id}`),
  updateShipTo: (id: number, data: any) => api.put(`/settings/ship-tos/${id}`, data),
  deleteShipTo: (id: number) => api.delete(`/settings/ship-tos/${id}`),
  listSalesTaxOptions: () => api.get('/settings/sales-tax-options'),
  createSalesTaxOption: (data: any) => api.post('/settings/sales-tax-options', data),
  updateSalesTaxOption: (id: number, data: any) => api.put(`/settings/sales-tax-options/${id}`, data),
  deleteSalesTaxOption: (id: number) => api.delete(`/settings/sales-tax-options/${id}`),
};

// --- Recipes ---
export const recipesAPI = {
  list: (params?: any) => api.get('/recipes/', { params }),
  create: (data: any) => api.post('/recipes/', data),
  get: (id: number) => api.get(`/recipes/${id}`),
  update: (id: number, data: any) => api.put(`/recipes/${id}`, data),
  addVersion: (recipeId: number, data: any) => api.post(`/recipes/${recipeId}/versions`, data),
  updateVersion: (versionId: number, data: any) => api.put(`/recipes/versions/${versionId}`, data),
  publishVersion: (versionId: number) => api.post(`/recipes/versions/${versionId}/publish`),
  cloneVersion: (recipeId: number, sourceVersionId?: number) =>
    api.post(`/recipes/${recipeId}/clone`, null, { params: sourceVersionId ? { source_version_id: sourceVersionId } : undefined }),
  // Batch Tickets
  listBatchTickets: (params?: any) => api.get('/recipes/batch-tickets', { params }),
  createBatchTicket: (data: any) => api.post('/recipes/batch-tickets', data),
  getBatchTicket: (id: number) => api.get(`/recipes/batch-tickets/${id}`),
  updateBatchTicket: (id: number, data: any) => api.put(`/recipes/batch-tickets/${id}`, data),
  // Batch Execution
  startExecution: (ticketId: number, data?: any) => api.post(`/recipes/batch-tickets/${ticketId}/execute`, data || {}),
  getExecution: (ticketId: number) => api.get(`/recipes/batch-tickets/${ticketId}/execution`),
  recordConsumption: (ticketId: number, data: any) => api.post(`/recipes/batch-tickets/${ticketId}/execute/consume`, data),
  completeExecution: (ticketId: number, data: any) => api.post(`/recipes/batch-tickets/${ticketId}/execute/complete`, data),
  // QC during execution
  getExecutionQCTests: (ticketId: number) => api.get(`/recipes/batch-tickets/${ticketId}/execute/qc-tests`),
  recordExecutionQCResults: (ticketId: number, data: any) => api.post(`/recipes/batch-tickets/${ticketId}/execute/qc-results`, data),
  getExecutionQCResults: (ticketId: number) => api.get(`/recipes/batch-tickets/${ticketId}/execute/qc-results`),
  createCOAFromExecution: (ticketId: number, params?: any) => api.post(`/recipes/batch-tickets/${ticketId}/execute/create-coa`, null, { params }),
};

// --- Documents ---
export const documentsAPI = {
  listTemplates: (docType?: string) => api.get('/documents/templates', { params: { doc_type: docType } }),
  getTemplate: (id: number) => api.get(`/documents/templates/${id}`),
  createTemplate: (data: any) => api.post('/documents/templates', data),
  updateTemplate: (id: number, data: any) => api.put(`/documents/templates/${id}`, data),
  deleteTemplate: (id: number) => api.delete(`/documents/templates/${id}`),
  generateDocument: (data: any) => api.post('/documents/generate', data),
  listGenerated: (params?: any) => api.get('/documents/generated', { params }),
  downloadDocument: (id: number) => api.get(`/documents/download/${id}`, { responseType: 'blob' }),
  listCOAs: (params?: any) => api.get('/documents/coa', { params }),
  getCOA: (id: number) => api.get(`/documents/coa/${id}`),
  createCOA: (data: any) => api.post('/documents/coa', data),
  approveCOA: (id: number, data?: any) => api.post(`/documents/coa/${id}/approve`, data || {}),
  downloadCOA: (id: number) => api.get(`/documents/coa/${id}/download`, { responseType: 'blob' }),
};

// --- QuickBooks ---
export const quickbooksAPI = {
  getStatus: () => api.get('/quickbooks/status'),
  getPending: () => api.get('/quickbooks/pending'),
  triggerSync: () => api.post('/quickbooks/sync'),
  getSyncResults: () => api.get('/quickbooks/sync/results'),
  previewQbxml: (entityType: string, entityId: number) => api.get(`/quickbooks/qbxml/preview/${entityType}/${entityId}`),
};
