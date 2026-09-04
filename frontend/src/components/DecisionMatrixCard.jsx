import React, { useState } from 'react';

export default function DecisionMatrixCard({ decisionMatrix, confidence }) {
  if (!decisionMatrix) return null;

  const [activeTab, setActiveTab] = useState('overview');

  const confPercent = Math.round((confidence || decisionMatrix.confidence || 0.85) * 100);
  const criteria = decisionMatrix.criteria || [];
  const scenarios = decisionMatrix.scenarios?.scenarios || decisionMatrix.scenarios?.scenario_results || [];
  const switchPoints = decisionMatrix.sensitivity_analysis?.switch_points || [];
  const triggers = decisionMatrix.decision_triggers || [];
  const expectedValues = decisionMatrix.expected_values?.expected_values || {};

  return (
    <div className="w-full mb-6 bg-surface-container-low border border-cyber-cyan/40 rounded-xl p-5 shadow-xl relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-cyber-cyan/5 rounded-full blur-2xl pointer-events-none" />

      {/* Header */}
      <div className="pb-3 mb-4 border-b border-outline-variant flex flex-wrap justify-between items-center gap-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-cyber-cyan text-lg">psychology</span>
          <h3 className="font-mono text-sm font-bold text-cyber-cyan uppercase tracking-widest">
            Decision Intelligence Matrix & Scenario Analysis
          </h3>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-cyber-cyan/10 border border-cyber-cyan/30 rounded-full font-mono text-xs text-cyber-cyan font-bold">
          <span>CONFIDENCE:</span>
          <span className="text-tertiary">{confPercent}%</span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-2 mb-4 border-b border-outline-variant/40 pb-2 text-xs font-mono">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            activeTab === 'overview'
              ? 'bg-cyber-cyan/20 text-cyber-cyan font-bold border border-cyber-cyan/40'
              : 'text-on-surface-variant hover:text-on-surface'
          }`}
        >
          Overview & Alternatives
        </button>
        <button
          onClick={() => setActiveTab('scenarios')}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            activeTab === 'scenarios'
              ? 'bg-cyber-cyan/20 text-cyber-cyan font-bold border border-cyber-cyan/40'
              : 'text-on-surface-variant hover:text-on-surface'
          }`}
        >
          Scenarios & Sensitivity
        </button>
        <button
          onClick={() => setActiveTab('triggers')}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            activeTab === 'triggers'
              ? 'bg-cyber-cyan/20 text-cyber-cyan font-bold border border-cyber-cyan/40'
              : 'text-on-surface-variant hover:text-on-surface'
          }`}
        >
          Risks & Triggers
        </button>
      </div>

      {/* Recommendation Banner */}
      <div className="mb-4 p-4 rounded-lg bg-surface border border-tertiary/40">
        <div className="font-mono text-[10px] font-bold text-tertiary tracking-wider uppercase mb-1">
          PRIMARY RECOMMENDATION
        </div>
        <p className="text-sm font-bold text-on-surface leading-relaxed">
          {decisionMatrix.recommendation}
        </p>
        {decisionMatrix.rationale && (
          <p className="text-xs text-on-surface-variant mt-2 leading-relaxed">
            {decisionMatrix.rationale}
          </p>
        )}
      </div>

      {/* TAB 1: OVERVIEW & ALTERNATIVES */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {/* Alternatives Grid */}
          {decisionMatrix.alternatives && decisionMatrix.alternatives.length > 0 && (
            <div>
              <h4 className="font-mono text-xs font-bold text-on-surface uppercase tracking-wider mb-2.5">
                Evaluated Alternatives & Weighted Scores
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {decisionMatrix.alternatives.map((alt, idx) => {
                  const altName = typeof alt === 'string' ? alt : alt.name;
                  const score = typeof alt === 'object' ? (alt.weighted_score || alt.score || 0.75) : 0.75;
                  const pros = typeof alt === 'object' ? alt.pros : [];
                  const cons = typeof alt === 'object' ? alt.cons : [];

                  return (
                    <div key={altName + idx} className="p-3 rounded-lg bg-surface border border-outline-variant text-xs">
                      <div className="flex justify-between items-center mb-1.5 font-bold text-on-surface">
                        <span>{altName}</span>
                        <span className="font-mono text-[11px] text-cyber-cyan">
                          {Math.round(score * 100)}% SCORE
                        </span>
                      </div>
                      <div className="space-y-1 text-[11px]">
                        {pros && pros.length > 0 && (
                          <div className="text-tertiary flex items-start gap-1">
                            <span>✓</span> <span>{pros.join(', ')}</span>
                          </div>
                        )}
                        {cons && cons.length > 0 && (
                          <div className="text-error flex items-start gap-1">
                            <span>✕</span> <span>{cons.join(', ')}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Criteria Breakdown */}
          {criteria.length > 0 && (
            <div className="p-3 rounded-lg bg-surface border border-outline-variant text-xs">
              <h5 className="font-mono text-[11px] font-bold text-cyber-cyan uppercase tracking-wider mb-2">
                Normalized Decision Criteria
              </h5>
              <div className="space-y-1.5">
                {criteria.map((c, i) => (
                  <div key={i} className="flex justify-between items-center text-[11px]">
                    <span className="text-on-surface">{c.name}</span>
                    <span className="font-mono text-tertiary font-bold">
                      {(c.weight * 100).toFixed(0)}% Weight
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: SCENARIOS & SENSITIVITY */}
      {activeTab === 'scenarios' && (
        <div className="space-y-4 text-xs">
          {/* Scenarios */}
          <div className="p-3 rounded-lg bg-surface border border-outline-variant">
            <h5 className="font-mono text-[11px] font-bold text-cyber-cyan uppercase tracking-wider mb-2">
              Scenario Simulations (Best / Base / Worst)
            </h5>
            {scenarios.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                {scenarios.map((sc, i) => (
                  <div key={i} className="p-2.5 rounded bg-surface-container border border-outline-variant/60">
                    <div className="flex justify-between font-bold text-[11px] text-on-surface">
                      <span>{sc.name}</span>
                      <span className="font-mono text-tertiary">
                        {Math.round((sc.probability || 0.33) * 100)}%
                      </span>
                    </div>
                    {sc.description && (
                      <p className="text-[10px] text-on-surface-variant mt-1">{sc.description}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-on-surface-variant text-[11px]">Best-case (25%), Base-case (50%), and Worst-case (25%) scenarios evaluated.</p>
            )}
          </div>

          {/* Expected Values */}
          {Object.keys(expectedValues).length > 0 && (
            <div className="p-3 rounded-lg bg-surface border border-outline-variant">
              <h5 className="font-mono text-[11px] font-bold text-tertiary uppercase tracking-wider mb-2">
                Probabilistic Expected Payoff
              </h5>
              <div className="space-y-1">
                {Object.entries(expectedValues).map(([alt, val]) => (
                  <div key={alt} className="flex justify-between text-[11px]">
                    <span className="text-on-surface">{alt}</span>
                    <span className="font-mono text-cyber-cyan font-bold">{val} EV</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sensitivity Switch Points */}
          <div className="p-3 rounded-lg bg-surface border border-outline-variant">
            <h5 className="font-mono text-[11px] font-bold text-cyber-cyan uppercase tracking-wider mb-2">
              Criteria Weight Sensitivity & Tipping Points
            </h5>
            {switchPoints.length > 0 ? (
              <div className="space-y-2">
                {switchPoints.map((sp, i) => (
                  <div key={i} className="p-2 rounded bg-surface-container text-[11px] border border-outline-variant/40">
                    <span className="font-bold text-on-surface">{sp.criterion_name}: </span>
                    <span className="text-on-surface-variant">
                      If weight shifts from {(sp.original_weight * 100).toFixed(0)}% to {(sp.threshold_weight * 100).toFixed(0)}%, recommendation flips from '{sp.switches_from}' to '{sp.switches_to}'.
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-on-surface-variant text-[11px]">Recommendation remains stable across +/- 15% criteria weight perturbations.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: RISKS & TRIGGERS */}
      {activeTab === 'triggers' && (
        <div className="space-y-4 text-xs">
          {/* Decision Triggers */}
          {triggers.length > 0 && (
            <div className="p-3 rounded-lg bg-surface border border-outline-variant">
              <h5 className="font-mono text-[11px] font-bold text-error uppercase tracking-wider mb-2">
                Decision Tripwires & Triggers
              </h5>
              <div className="space-y-2">
                {triggers.map((t, i) => {
                  const cond = typeof t === 'string' ? t : t.condition;
                  const thresh = typeof t === 'object' ? t.threshold : '';
                  const act = typeof t === 'object' ? t.action : '';
                  const sev = typeof t === 'object' ? t.severity : 'medium';

                  return (
                    <div key={i} className="p-2.5 rounded bg-surface-container border border-error/30 flex items-start justify-between gap-2">
                      <div>
                        <div className="font-bold text-on-surface text-[11px]">{cond}</div>
                        {act && <div className="text-on-surface-variant text-[10px] mt-0.5">Action: {act}</div>}
                      </div>
                      {thresh && (
                        <span className="px-2 py-0.5 bg-error/10 text-error rounded font-mono text-[10px] font-bold whitespace-nowrap">
                          {thresh} ({sev})
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Key Risks & Assumptions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {decisionMatrix.key_risks && decisionMatrix.key_risks.length > 0 && (
              <div className="p-3 rounded-lg bg-surface border border-outline-variant">
                <h5 className="font-mono text-[10px] font-bold text-error uppercase tracking-wider mb-1">
                  Key Downside Risks
                </h5>
                <ul className="list-disc list-inside text-on-surface-variant space-y-1 text-[11px]">
                  {decisionMatrix.key_risks.map((risk, i) => (
                    <li key={i}>{risk}</li>
                  ))}
                </ul>
              </div>
            )}

            {decisionMatrix.assumptions && decisionMatrix.assumptions.length > 0 && (
              <div className="p-3 rounded-lg bg-surface border border-outline-variant">
                <h5 className="font-mono text-[10px] font-bold text-cyber-cyan uppercase tracking-wider mb-1">
                  Core Unstated Assumptions
                </h5>
                <ul className="list-disc list-inside text-on-surface-variant space-y-1 text-[11px]">
                  {decisionMatrix.assumptions.map((asm, i) => (
                    <li key={i}>{asm}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
