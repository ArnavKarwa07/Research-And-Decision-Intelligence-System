import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function HeuristicsViewerCard({
  initialHeuristics = null,
  domain = 'finance',
  onSave = null,
}) {
  const [untrustedDomains, setUntrustedDomains] = useState([]);
  const [effectiveTemplates, setEffectiveTemplates] = useState([]);
  const [verifiedPatterns, setVerifiedPatterns] = useState([]);
  const [failureModes, setFailureModes] = useState([]);
  const [newDomainInput, setNewDomainInput] = useState('');
  const [newTemplateInput, setNewTemplateInput] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (initialHeuristics) {
      setUntrustedDomains(initialHeuristics.untrusted_domains || []);
      setEffectiveTemplates(initialHeuristics.effective_query_templates || []);
      setVerifiedPatterns(initialHeuristics.verified_tool_patterns || []);
      setFailureModes(initialHeuristics.failure_modes || []);
    } else {
      // Default domain heuristic samples
      setUntrustedDomains(['untrusted-disclosures.blog', 'unverified-news-daily.com', 'sponsored-pr-newswire.net']);
      setEffectiveTemplates([
        'site:sec.gov "{company}" "Item 1A. Risk Factors"',
        '"{company}" AND ("SLA guarantee" OR "uptime benchmark")',
        '"{company}" AND "ISO 27001 audit report" filetype:pdf',
      ]);
      setVerifiedPatterns([
        { pattern: 'web_search -> sec_edgar_parser -> materiality_calculator', success_rate: 0.94, runs: 42 },
        { pattern: 'retrieval_agent -> fact_check -> contradiction_agent', success_rate: 0.88, runs: 29 },
      ]);
      setFailureModes([
        { error: 'Rate limit timeout on primary SEC gateway', mitigation: 'Fallback to archived 10-K cache' },
        { error: 'Ambiguous corporate legal entity name', mitigation: 'Query CIK identifier registry first' },
      ]);
    }
  }, [initialHeuristics]);

  const [toastMsg, setToastMsg] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const showToast = (msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleAddUntrustedDomain = () => {
    if (!newDomainInput.trim()) return;
    const clean = newDomainInput.trim().toLowerCase();
    const domainRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
    if (!domainRegex.test(clean)) {
      setErrorMsg(`Invalid domain format '${clean}'. Please enter a valid domain (e.g. example.com).`);
      return;
    }
    setErrorMsg(null);
    if (!untrustedDomains.includes(clean)) {
      setUntrustedDomains([...untrustedDomains, clean]);
    }
    setNewDomainInput('');
  };

  const handleRemoveUntrustedDomain = (dom) => {
    setUntrustedDomains(untrustedDomains.filter((d) => d !== dom));
  };

  const handleAddTemplate = () => {
    if (!newTemplateInput.trim()) return;
    setEffectiveTemplates([...effectiveTemplates, newTemplateInput.trim()]);
    setNewTemplateInput('');
  };

  const handleCopyTemplate = async (tpl) => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(tpl);
        showToast(`Copied template to clipboard: ${tpl}`);
      } else {
        showToast('Clipboard API unavailable');
      }
    } catch (e) {
      console.error('Clipboard copy error:', e);
      showToast('Failed to copy template');
    }
  };

  const handleSaveHeuristics = async () => {
    setIsSaving(true);
    setSaveSuccess(false);
    setErrorMsg(null);
    const payload = {
      domain,
      untrusted_domains: untrustedDomains,
      effective_query_templates: effectiveTemplates,
      verified_tool_patterns: verifiedPatterns,
      failure_modes: failureModes,
    };
    try {
      await api.createOrUpdateHeuristics(payload);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
      if (onSave) onSave(payload);
    } catch (e) {
      console.error('API update heuristics error:', e);
      setErrorMsg(e.message || 'Failed to save heuristics');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-xl p-5 shadow-xl space-y-6 text-on-surface relative">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 bg-cyber-cyan text-black px-4 py-2.5 rounded-lg shadow-2xl font-mono text-xs font-bold flex items-center gap-2 animate-bounce">
          <span className="material-symbols-outlined text-sm">content_copy</span>
          <span>{toastMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-red-950/40 border border-red-500/50 rounded text-red-300 text-xs flex items-center gap-2 font-mono">
          <span className="material-symbols-outlined text-sm">error</span>
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/40 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-cyber-cyan text-xl">psychology_alt</span>
            <h3 className="font-mono text-xs font-bold text-cyber-cyan uppercase tracking-wider">
              Domain Research Heuristics Store ({domain.toUpperCase()})
            </h3>
          </div>
          <p className="text-[11px] text-on-surface-variant">
            Adaptive rules, untrusted domain filters, verified tool call paths, and query templates.
          </p>
        </div>

        <button
          onClick={handleSaveHeuristics}
          disabled={isSaving}
          className="px-3.5 py-1.5 bg-cyber-cyan text-black font-bold font-mono text-xs rounded hover:bg-cyber-cyan/80 transition-colors cursor-pointer flex items-center gap-1.5 shadow"
        >
          {isSaving ? (
            <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
          ) : (
            <span className="material-symbols-outlined text-sm">save</span>
          )}
          {saveSuccess ? 'Saved!' : 'Save Heuristics'}
        </button>
      </div>

      {/* Section 1: Untrusted Domains / Source Filters */}
      <div className="p-4 bg-surface rounded-lg border border-outline-variant/60 space-y-3 font-mono text-xs">
        <div className="flex justify-between items-center">
          <span className="font-bold text-red-400 flex items-center gap-1.5 uppercase text-[11px]">
            <span className="material-symbols-outlined text-sm">block</span>
            Untrusted Source Filters & Blacklist
          </span>
          <span className="text-[10px] text-on-surface-variant font-semibold">
            {untrustedDomains.length} DOMAINS BLOCKED
          </span>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={newDomainInput}
            onChange={(e) => setNewDomainInput(e.target.value)}
            placeholder="e.g. dubious-blog.com"
            className="flex-1 bg-surface-container border border-outline-variant rounded px-3 py-1 text-on-surface focus:outline-none focus:border-cyber-cyan text-xs"
          />
          <button
            onClick={handleAddUntrustedDomain}
            className="px-3 py-1 bg-red-950/60 text-red-300 border border-red-800 rounded hover:bg-red-900 cursor-pointer font-bold text-xs"
          >
            + Add Filter
          </button>
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          {untrustedDomains.map((dom) => (
            <span
              key={dom}
              className="px-2.5 py-1 rounded bg-red-950/40 border border-red-800 text-red-300 text-[11px] flex items-center gap-1.5"
            >
              <span>{dom}</span>
              <button
                onClick={() => handleRemoveUntrustedDomain(dom)}
                className="hover:text-white cursor-pointer"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      </div>

      {/* Section 2: Effective Search Query Templates */}
      <div className="p-4 bg-surface rounded-lg border border-outline-variant/60 space-y-3 font-mono text-xs">
        <div className="flex justify-between items-center">
          <span className="font-bold text-tertiary flex items-center gap-1.5 uppercase text-[11px]">
            <span className="material-symbols-outlined text-sm">manage_search</span>
            Effective Search Query Templates
          </span>
          <span className="text-[10px] text-on-surface-variant font-semibold">
            PROVEN HIGH RECALL PATTERNS
          </span>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={newTemplateInput}
            onChange={(e) => setNewTemplateInput(e.target.value)}
            placeholder='site:domain.org "{target}" AND "clause"'
            className="flex-1 bg-surface-container border border-outline-variant rounded px-3 py-1 text-on-surface focus:outline-none focus:border-cyber-cyan text-xs font-mono"
          />
          <button
            onClick={handleAddTemplate}
            className="px-3 py-1 bg-tertiary/20 text-tertiary border border-tertiary/50 rounded hover:bg-tertiary/30 cursor-pointer font-bold text-xs"
          >
            + Add Template
          </button>
        </div>

        <div className="space-y-2">
          {effectiveTemplates.map((tpl, i) => (
            <div key={i} className="p-2.5 bg-surface-container/60 rounded border border-outline-variant/40 flex items-center justify-between gap-3 text-[11px]">
              <code className="text-cyber-cyan truncate">{tpl}</code>
              <button
                onClick={() => handleCopyTemplate(tpl)}
                className="px-2 py-0.5 bg-surface border border-outline-variant rounded text-[10px] text-on-surface-variant hover:text-on-surface cursor-pointer flex items-center gap-1 shrink-0"
              >
                <span className="material-symbols-outlined text-[12px]">content_copy</span>
                Copy
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Verified Tool Execution Patterns */}
      <div className="p-4 bg-surface rounded-lg border border-outline-variant/60 space-y-3 font-mono text-xs">
        <span className="font-bold text-cyber-cyan flex items-center gap-1.5 uppercase text-[11px]">
          <span className="material-symbols-outlined text-sm">schema</span>
          Verified Tool Execution Patterns & Success Rates
        </span>

        <div className="space-y-2">
          {verifiedPatterns.map((pat, i) => (
            <div key={i} className="p-3 bg-surface-container/60 rounded border border-outline-variant/40 flex items-center justify-between gap-4">
              <div className="space-y-0.5">
                <div className="font-bold text-on-surface text-[11px]">{pat.pattern}</div>
                <div className="text-[10px] text-on-surface-variant">Validated over {pat.runs || 10} agent runs</div>
              </div>
              <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-xs font-bold shrink-0">
                {((pat.success_rate || 0.9) * 100).toFixed(0)}% SUCCESS
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
