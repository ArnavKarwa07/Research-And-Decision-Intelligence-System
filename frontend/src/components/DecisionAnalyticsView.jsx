import React, { useState } from 'react';

export default function DecisionAnalyticsView({ decisionMatrix = null, onExportTrigger = null }) {
  const [baseWeight, setBaseWeight] = useState(0.4);
  const [worstWeight, setWorstWeight] = useState(0.2);

  const mockAlternatives = decisionMatrix?.alternatives || [
    { name: 'Option A: Cloud-Native Microservices Architecture', score: 8.8, pros: ['High scalability', 'Isolated failure domains'], cons: ['Higher operational complexity'] },
    { name: 'Option B: Hybrid Serverless & Modular Monolith', score: 7.6, pros: ['Lower initial cost', 'Fast deployment'], cons: ['Vendor lock-in risks'] },
    { name: 'Option C: On-Premises Air-Gapped Appliance', score: 6.2, pros: ['Maximum security compliance'], cons: ['High infrastructure CAPEX'] },
  ];

  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto w-full text-on-surface pb-28 pt-2">
      
      {/* Header Banner */}
      <div className="flex justify-between items-center bg-surface-container-low border border-outline-variant rounded-xl p-6 shadow-md">
        <div>
          <h2 className="text-xl font-bold font-headline-md text-primary flex items-center gap-2">
            <span className="material-symbols-outlined text-2xl">analytics</span>
            <span>Multi-Criteria Decision & Scenario Simulator</span>
          </h2>
          <p className="text-xs text-on-surface-variant mt-1">
            Quantitative option trade-off matrix, sensitivity analysis, and scenario simulation.
          </p>
        </div>
        {onExportTrigger && (
          <button
            type="button"
            onClick={onExportTrigger}
            className="px-4 py-2 bg-primary text-on-primary border border-primary/40 rounded-lg font-bold text-xs hover:bg-primary-container transition-all cursor-pointer shadow-md flex items-center gap-1.5"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            <span>Export Report & Data ZIP</span>
          </button>
        )}
      </div>

      {/* Alternatives Scoring Matrix Table */}
      <div className="bg-surface-container-low border border-outline-variant rounded-xl overflow-hidden shadow-md">
        <div className="p-4 border-b border-outline-variant font-bold text-sm text-primary font-headline-md bg-surface-container">
          MCDA Alternative Options & Weighted Evaluation
        </div>
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="bg-surface-container-high text-outline font-mono uppercase text-[11px] border-b border-outline-variant">
              <th className="p-4">Strategic Alternative Option</th>
              <th className="p-4">Weighted Score</th>
              <th className="p-4">Key Pros</th>
              <th className="p-4">Key Cons</th>
            </tr>
          </thead>
          <tbody>
            {mockAlternatives.map((alt, i) => (
              <tr key={i} className="border-b border-outline-variant/60 text-xs hover:bg-surface-container/40">
                <td className="p-4 font-bold text-on-surface">{alt.name}</td>
                <td className="p-4">
                  <span className={`px-3 py-1 rounded-full font-bold font-mono text-xs ${
                    i === 0 ? 'bg-tertiary-container/30 text-tertiary border border-tertiary/40' : 'bg-surface-container text-on-surface-variant border border-outline-variant'
                  }`}>
                    {alt.score} / 10
                  </span>
                </td>
                <td className="p-4 text-tertiary font-medium">
                  {alt.pros.join(', ')}
                </td>
                <td className="p-4 text-error font-medium">
                  {alt.cons.join(', ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Interactive Scenario Weight Simulator */}
      <div className="bg-surface-container-low border border-outline-variant rounded-xl p-6 shadow-md">
        <h3 className="text-base font-bold font-headline-md text-primary mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-lg">tune</span>
          <span>Scenario Simulation & Sensitivity Controls</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-xs text-on-surface mb-2 font-medium">
              Base Case Growth Weight: <strong className="text-primary">{Math.round(baseWeight * 100)}%</strong>
            </label>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={baseWeight}
              onChange={(e) => setBaseWeight(parseFloat(e.target.value))}
              className="w-full accent-primary cursor-pointer"
            />
          </div>

          <div>
            <label className="block text-xs text-on-surface mb-2 font-medium">
              Worst Case Downside Penalty: <strong className="text-error">{Math.round(worstWeight * 100)}%</strong>
            </label>
            <input
              type="range"
              min="0.05"
              max="0.5"
              step="0.05"
              value={worstWeight}
              onChange={(e) => setWorstWeight(parseFloat(e.target.value))}
              className="w-full accent-error cursor-pointer"
            />
          </div>
        </div>

        <div className="mt-5 p-3.5 bg-surface-container rounded-lg border border-outline-variant/60 text-xs text-on-surface-variant font-mono flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">lightbulb</span>
          <span><strong className="text-primary">Sensitivity Tipping Point:</strong> Recommendation flips from Option A to Option B if Base Case weight drops below 25% or Downside Penalty exceeds 40%.</span>
        </div>
      </div>

    </div>
  );
}
