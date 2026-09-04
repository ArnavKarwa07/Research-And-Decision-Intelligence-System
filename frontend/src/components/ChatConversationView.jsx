import React, { useState } from 'react';

export default function ChatConversationView({
  steps = [],
  evidence = [],
  claims = [],
  decisionMatrix = null,
  isResearching = false,
  currentQuery = null,
}) {
  const [showEvidenceDrawer, setShowEvidenceDrawer] = useState(false);

  const activeStep = steps[steps.length - 1];

  return (
    <div className="flex flex-col gap-5 max-w-4xl mx-auto w-full pb-28 pt-2">
      
      {/* Live Agent Workstream Pipeline Progress Banner */}
      {isResearching && (
        <div className="bg-surface-container-high/90 border border-primary/40 rounded-xl p-4 flex items-center justify-between shadow-lg backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-cyber-cyan animate-pulse-cyan shadow-[0_0_10px_rgba(56,189,248,0.8)]" />
            <div>
              <div className="font-mono text-xs font-bold text-cyber-cyan uppercase tracking-wider">
                Agent Workstream: {activeStep?.agentType || 'Supervisor'} Execution
              </div>
              <div className="text-xs text-on-surface-variant mt-0.5 font-medium">
                {activeStep?.message || 'Orchestrating sub-tasks and gathering multi-source evidence...'}
              </div>
            </div>
          </div>
          <span className="font-mono text-[11px] text-outline font-semibold">
            {steps.length} Steps Logged
          </span>
        </div>
      )}

      {/* User Prompt Message Card */}
      {currentQuery && (
        <div className="flex gap-3.5 items-start">
          <div className="w-9 h-9 rounded-full bg-surface-container-highest border border-outline-variant flex items-center justify-center font-bold text-sm text-primary flex-shrink-0 shadow-sm">
            U
          </div>
          <div className="bg-surface-container-low border border-outline-variant rounded-xl p-4 flex-1 text-on-surface text-sm leading-relaxed shadow-sm">
            {currentQuery.text}
          </div>
        </div>
      )}

      {/* Assistant Synthesized Answer Card */}
      {(decisionMatrix || evidence.length > 0 || claims.length > 0) && (
        <div className="flex gap-3.5 items-start">
          <div className="w-9 h-9 rounded-full bg-primary border border-primary/40 flex items-center justify-center font-bold text-sm text-on-primary flex-shrink-0 shadow-md">
            R
          </div>
          <div className="flex flex-col gap-4 flex-1">
            
            {/* Primary Strategic Recommendation Banner */}
            {decisionMatrix && (
              <div className="bg-surface-container border border-primary/50 rounded-xl p-5 shadow-xl relative overflow-hidden">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-mono text-[10px] font-bold text-primary uppercase tracking-widest flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">workspace_premium</span>
                    <span>Primary Strategic Recommendation</span>
                  </span>
                  <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-tertiary-container/30 text-tertiary border border-tertiary/40">
                    {Math.round((decisionMatrix.confidence || 0.88) * 100)}% Confidence
                  </span>
                </div>
                <h3 className="text-lg font-bold text-on-surface font-headline-md mb-2">
                  {decisionMatrix.recommendation}
                </h3>
                <p className="text-xs text-on-surface-variant leading-relaxed">
                  {decisionMatrix.rationale}
                </p>
              </div>
            )}

            {/* Synthesized Findings Block */}
            <div className="bg-surface-container-low border border-outline-variant rounded-xl p-5 text-on-surface text-sm leading-relaxed shadow-md">
              <div className="font-headline-md font-bold text-primary text-base mb-3">
                Synthesized Findings & Claim Analysis
              </div>

              <p className="text-xs text-on-surface-variant mb-3">
                Multi-agent research completed across verified primary sources, internal project knowledge, and quantitative trade-off criteria.
              </p>

              {/* Claims & Citation Chips */}
              {claims.length > 0 && (
                <div className="mt-4 flex flex-col gap-2">
                  <div className="font-mono text-[11px] font-bold text-outline uppercase tracking-wider">
                    Extracted Factual Claims ({claims.length})
                  </div>
                  {claims.slice(0, 4).map((c, idx) => (
                    <div key={c.id || idx} className="flex items-start gap-2.5 text-xs bg-surface-container p-3 rounded-lg border border-outline-variant/60">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                        c.support_status === 'SUPPORTED' ? 'bg-tertiary-container/30 text-tertiary' : 'bg-primary-container/30 text-primary'
                      }`}>
                        [{idx + 1}] {c.support_status || 'FACT'}
                      </span>
                      <span className="text-on-surface-variant flex-1">{c.text}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Collapsible Evidence Link Trigger */}
              {evidence.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowEvidenceDrawer(!showEvidenceDrawer)}
                  className="mt-4 px-3.5 py-2 bg-surface-container border border-outline-variant rounded-lg text-primary text-xs font-semibold hover:bg-surface-container-high transition-all flex items-center gap-2 cursor-pointer"
                >
                  <span className="material-symbols-outlined text-sm">manage_search</span>
                  <span>{showEvidenceDrawer ? 'Hide' : 'Inspect'} Verified Sources & Evidence Trail ({evidence.length})</span>
                </button>
              )}

              {/* Collapsible Evidence List */}
              {showEvidenceDrawer && (
                <div className="mt-3 flex flex-col gap-2">
                  {evidence.map((ev, i) => (
                    <div key={i} className="p-3 bg-surface-container border border-outline-variant/60 rounded-lg text-xs">
                      <div className="font-bold text-on-surface">{ev.source_title || ev.title || 'Source'}</div>
                      <div className="text-on-surface-variant mt-1 text-[11px]">{ev.excerpt || ev.snippet || ev.url}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
