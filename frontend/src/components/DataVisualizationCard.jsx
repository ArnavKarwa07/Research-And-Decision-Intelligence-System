import React, { useState } from 'react';

export function DataVisualizationCard({ spec, tableData, keyFindings, queryId, onOpenArtifacts }) {
  const [activeTab, setActiveTab] = useState('chart');

  if (!spec && (!tableData || tableData.length === 0)) {
    return null;
  }

  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.6)',
      border: '1px solid rgba(56, 189, 248, 0.2)',
      borderRadius: '12px',
      padding: '20px',
      marginTop: '20px',
      color: '#e2e8f0',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#38bdf8', fontWeight: 600 }}>
            📊 {spec?.title || 'Data Investigation & Visual Insights'}
          </h3>
          {spec?.description && (
            <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#94a3b8' }}>{spec.description}</p>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setActiveTab('chart')}
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'chart' ? '#0284c7' : 'rgba(51, 65, 85, 0.6)',
              color: '#ffffff',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 500
            }}
          >
            Chart Spec
          </button>
          <button
            onClick={() => setActiveTab('table')}
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'table' ? '#0284c7' : 'rgba(51, 65, 85, 0.6)',
              color: '#ffffff',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 500
            }}
          >
            Summary Table
          </button>
          {queryId && onOpenArtifacts && (
            <button
              onClick={() => onOpenArtifacts(queryId)}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid #38bdf8',
                background: 'transparent',
                color: '#38bdf8',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 500
              }}
            >
              ⚡ Reproducible Artifacts
            </button>
          )}
        </div>
      </div>

      {keyFindings && keyFindings.length > 0 && (
        <div style={{
          background: 'rgba(30, 41, 59, 0.5)',
          borderRadius: '8px',
          padding: '12px 16px',
          marginBottom: '16px',
          borderLeft: '4px solid #38bdf8'
        }}>
          <h4 style={{ margin: '0 0 8px 0', fontSize: '0.9rem', color: '#f8fafc' }}>Key Statistical Findings:</h4>
          <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.85rem', color: '#cbd5e1' }}>
            {keyFindings.map((finding, idx) => (
              <li key={idx} style={{ marginBottom: '4px' }}>{finding}</li>
            ))}
          </ul>
        </div>
      )}

      {activeTab === 'chart' ? (
        <div style={{
          background: '#0f172a',
          padding: '16px',
          borderRadius: '8px',
          overflowX: 'auto',
          fontSize: '0.8rem',
          color: '#38bdf8'
        }}>
          <pre style={{ margin: 0 }}>{JSON.stringify(spec?.spec_json || spec, null, 2)}</pre>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(30, 41, 59, 0.8)', color: '#38bdf8' }}>
                {tableData && tableData.length > 0 && Object.keys(tableData[0]).map((col) => (
                  <th key={col} style={{ padding: '8px 12px', borderBottom: '1px solid #334155' }}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableData && tableData.map((row, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.4)' }}>
                  {Object.values(row).map((val, cIdx) => (
                    <td key={cIdx} style={{ padding: '8px 12px', color: '#cbd5e1' }}>
                      {val !== null && val !== undefined ? String(val) : '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
