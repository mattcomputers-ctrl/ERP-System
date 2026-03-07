import React, { useState, useEffect, useCallback } from 'react';
import { documentsAPI } from '../services/api';
import type { DocumentTemplate, GeneratedDocument, COACertificate } from '../types';

const DOC_TYPES = [
  { value: 'invoice', label: 'Invoice' },
  { value: 'purchase_order', label: 'Purchase Order' },
  { value: 'packing_list', label: 'Packing List' },
  { value: 'batch_ticket', label: 'Batch Ticket' },
  { value: 'coa', label: 'Certificate of Analysis' },
  { value: 'custom', label: 'Custom' },
];

const FIELD_PALETTE = [
  { id: 'company_name', label: 'Company Name', category: 'Header' },
  { id: 'company_address', label: 'Company Address', category: 'Header' },
  { id: 'company_phone', label: 'Company Phone', category: 'Header' },
  { id: 'company_logo', label: 'Company Logo', category: 'Header' },
  { id: 'doc_number', label: 'Document Number', category: 'Document' },
  { id: 'doc_date', label: 'Document Date', category: 'Document' },
  { id: 'doc_status', label: 'Status', category: 'Document' },
  { id: 'entity_name', label: 'Customer/Vendor Name', category: 'Entity' },
  { id: 'entity_address', label: 'Customer/Vendor Address', category: 'Entity' },
  { id: 'entity_contact', label: 'Contact Name', category: 'Entity' },
  { id: 'line_items_table', label: 'Line Items Table', category: 'Content' },
  { id: 'totals_section', label: 'Totals Section', category: 'Content' },
  { id: 'notes_field', label: 'Notes', category: 'Content' },
  { id: 'qc_results_table', label: 'QC Results Table', category: 'Quality' },
  { id: 'ingredients_table', label: 'Ingredients Table', category: 'Manufacturing' },
  { id: 'signoff_section', label: 'Sign-Off Section', category: 'Footer' },
  { id: 'footer_text', label: 'Footer Text', category: 'Footer' },
];

interface LayoutSection {
  id: string;
  type: string;
  fields: string[];
  label: string;
}

const DocumentsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'generate' | 'templates' | 'coa' | 'history'>('generate');

  // Generate tab state
  const [genDocType, setGenDocType] = useState('invoice');
  const [genRefId, setGenRefId] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<string | null>(null);

  // Templates tab state
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [editingTemplate, setEditingTemplate] = useState<DocumentTemplate | null>(null);
  const [showTemplateForm, setShowTemplateForm] = useState(false);
  const [templateForm, setTemplateForm] = useState({ name: '', doc_type: 'invoice', description: '', header_html: '', footer_html: '', is_default: false });
  const [layoutSections, setLayoutSections] = useState<LayoutSection[]>([]);
  const [dragField, setDragField] = useState<string | null>(null);

  // COA tab state
  const [coas, setCoas] = useState<COACertificate[]>([]);
  const [coaForm, setCoaForm] = useState({ lot_id: '', specification_id: '', customer_id: '', notes: '' });
  const [showCoaForm, setShowCoaForm] = useState(false);

  // History tab state
  const [generatedDocs, setGeneratedDocs] = useState<GeneratedDocument[]>([]);

  const loadTemplates = useCallback(async () => {
    try {
      const res = await documentsAPI.listTemplates();
      setTemplates(res.data);
    } catch { /* ignore */ }
  }, []);

  const loadCOAs = useCallback(async () => {
    try {
      const res = await documentsAPI.listCOAs();
      setCoas(res.data);
    } catch { /* ignore */ }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const res = await documentsAPI.listGenerated();
      setGeneratedDocs(res.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadTemplates();
    loadCOAs();
    loadHistory();
  }, [loadTemplates, loadCOAs, loadHistory]);

  // --- Generate Document ---
  const handleGenerate = async () => {
    if (!genRefId) return;
    setGenerating(true);
    setGenResult(null);
    try {
      const res = await documentsAPI.generateDocument({ doc_type: genDocType, reference_id: parseInt(genRefId) });
      setGenResult(`Generated: ${res.data.file_name} (ID: ${res.data.id})`);
      loadHistory();
    } catch (err: any) {
      setGenResult(`Error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (docId: number, fileName: string) => {
    try {
      const res = await documentsAPI.downloadDocument(docId);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch { /* ignore */ }
  };

  // --- Template Builder ---
  const openTemplateEditor = (template?: DocumentTemplate) => {
    if (template) {
      setEditingTemplate(template);
      setTemplateForm({
        name: template.name,
        doc_type: template.doc_type,
        description: template.description || '',
        header_html: template.header_html || '',
        footer_html: template.footer_html || '',
        is_default: template.is_default,
      });
      try {
        const parsed = JSON.parse(template.layout_json);
        setLayoutSections(parsed.sections || []);
      } catch {
        setLayoutSections([]);
      }
    } else {
      setEditingTemplate(null);
      setTemplateForm({ name: '', doc_type: 'invoice', description: '', header_html: '', footer_html: '', is_default: false });
      setLayoutSections([
        { id: 'header', type: 'header', fields: ['company_name', 'company_address'], label: 'Header' },
        { id: 'info', type: 'info', fields: ['doc_number', 'doc_date', 'entity_name'], label: 'Document Info' },
        { id: 'content', type: 'content', fields: ['line_items_table'], label: 'Content' },
        { id: 'totals', type: 'totals', fields: ['totals_section'], label: 'Totals' },
        { id: 'footer', type: 'footer', fields: ['signoff_section'], label: 'Footer' },
      ]);
    }
    setShowTemplateForm(true);
  };

  const saveTemplate = async () => {
    const layoutJson = JSON.stringify({ sections: layoutSections });
    const data = { ...templateForm, layout_json: layoutJson };
    try {
      if (editingTemplate) {
        await documentsAPI.updateTemplate(editingTemplate.id, data);
      } else {
        await documentsAPI.createTemplate(data);
      }
      setShowTemplateForm(false);
      loadTemplates();
    } catch { /* ignore */ }
  };

  const handleDragStart = (fieldId: string) => {
    setDragField(fieldId);
  };

  const handleDropOnSection = (sectionIndex: number) => {
    if (!dragField) return;
    setLayoutSections(prev => {
      const updated = [...prev];
      if (!updated[sectionIndex].fields.includes(dragField)) {
        updated[sectionIndex] = { ...updated[sectionIndex], fields: [...updated[sectionIndex].fields, dragField] };
      }
      return updated;
    });
    setDragField(null);
  };

  const removeFieldFromSection = (sectionIndex: number, fieldId: string) => {
    setLayoutSections(prev => {
      const updated = [...prev];
      updated[sectionIndex] = { ...updated[sectionIndex], fields: updated[sectionIndex].fields.filter(f => f !== fieldId) };
      return updated;
    });
  };

  const addSection = () => {
    const id = `section_${Date.now()}`;
    setLayoutSections(prev => [...prev, { id, type: 'custom', fields: [], label: 'New Section' }]);
  };

  const removeSection = (index: number) => {
    setLayoutSections(prev => prev.filter((_, i) => i !== index));
  };

  const moveSectionUp = (index: number) => {
    if (index === 0) return;
    setLayoutSections(prev => {
      const updated = [...prev];
      [updated[index - 1], updated[index]] = [updated[index], updated[index - 1]];
      return updated;
    });
  };

  const moveSectionDown = (index: number) => {
    setLayoutSections(prev => {
      if (index >= prev.length - 1) return prev;
      const updated = [...prev];
      [updated[index], updated[index + 1]] = [updated[index + 1], updated[index]];
      return updated;
    });
  };

  // --- COA ---
  const handleCreateCOA = async () => {
    try {
      await documentsAPI.createCOA({
        lot_id: parseInt(coaForm.lot_id),
        specification_id: coaForm.specification_id ? parseInt(coaForm.specification_id) : null,
        customer_id: coaForm.customer_id ? parseInt(coaForm.customer_id) : null,
        notes: coaForm.notes || null,
      });
      setShowCoaForm(false);
      setCoaForm({ lot_id: '', specification_id: '', customer_id: '', notes: '' });
      loadCOAs();
    } catch { /* ignore */ }
  };

  const handleApproveCOA = async (coaId: number) => {
    try {
      await documentsAPI.approveCOA(coaId);
      loadCOAs();
    } catch { /* ignore */ }
  };

  const handleDownloadCOA = async (coaId: number, certNumber: string) => {
    try {
      const res = await documentsAPI.downloadCOA(coaId);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `COA_${certNumber}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch { /* ignore */ }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'approved': return 'bg-green-100 text-green-800';
      case 'sent': return 'bg-blue-100 text-blue-800';
      default: return 'bg-yellow-100 text-yellow-800';
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-sm text-gray-500">Generate PDFs, manage templates, and issue Certificates of Analysis</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {(['generate', 'templates', 'coa', 'history'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === tab ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
              {tab === 'generate' ? 'Generate PDF' : tab === 'templates' ? 'Template Builder' : tab === 'coa' ? 'Certificates of Analysis' : 'History'}
            </button>
          ))}
        </nav>
      </div>

      {/* Generate PDF Tab */}
      {activeTab === 'generate' && (
        <div className="bg-white rounded-lg shadow p-6 max-w-xl">
          <h2 className="text-lg font-semibold mb-4">Generate Document PDF</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Document Type</label>
              <select value={genDocType} onChange={e => setGenDocType(e.target.value)} className="w-full border rounded-md px-3 py-2 text-sm">
                {DOC_TYPES.filter(d => d.value !== 'custom').map(d => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reference ID
                <span className="text-gray-400 ml-1">
                  ({genDocType === 'invoice' ? 'Invoice ID' : genDocType === 'purchase_order' ? 'PO ID' : genDocType === 'packing_list' ? 'Sales Order ID' : genDocType === 'batch_ticket' ? 'Production Order ID' : 'Lot ID'})
                </span>
              </label>
              <input type="number" value={genRefId} onChange={e => setGenRefId(e.target.value)} className="w-full border rounded-md px-3 py-2 text-sm" placeholder="Enter ID" />
            </div>
            <button onClick={handleGenerate} disabled={generating || !genRefId} className="bg-primary-600 text-white px-4 py-2 rounded-md text-sm hover:bg-primary-700 disabled:opacity-50">
              {generating ? 'Generating...' : 'Generate PDF'}
            </button>
            {genResult && (
              <div className={`p-3 rounded text-sm ${genResult.startsWith('Error') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
                {genResult}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Template Builder Tab */}
      {activeTab === 'templates' && !showTemplateForm && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Document Templates</h2>
            <button onClick={() => openTemplateEditor()} className="bg-primary-600 text-white px-4 py-2 rounded-md text-sm hover:bg-primary-700">New Template</button>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Default</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {templates.map(t => (
                  <tr key={t.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">{t.name}</td>
                    <td className="px-4 py-3 text-sm capitalize">{t.doc_type.replace('_', ' ')}</td>
                    <td className="px-4 py-3 text-sm">{t.is_default ? <span className="text-green-600 font-medium">Yes</span> : 'No'}</td>
                    <td className="px-4 py-3 text-sm space-x-2">
                      <button onClick={() => openTemplateEditor(t)} className="text-primary-600 hover:underline">Edit</button>
                      <button onClick={async () => { await documentsAPI.deleteTemplate(t.id); loadTemplates(); }} className="text-red-600 hover:underline">Delete</button>
                    </td>
                  </tr>
                ))}
                {templates.length === 0 && (
                  <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-500">No templates yet. Create one to get started.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Template Editor / Drag-and-Drop Builder */}
      {activeTab === 'templates' && showTemplateForm && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">{editingTemplate ? 'Edit Template' : 'New Template'}</h2>
            <button onClick={() => setShowTemplateForm(false)} className="text-gray-500 hover:text-gray-700 text-sm">Cancel</button>
          </div>
          <div className="grid grid-cols-12 gap-6">
            {/* Left: Field Palette */}
            <div className="col-span-3">
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-sm font-semibold mb-3 text-gray-700">Field Palette</h3>
                <p className="text-xs text-gray-400 mb-3">Drag fields to sections below</p>
                {Object.entries(
                  FIELD_PALETTE.reduce((acc, f) => {
                    (acc[f.category] = acc[f.category] || []).push(f);
                    return acc;
                  }, {} as Record<string, typeof FIELD_PALETTE>)
                ).map(([cat, fields]) => (
                  <div key={cat} className="mb-3">
                    <div className="text-xs font-medium text-gray-500 uppercase mb-1">{cat}</div>
                    {fields.map(f => (
                      <div
                        key={f.id}
                        draggable
                        onDragStart={() => handleDragStart(f.id)}
                        className="bg-gray-50 border border-gray-200 rounded px-2 py-1 text-xs mb-1 cursor-grab hover:bg-primary-50 hover:border-primary-300"
                      >
                        {f.label}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>

            {/* Center: Layout Builder */}
            <div className="col-span-6">
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="text-sm font-semibold mb-3 text-gray-700">Document Layout</h3>
                <div className="space-y-3">
                  {layoutSections.map((section, idx) => (
                    <div
                      key={section.id}
                      onDragOver={e => e.preventDefault()}
                      onDrop={() => handleDropOnSection(idx)}
                      className="border-2 border-dashed border-gray-300 rounded-lg p-3 min-h-[60px] hover:border-primary-400 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <input
                          value={section.label}
                          onChange={e => setLayoutSections(prev => {
                            const updated = [...prev];
                            updated[idx] = { ...updated[idx], label: e.target.value };
                            return updated;
                          })}
                          className="text-xs font-semibold text-gray-600 bg-transparent border-none focus:outline-none"
                        />
                        <div className="flex gap-1">
                          <button onClick={() => moveSectionUp(idx)} className="text-gray-400 hover:text-gray-600 text-xs px-1" title="Move up">&#9650;</button>
                          <button onClick={() => moveSectionDown(idx)} className="text-gray-400 hover:text-gray-600 text-xs px-1" title="Move down">&#9660;</button>
                          <button onClick={() => removeSection(idx)} className="text-red-400 hover:text-red-600 text-xs px-1" title="Remove">&#10005;</button>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {section.fields.map(fieldId => {
                          const field = FIELD_PALETTE.find(f => f.id === fieldId);
                          return (
                            <span key={fieldId} className="inline-flex items-center bg-primary-100 text-primary-800 text-xs px-2 py-0.5 rounded">
                              {field?.label || fieldId}
                              <button onClick={() => removeFieldFromSection(idx, fieldId)} className="ml-1 text-primary-600 hover:text-primary-800">&times;</button>
                            </span>
                          );
                        })}
                        {section.fields.length === 0 && (
                          <span className="text-xs text-gray-400 italic">Drop fields here</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <button onClick={addSection} className="mt-3 text-sm text-primary-600 hover:text-primary-700">+ Add Section</button>
              </div>
            </div>

            {/* Right: Template Properties */}
            <div className="col-span-3">
              <div className="bg-white rounded-lg shadow p-4 space-y-3">
                <h3 className="text-sm font-semibold mb-2 text-gray-700">Template Properties</h3>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
                  <input value={templateForm.name} onChange={e => setTemplateForm(p => ({ ...p, name: e.target.value }))} className="w-full border rounded px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Document Type</label>
                  <select value={templateForm.doc_type} onChange={e => setTemplateForm(p => ({ ...p, doc_type: e.target.value }))} className="w-full border rounded px-2 py-1 text-sm">
                    {DOC_TYPES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                  <textarea value={templateForm.description} onChange={e => setTemplateForm(p => ({ ...p, description: e.target.value }))} rows={2} className="w-full border rounded px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Header HTML</label>
                  <textarea value={templateForm.header_html} onChange={e => setTemplateForm(p => ({ ...p, header_html: e.target.value }))} rows={3} className="w-full border rounded px-2 py-1 text-sm font-mono" placeholder="<div>Custom header...</div>" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Footer HTML</label>
                  <textarea value={templateForm.footer_html} onChange={e => setTemplateForm(p => ({ ...p, footer_html: e.target.value }))} rows={3} className="w-full border rounded px-2 py-1 text-sm font-mono" placeholder="<div>Custom footer...</div>" />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={templateForm.is_default} onChange={e => setTemplateForm(p => ({ ...p, is_default: e.target.checked }))} />
                  Set as default for this type
                </label>
                <button onClick={saveTemplate} className="w-full bg-primary-600 text-white px-4 py-2 rounded-md text-sm hover:bg-primary-700">
                  {editingTemplate ? 'Update Template' : 'Create Template'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* COA Tab */}
      {activeTab === 'coa' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Certificates of Analysis</h2>
            <button onClick={() => setShowCoaForm(true)} className="bg-primary-600 text-white px-4 py-2 rounded-md text-sm hover:bg-primary-700">New COA</button>
          </div>

          {showCoaForm && (
            <div className="bg-white rounded-lg shadow p-4 mb-4 max-w-lg">
              <h3 className="text-sm font-semibold mb-3">Create Certificate of Analysis</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Lot ID *</label>
                  <input type="number" value={coaForm.lot_id} onChange={e => setCoaForm(p => ({ ...p, lot_id: e.target.value }))} className="w-full border rounded px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">QC Specification ID (optional)</label>
                  <input type="number" value={coaForm.specification_id} onChange={e => setCoaForm(p => ({ ...p, specification_id: e.target.value }))} className="w-full border rounded px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Customer ID (optional)</label>
                  <input type="number" value={coaForm.customer_id} onChange={e => setCoaForm(p => ({ ...p, customer_id: e.target.value }))} className="w-full border rounded px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
                  <textarea value={coaForm.notes} onChange={e => setCoaForm(p => ({ ...p, notes: e.target.value }))} rows={2} className="w-full border rounded px-2 py-1 text-sm" />
                </div>
                <div className="flex gap-2">
                  <button onClick={handleCreateCOA} className="bg-primary-600 text-white px-4 py-1.5 rounded text-sm hover:bg-primary-700">Create & Generate PDF</button>
                  <button onClick={() => setShowCoaForm(false)} className="text-gray-500 hover:text-gray-700 text-sm">Cancel</button>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Certificate #</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lot ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {coas.map(coa => (
                  <tr key={coa.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium">{coa.certificate_number}</td>
                    <td className="px-4 py-3 text-sm">{coa.lot_id}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(coa.status)}`}>{coa.status}</span>
                    </td>
                    <td className="px-4 py-3 text-sm">{new Date(coa.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-sm space-x-2">
                      <button onClick={() => handleDownloadCOA(coa.id, coa.certificate_number)} className="text-primary-600 hover:underline">Download</button>
                      {coa.status === 'draft' && (
                        <button onClick={() => handleApproveCOA(coa.id)} className="text-green-600 hover:underline">Approve</button>
                      )}
                    </td>
                  </tr>
                ))}
                {coas.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No certificates of analysis yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Generated Documents</h2>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">File</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reference</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Generated</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {generatedDocs.map(doc => (
                  <tr key={doc.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">{doc.id}</td>
                    <td className="px-4 py-3 text-sm capitalize">{doc.doc_type.replace('_', ' ')}</td>
                    <td className="px-4 py-3 text-sm font-mono text-xs">{doc.file_name}</td>
                    <td className="px-4 py-3 text-sm">{doc.reference_type} #{doc.reference_id}</td>
                    <td className="px-4 py-3 text-sm">{new Date(doc.generated_at).toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm">
                      <button onClick={() => handleDownload(doc.id, doc.file_name)} className="text-primary-600 hover:underline">Download</button>
                    </td>
                  </tr>
                ))}
                {generatedDocs.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No documents generated yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentsPage;
