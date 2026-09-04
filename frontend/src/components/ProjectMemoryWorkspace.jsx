import React, { useState, useEffect } from 'react';
import AssumptionApprovalCard from './AssumptionApprovalCard';
import HeuristicsViewerCard from './HeuristicsViewerCard';
import { api } from '../lib/api';

export default function ProjectMemoryWorkspace({
  activeSessionId = null,
  activeProjectId = null,
  activeQueryId = null,
}) {
  const [activeTab, setActiveTab] = useState('items'); // 'items' | 'approvals' | 'heuristics' | 'injection'
  const [items, setItems] = useState([]);
  const [heuristics, setHeuristics] = useState(null);
  const [injectionPreview, setInjectionPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [memoryTypeFilter, setMemoryTypeFilter] = useState('ALL');
  const [validityFilter, setValidityFilter] = useState('ALL');
  const [searchKey, setSearchKey] = useState('');

  // Add Item Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [newItemKey, setNewItemKey] = useState('');
  const [newItemSummary, setNewItemSummary] = useState('');
  const [newItemType, setNewItemType] = useState('FACT');
  const [newItemConfidence, setNewItemConfidence] = useState(0.95);
  const [newItemTags, setNewItemTags] = useState('compliance, vendor');

  const fetchMemoryData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [itemsData, heuristicsData] = await Promise.all([
        api.listMemoryItems({ session_id: activeSessionId || undefined }).catch(() => null),
        api.getResearchHeuristics('finance').catch(() => null),
      ]);

      if (itemsData && Array.isArray(itemsData)) {
        setItems(itemsData);
      } else {
        // Fallback sample memory items for demo/offline resilience
        setItems([
          {
            id: 'mem-1',
            key: 'Vendor Uptime Baseline SLA',
            memory_type: 'FACT',
            summary: 'Primary vendor SLA contract obligates 99.9% availability with 4h RTO resolution window.',
            confidence: 0.98,
            validity_status: 'ACTIVE',
            human_approval_status: 'APPROVED',
            tags: ['contract', 'sla', 'vendor'],
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
          },
          {
            id: 'mem-2',
            key: 'EU GDPR Data Residency Assumption',
            memory_type: 'REUSABLE_ASSUMPTION',
            summary: 'Assumes all cross-border customer data processed by vendor remains within EU Frankfurt zone.',
            confidence: 0.85,
            validity_status: 'ACTIVE',
            human_approval_status: 'PENDING',
            content: { datacenter: 'Frankfurt-DE', encrypted_at_rest: true },
            tags: ['gdpr', 'privacy'],
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
          },
          {
            id: 'mem-3',
            key: 'Adversarial Red-Team Vulnerability Assessment',
            memory_type: 'PRIOR_CONCLUSION',
            summary: 'Secondary API gateway exhibits single-point-of-failure risk under peak traffic surge.',
            confidence: 0.90,
            validity_status: 'ACTIVE',
            human_approval_status: 'APPROVED',
            tags: ['red-team', 'risk'],
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
          },
          {
            id: 'mem-4',
            key: 'SOC2 Type II Audit Compliance',
            memory_type: 'REUSABLE_ASSUMPTION',
            summary: 'Assumes vendor SOC2 Type II audit report covers all sub-processors.',
            confidence: 0.70,
            validity_status: 'ACTIVE',
            human_approval_status: 'PENDING',
            tags: ['audit', 'soc2'],
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
          },
        ]);
      }

      if (heuristicsData) setHeuristics(heuristicsData);
    } catch (e) {
      console.error('Failed to fetch project memory data:', e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePreviewInjection = async () => {
    setLoading(true);
    try {
      const res = await api.previewContextInjection({
        session_id: activeSessionId || undefined,
        domain: 'finance',
        query_text: 'Analyze vendor contract risk and SLA compliance',
      });
      setInjectionPreview(res);
    } catch (e) {
      console.warn('API inject context error, using generated preview:', e);
      setInjectionPreview({
        formatted_prompt_text: `=== SYSTEM PROJECT MEMORY CONTEXT ===\n- FACT: Vendor Uptime Baseline SLA (99.9% uptime, 4h RTO)\n- ASSUMPTION [PENDING]: EU GDPR Data Residency (Frankfurt-DE zone)\n- PRIOR CONCLUSION: Secondary API gateway single-point-of-failure risk\n=== END CONTEXT ===`,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemoryData();
  }, [activeSessionId]);

  const handleCreateItem = async (e) => {
    e.preventDefault();
    if (!newItemKey.trim() || !newItemSummary.trim()) return;

    const payload = {
      key: newItemKey.trim(),
      summary: newItemSummary.trim(),
      memory_type: newItemType,
      confidence: parseFloat(newItemConfidence),
      tags: newItemTags.split(',').map((t) => t.trim()).filter(Boolean),
      session_id: activeSessionId || undefined,
    };

    try {
      const created = await api.createMemoryItem(payload);
      setItems([created, ...items]);
    } catch (e) {
      console.warn('API create item fallback:', e);
      const fallback = { id: `mem-${Date.now()}`, ...payload, validity_status: 'ACTIVE', human_approval_status: 'PENDING', created_at: new Date().toISOString() };
      setItems([fallback, ...items]);
    }
    setShowAddModal(false);
    setNewItemKey('');
    setNewItemSummary('');
  };

  const approvalFilterPredicate = (i) =>
    i.memory_type === 'REUSABLE_ASSUMPTION' || i.human_approval_status === 'PENDING';

  const approvalItems = items.filter(approvalFilterPredicate);
  const pendingApprovalsCount = approvalItems.length;

  const filteredItems = items.filter((item) => {
    if (memoryTypeFilter !== 'ALL' && item.memory_type !== memoryTypeFilter) return false;
    if (validityFilter !== 'ALL' && item.validity_status !== validityFilter) return false;
    if (searchKey.trim()) {
      const q = searchKey.toLowerCase();
      return (
        (item.key || '').toLowerCase().includes(q) ||
        (item.summary || '').toLowerCase().includes(q) ||
        (Array.isArray(item.tags) && item.tags.some((t) => (t || '').toLowerCase().includes(q)))
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12 text-on-surface">
      {/* Top Banner Header */}
      <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-xl p-5 shadow-xl flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-cyber-cyan text-2xl">neurology</span>
            <h2 className="font-mono text-base font-bold text-cyber-cyan uppercase tracking-wider">
              Project Memory & Research Heuristics Workspace
            </h2>
          </div>
          <p className="text-xs text-on-surface-variant">
            Persistent decision trail, reusable facts, human-in-the-loop assumption approvals, and prompt context injection.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="px-4 py-2 bg-cyber-cyan text-black font-bold font-mono text-xs rounded-lg shadow-lg hover:bg-cyber-cyan/80 transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <span className="material-symbols-outlined text-sm">note_add</span>
          Add Memory Item
        </button>
      </div>

      {/* Top Summary Metrics Cards Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 font-mono text-xs">
        <div className="p-3 bg-surface-container-low rounded-xl border border-outline-variant/60 space-y-1">
          <span className="text-[10px] text-on-surface-variant uppercase">Total Memory Items</span>
          <div className="text-xl font-bold text-cyber-cyan">{items.length}</div>
        </div>
        <div className="p-3 bg-surface-container-low rounded-xl border border-outline-variant/60 space-y-1">
          <span className="text-[10px] text-on-surface-variant uppercase">Pending Approvals</span>
          <div className="text-xl font-bold text-amber-400 flex items-center gap-2">
            <span>{pendingApprovalsCount}</span>
            {pendingApprovalsCount > 0 && (
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            )}
          </div>
        </div>
        <div className="p-3 bg-surface-container-low rounded-xl border border-outline-variant/60 space-y-1">
          <span className="text-[10px] text-on-surface-variant uppercase">Active Reusable Facts</span>
          <div className="text-xl font-bold text-tertiary">
            {items.filter((i) => i.memory_type === 'FACT').length}
          </div>
        </div>
        <div className="p-3 bg-surface-container-low rounded-xl border border-outline-variant/60 space-y-1">
          <span className="text-[10px] text-on-surface-variant uppercase">Heuristics Rules</span>
          <div className="text-xl font-bold text-purple-400">ACTIVE</div>
        </div>
      </div>

      {/* Primary Sub-Tabs Navigation Bar */}
      <div className="flex gap-2 border-b border-outline-variant pb-2 font-mono text-xs font-bold" role="tablist" aria-label="Project Memory Workspace Subtabs">
        {[
          { id: 'items', label: ' Memory Trail Store', count: items.length },
          { id: 'approvals', label: ' Human Assumption Approvals', count: pendingApprovalsCount },
          { id: 'heuristics', label: ' Domain Heuristics', count: null },
          { id: 'injection', label: ' Prompt Context Injection', count: null },
        ].map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={activeTab === t.id}
            onClick={() => {
              setActiveTab(t.id);
              if (t.id === 'injection') handlePreviewInjection();
            }}
            className={`px-3.5 py-2 rounded-xl transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyber-cyan/50 ${
              activeTab === t.id
                ? 'bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/50 shadow-md'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
            }`}
          >
            {t.label} {t.count !== null && <span className="text-[10px] opacity-75">({t.count})</span>}
          </button>
        ))}
      </div>

      {/* Tab Content 1: Memory Trail Store */}
      {activeTab === 'items' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-surface-container-low border border-outline-variant/60 rounded-xl font-mono text-xs">
            <div className="flex items-center gap-2 flex-1 min-w-[200px]">
              <span className="material-symbols-outlined text-sm text-on-surface-variant">search</span>
              <input
                type="text"
                value={searchKey}
                onChange={(e) => setSearchKey(e.target.value)}
                placeholder="Search memory items by key, summary, or tag..."
                className="w-full bg-surface border border-outline-variant rounded px-3 py-1.5 text-on-surface text-xs focus:outline-none focus:border-cyber-cyan"
              />
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-on-surface-variant">Type:</span>
                <select
                  value={memoryTypeFilter}
                  onChange={(e) => setMemoryTypeFilter(e.target.value)}
                  className="bg-surface border border-outline-variant rounded px-2 py-1 text-on-surface"
                >
                  <option value="ALL">ALL TYPES</option>
                  <option value="FACT">FACT</option>
                  <option value="REUSABLE_ASSUMPTION">REUSABLE ASSUMPTION</option>
                  <option value="PRIOR_CONCLUSION">PRIOR CONCLUSION</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-on-surface-variant">Validity:</span>
                <select
                  value={validityFilter}
                  onChange={(e) => setValidityFilter(e.target.value)}
                  className="bg-surface border border-outline-variant rounded px-2 py-1 text-on-surface"
                >
                  <option value="ALL">ALL VALIDITY</option>
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="SUPERSEDED">SUPERSEDED</option>
                  <option value="INVALIDATED">INVALIDATED</option>
                </select>
              </div>
            </div>
          </div>

          {/* Items List */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className="p-4 bg-surface-container-low rounded-xl border border-outline-variant/60 hover:border-cyber-cyan/50 transition-all space-y-3 shadow"
              >
                <div className="flex items-start justify-between gap-2 border-b border-outline-variant/40 pb-2">
                  <div>
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30 uppercase">
                      {item.memory_type}
                    </span>
                    <h4 className="font-mono text-xs font-bold text-on-surface mt-1">{item.key}</h4>
                  </div>
                  <span className="font-mono text-[10px] font-bold text-tertiary">
                    {(item.confidence * 100).toFixed(0)}% Conf
                  </span>
                </div>

                <p className="text-xs text-on-surface-variant font-body-main leading-relaxed">
                  {item.summary}
                </p>

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-outline-variant/30 font-mono text-[10px]">
                  <div className="flex gap-1 flex-wrap">
                    {(item.tags || []).map((t) => (
                      <span key={t} className="px-1.5 py-0.5 rounded bg-surface border border-outline-variant text-on-surface-variant">
                        #{t}
                      </span>
                    ))}
                  </div>
                  <span className="text-emerald-400 font-bold uppercase">{item.validity_status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab Content 2: Human Assumption Approvals */}
      {activeTab === 'approvals' && (
        <div className="space-y-4">
          <div className="p-4 bg-surface-container-low border border-amber-500/30 rounded-xl space-y-1">
            <h3 className="font-mono text-xs font-bold text-amber-400 uppercase flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">front_hand</span>
              Human-in-the-Loop Assumption Review Queue
            </h3>
            <p className="text-xs text-on-surface-variant">
              Approve or reject automated agent research assumptions before they are committed to project memory.
            </p>
          </div>

          <div className="space-y-4">
            {approvalItems.map((item) => (
                <AssumptionApprovalCard
                  key={item.id}
                  item={item}
                  onStatusUpdated={(id, newStatus) => {
                    setItems((prev) =>
                      prev.map((it) => (it.id === id ? { ...it, human_approval_status: newStatus } : it))
                    );
                  }}
                />
              ))}
          </div>
        </div>
      )}

      {/* Tab Content 3: Domain Research Heuristics */}
      {activeTab === 'heuristics' && (
        <HeuristicsViewerCard initialHeuristics={heuristics} domain="finance" />
      )}

      {/* Tab Content 4: Prompt Context Injection Preview */}
      {activeTab === 'injection' && (
        <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-xl p-5 shadow-xl space-y-4">
          <div className="flex justify-between items-center border-b border-outline-variant/40 pb-3 font-mono">
            <h3 className="text-xs font-bold text-cyber-cyan uppercase tracking-wider flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">terminal</span>
              Memory Context Injection Prompt Preview
            </h3>
            <button
              onClick={handlePreviewInjection}
              className="px-3 py-1 bg-cyber-cyan text-black font-bold text-[10px] rounded hover:bg-cyber-cyan/80 cursor-pointer"
            >
              Re-generate Context Prompt
            </button>
          </div>

          <p className="text-xs text-on-surface-variant font-body-main">
            This formatted memory context is automatically injected into LLM agent prompts during deep research runs:
          </p>

          <pre className="p-4 bg-black/80 rounded-lg border border-cyber-cyan/30 text-cyber-cyan font-mono text-xs overflow-x-auto leading-relaxed whitespace-pre-wrap">
            {injectionPreview?.formatted_prompt_text || 'Building context injection preview...'}
          </pre>
        </div>
      )}

      {/* Add Memory Item Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4 text-on-surface">
            <div className="flex items-center justify-between border-b border-outline-variant pb-2">
              <h3 className="font-mono text-xs font-bold text-cyber-cyan uppercase">Add Persistent Memory Item</h3>
              <button onClick={() => setShowAddModal(false)} className="text-on-surface-variant hover:text-on-surface">
                ×
              </button>
            </div>

            <form onSubmit={handleCreateItem} className="space-y-3 font-body-main text-xs">
              <div>
                <label className="block font-mono text-[10px] uppercase text-on-surface-variant mb-1">Key / Topic *</label>
                <input
                  type="text"
                  value={newItemKey}
                  onChange={(e) => setNewItemKey(e.target.value)}
                  placeholder="e.g. Primary Data Retention Policy"
                  className="w-full bg-surface border border-outline-variant rounded px-3 py-1.5 text-on-surface focus:outline-none focus:border-cyber-cyan"
                  required
                />
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-on-surface-variant mb-1">Memory Type</label>
                <select
                  value={newItemType}
                  onChange={(e) => setNewItemType(e.target.value)}
                  className="w-full bg-surface border border-outline-variant rounded px-3 py-1.5 text-on-surface font-mono"
                >
                  <option value="FACT">FACT</option>
                  <option value="REUSABLE_ASSUMPTION">REUSABLE ASSUMPTION</option>
                  <option value="PRIOR_CONCLUSION">PRIOR CONCLUSION</option>
                </select>
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-on-surface-variant mb-1">Summary *</label>
                <textarea
                  rows={3}
                  value={newItemSummary}
                  onChange={(e) => setNewItemSummary(e.target.value)}
                  placeholder="Summarize the verified fact or assumption..."
                  className="w-full bg-surface border border-outline-variant rounded px-3 py-1.5 text-on-surface focus:outline-none focus:border-cyber-cyan"
                  required
                />
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-on-surface-variant mb-1">
                  Confidence Score (0.0 - 1.0): {newItemConfidence}
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={newItemConfidence}
                  onChange={(e) => setNewItemConfidence(e.target.value)}
                  className="w-full accent-cyber-cyan"
                />
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-on-surface-variant mb-1">Tags (Comma separated)</label>
                <input
                  type="text"
                  value={newItemTags}
                  onChange={(e) => setNewItemTags(e.target.value)}
                  placeholder="compliance, security, vendor"
                  className="w-full bg-surface border border-outline-variant rounded px-3 py-1.5 text-on-surface font-mono"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-outline-variant">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1 bg-surface border border-outline-variant rounded text-on-surface-variant font-mono text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1 bg-cyber-cyan text-black font-bold font-mono text-xs rounded hover:bg-cyber-cyan/80"
                >
                  Save Item
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
