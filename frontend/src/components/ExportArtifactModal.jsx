import React, { useState } from 'react';
import { api } from '../lib/api';

/**
 * ExportArtifactModal - One-Click Multi-Format Export Package Center.
 * Bundles complete research findings, decision memos, evidence graphs, and sources into downloadable ZIP, Markdown, CSV, and JSON specs.
 */
export default function ExportArtifactModal({ queryId, onClose }) {
  const [loading, setLoading] = useState(false);
  const [previewContent, setPreviewContent] = useState(null);
  const [activeFormat, setActiveFormat] = useState('ZIP');

  const downloadZipUrl = api.getExportPackageUrl(queryId || 'current');

  const handleFetchPreview = async (format) => {
    setActiveFormat(format);
    if (format === 'ZIP') {
      setPreviewContent(null);
      return;
    }
    setLoading(true);
    try {
      if (format === 'MEMO') {
        const res = await api.getDecisionMemo(queryId);
        setPreviewContent(res.markdown_content);
      } else if (format === 'REPORT') {
        const res = await api.getResearchReport(queryId);
        setPreviewContent(res.markdown_content);
      } else if (format === 'CSV') {
        const res = await api.getComparisonTable(queryId);
        setPreviewContent(res.csv_spec);
      }
    } catch (e) {
      console.error('Failed to fetch export preview:', e);
      setPreviewContent(`Error generating preview: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-5 relative">
        {/* Header */}
        <div className="flex justify-between items-start border-b border-outline-variant pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-cyber-cyan text-2xl">file_download</span>
              <h2 className="font-mono text-base font-bold text-cyber-cyan uppercase tracking-wider">
                Multi-Format Research Export Package Center
              </h2>
            </div>
            <p className="text-xs text-on-surface-variant mt-1">
              Bundle decision memos, technical research reports, MCDA comparison matrices, raw sources, and state dumps.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded font-bold text-lg cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Format Selector Bar */}
        <div className="flex gap-2 border-b border-outline-variant/40 pb-3 text-xs font-mono">
          {[
            { id: 'ZIP', label: '📦 Complete ZIP Package' },
            { id: 'MEMO', label: '📝 Decision Memo (MD)' },
            { id: 'REPORT', label: '📊 Technical Report (MD)' },
            { id: 'CSV', label: '📑 MCDA Matrix (CSV)' },
          ].map(fmt => (
            <button
              key={fmt.id}
              onClick={() => handleFetchPreview(fmt.id)}
              className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                activeFormat === fmt.id
                  ? 'bg-cyber-cyan text-black border border-cyber-cyan'
                  : 'bg-surface text-on-surface-variant hover:text-on-surface border border-outline-variant'
              }`}
            >
              {fmt.label}
            </button>
          ))}
        </div>

        {/* Download & Preview Area */}
        {activeFormat === 'ZIP' ? (
          <div className="p-6 rounded-xl bg-surface border border-cyber-cyan/30 text-center space-y-4">
            <span className="material-symbols-outlined text-5xl text-cyber-cyan animate-bounce">folder_zip</span>
            <div>
              <h3 className="text-sm font-bold text-on-surface">One-Click Multi-Format ZIP Archive Download</h3>
              <p className="text-xs text-on-surface-variant mt-1 max-w-md mx-auto">
                Includes decision_memo.md, research_report.md, executive_summary.html, sources_manifest.csv, mcda_comparison.csv, and research_state.json.
              </p>
            </div>
            <a
              href={downloadZipUrl}
              download
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-cyber-cyan text-black font-bold font-mono text-xs rounded-xl shadow-xl hover:bg-cyber-cyan/80 transition-colors"
            >
              <span className="material-symbols-outlined text-base">download</span>
              Download Export Package Archive (.zip)
            </a>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-surface border border-outline-variant max-h-80 overflow-y-auto font-mono text-xs text-on-surface space-y-2">
            {loading ? (
              <div className="text-center py-6 text-on-surface-variant">Generating preview artifact...</div>
            ) : (
              <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-on-surface-variant">
                {previewContent || 'Select an export artifact format to preview.'}
              </pre>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-between items-center pt-2 border-t border-outline-variant/40 text-xs text-on-surface-variant font-mono">
          <span>Format Specifications: UTF-8 Enforced & Citations Footnoted</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-surface border border-outline-variant rounded text-on-surface hover:border-primary cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
