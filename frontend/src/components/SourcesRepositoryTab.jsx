import React, { useState, useEffect } from 'react';
import SourceScoringCard from './SourceScoringCard';
import { api } from '../lib/api';

/**
 * SourcesRepositoryTab - Dedicated Sources repository view.
 * Filterable and searchable repository of all external web results, internal documents (RAG), and data tables.
 */
export default function SourcesRepositoryTab({ queryId = null, initialSources = [] }) {
  const [sources, setSources] = useState(initialSources);
  const [loading, setLoading] = useState(false);
  const [selectedType, setSelectedType] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (!queryId) return;
    setLoading(true);
    api.getSources(queryId)
      .then(res => {
        if (Array.isArray(res)) setSources(res);
      })
      .catch(err => console.error('Failed to load sources:', err))
      .finally(() => setLoading(false));
  }, [queryId]);

  const filteredSources = sources.filter(src => {
    const matchesType = selectedType === 'ALL' || (src.source_type || 'web').toUpperCase() === selectedType;
    const matchesSearch = (src.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (src.publisher || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (src.url || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl">
        <div className="flex flex-wrap justify-between items-center gap-4 border-b border-outline-variant/40 pb-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-cyber-cyan text-xl">folder_open</span>
              <h2 className="font-mono text-sm font-bold text-cyber-cyan uppercase tracking-widest">
                Sources Repository & Domain Authority Index
              </h2>
            </div>
            <p className="text-xs text-on-surface-variant">
              Searchable catalog of web findings, internal PDF/DOCX RAG chunks, and database metrics with domain trust ratings.
            </p>
          </div>
          <div className="px-3 py-1 bg-cyber-cyan/10 border border-cyber-cyan/30 rounded-full font-mono text-xs text-cyber-cyan font-bold">
            {filteredSources.length} SOURCES INDEXED
          </div>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 font-mono">
            <span className="text-on-surface-variant font-bold">TYPE:</span>
            {['ALL', 'WEB', 'PDF', 'DB', 'ACADEMIC'].map(t => (
              <button
                key={t}
                onClick={() => setSelectedType(t)}
                className={`px-3 py-1 rounded-lg font-bold transition-colors ${
                  selectedType === t
                    ? 'bg-cyber-cyan text-black border border-cyber-cyan'
                    : 'bg-surface text-on-surface-variant hover:text-on-surface border border-outline-variant'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <input
            type="text"
            placeholder="Search source title, publisher, or URL..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-surface border border-outline-variant rounded-lg px-3 py-1.5 text-xs text-on-surface focus:outline-none focus:border-cyber-cyan max-w-xs w-full"
          />
        </div>
      </div>

      {/* Sources Grid */}
      {loading ? (
        <div className="p-8 text-center text-xs text-on-surface-variant">Loading indexed sources...</div>
      ) : filteredSources.length === 0 ? (
        <div className="p-8 text-center bg-surface-container-low border border-outline-variant/60 rounded-xl text-xs text-on-surface-variant">
          No sources match the selected criteria.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredSources.map(src => (
            <SourceScoringCard key={src.id || src.url} source={src} />
          ))}
        </div>
      )}
    </div>
  );
}
