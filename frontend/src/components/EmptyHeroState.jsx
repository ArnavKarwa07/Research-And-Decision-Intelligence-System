import React from 'react';

const SAMPLE_QUERIES = [
  { tag: 'Supply Chain', icon: 'hub', query: 'Analyze Q3 semiconductor supply chain risks and export controls' },
  { tag: 'Verification', icon: 'science', query: 'Validate fusion energy net-gain claims and scaling benchmarks' }
];

export default function EmptyHeroState({ onSubmitQuery }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center max-w-3xl mx-auto w-full">
      {/* Glowing Radar Emblem */}
      <div className="relative w-32 h-32 flex items-center justify-center mb-8">
        <div className="absolute inset-0 bg-primary/5 rounded-full blur-2xl animate-pulse" />
        <div className="absolute inset-4 border border-primary/20 rounded-full animate-[spin_10s_linear_infinite]" />
        <div className="absolute inset-8 border border-primary/40 rounded-full animate-[spin_15s_linear_infinite_reverse]" />
        <svg className="w-12 h-12 text-primary relative z-10" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
          <path d="M12 2L2 12l10 10 10-10L12 2z" strokeLinecap="round" strokeLinejoin="round" />
          <path className="opacity-50" d="M12 6v12M6 12h12" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      <h1 className="font-display-lg text-3xl font-bold text-on-surface mb-3 text-center">
        Begin Autonomous Investigation
      </h1>
      <p className="font-body-main text-sm text-on-surface-variant text-center max-w-xl mb-10 leading-relaxed">
        Initialize a deep-research agent to crawl, verify, and synthesize disparate data sources. Select a starting heuristic or input a custom parameter set below.
      </p>

      {/* Bento Query Pills */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
        {SAMPLE_QUERIES.map((item) => (
          <button
            key={item.tag}
            type="button"
            onClick={() => onSubmitQuery(item.query)}
            className="bg-surface-container-low border border-outline-variant p-4 rounded hover:border-primary/50 cursor-pointer transition-all hover:-translate-y-0.5 group text-left"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-primary text-sm">{item.icon}</span>
              <span className="font-mono text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">{item.tag}</span>
            </div>
            <p className="font-body-strong text-sm text-on-surface group-hover:text-primary transition-colors">
              {item.query}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
