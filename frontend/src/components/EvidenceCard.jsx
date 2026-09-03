import React, { useState } from 'react';
import SourceBadge from './SourceBadge';

function getBadgeColor(type) {
  switch (type) {
    case 'FACT': return 'bg-tertiary/10 text-tertiary border-tertiary/30';
    case 'CALCULATION': return 'bg-cyber-cyan/10 text-cyber-cyan border-cyber-cyan/30';
    case 'INFERENCE': return 'bg-gold-amber/10 text-gold-amber border-gold-amber/30';
    case 'ASSUMPTION': return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
    case 'PREDICTION': return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    default: return 'bg-surface-variant text-on-surface-variant border-outline-variant';
  }
}

export default function EvidenceCard({ evidence }) {
  const [copied, setCopied] = useState(false);
  const confidencePct = Math.round((evidence.confidence || 0) * 100);

  const handleCopy = () => {
    navigator.clipboard.writeText(evidence.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-surface-container-low border border-outline-variant rounded-lg p-4 mb-3 shadow-md hover:border-primary/40 transition-all">
      <div className="flex items-center justify-between gap-3 mb-3 pb-2 border-b border-outline-variant/50">
        <div className="flex items-center gap-2">
          <span className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider ${getBadgeColor(evidence.type)}`}>
            {evidence.type || 'EVIDENCE'}
          </span>
          {evidence.source?.qualityScore && (
            <span className="font-mono text-[10px] text-on-surface-variant">
              Quality Score: {evidence.source.qualityScore}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-12 bg-surface-container-high h-1.5 rounded-full overflow-hidden">
              <div className="bg-tertiary h-full rounded-full" style={{ width: `${confidencePct}%` }} />
            </div>
            <span className="font-mono text-[10px] font-bold text-on-surface">{confidencePct}% Conf.</span>
          </div>

          <button
            type="button"
            onClick={handleCopy}
            className="px-2 py-1 bg-surface-container border border-outline-variant rounded text-xs text-on-surface-variant hover:text-on-surface hover:border-primary transition-colors cursor-pointer"
            title="Copy Evidence Content"
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
        </div>
      </div>

      <p className="font-body-main text-sm text-on-surface leading-relaxed mb-3">
        {evidence.content}
      </p>

      {evidence.source && (
        <div className="pt-2 border-t border-outline-variant/30 flex items-center">
          <SourceBadge source={evidence.source} />
        </div>
      )}
    </div>
  );
}
