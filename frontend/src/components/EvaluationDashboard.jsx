import React, { useState, useEffect } from 'react';

/**
 * EvaluationDashboard - React UI Component for viewing Golden Datasets,
 * triggering evaluation benchmark runs, and reviewing metric scores & regression reports.
 */
export default function EvaluationDashboard({ apiBase = '/api/v1' }) {
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [evalRuns, setEvalRuns] = useState([]);
  const [activeRun, setActiveRun] = useState(null);
  const [regressionReport, setRegressionReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDatasets();
  }, []);

  const fetchDatasets = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/eval/datasets`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDatasets(data);
      if (data.length > 0) {
        setSelectedDataset(data[0]);
        fetchRunsForDataset(data[0].id);
      } else {
        // Auto-seed datasets if none exist
        const seedRes = await fetch(`${apiBase}/eval/datasets/seed`, { method: 'POST' });
        if (seedRes.ok) {
          const seededData = await seedRes.json();
          setDatasets(seededData);
          if (seededData.length > 0) {
            setSelectedDataset(seededData[0]);
            fetchRunsForDataset(seededData[0].id);
          }
        }
      }
    } catch (err) {
      setError(`Failed to load golden datasets: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchRunsForDataset = async (datasetId) => {
    try {
      const res = await fetch(`${apiBase}/eval/runs?dataset_id=${datasetId}`);
      if (res.ok) {
        const data = await res.json();
        setEvalRuns(data);
        if (data.length > 0) {
          setActiveRun(data[0]);
        }
      }
    } catch (err) {
      console.error('Error fetching eval runs:', err);
    }
  };

  const handleTriggerRun = async () => {
    if (!selectedDataset) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/eval/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: selectedDataset.id,
          model_name: 'default',
          prompt_version: 'v1.0',
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const newRun = await res.json();
      setEvalRuns((prev) => [newRun, ...prev]);
      setActiveRun(newRun);
    } catch (err) {
      setError(`Failed to trigger evaluation run: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '1.5rem', background: '#0f172a', color: '#f8fafc', borderRadius: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#38bdf8' }}> LLMOps Golden Evaluation Benchmark</h2>
        <button
          onClick={handleTriggerRun}
          disabled={loading || !selectedDataset}
          style={{
            background: 'linear-gradient(135deg, #0284c7, #2563eb)',
            color: '#fff',
            border: 'none',
            padding: '0.5rem 1rem',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          {loading ? 'Running Suite...' : ' Execute Benchmark Suite'}
        </button>
      </div>

      {error && (
        <div style={{ background: '#7f1d1d', color: '#fca5a5', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {/* Dataset Selection Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid #334155', paddingBottom: '0.5rem' }}>
        {datasets.map((ds) => (
          <button
            key={ds.id}
            onClick={() => {
              setSelectedDataset(ds);
              fetchRunsForDataset(ds.id);
            }}
            style={{
              background: selectedDataset?.id === ds.id ? '#1e293b' : 'transparent',
              color: selectedDataset?.id === ds.id ? '#38bdf8' : '#94a3b8',
              border: '1px solid ' + (selectedDataset?.id === ds.id ? '#38bdf8' : '#334155'),
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            {ds.name} ({ds.test_case_count} cases)
          </button>
        ))}
      </div>

      {/* Active Run Overview */}
      {activeRun ? (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '8px' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Overall Score</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#4ade80' }}>
                {(activeRun.summary_metrics?.overall_score * 100 || 0).toFixed(1)}%
              </div>
            </div>
            <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '8px' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Pass Rate</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#38bdf8' }}>
                {(activeRun.summary_metrics?.pass_rate * 100 || 0).toFixed(0)}%
              </div>
            </div>
            <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '8px' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Total Cost</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#facc15' }}>
                ${(activeRun.total_cost || 0).toFixed(4)}
              </div>
            </div>
            <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '8px' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Latency</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#c084fc' }}>
                {(activeRun.total_latency_ms || 0).toFixed(0)} ms
              </div>
            </div>
          </div>

          {/* Test Case Results Breakdown */}
          <h3 style={{ fontSize: '1rem', color: '#cbd5e1', marginBottom: '0.75rem' }}>Test Case Metric Scores</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {activeRun.results?.map((res, idx) => (
              <div key={res.id || idx} style={{ background: '#1e293b', padding: '1rem', borderRadius: '8px', borderLeft: res.pass_status ? '4px solid #4ade80' : '4px solid #f87171' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 600 }}>Test Case #{idx + 1}</span>
                  <span style={{ color: res.pass_status ? '#4ade80' : '#f87171', fontWeight: 600 }}>
                    {res.pass_status ? 'PASSED' : 'FAILED'} (Score: {(res.overall_score * 100).toFixed(1)}%)
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem', fontSize: '0.8rem', color: '#94a3b8' }}>
                  <div>Retrieval NDCG: <strong style={{ color: '#e2e8f0' }}>{res.retrieval_metrics?.ndcg}</strong></div>
                  <div>Groundedness: <strong style={{ color: '#e2e8f0' }}>{res.claim_metrics?.evidence_groundedness_score}</strong></div>
                  <div>Citation Coverage: <strong style={{ color: '#e2e8f0' }}>{res.citation_metrics?.citation_coverage}</strong></div>
                  <div>Trajectory Efficiency: <strong style={{ color: '#e2e8f0' }}>{res.trajectory_metrics?.trajectory_efficiency}</strong></div>
                  <div>Decision MCDA Weight: <strong style={{ color: '#e2e8f0' }}>{res.decision_metrics?.mcda_criteria_weighting_score}</strong></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ color: '#64748b', textAlign: 'center', padding: '2rem' }}>No evaluation runs yet for this dataset.</div>
      )}
    </div>
  );
}
