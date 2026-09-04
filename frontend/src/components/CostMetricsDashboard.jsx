import React, { useState, useEffect } from 'react';

/**
 * CostMetricsDashboard - Dashboard component for monitoring LLM token usage,
 * USD financial cost breakdown per agent/model, and latency percentiles (p50/p90/p99).
 */
export default function CostMetricsDashboard({ apiBase = '/api/v1' }) {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDashboardMetrics();
    const interval = setInterval(fetchDashboardMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardMetrics = async () => {
    try {
      const res = await fetch(`${apiBase}/observability/metrics/dashboard`);
      if (res.ok) {
        const data = await res.json();
        setDashboard(data);
      }
    } catch (err) {
      console.error('Failed to fetch cost metrics dashboard:', err);
    }
  };

  return (
    <div style={{ background: '#0f172a', padding: '1.25rem', borderRadius: '10px', color: '#f8fafc' }}>
      <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#facc15' }}>
         Cost, Token & Latency Monitoring (p50 / p90 / p99)
      </h3>

      {!dashboard ? (
        <div style={{ color: '#64748b', textAlign: 'center', padding: '1rem' }}>Loading cost telemetry...</div>
      ) : (
        <div>
          {/* Top Row Overview Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1.25rem' }}>
            <div style={{ background: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Total Financial Cost</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#facc15' }}>
                ${dashboard.total_cost_usd?.toFixed(4)}
              </div>
            </div>
            <div style={{ background: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Tokens Consumption</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#38bdf8' }}>
                {dashboard.total_tokens?.toLocaleString()}
              </div>
            </div>
            <div style={{ background: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>p50 / p90 / p99 Latency</div>
              <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#c084fc' }}>
                {dashboard.latency_distribution?.p50_ms}ms / {dashboard.latency_distribution?.p90_ms}ms / {dashboard.latency_distribution?.p99_ms}ms
              </div>
            </div>
          </div>

          {/* Breakdown Section */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            {/* Cost by Agent */}
            <div style={{ background: '#1e293b', padding: '0.75rem 1rem', borderRadius: '8px' }}>
              <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: '#cbd5e1' }}>Cost by Agent Role</h4>
              {Object.keys(dashboard.cost_by_agent || {}).length === 0 ? (
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>No agent costs recorded yet</div>
              ) : (
                Object.entries(dashboard.cost_by_agent).map(([agent, cost]) => (
                  <div key={agent} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.3rem' }}>
                    <span style={{ color: '#94a3b8' }}>{agent}</span>
                    <strong style={{ color: '#facc15' }}>${cost.toFixed(4)}</strong>
                  </div>
                ))
              )}
            </div>

            {/* Cost by Model */}
            <div style={{ background: '#1e293b', padding: '0.75rem 1rem', borderRadius: '8px' }}>
              <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: '#cbd5e1' }}>Cost by Model Provider</h4>
              {Object.keys(dashboard.cost_by_model || {}).length === 0 ? (
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>No model costs recorded yet</div>
              ) : (
                Object.entries(dashboard.cost_by_model).map(([model, cost]) => (
                  <div key={model} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.3rem' }}>
                    <span style={{ color: '#94a3b8' }}>{model}</span>
                    <strong style={{ color: '#38bdf8' }}>${cost.toFixed(4)}</strong>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
