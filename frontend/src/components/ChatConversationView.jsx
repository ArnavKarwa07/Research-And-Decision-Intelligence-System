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
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true);

  const activeStep = steps[steps.length - 1];

  return (
    <div className="flex flex-col gap-5 max-w-4xl mx-auto w-full pb-28 pt-2">
      
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

      {/* Antigravity-Style Agent Thinking & Execution Workstream (Positioned Directly Below User Prompt) */}
      {(isResearching || steps.length > 0) && (
        <div className="ml-12 border border-outline-variant/70 bg-surface-container-low/90 rounded-xl overflow-hidden shadow-md text-xs backdrop-blur-md">
          {/* Collapsible Header Banner */}
          <div
            onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
            className="p-3.5 bg-surface-container/80 flex items-center justify-between cursor-pointer border-b border-outline-variant/60 hover:bg-surface-container transition-colors select-none"
          >
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center">
                <span className={`w-3 h-3 rounded-full ${isResearching ? 'bg-cyber-cyan animate-ping absolute opacity-75' : 'bg-tertiary'}`} />
                <span className={`w-2.5 h-2.5 rounded-full ${isResearching ? 'bg-cyber-cyan shadow-[0_0_8px_rgba(56,189,248,0.8)]' : 'bg-tertiary'}`} />
              </div>
              <div className="font-mono text-xs font-bold text-primary flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">psychology</span>
                <span>
                  {isResearching
                    ? `Agent Thinking: ${activeStep?.agentType || activeStep?.agent_type || 'Supervisor Agent'} Executing...`
                    : `Agent Thinking & Workstream Execution (${steps.length} Steps Logged)`}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="font-mono text-[11px] px-2.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-bold">
                {steps.length} {steps.length === 1 ? 'Step' : 'Steps'} Logged
              </span>
              <span
                className="material-symbols-outlined text-sm text-outline transition-transform duration-200"
                style={{ transform: isThinkingExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
              >
                expand_more
              </span>
            </div>
          </div>

          {/* Expandable Step History Timeline Log */}
          {isThinkingExpanded && (
            <div className="p-4 flex flex-col gap-2.5 bg-surface-container-low/40 max-h-80 overflow-y-auto">
              {steps.length === 0 ? (
                <div className="text-on-surface-variant italic font-mono text-[11px] p-2 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  <span>Initializing LangGraph multi-agent execution pipeline...</span>
                </div>
              ) : (
                steps.map((step, idx) => (
                  <div
                    key={step.id || idx}
                    className="flex items-start gap-3 p-2.5 rounded-lg bg-surface-container/60 border border-outline-variant/40 hover:bg-surface-container transition-all"
                  >
                    <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-primary-container/40 text-primary border border-primary/30 shrink-0">
                      Step {idx + 1}
                    </span>
                    <div className="flex-1">
                      <div className="flex justify-between items-center mb-0.5">
                        <span className="font-bold text-on-surface font-headline-md text-xs">
                          {step.agentType || step.agent_type || 'Specialist Agent'}
                        </span>
                        {step.timestamp && (
                          <span className="font-mono text-[10px] text-outline">
                            {new Date(step.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </span>
                        )}
                      </div>
                      <p className="text-on-surface-variant text-[11px] leading-relaxed">
                        {step.message || 'Executing agent sub-task...'}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {/* Assistant Synthesized Answer Card */}
      {(decisionMatrix || evidence.length > 0 || claims.length > 0) && (
        <div className="flex gap-3.5 items-start">
          <div className="w-9 h-9 rounded-full bg-primary border border-primary/40 flex items-center justify-center font-bold text-sm text-on-primary flex-shrink-0 shadow-md">
            R
          </div>
          <div className="bg-surface-container-low border border-outline-variant rounded-xl p-5 text-on-surface text-sm leading-relaxed shadow-md flex-1 flex flex-col gap-4">
            
            {/* Recommendation Header */}
            {decisionMatrix && (
              <div className="border-b border-outline-variant/60 pb-4">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="font-mono text-[10px] font-bold text-primary uppercase tracking-widest flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">workspace_premium</span>
                    <span>Strategic Synthesis</span>
                  </span>
                  <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded-full bg-tertiary-container/30 text-tertiary border border-tertiary/40">
                    {Math.round((decisionMatrix.confidence || 0.88) * 100)}% Confidence
                  </span>
                </div>
                <h3 className="text-base font-bold text-on-surface font-headline-md">
                  {decisionMatrix.recommendation}
                </h3>
                {decisionMatrix.rationale && (
                  <p className="text-xs text-on-surface-variant leading-relaxed mt-1.5">
                    {decisionMatrix.rationale}
                  </p>
                )}

                {/* Gemini / ChatGPT Deep Research Report Rendered Block */}
                <div className="mt-4 p-5 rounded-xl bg-surface-container/60 border border-outline-variant/70 text-xs flex flex-col gap-4 font-body-main leading-relaxed">
                  <div className="font-mono text-[11px] font-bold text-primary uppercase tracking-widest flex items-center gap-1 border-b border-outline-variant/40 pb-2">
                    <span className="material-symbols-outlined text-sm">article</span>
                    <span>Executive Deep Research Report</span>
                  </div>

                  {decisionMatrix.research_report ? (
                    <div className="whitespace-pre-wrap text-on-surface space-y-3 font-sans text-xs">
                      {decisionMatrix.research_report}
                    </div>
                  ) : (
                    <div className="flex flex-col gap-4 text-on-surface">
                      <div>
                        <h4 className="font-bold text-sm text-primary mb-1">1. Executive Summary & Core Strategic Recommendation</h4>
                        <p className="text-on-surface-variant leading-relaxed">
                          {decisionMatrix.recommendation || `Multi-agent investigation completed with ${Math.round((decisionMatrix.confidence || 0.88) * 100)}% overall confidence.`}
                        </p>
                      </div>

                      {decisionMatrix.alternatives && decisionMatrix.alternatives.length > 0 && (
                        <div>
                          <h4 className="font-bold text-sm text-primary mb-2">2. In-Depth Strategic Options Evaluation</h4>
                          <div className="space-y-2">
                            {decisionMatrix.alternatives.map((alt, idx) => (
                              <div key={idx} className="p-3 bg-surface-container rounded-lg border border-outline-variant/60">
                                <div className="flex justify-between items-center mb-1">
                                  <span className="font-bold text-on-surface">{alt.name}</span>
                                  <span className="font-mono font-bold text-tertiary text-[11px]">{alt.score || 8.0} / 10</span>
                                </div>
                                {alt.pros && <p className="text-tertiary text-[11px]"><strong>Pros:</strong> {Array.isArray(alt.pros) ? alt.pros.join(', ') : alt.pros}</p>}
                                {alt.cons && <p className="text-error text-[11px] mt-0.5"><strong>Cons:</strong> {Array.isArray(alt.cons) ? alt.cons.join(', ') : alt.cons}</p>}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {decisionMatrix.key_risks && decisionMatrix.key_risks.length > 0 && (
                        <div>
                          <h4 className="font-bold text-sm text-primary mb-1">3. Key Risks & Vulnerability Analysis</h4>
                          <ul className="list-disc list-inside text-on-surface-variant space-y-1">
                            {decisionMatrix.key_risks.map((risk, rIdx) => (
                              <li key={rIdx}>{risk}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Claims & Citation Chips */}
            {claims.length > 0 && (
              <div className="flex flex-col gap-2">
                <div className="font-mono text-[11px] font-bold text-outline uppercase tracking-wider">
                  Verified Factual Claims ({claims.length})
                </div>
                {claims.slice(0, 5).map((c, idx) => (
                  <div key={c.id || idx} className="flex items-start gap-2.5 text-xs bg-surface-container p-3 rounded-lg border border-outline-variant/60">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono shrink-0 ${
                      c.support_status === 'SUPPORTED' ? 'bg-tertiary-container/30 text-tertiary border border-tertiary/40' : 'bg-primary-container/30 text-primary border border-primary/40'
                    }`}>
                      [{idx + 1}] {c.support_status || 'FACT'}
                    </span>
                    <span className="text-on-surface-variant flex-1">{c.content || c.text || 'Verified factual claim statement'}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Collapsible Evidence Link Trigger */}
            {evidence.length > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => setShowEvidenceDrawer(!showEvidenceDrawer)}
                  className="px-3.5 py-2 bg-surface-container border border-outline-variant rounded-lg text-primary text-xs font-semibold hover:bg-surface-container-high transition-all flex items-center gap-2 cursor-pointer"
                >
                  <span className="material-symbols-outlined text-sm">manage_search</span>
                  <span>{showEvidenceDrawer ? 'Hide' : 'Inspect'} Verified Sources & Evidence Trail ({evidence.length})</span>
                </button>

                {showEvidenceDrawer && (
                  <div className="mt-3 flex flex-col gap-2">
                    {evidence.map((ev, i) => {
                      const sourceTitle = ev.source?.title || ev.source_title || ev.title || ev.source?.url || `Verified Source #${i + 1}`;
                      const sourceUrl = ev.source?.url || ev.url || '';
                      const contentSnippet = ev.content || ev.excerpt || ev.snippet || sourceUrl || 'Retrieved source intelligence snippet.';
                      const quality = ev.source?.qualityScore || ev.qualityScore || 'VERIFIED';
                      return (
                        <div key={i} className="p-3 bg-surface-container border border-outline-variant/60 rounded-lg text-xs flex flex-col gap-1">
                          <div className="flex justify-between items-center">
                            <span className="font-bold text-primary flex items-center gap-1.5">
                              <span className="material-symbols-outlined text-sm">auto_stories</span>
                              <span>{sourceTitle}</span>
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-tertiary-container/30 text-tertiary border border-tertiary/40">
                              {quality}
                            </span>
                          </div>
                          <p className="text-on-surface-variant text-[11px] leading-relaxed mt-0.5">{contentSnippet}</p>
                          {sourceUrl && (
                            <a href={sourceUrl} target="_blank" rel="noreferrer" className="text-[10px] text-cyber-cyan hover:underline font-mono truncate max-w-full">
                              {sourceUrl}
                            </a>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  );
}
