import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PageHeader from '../components/common/PageHeader';
import DataTable from '../components/common/DataTable';
import Modal from '../components/common/Modal';
import { recipesAPI, inventoryAPI } from '../services/api';
import type { Recipe, RecipeVersion, Item } from '../types';

type RecipeTab = 'general' | 'ingredients' | 'procedure';

interface IngredientRow {
  item_id: number;
  sequence: number;
  weight_percent: string;
  notes: string;
}

interface ProcedureRow {
  sequence: number;
  step_type: string; // add_ingredient, instruction
  ingredient_item_id: number | null;
  instruction_text: string;
}

const RecipesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [showEditor, setShowEditor] = useState(false);
  const [editingRecipe, setEditingRecipe] = useState<Recipe | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<RecipeVersion | null>(null);
  const [editorTab, setEditorTab] = useState<RecipeTab>('general');

  // Editor form state
  const [productItemId, setProductItemId] = useState<number | null>(null);
  const [description, setDescription] = useState('');
  const [comment, setComment] = useState('');
  const [batchSize, setBatchSize] = useState('');
  const [expectedYield, setExpectedYield] = useState('100');
  const [ingredients, setIngredients] = useState<IngredientRow[]>([]);
  const [procedureSteps, setProcedureSteps] = useState<ProcedureRow[]>([]);

  // New ingredient form
  const [newIngItemId, setNewIngItemId] = useState<number | null>(null);
  const [newIngPercent, setNewIngPercent] = useState('');

  const { data: recipes } = useQuery({ queryKey: ['recipes'], queryFn: () => recipesAPI.list() });
  const { data: itemsList } = useQuery({ queryKey: ['items'], queryFn: () => inventoryAPI.listItems() });
  const items: Item[] = itemsList?.data || [];
  const recipeList: Recipe[] = recipes?.data || [];

  const getItemCode = (id: number) => items.find(i => i.id === id)?.item_code || '?';
  const getItemName = (id: number) => items.find(i => i.id === id)?.name || '?';

  const getRecipeNumber = (recipe: Recipe, version: RecipeVersion) => {
    const item = items.find(i => i.id === recipe.product_item_id);
    return `${item?.item_code || '?'}.${String(version.version_number).padStart(2, '0')}`;
  };

  const resetEditor = () => {
    setProductItemId(null);
    setDescription('');
    setComment('');
    setBatchSize('');
    setExpectedYield('100');
    setIngredients([]);
    setProcedureSteps([]);
    setNewIngItemId(null);
    setNewIngPercent('');
    setEditorTab('general');
    setSelectedVersion(null);
    setEditingRecipe(null);
  };

  const openNew = () => {
    resetEditor();
    setShowEditor(true);
  };

  const openRecipe = (recipe: Recipe, version?: RecipeVersion) => {
    setEditingRecipe(recipe);
    setProductItemId(recipe.product_item_id);
    setDescription(recipe.description || '');
    const ver = version || recipe.versions[0];
    if (ver) {
      setSelectedVersion(ver);
      setComment(ver.comment || '');
      setBatchSize(ver.batch_size != null ? String(ver.batch_size) : '');
      setExpectedYield(String(ver.expected_yield_percent));
      setIngredients(ver.ingredients.map(ing => ({
        item_id: ing.item_id,
        sequence: ing.sequence,
        weight_percent: String(ing.weight_percent),
        notes: ing.notes || '',
      })));
      setProcedureSteps(ver.procedure_steps.map(s => ({
        sequence: s.sequence,
        step_type: s.step_type,
        ingredient_item_id: s.ingredient_item_id || null,
        instruction_text: s.instruction_text || '',
      })));
    }
    setEditorTab('general');
    setShowEditor(true);
  };

  const buildVersionPayload = () => ({
    comment,
    batch_size: batchSize ? Number(batchSize) : null,
    expected_yield_percent: Number(expectedYield) || 100,
    ingredients: ingredients.map((ing, i) => ({
      item_id: ing.item_id,
      sequence: i + 1,
      weight_percent: Number(ing.weight_percent),
      notes: ing.notes || null,
    })),
    procedure_steps: procedureSteps.map((s, i) => ({
      sequence: i + 1,
      step_type: s.step_type,
      ingredient_item_id: s.ingredient_item_id,
      instruction_text: s.instruction_text || null,
    })),
  });

  // Save (create or update draft)
  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!editingRecipe) {
        return recipesAPI.create({
          product_item_id: productItemId,
          description: description || null,
          initial_version: buildVersionPayload(),
        });
      } else if (selectedVersion && selectedVersion.status === 'draft') {
        await recipesAPI.update(editingRecipe.id, { description: description || null });
        return recipesAPI.updateVersion(selectedVersion.id, buildVersionPayload());
      } else {
        throw new Error('Cannot edit a published version. Clone to create a new revision.');
      }
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      toast.success('Recipe saved');
      if (!editingRecipe && res?.data) {
        const newRecipe = res.data as Recipe;
        setEditingRecipe(newRecipe);
        if (newRecipe.versions?.length) {
          setSelectedVersion(newRecipe.versions[0]);
        }
      }
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || err?.message || 'Failed to save'),
  });

  const publishMutation = useMutation({
    mutationFn: (versionId: number) => recipesAPI.publishVersion(versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      toast.success('Recipe published - this version is now locked');
      setShowEditor(false);
      resetEditor();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to publish'),
  });

  const cloneMutation = useMutation({
    mutationFn: ({ recipeId, versionId }: { recipeId: number; versionId?: number }) =>
      recipesAPI.cloneVersion(recipeId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      toast.success('New revision created from clone');
      if (editingRecipe) {
        recipesAPI.get(editingRecipe.id).then(r => {
          const recipe = r.data as Recipe;
          setEditingRecipe(recipe);
          const newVer = recipe.versions[0]; // newest
          if (newVer) openRecipe(recipe, newVer);
        });
      }
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed to clone'),
  });

  // --- Ingredient helpers ---
  const addIngredient = () => {
    if (!newIngItemId || !newIngPercent) {
      toast.error('Select item and enter weight %');
      return;
    }
    setIngredients([...ingredients, {
      item_id: newIngItemId,
      sequence: ingredients.length + 1,
      weight_percent: newIngPercent,
      notes: '',
    }]);
    setNewIngItemId(null);
    setNewIngPercent('');
  };

  const removeIngredient = (idx: number) => {
    setIngredients(ingredients.filter((_, i) => i !== idx));
  };

  const totalPercent = ingredients.reduce((s, i) => s + (Number(i.weight_percent) || 0), 0);

  // --- Procedure helpers ---
  const addFormulaSteps = () => {
    if (ingredients.length === 0) {
      toast.error('Add ingredients first before adding formula to procedure');
      return;
    }
    const newSteps: ProcedureRow[] = ingredients.map((ing, idx) => ({
      sequence: procedureSteps.length + idx + 1,
      step_type: 'add_ingredient',
      ingredient_item_id: ing.item_id,
      instruction_text: '',
    }));
    setProcedureSteps([...procedureSteps, ...newSteps]);
    toast.success(`Added ${newSteps.length} ingredient steps`);
  };

  const addInstructionStep = () => {
    setProcedureSteps([...procedureSteps, {
      sequence: procedureSteps.length + 1,
      step_type: 'instruction',
      ingredient_item_id: null,
      instruction_text: '',
    }]);
  };

  const clearProcedure = () => {
    if (procedureSteps.length === 0) return;
    if (confirm('Clear all procedure steps? This cannot be undone.')) {
      setProcedureSteps([]);
      toast.success('Procedure cleared');
    }
  };

  const moveProcedureStep = (idx: number, direction: 'up' | 'down') => {
    const newSteps = [...procedureSteps];
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= newSteps.length) return;
    [newSteps[idx], newSteps[targetIdx]] = [newSteps[targetIdx], newSteps[idx]];
    setProcedureSteps(newSteps);
  };

  const removeProcedureStep = (idx: number) => {
    setProcedureSteps(procedureSteps.filter((_, i) => i !== idx));
  };

  const updateProcedureStep = (idx: number, text: string) => {
    const newSteps = [...procedureSteps];
    newSteps[idx] = { ...newSteps[idx], instruction_text: text };
    setProcedureSteps(newSteps);
  };

  // Published versions are locked - only drafts are editable
  const isPublished = selectedVersion?.status === 'published';
  const isEditable = !selectedVersion || selectedVersion.status === 'draft';

  // --- List columns ---
  const columns = [
    { header: 'Recipe #', accessor: ((row: Recipe) => {
      const ver = row.versions[0];
      return ver ? getRecipeNumber(row, ver) : '-';
    }) },
    { header: 'Product', accessor: ((row: Recipe) => getItemCode(row.product_item_id)) },
    { header: 'Description', accessor: ((row: Recipe) => getItemName(row.product_item_id)) },
    { header: 'Versions', accessor: ((row: Recipe) => row.versions.length) },
    { header: 'Latest Status', accessor: ((row: Recipe) => {
      const ver = row.versions[0];
      if (!ver) return '-';
      return <span className={ver.status === 'published' ? 'badge-green' : 'badge-yellow'}>{ver.status}</span>;
    }) },
    { header: 'Actions', accessor: ((row: Recipe) => (
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline" onClick={(e) => { e.stopPropagation(); openRecipe(row); }}>Open</button>
      </div>
    )) },
  ];

  const editorTabs: { id: RecipeTab; label: string }[] = [
    { id: 'general', label: 'General' },
    { id: 'ingredients', label: 'Ingredients' },
    { id: 'procedure', label: 'Procedure' },
  ];

  return (
    <div>
      <PageHeader
        title="Recipe Management"
        subtitle="Create and manage product recipes"
        actions={<button className="btn-primary" onClick={openNew}>New Recipe</button>}
      />
      <div className="card">
        <DataTable columns={columns} data={recipeList} />
      </div>

      {/* Recipe Editor Modal */}
      <Modal
        isOpen={showEditor}
        onClose={() => { setShowEditor(false); resetEditor(); }}
        title={editingRecipe
          ? `Recipe: ${selectedVersion ? getRecipeNumber(editingRecipe, selectedVersion) : '...'}`
          : 'New Recipe'
        }
        size="xl"
      >
        <div>
          {/* Published banner */}
          {isPublished && (
            <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
              <strong>This version is published and locked.</strong> No changes can be made. To modify, clone this version to create a new revision.
            </div>
          )}

          {/* Version selector */}
          {editingRecipe && editingRecipe.versions.length > 1 && (
            <div className="mb-4 flex items-center gap-2">
              <label className="text-sm font-medium">Version:</label>
              <select
                className="input-field w-48"
                value={selectedVersion?.id || ''}
                onChange={(e) => {
                  const ver = editingRecipe.versions.find(v => v.id === Number(e.target.value));
                  if (ver) openRecipe(editingRecipe, ver);
                }}
              >
                {editingRecipe.versions.map(v => (
                  <option key={v.id} value={v.id}>
                    .{String(v.version_number).padStart(2, '0')} ({v.status})
                  </option>
                ))}
              </select>
              <span className="text-xs text-gray-400">All versions are preserved permanently</span>
            </div>
          )}

          {/* Tab bar */}
          <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
            {editorTabs.map(t => (
              <button key={t.id} onClick={() => setEditorTab(t.id)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${editorTab === t.id ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
              >{t.label}</button>
            ))}
          </div>

          {/* ===== GENERAL TAB ===== */}
          {editorTab === 'general' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Product (Item Code)</label>
                  <select
                    className="input-field"
                    value={productItemId || ''}
                    onChange={(e) => setProductItemId(e.target.value ? Number(e.target.value) : null)}
                    disabled={!!editingRecipe}
                  >
                    <option value="">-- Select Product --</option>
                    {items.filter(i => i.item_type === 'finished_good' || i.item_type === 'intermediate').map(i => (
                      <option key={i.id} value={i.id}>{i.item_code} - {i.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Recipe Number</label>
                  <input
                    className="input-field bg-gray-50"
                    readOnly
                    value={editingRecipe && selectedVersion
                      ? getRecipeNumber(editingRecipe, selectedVersion)
                      : productItemId
                        ? `${getItemCode(productItemId)}.01`
                        : ''
                    }
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Recipe Comment</label>
                <textarea
                  className="input-field"
                  rows={2}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  disabled={!isEditable}
                  placeholder="Reason for this recipe version"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Batch Size</label>
                  <input
                    type="number" step="0.01"
                    className="input-field"
                    value={batchSize}
                    onChange={(e) => setBatchSize(e.target.value)}
                    disabled={!isEditable}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Expected Yield %</label>
                  <input
                    type="number" step="0.01"
                    className="input-field"
                    value={expectedYield}
                    onChange={(e) => setExpectedYield(e.target.value)}
                    disabled={!isEditable}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Date Created</label>
                  <input
                    className="input-field bg-gray-50"
                    readOnly
                    value={selectedVersion ? new Date(selectedVersion.created_at).toLocaleDateString() : 'Not saved yet'}
                  />
                </div>
              </div>
              {selectedVersion?.published_at && (
                <div>
                  <label className="block text-sm font-medium mb-1">Date Published</label>
                  <input
                    className="input-field bg-gray-50"
                    readOnly
                    value={new Date(selectedVersion.published_at).toLocaleDateString()}
                  />
                </div>
              )}
            </div>
          )}

          {/* ===== INGREDIENTS TAB ===== */}
          {editorTab === 'ingredients' && (
            <div className="space-y-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-gray-500">
                    <th className="text-left py-2 w-8">#</th>
                    <th className="text-left py-2">Ingredient</th>
                    <th className="text-left py-2">Description</th>
                    <th className="text-right py-2 w-28">Weight %</th>
                    {isEditable && <th className="w-16"></th>}
                  </tr>
                </thead>
                <tbody>
                  {ingredients.map((ing, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="py-2 text-gray-400">{idx + 1}</td>
                      <td className="py-2 font-mono">{getItemCode(ing.item_id)}</td>
                      <td className="py-2">{getItemName(ing.item_id)}</td>
                      <td className="py-2 text-right">
                        {isEditable ? (
                          <input
                            type="number" step="0.01"
                            className="input-field w-24 text-right"
                            value={ing.weight_percent}
                            onChange={(e) => {
                              const newIngs = [...ingredients];
                              newIngs[idx] = { ...newIngs[idx], weight_percent: e.target.value };
                              setIngredients(newIngs);
                            }}
                          />
                        ) : `${ing.weight_percent}%`}
                      </td>
                      {isEditable && (
                        <td className="py-2">
                          <button className="text-red-500 text-xs hover:underline" onClick={() => removeIngredient(idx)}>Remove</button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 font-semibold">
                    <td></td>
                    <td></td>
                    <td className="py-2 text-right">Total:</td>
                    <td className={`py-2 text-right ${Math.abs(totalPercent - 100) > 0.01 ? 'text-red-600' : 'text-green-600'}`}>
                      {totalPercent.toFixed(2)}%
                    </td>
                    {isEditable && <td></td>}
                  </tr>
                </tfoot>
              </table>

              {isEditable && (
                <div className="flex gap-2 items-end">
                  <div className="flex-1">
                    <label className="block text-xs mb-1">Ingredient (Item Code)</label>
                    <select className="input-field" value={newIngItemId || ''} onChange={(e) => setNewIngItemId(e.target.value ? Number(e.target.value) : null)}>
                      <option value="">-- Select --</option>
                      {items.filter(i => i.item_type === 'raw_material' || i.item_type === 'intermediate').map(i => (
                        <option key={i.id} value={i.id}>{i.item_code} - {i.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="w-28">
                    <label className="block text-xs mb-1">Weight %</label>
                    <input type="number" step="0.01" className="input-field" value={newIngPercent} onChange={(e) => setNewIngPercent(e.target.value)} />
                  </div>
                  <button type="button" className="btn-secondary text-sm" onClick={addIngredient}>Add</button>
                </div>
              )}
            </div>
          )}

          {/* ===== PROCEDURE TAB ===== */}
          {editorTab === 'procedure' && (
            <div className="space-y-4">
              {procedureSteps.length === 0 && (
                <p className="text-gray-400 text-sm text-center py-4">
                  No procedure steps yet.{isEditable && ' Use "Add Formula" to add each ingredient as a step, then intersperse instructions as needed.'}
                </p>
              )}
              {procedureSteps.map((step, idx) => (
                <div key={idx} className={`flex gap-2 items-start border rounded-lg p-3 ${step.step_type === 'add_ingredient' ? 'bg-blue-50 border-blue-200' : 'bg-gray-50'}`}>
                  {isEditable && (
                    <div className="flex flex-col gap-1 pt-1">
                      <button
                        className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
                        disabled={idx === 0}
                        onClick={() => moveProcedureStep(idx, 'up')}
                        title="Move up"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" /></svg>
                      </button>
                      <button
                        className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
                        disabled={idx === procedureSteps.length - 1}
                        onClick={() => moveProcedureStep(idx, 'down')}
                        title="Move down"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                      </button>
                    </div>
                  )}
                  <div className="text-sm font-medium text-gray-500 w-8 pt-2">{idx + 1}.</div>
                  <div className="flex-1">
                    {step.step_type === 'add_ingredient' ? (
                      <div className="text-sm text-blue-800 font-medium">
                        <span className="inline-block bg-blue-100 rounded px-2 py-0.5 mr-2 text-xs uppercase tracking-wide">Add</span>
                        <span className="font-mono">{step.ingredient_item_id ? getItemCode(step.ingredient_item_id) : '?'}</span>
                        {' - '}
                        <span>{step.ingredient_item_id ? getItemName(step.ingredient_item_id) : '?'}</span>
                        {(() => {
                          const ing = ingredients.find(i => i.item_id === step.ingredient_item_id);
                          return ing ? <span className="text-blue-600 ml-2">({ing.weight_percent}%)</span> : null;
                        })()}
                      </div>
                    ) : (
                      isEditable ? (
                        <textarea
                          className="input-field w-full"
                          rows={2}
                          value={step.instruction_text}
                          onChange={(e) => updateProcedureStep(idx, e.target.value)}
                          placeholder="Enter instruction..."
                        />
                      ) : (
                        <div className="text-sm py-1">{step.instruction_text || <span className="text-gray-400 italic">No instruction text</span>}</div>
                      )
                    )}
                  </div>
                  {isEditable && (
                    <button className="text-red-500 text-xs hover:underline pt-2" onClick={() => removeProcedureStep(idx)}>Remove</button>
                  )}
                </div>
              ))}

              {isEditable && (
                <div className="flex gap-2 items-center">
                  <button type="button" className="btn-secondary text-sm" onClick={addFormulaSteps}>
                    + Add Formula
                  </button>
                  <button type="button" className="btn-secondary text-sm" onClick={addInstructionStep}>
                    + Add Instruction
                  </button>
                  {procedureSteps.length > 0 && (
                    <button
                      type="button"
                      className="ml-auto text-sm text-red-600 hover:text-red-800 hover:underline"
                      onClick={clearProcedure}
                    >
                      Clear All
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex justify-between mt-6 pt-4 border-t">
            <div className="flex gap-2">
              {editingRecipe && selectedVersion && (
                <button
                  type="button"
                  className="btn-secondary text-sm"
                  onClick={() => cloneMutation.mutate({ recipeId: editingRecipe.id, versionId: selectedVersion.id })}
                  disabled={cloneMutation.isPending}
                >
                  Clone (New Revision)
                </button>
              )}
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary" onClick={() => { setShowEditor(false); resetEditor(); }}>Close</button>
              {isEditable && (
                <>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => saveMutation.mutate()}
                    disabled={saveMutation.isPending || !productItemId}
                  >
                    Save Draft
                  </button>
                  {editingRecipe && selectedVersion && (
                    <button
                      type="button"
                      className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                      onClick={() => {
                        if (confirm('Publish this version? Once published, it is locked permanently and can only be changed by creating a new revision.')) {
                          publishMutation.mutate(selectedVersion.id);
                        }
                      }}
                      disabled={publishMutation.isPending}
                    >
                      Publish
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default RecipesPage;
