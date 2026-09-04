import React, { useState } from 'react';
import DecisionMatrixCard from './DecisionMatrixCard';

/**
 * DecisionViewTab - Dedicated Decision Intelligence view.
 * Features primary recommendation banner, interactive MCDA matrix with dynamic weight sliders,
 * scenario projections (Best/Base/Worst), sensitivity switch points, and decision tripwires.
 */
export default function DecisionViewTab({ decisionMatrix, confidence, onExportTrigger = null }) {
  if (!decisionMatrix) {
    return (
      <div className="p-8 text-center bg-surface-container-low border border-outline-variant/60 rounded-xl">
        <span className="material-symbols-outlined text-4xl text-outline-variant mb-2">psychology</span>
        <h3 className="text-base font-bold text-on-surface">No Decision Matrix Available</h3>
        <p className="text-xs text-on-surface-variant mt-1">Submit a decision query to evaluate alternatives, criteria weights, and scenarios.</p>
      </div>
    );
  }

  const initialCriteria = decisionMatrix.criteria || [
    { name: "Total Cost of Ownership", weight: 0.35 },
    { name: "Technical Feasibility", weight: 0.35 },
    { name: "Risk Mitigation", weight: 0.30 }
  ];

  const [criteriaWeights, setCriteriaWeights] = useState(initialCriteria);

  const handleWeightChange = (index, newWeight) => {
    const updated = [...criteriaWeights];
    updated[index].weight = parseFloat(newWeight);
    setCriteriaWeights(updated);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner with One-Click Export Trigger */}
      <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-xl p-5 shadow-xl flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-cyber-cyan text-xl">gavel</span>
            <h2 className="font-mono text-sm font-bold text-cyber-cyan uppercase tracking-widest">
              Executive Decision Intelligence Workspace
            </h2>
          </div>
          <p className="text-xs text-on-surface-variant">
            Structured Multi-Criteria Decision Analysis (MCDA), probabilistic scenario projections, and interactive weight tuning.
          </p>
        </div>
        {onExportTrigger && (
          <button
            onClick={onExportTrigger}
            className="px-4 py-2 bg-cyber-cyan text-black font-bold font-mono text-xs rounded-lg shadow-lg hover:bg-cyber-cyan/80 transition-colors flex items-center gap-2 cursor-pointer"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            Export Package (ZIP)
          </button>
        )}
      </div>

      {/* Main Decision Matrix Card Component */}
      <DecisionMatrixCard decisionMatrix={decisionMatrix} confidence={confidence} />

      {/* Interactive Dynamic Criteria Weight Tuner */}
      <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex justify-between items-center border-b border-outline-variant/40 pb-3">
          <h3 className="font-mono text-xs font-bold text-cyber-cyan uppercase tracking-wider flex items-center gap-2">
            <span className="material-symbols-outlined text-sm">tune</span>
            Interactive Criteria Weight Adjustment Simulator
          </h3>
          <span className="font-mono text-[10px] text-on-surface-variant font-bold">LIVE RE-SCORING</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {criteriaWeights.map((crit, idx) => (
            <div key={crit.name + idx} className="p-3 bg-surface rounded-lg border border-outline-variant text-xs space-y-2">
              <div className="flex justify-between items-center font-bold text-on-surface">
                <span>{crit.name}</span>
                <span className="font-mono text-tertiary">{(crit.weight * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="0.80"
                step="0.05"
                value={crit.weight}
                onChange={(e) => handleWeightChange(idx, e.target.value)}
                className="w-full accent-cyber-cyan cursor-pointer"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
