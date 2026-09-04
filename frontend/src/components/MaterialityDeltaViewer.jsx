import React, { useState } from 'react';

const formatPct = (val, digits = 0) => {
  const num = Number(val ?? 0);
  return Number.isFinite(num) ? (num * 100).toFixed(digits) : (0).toFixed(digits);
};

export default function MaterialityDeltaViewer({
  deltaSummary = null,
  materialityScore = 0.0,
  materialityLevel = 'NEGLIGIBLE',
  alertThreshold = 0.5,
  onClose = null,
}) {
  const [activeTab, setActiveTab] = useState('breakdown');

  // Extract delta details or provide robust structured defaults if delta object passed
  const breakdown = {
    claims_delta_score: deltaSummary?.score_breakdown?.claims_delta_score ?? deltaSummary?.claims_delta_score ?? 0.15,
    sources_delta_score: deltaSummary?.score_breakdown?.sources_delta_score ?? deltaSummary?.sources_delta_score ?? 0.10,
    assumptions_delta_score: deltaSummary?.score_breakdown?.assumptions_delta_score ?? deltaSummary?.assumptions_delta_score ?? 0.45,
    recommendation_flip_score: deltaSummary?.score_breakdown?.recommendation_flip_score ?? deltaSummary?.recommendation_flip_score ?? 0.0,
    total_score: materialityScore ?? deltaSummary?.score_breakdown?.total_score ?? deltaSummary?.total_score ?? 0.52,
    materiality_level: materialityLevel || deltaSummary?.score_breakdown?.materiality_level || deltaSummary?.materiality_level || 'MODERATE',
  };

  const claimsDrift = deltaSummary?.claims_drift || [
    {
      id: 'c1',
      claim: 'Vendor operational uptime guaranteed at 99.9%',
      baseline_text: 'SLA guarantees 99.9% uptime with 4h RTO',
      current_text: 'SLA downgraded to 99.5% uptime with 12h RTO',
      drift_score: 0.35,
      status: 'DRIFTED',
    },
    {
      id: 'c2',
      claim: 'ISO 27001 Security compliance verified',
      baseline_text: 'Active ISO 27001 certificate valid through 2027',
      current_text: 'Certificate pending renewal audit under review',
      drift_score: 0.20,
      status: 'MODIFIED',
    },
  ];

  const assumptionChanges = deltaSummary?.assumption_changes || [
    {
      id: 'a1',
      key: 'Data Sovereignty Compliance',
      baseline_status: 'VALIDATED',
      current_status: 'INVALIDATED',
      impact: 'EU data residency regulation update invalidates standard clause',
      confidence_change: -0.40,
    },
    {
      id: 'a2',
      key: 'Fixed Pricing Cap',
      baseline_status: 'VALIDATED',
      current_status: 'MODIFIED',
      impact: 'Annual indexation clause allows up to 7% increase',
      confidence_change: -0.15,
    },
  ];

  const sourceChanges = deltaSummary?.source_changes || [
    {
      id: 's1',
      domain: 'vendor-tech-disclosures.com',
      baseline_score: 0.85,
      current_score: 0.55,
      delta: -0.30,
      reason: 'Retracted press release & updated TOS',
    },
    {
      id: 's2',
      domain: 'sec-filings-audit.org',
      baseline_score: 0.90,
      current_score: 0.92,
      delta: +0.02,
      reason: 'Verified 10-Q filing submission',
    },
  ];

  const getLevelBadgeClass = (lvl) => {
    switch (lvl?.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-900/60 text-red-300 border-red-500/80 shadow-[0_0_10px_rgba(239,68,68,0.4)]';
      case 'HIGH':
        return 'bg-amber-900/60 text-amber-300 border-amber-500/80 shadow-[0_0_10px_rgba(245,158,11,0.4)]';
      case 'MODERATE':
        return 'bg-yellow-900/60 text-yellow-300 border-yellow-500/80';
      case 'LOW':
        return 'bg-blue-900/60 text-blue-300 border-blue-500/80';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-600';
    }
  };

  const isAlertTriggered = (breakdown.total_score ?? 0) >= alertThreshold;

  const content = (
    <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-xl p-6 shadow-2xl space-y-6 text-on-surface">
      {/* Top Banner & Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-outline-variant pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-cyber-cyan text-2xl">insights</span>
            <h2 className="font-mono text-base font-bold text-cyber-cyan uppercase tracking-wider">
              Continuous Intelligence Materiality Delta Viewer
            </h2>
          </div>
          <p className="text-xs text-on-surface-variant">
            Visual diff of baseline vs execution state, claim drift vectors, assumption invalidations, and mathematical scores.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-[10px] font-mono text-on-surface-variant uppercase">Materiality Status</span>
            <span
              className={`px-3 py-1 text-xs font-mono font-bold rounded-full border ${getLevelBadgeClass(
                breakdown.materiality_level
              )}`}
            >
              {breakdown.materiality_level} ({formatPct(breakdown.total_score)}%)
            </span>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 text-on-surface-variant hover:text-on-surface rounded bg-surface border border-outline-variant cursor-pointer"
            >
              <span className="material-symbols-outlined text-lg">close</span>
            </button>
          )}
        </div>
      </div>

      {/* Threshold Comparison Metric Bar */}
      <div className="p-4 bg-surface rounded-lg border border-outline-variant/60 space-y-3">
        <div className="flex justify-between items-center text-xs font-mono">
          <span className="text-on-surface-variant font-bold uppercase tracking-wider flex items-center gap-1.5">
            <span className="material-symbols-outlined text-sm text-cyber-cyan">query_stats</span>
            Aggregated Materiality Score vs Alert Threshold
          </span>
          <span className={isAlertTriggered ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
            {isAlertTriggered ? '⚠️ EXCEEDS THRESHOLD — ALERT TRIGGERED' : '✅ BELOW ALERT THRESHOLD'}
          </span>
        </div>

        {/* Multi-segmented Progress Bar */}
        <div className="w-full h-3 bg-surface-container rounded-full overflow-hidden relative border border-outline-variant/40">
          <div
            className={`h-full transition-all duration-500 ${
              (breakdown.total_score ?? 0) >= 0.8
                ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]'
                : (breakdown.total_score ?? 0) >= 0.5
                ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.8)]'
                : 'bg-emerald-500'
            }`}
            style={{ width: `${Math.min(100, Math.max(0, Number(formatPct(breakdown.total_score))))}%` }}
          />
          {/* Threshold Marker Pin */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_6px_#fff] z-10"
            style={{ left: `${Math.min(100, Math.max(0, Number(formatPct(alertThreshold))))}%` }}
            title={`Threshold: ${alertThreshold}`}
          />
        </div>
        <div className="flex justify-between items-center text-[10px] font-mono text-on-surface-variant">
          <span>0.0 (No Drift)</span>
          <span className="text-cyber-cyan font-bold">Threshold Pin: {formatPct(alertThreshold)}%</span>
          <span>1.0 (Critical Drift)</span>
        </div>
      </div>

      {/* Sub-Tabs Selector */}
      <div className="flex gap-2 border-b border-outline-variant pb-2 font-mono text-xs font-bold" role="tablist" aria-label="Delta Viewer Subtabs">
        {[
          { id: 'breakdown', label: '🧮 Math Breakdown', count: null },
          { id: 'claims', label: '🔴 Claim Drift', count: claimsDrift.length },
          { id: 'assumptions', label: '⚠️ Assumptions', count: assumptionChanges.length },
          { id: 'sources', label: '🌐 Source Scores', count: sourceChanges.length },
        ].map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={activeTab === t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-3 py-1.5 rounded transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyber-cyan/50 ${
              activeTab === t.id
                ? 'bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/50 shadow'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
            }`}
          >
            {t.label} {t.count !== null && <span className="text-[10px] opacity-75">({t.count})</span>}
          </button>
        ))}
      </div>

      {/* Tab Content 1: Mathematical Breakdown */}
      {activeTab === 'breakdown' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 font-mono">
            <div className="p-3 bg-surface rounded border border-outline-variant/60 space-y-1">
              <span className="text-[10px] text-on-surface-variant uppercase">S(claims)</span>
              <div className="text-lg font-bold text-cyber-cyan">
                {formatPct(breakdown.claims_delta_score)}%
              </div>
              <p className="text-[10px] text-on-surface-variant">Claim drift impact</p>
            </div>
            <div className="p-3 bg-surface rounded border border-outline-variant/60 space-y-1">
              <span className="text-[10px] text-on-surface-variant uppercase">S(sources)</span>
              <div className="text-lg font-bold text-tertiary">
                {formatPct(breakdown.sources_delta_score)}%
              </div>
              <p className="text-[10px] text-on-surface-variant">Source score change</p>
            </div>
            <div className="p-3 bg-surface rounded border border-outline-variant/60 space-y-1">
              <span className="text-[10px] text-on-surface-variant uppercase">S(assumptions)</span>
              <div className="text-lg font-bold text-amber-400">
                {formatPct(breakdown.assumptions_delta_score)}%
              </div>
              <p className="text-[10px] text-on-surface-variant">Invalidated assumptions</p>
            </div>
            <div className="p-3 bg-surface rounded border border-outline-variant/60 space-y-1">
              <span className="text-[10px] text-on-surface-variant uppercase">S(flip)</span>
              <div className="text-lg font-bold text-red-400">
                {formatPct(breakdown.recommendation_flip_score)}%
              </div>
              <p className="text-[10px] text-on-surface-variant">Recommendation flip</p>
            </div>
          </div>

          <div className="p-4 bg-surface rounded border border-outline-variant/60 font-mono text-xs space-y-2">
            <div className="text-cyber-cyan font-bold flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm">functions</span>
              Materiality Calculation Formula
            </div>
            <p className="text-on-surface-variant text-[11px] leading-relaxed">
              <code className="text-tertiary">
                M = max(S_claims, S_sources, S_assumptions, S_flip) * 0.6 + avg(S_i) * 0.4
              </code>
            </p>
          </div>
        </div>
      )}

      {/* Tab Content 2: Claim Drift Visual Diff */}
      {activeTab === 'claims' && (
        <div className="space-y-3 font-body-main text-xs">
          {claimsDrift.length === 0 ? (
            <p className="text-xs text-on-surface-variant italic py-4 text-center">No claim drift detected.</p>
          ) : (
            claimsDrift.map((c) => (
              <div key={c.id || c.claim} className="p-4 bg-surface rounded-lg border border-outline-variant/60 space-y-3">
                <div className="flex justify-between items-start gap-2">
                  <div className="font-bold text-on-surface flex items-center gap-2">
                    <span className="material-symbols-outlined text-amber-400 text-sm">compare_arrows</span>
                    <span>{c.claim}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-700">
                    {c.status} (+{formatPct(c.drift_score)}% drift)
                  </span>
                </div>

                {/* Side-by-side diff */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-[11px]">
                  <div className="p-3 bg-red-950/20 border border-red-900/40 rounded space-y-1">
                    <span className="text-red-400 font-bold uppercase text-[10px]">Baseline State</span>
                    <p className="text-red-200">{c.baseline_text}</p>
                  </div>
                  <div className="p-3 bg-emerald-950/20 border border-emerald-900/40 rounded space-y-1">
                    <span className="text-emerald-400 font-bold uppercase text-[10px]">Current Monitoring Run</span>
                    <p className="text-emerald-200">{c.current_text}</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab Content 3: Assumption Status Changes */}
      {activeTab === 'assumptions' && (
        <div className="space-y-3 font-body-main text-xs">
          {assumptionChanges.length === 0 ? (
            <p className="text-xs text-on-surface-variant italic py-4 text-center">No assumption status changes.</p>
          ) : (
            assumptionChanges.map((a) => (
              <div key={a.id || a.key} className="p-4 bg-surface rounded-lg border border-outline-variant/60 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-on-surface flex items-center gap-2 font-mono">
                    <span className="material-symbols-outlined text-red-400 text-sm">warning</span>
                    {a.key}
                  </span>
                  <div className="flex items-center gap-2 font-mono text-[10px]">
                    <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                      {a.baseline_status}
                    </span>
                    <span>➔</span>
                    <span className="px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 font-bold">
                      {a.current_status}
                    </span>
                  </div>
                </div>
                <p className="text-on-surface-variant text-xs">{a.impact}</p>
                <div className="text-[10px] font-mono text-red-400 font-bold">
                  Confidence impact: {formatPct(a.confidence_change)}%
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab Content 4: Source Score Changes */}
      {activeTab === 'sources' && (
        <div className="space-y-3 font-body-main text-xs">
          {sourceChanges.length === 0 ? (
            <p className="text-xs text-on-surface-variant italic py-4 text-center">No source reliability score changes.</p>
          ) : (
            sourceChanges.map((s) => (
              <div key={s.id || s.domain} className="p-3 bg-surface rounded-lg border border-outline-variant/60 flex items-center justify-between gap-4 font-mono">
                <div className="space-y-0.5">
                  <div className="font-bold text-cyber-cyan flex items-center gap-1.5 text-xs">
                    <span className="material-symbols-outlined text-sm">language</span>
                    {s.domain}
                  </div>
                  <p className="text-[10px] text-on-surface-variant font-body-main">{s.reason}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-[10px] text-on-surface-variant">Baseline ➔ Current</div>
                    <div className="text-xs font-bold text-on-surface">
                      {formatPct(s.baseline_score)}% ➔ {formatPct(s.current_score)}%
                    </div>
                  </div>
                  <span
                    className={`px-2 py-1 rounded text-xs font-bold ${
                      s.delta < 0 ? 'bg-red-950 text-red-300 border border-red-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    }`}
                  >
                    {s.delta > 0 ? `+${formatPct(s.delta)}%` : `${formatPct(s.delta)}%`}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );

  if (onClose) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
        <div className="max-w-3xl w-full">{content}</div>
      </div>
    );
  }

  return content;
}
