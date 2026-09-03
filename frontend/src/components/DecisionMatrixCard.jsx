import React from 'react';

export default function DecisionMatrixCard({ decisionMatrix, confidence }) {
  if (!decisionMatrix) return null;

  const confPercent = Math.round((confidence || decisionMatrix.confidence || 0.90) * 100);

  return (
    <div className="w-full mb-6 bg-surface-container-low border border-cyber-cyan/40 rounded-xl p-5 shadow-xl relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-cyber-cyan/5 rounded-full blur-2xl pointer-events-none" />

      {/* Header */}
      <div className="pb-3 mb-4 border-b border-outline-variant flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-cyber-cyan text-lg">science</span>
          <h3 className="font-mono text-sm font-bold text-cyber-cyan uppercase tracking-widest">
            Executive Decision Matrix & Recommendation
          </h3>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-cyber-cyan/10 border border-cyber-cyan/30 rounded-full font-mono text-xs text-cyber-cyan font-bold">
          <span>CALIBRATED CONFIDENCE:</span>
          <span className="text-tertiary">{confPercent}%</span>
        </div>
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

      {/* Alternatives Trade-off Grid */}
      {decisionMatrix.alternatives && decisionMatrix.alternatives.length > 0 && (
        <div className="mb-4">
          <h4 className="font-mono text-xs font-bold text-on-surface uppercase tracking-wider mb-2.5">
            Evaluated Alternatives & Trade-offs
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {decisionMatrix.alternatives.map((alt) => (
              <div key={alt.name} className="p-3 rounded-lg bg-surface border border-outline-variant text-xs">
                <div className="flex justify-between items-center mb-1.5 font-bold text-on-surface">
                  <span>{alt.name}</span>
                  <span className="font-mono text-[11px] text-cyber-cyan">{Math.round((alt.score || 0.8) * 100)}% SCORE</span>
                </div>
                <div className="space-y-1 text-[11px]">
                  {alt.pros && alt.pros.length > 0 && (
                    <div className="text-tertiary flex items-start gap-1">
                      <span>✓</span> <span>{alt.pros.join(', ')}</span>
                    </div>
                  )}
                  {alt.cons && alt.cons.length > 0 && (
                    <div className="text-error flex items-start gap-1">
                      <span>✕</span> <span>{alt.cons.join(', ')}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Risks & Assumptions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        {decisionMatrix.key_risks && decisionMatrix.key_risks.length > 0 && (
          <div className="p-3 rounded-lg bg-surface border border-outline-variant">
            <h5 className="font-mono text-[10px] font-bold text-error uppercase tracking-wider mb-1">
              Key Risks
            </h5>
            <ul className="list-disc list-inside text-on-surface-variant space-y-1 text-[11px]">
              {decisionMatrix.key_risks.map((risk) => (
                <li key={risk}>{risk}</li>
              ))}
            </ul>
          </div>
        )}
        {decisionMatrix.assumptions && decisionMatrix.assumptions.length > 0 && (
          <div className="p-3 rounded-lg bg-surface border border-outline-variant">
            <h5 className="font-mono text-[10px] font-bold text-cyber-cyan uppercase tracking-wider mb-1">
              Core Assumptions
            </h5>
            <ul className="list-disc list-inside text-on-surface-variant space-y-1 text-[11px]">
              {decisionMatrix.assumptions.map((asm) => (
                <li key={asm}>{asm}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
