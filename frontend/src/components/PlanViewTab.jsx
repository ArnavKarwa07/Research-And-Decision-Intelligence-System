import React, { useState } from 'react';

/**
 * PlanViewTab - Interactive Plan & State Inspection view
 * Dynamic visual graph of current research plan, subtasks, subagent assignments, dependencies, and state checkpoints.
 */
export default function PlanViewTab({ plan = [], activeAgent = null, steps = [] }) {
  const [selectedTask, setSelectedTask] = useState(null);

  if (!plan || plan.length === 0) {
    return (
      <div className="p-8 text-center bg-surface-container-low border border-outline-variant/60 rounded-xl">
        <span className="material-symbols-outlined text-4xl text-outline-variant mb-2">schema</span>
        <h3 className="text-base font-bold text-on-surface">No Research Plan Active</h3>
        <p className="text-xs text-on-surface-variant mt-1">Submit a research query to decompose objectives into a dynamic multi-agent workstream plan.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-xl p-5 shadow-xl relative overflow-hidden flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-cyber-cyan text-xl">hub</span>
            <h2 className="font-mono text-sm font-bold text-cyber-cyan uppercase tracking-widest">
              Dynamic Research Plan & Workstream Decomposition
            </h2>
          </div>
          <p className="text-xs text-on-surface-variant leading-relaxed">
            Decomposed execution DAG showing active subtasks, assigned agents, DAG dependencies, and durable checkpoints.
          </p>
        </div>
        <div className="px-3 py-1.5 rounded-full bg-cyber-cyan/10 border border-cyber-cyan/30 font-mono text-xs text-cyber-cyan font-bold">
          {plan.length} SUBTASKS ACTIVE
        </div>
      </div>

      {/* DAG Visual Node Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {plan.map((task, idx) => {
          const isCurrent = activeAgent && activeAgent.toLowerCase().includes((task.assigned_agent || '').toLowerCase());
          const isSelected = selectedTask && selectedTask.id === (task.id || idx);

          return (
            <div
              key={task.id || idx}
              onClick={() => setSelectedTask(task)}
              className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? 'border-primary bg-primary/10 shadow-[0_0_16px_rgba(56,189,248,0.25)]'
                  : isCurrent
                  ? 'border-cyber-cyan bg-cyber-cyan/10 shadow-[0_0_12px_rgba(56,189,248,0.15)]'
                  : 'border-outline-variant/60 bg-surface hover:border-outline-variant'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-surface-variant text-on-surface-variant border border-outline-variant">
                    WORKSTREAM {idx + 1}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${isCurrent ? 'bg-cyber-cyan animate-ping' : 'bg-tertiary'}`} />
                    <span className="font-mono text-[10px] font-bold text-tertiary">
                      {isCurrent ? 'EXECUTING' : 'CHECKPOINT READY'}
                    </span>
                  </div>
                </div>

                <h4 className="text-sm font-bold text-on-surface leading-snug mb-2">
                  {task.title || task.objective}
                </h4>

                {task.description && (
                  <p className="text-xs text-on-surface-variant line-clamp-2 leading-relaxed mb-3">
                    {task.description}
                  </p>
                )}
              </div>

              <div className="pt-3 border-t border-outline-variant/40 flex justify-between items-center text-xs font-mono">
                <span className="text-cyber-cyan font-bold">🤖 {task.assigned_agent || 'Supervisor'}</span>
                <span className="text-on-surface-variant text-[10px]">Click to inspect &rarr;</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Task Inspector Drawer / Modal */}
      {selectedTask && (
        <div className="p-5 rounded-xl bg-surface-container border border-primary/40 shadow-2xl space-y-3">
          <div className="flex justify-between items-center border-b border-outline-variant pb-2">
            <h4 className="font-bold text-sm text-primary flex items-center gap-2">
              <span className="material-symbols-outlined text-base">info</span>
              Inspect Workstream Checkpoint: {selectedTask.title || selectedTask.id}
            </h4>
            <button
              onClick={() => setSelectedTask(null)}
              className="text-on-surface-variant hover:text-on-surface text-xs font-bold px-2 py-1 bg-surface rounded"
            >
              Close
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-surface rounded border border-outline-variant/60">
              <span className="font-mono text-[10px] text-on-surface-variant uppercase font-bold block mb-1">Assigned Agent</span>
              <span className="font-bold text-cyber-cyan">{selectedTask.assigned_agent || 'Supervisor'}</span>
            </div>
            <div className="p-3 bg-surface rounded border border-outline-variant/60">
              <span className="font-mono text-[10px] text-on-surface-variant uppercase font-bold block mb-1">Dependencies</span>
              <span className="text-on-surface">{selectedTask.dependencies?.join(', ') || 'Root Task'}</span>
            </div>
            <div className="p-3 bg-surface rounded border border-outline-variant/60">
              <span className="font-mono text-[10px] text-on-surface-variant uppercase font-bold block mb-1">Checkpoint Status</span>
              <span className="text-tertiary font-bold">✓ State Durable & Validated</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
