import React, { useState } from 'react';
import AgentTimelineGantt from './AgentTimelineGantt';
import CostMetricsDashboard from './CostMetricsDashboard';
import TerminalLogsModal from './TerminalLogsModal';

/**
 * AgentActivityTab - Dedicated Agent Activity & Real-Time Telemetry view.
 * Real-time Gantt execution chart, live tool call stream, token/cost budget gauges, and terminal logs.
 */
export default function AgentActivityTab({ steps = [], queryId = null, runId = null, isResearching = false }) {
  const [showLogsModal, setShowLogsModal] = useState(false);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-cyber-cyan text-xl">insights</span>
            <h2 className="font-mono text-sm font-bold text-cyber-cyan uppercase tracking-widest">
              Live Multi-Agent Execution Telemetry & Gantt Timeline
            </h2>
          </div>
          <p className="text-xs text-on-surface-variant">
            Real-time execution step durations, tool invocations, token budgets, and subagent stdout/stderr logs.
          </p>
        </div>
        <button
          onClick={() => setShowLogsModal(true)}
          className="px-3.5 py-1.5 bg-surface border border-outline-variant hover:border-primary text-on-surface rounded text-xs font-mono transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <span className="material-symbols-outlined text-sm">terminal</span>
          View Terminal Stream Logs
        </button>
      </div>

      {/* Gantt Timeline Component */}
      <AgentTimelineGantt runId={runId || queryId || 'demo-run'} />

      {/* Token & Cost Budget Dashboard Component */}
      <CostMetricsDashboard runId={runId || queryId || 'demo-run'} />

      {/* Live Tool Call Log Stream */}
      <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl space-y-3">
        <h3 className="font-mono text-xs font-bold text-tertiary uppercase tracking-wider flex items-center gap-2">
          <span className="material-symbols-outlined text-sm">stream</span>
          Real-Time Tool Invocation Audit Stream ({steps.length} EVENTS)
        </h3>

        <div className="bg-surface p-4 rounded-lg border border-outline-variant max-h-60 overflow-y-auto space-y-2 font-mono text-xs">
          {steps.length === 0 ? (
            <div className="text-on-surface-variant text-center py-4">No agent telemetry events recorded yet.</div>
          ) : (
            steps.map((step, i) => (
              <div key={step.id || i} className="flex justify-between items-center pb-1 border-b border-outline-variant/30">
                <span className="text-cyber-cyan font-bold">[{step.agentType || 'Agent'}]</span>
                <span className="text-on-surface flex-1 mx-3 truncate">{step.message}</span>
                <span className="text-on-surface-variant text-[10px]">{step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : 'Live'}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Terminal Logs Modal */}
      {showLogsModal && (
        <TerminalLogsModal steps={steps} onClose={() => setShowLogsModal(false)} />
      )}
    </div>
  );
}
