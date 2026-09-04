import React, { useState, useEffect } from 'react';

/**
 * AgentTimelineGantt - Real-time step-by-step Gantt chart visualization component
 * for parallel agent workstreams and subagent tool executions.
 */
export default function AgentTimelineGantt({ runId, apiBase = '/api/v1' }) {
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!runId) return;
    fetchTimeline();

    // SSE listener for real-time timeline updates
    const eventSource = new EventSource(`${apiBase}/stream/runs/${runId}/events`);
    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event_type === 'telemetry:agent_timeline_step') {
          fetchTimeline();
        }
      } catch (err) {
        console.error('SSE timeline error:', err);
      }
    };

    return () => eventSource.close();
  }, [runId]);

  const fetchTimeline = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/observability/timeline/${runId}`);
      if (res.ok) {
        const data = await res.json();
        setTimeline(data);
      }
    } catch (err) {
      console.error('Failed to fetch timeline:', err);
    } finally {
      setLoading(false);
    }
  };

  const getAgentColor = (agentName) => {
    const map = {
      supervisor: '#38bdf8',
      research: '#818cf8',
      fact_check: '#f472b6',
      data_agent: '#34d399',
      decision: '#fbbf24',
      critic: '#f87171',
    };
    return map[agentName] || '#a78bfa';
  };

  return (
    <div style={{ background: '#0f172a', padding: '1.25rem', borderRadius: '10px', color: '#f8fafc' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#38bdf8' }}>⏱️ Multi-Agent Execution Timeline (Gantt)</h3>
        {timeline && (
          <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
            Total Elapsed: <strong>{timeline.total_duration_ms?.toFixed(0)} ms</strong>
          </span>
        )}
      </div>

      {!timeline || timeline.steps?.length === 0 ? (
        <div style={{ color: '#64748b', fontSize: '0.9rem', textAlign: 'center', padding: '1.5rem' }}>
          {loading ? 'Loading timeline...' : 'No agent execution steps recorded yet.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {timeline.steps.map((step, idx) => {
            const color = getAgentColor(step.agent_name);
            return (
              <div key={idx} style={{ background: '#1e293b', padding: '0.75rem 1rem', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                  <span>
                    <strong style={{ color }}>{step.agent_name}</strong> &rarr; {step.step_name}
                  </span>
                  <span style={{ color: '#cbd5e1' }}>{step.duration_ms?.toFixed(0)} ms</span>
                </div>
                {/* Gantt Bar Visualization */}
                <div style={{ width: '100%', background: '#334155', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${Math.min(100, Math.max(10, (step.duration_ms / (timeline.total_duration_ms || 1)) * 100))}%`,
                      background: color,
                      height: '100%',
                      borderRadius: '4px',
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
                {step.tool_calls && step.tool_calls.length > 0 && (
                  <div style={{ marginTop: '0.4rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                    Tools: {step.tool_calls.map((tc) => `<${tc}>`).join(', ')}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
