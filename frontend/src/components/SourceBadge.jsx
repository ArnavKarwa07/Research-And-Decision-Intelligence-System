import React from 'react';

export default function SourceBadge({ source }) {
  if (!source || (!source.url && !source.title)) return null;

  let domain = '';
  try {
    if (source.url) {
      domain = new URL(source.url).hostname.replace('www.', '');
    }
  } catch {
    domain = source.url || '';
  }

  return (
    <a
      href={source.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 px-3 py-1 bg-surface border border-outline-variant rounded-full text-cyber-cyan text-xs hover:border-cyber-cyan hover:text-white transition-colors"
    >
      <span className="material-symbols-outlined text-xs">language</span>
      <span className="font-medium truncate max-w-[240px]">{source.title || domain || 'Source Link'}</span>
      {domain && <span className="font-mono text-[10px] text-on-surface-variant">({domain})</span>}
      <span className="material-symbols-outlined text-xs">open_in_new</span>
    </a>
  );
}
