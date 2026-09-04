import React, { useState } from 'react';
import EvidenceCard from './EvidenceCard';
import EvidenceEditorModal from './EvidenceEditorModal';

/**
 * EvidenceViewTab - Dedicated Evidence Explorer & Claim Mapping view.
 * Filterable evidence cards by confidence score, status, or search query.
 */
export default function EvidenceViewTab({ evidence = [], queryId = null }) {
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [editingEvidence, setEditingEvidence] = useState(null);

  const filteredEvidence = evidence.filter(item => {
    const matchesSearch = (item.claim || item.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (item.excerpt || item.summary || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === 'ALL' || (item.verification_status || 'verified').toUpperCase() === filterStatus;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner & Filter Controls */}
      <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl">
        <div className="flex flex-wrap justify-between items-center gap-4 border-b border-outline-variant/40 pb-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-tertiary text-xl">fact_check</span>
              <h2 className="font-mono text-sm font-bold text-tertiary uppercase tracking-widest">
                Verified Findings & Evidence Store
              </h2>
            </div>
            <p className="text-xs text-on-surface-variant">
              Multi-source evidence links with source provenance ratings, confidence meters, and claim validation states.
            </p>
          </div>
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="px-3 py-1 rounded-full bg-tertiary/10 border border-tertiary/30 text-tertiary font-bold">
              {filteredEvidence.length} / {evidence.length} ITEMS VISIBLE
            </span>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-mono text-on-surface-variant font-bold">STATUS FILTER:</span>
            {['ALL', 'VERIFIED', 'CONTRADICTED', 'INFERRED'].map(status => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                className={`px-3 py-1 rounded-lg font-mono font-bold transition-colors ${
                  filterStatus === status
                    ? 'bg-tertiary text-black border border-tertiary'
                    : 'bg-surface text-on-surface-variant hover:text-on-surface border border-outline-variant'
                }`}
              >
                {status}
              </button>
            ))}
          </div>

          <div className="relative flex-1 max-w-xs">
            <input
              type="text"
              placeholder="Search evidence & snippets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface border border-outline-variant rounded-lg px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-tertiary"
            />
          </div>
        </div>
      </div>

      {/* Evidence Cards List */}
      {filteredEvidence.length === 0 ? (
        <div className="p-8 text-center bg-surface-container-low border border-outline-variant/60 rounded-xl text-on-surface-variant text-xs">
          No evidence items matching current filters.
        </div>
      ) : (
        <div className="space-y-4">
          {filteredEvidence.map(item => (
            <div key={item.id || item.claim} className="relative group">
              <EvidenceCard evidence={item} />
              <button
                onClick={() => setEditingEvidence(item)}
                className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity px-2.5 py-1 bg-surface-variant border border-outline-variant text-on-surface rounded text-[11px] font-mono hover:border-primary"
              >
                 Edit Evidence
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Evidence Editor Modal */}
      {editingEvidence && (
        <EvidenceEditorModal
          evidence={editingEvidence}
          onClose={() => setEditingEvidence(null)}
          onSave={() => setEditingEvidence(null)}
        />
      )}
    </div>
  );
}
