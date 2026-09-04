import React, { useState } from 'react';
import ClaimsPanel from './ClaimsPanel';
import EvidenceGraphView from './EvidenceGraphView';

/**
 * ClaimsGraphTab - Dedicated Claims Taxonomy & Evidence Graph view.
 * Filterable claim-to-source mapping interface distinguishing FACT, CALCULATION, INFERENCE, ASSUMPTION, PREDICTION, OPINION, UNRESOLVED claims.
 */
export default function ClaimsGraphTab({ claims = [], graphData = { nodes: [], edges: [], stats: {} } }) {
  const [activeSubTab, setActiveSubTab] = useState('TAXONOMY');
  const [selectedType, setSelectedType] = useState('ALL');

  const taxonomyTypes = ['ALL', 'FACT', 'CALCULATION', 'INFERENCE', 'ASSUMPTION', 'PREDICTION', 'OPINION', 'UNRESOLVED'];

  const filteredClaims = claims.filter(c => {
    if (selectedType === 'ALL') return true;
    return (c.claim_type || 'FACT').toUpperCase() === selectedType;
  });

  return (
    <div className="space-y-6">
      {/* Top Navigation & Sub-Tabs */}
      <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl">
        <div className="flex flex-wrap justify-between items-center gap-4 border-b border-outline-variant/40 pb-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-primary text-xl">account_tree</span>
              <h2 className="font-mono text-sm font-bold text-primary uppercase tracking-widest">
                Claims Taxonomy & Lineage Provenance Graph
              </h2>
            </div>
            <p className="text-xs text-on-surface-variant">
              Atomic claim classifications distinguishing factual assertions, calculations, deductions, and unstated assumptions.
            </p>
          </div>

          <div className="flex gap-2 font-mono text-xs">
            <button
              onClick={() => setActiveSubTab('TAXONOMY')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                activeSubTab === 'TAXONOMY'
                  ? 'bg-primary text-black border border-primary'
                  : 'bg-surface text-on-surface-variant hover:text-on-surface border border-outline-variant'
              }`}
            >
              Taxonomy Table
            </button>
            <button
              onClick={() => setActiveSubTab('GRAPH')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                activeSubTab === 'GRAPH'
                  ? 'bg-primary text-black border border-primary'
                  : 'bg-surface text-on-surface-variant hover:text-on-surface border border-outline-variant'
              }`}
            >
              Visual Provenance Graph
            </button>
          </div>
        </div>

        {/* Claim Type Filter Bar (Taxonomy Mode) */}
        {activeSubTab === 'TAXONOMY' && (
          <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
            <span className="text-on-surface-variant font-bold">TYPE FILTER:</span>
            {taxonomyTypes.map(t => (
              <button
                key={t}
                onClick={() => setSelectedType(t)}
                className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
                  selectedType === t
                    ? 'bg-primary/20 text-primary border border-primary/40'
                    : 'bg-surface text-on-surface-variant hover:text-on-surface border border-outline-variant'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Sub-Tab View Switching */}
      {activeSubTab === 'TAXONOMY' ? (
        <ClaimsPanel claims={filteredClaims} />
      ) : (
        <EvidenceGraphView graphData={graphData} />
      )}
    </div>
  );
}
