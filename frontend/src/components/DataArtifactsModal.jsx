import React, { useState, useEffect } from 'react';

export function DataArtifactsModal({ queryId, onClose }) {
  const [artifact, setArtifact] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!queryId) return;
    fetch(`/api/v1/data/artifacts/${queryId}`)
      .then((res) => {
        if (!res.ok) throw new Error('Artifact not found or failed to load');
        return res.json();
      })
      .then((data) => {
        setArtifact(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [queryId]);

  if (!queryId) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(15, 23, 42, 0.8)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: '#0f172a',
        border: '1px solid #38bdf8',
        borderRadius: '16px',
        width: '90%',
        maxWidth: '800px',
        maxHeight: '85vh',
        overflowY: 'auto',
        padding: '24px',
        color: '#e2e8f0',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#38bdf8' }}>
             Reproducible Analysis Artifacts
          </h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              fontSize: '1.5rem',
              cursor: 'pointer'
            }}
          >
            ×
          </button>
        </div>

        {loading && <p style={{ color: '#94a3b8' }}>Loading execution artifacts...</p>}
        {error && <p style={{ color: '#f87171' }}>Error: {error}</p>}

        {artifact && (
          <div>
            <h4 style={{ color: '#f8fafc', marginBottom: '8px' }}>Executed SQL Queries:</h4>
            {artifact.sql_queries.length > 0 ? (
              artifact.sql_queries.map((q, idx) => (
                <pre key={idx} style={{ background: '#1e293b', padding: '12px', borderRadius: '8px', fontSize: '0.8rem', color: '#38bdf8' }}>
                  {q}
                </pre>
              ))
            ) : (
              <p style={{ fontSize: '0.85rem', color: '#64748b' }}>No SQL queries recorded.</p>
            )}

            <h4 style={{ color: '#f8fafc', marginTop: '16px', marginBottom: '8px' }}>Python Analysis Scripts:</h4>
            {artifact.python_scripts.length > 0 ? (
              artifact.python_scripts.map((s, idx) => (
                <pre key={idx} style={{ background: '#1e293b', padding: '12px', borderRadius: '8px', fontSize: '0.8rem', color: '#4ade80' }}>
                  {s}
                </pre>
              ))
            ) : (
              <p style={{ fontSize: '0.85rem', color: '#64748b' }}>No Python scripts recorded.</p>
            )}

            <h4 style={{ color: '#f8fafc', marginTop: '16px', marginBottom: '8px' }}>Execution Logs & Timings:</h4>
            <div style={{ background: '#1e293b', padding: '12px', borderRadius: '8px', fontSize: '0.8rem', color: '#cbd5e1' }}>
              {artifact.execution_logs.map((log, idx) => (
                <div key={idx} style={{ marginBottom: '4px' }}>{log}</div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
