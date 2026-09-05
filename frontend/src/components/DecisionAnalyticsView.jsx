import React from 'react';

export default function DecisionAnalyticsView({
  decisionMatrix = null,
  baseWeight = 0.4,
  worstWeight = 0.2,
  onWeightChange = null,
  onExportTrigger = null
}) {
  const rawAlternatives = decisionMatrix?.alternatives || [];

  // Dynamic MCDA Score recalculation based on interactive sensitivity sliders
  const dynamicAlternatives = rawAlternatives.map((alt) => {
    const rawScore = typeof alt.score === 'number' ? alt.score : parseFloat(alt.score) || 7.5;
    const growthMult = baseWeight / 0.4;
    const penaltyFactor = 1 - (worstWeight - 0.2) * 0.6;
    const computedScore = Math.min(10, Math.max(1, Math.round(rawScore * growthMult * penaltyFactor * 10) / 10));

    return {
      ...alt,
      computedScore,
      pros: Array.isArray(alt.pros) ? alt.pros : [alt.pros || 'Strong objective alignment'],
      cons: Array.isArray(alt.cons) ? alt.cons : [alt.cons || 'Resource allocation required']
    };
  });

  const sortedAlternatives = [...dynamicAlternatives].sort((a, b) => b.computedScore - a.computedScore);

  let tippingPointText = decisionMatrix?.tipping_point || 'Requires completed decision analysis to calculate sensitivity tipping points.';
  if (sortedAlternatives.length > 0) {
    if (worstWeight >= baseWeight) {
      tippingPointText = `Tipping Point Reached: Downside penalty (${Math.round(worstWeight * 100)}%) equals or exceeds growth weight (${Math.round(baseWeight * 100)}%). Defensive risk mitigation strategies prioritize over expansion.`;
    } else {
      tippingPointText = `Base Case Growth Weight (${Math.round(baseWeight * 100)}%) dominates Downside Penalty (${Math.round(worstWeight * 100)}%). Top recommended option: '${sortedAlternatives[0]?.name}'.`;
    }
  }

  const handleBaseChange = (val) => {
    if (onWeightChange) onWeightChange(val, worstWeight);
  };

  const handleWorstChange = (val) => {
    if (onWeightChange) onWeightChange(baseWeight, val);
  };

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
            {sortedAlternatives.length === 0 ? (
              <tr>
                <td colSpan="4" className="p-8 text-center text-on-surface-variant italic">
                  Run a query to generate decision alternatives and view the analysis here.
                </td>
              </tr>
            ) : (
              sortedAlternatives.map((alt, i) => (
                <tr key={i} className="border-b border-outline-variant/60 text-xs hover:bg-surface-container/40">
                  <td className="p-4 font-bold text-on-surface">{alt.name}</td>
                  <td className="p-4 whitespace-nowrap min-w-[120px]">
                    <span className={`px-3 py-1.5 rounded-full font-bold font-mono text-xs whitespace-nowrap inline-flex items-center justify-center gap-1 ${
                      i === 0 ? 'bg-tertiary-container/30 text-tertiary border border-tertiary/40' : 'bg-surface-container text-on-surface-variant border border-outline-variant'
                    }`}>
                      {typeof alt.computedScore === 'number' ? alt.computedScore.toFixed(1) : alt.computedScore} / 10
                    </span>
                  </td>
                  <td className="p-4 text-tertiary font-medium">
                    {alt.pros.join(', ')}
                  </td>
                  <td className="p-4 text-error font-medium">
                    {alt.cons.join(', ')}
                  </td>
                </tr>
              ))
            )}
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
              onChange={(e) => handleBaseChange(parseFloat(e.target.value))}
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
              onChange={(e) => handleWorstChange(parseFloat(e.target.value))}
              className="w-full accent-error cursor-pointer"
            />
          </div>
        </div>

        <div className="mt-5 p-3.5 bg-surface-container rounded-lg border border-outline-variant/60 text-xs text-on-surface-variant font-mono flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-primary">lightbulb</span>
          <span>
            <strong className="text-primary">Sensitivity Tipping Point: </strong>
            {tippingPointText}
          </span>
        </div>
      </div>

    </div>
  );
}
