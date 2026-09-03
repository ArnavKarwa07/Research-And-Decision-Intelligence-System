import React from 'react';

export default function PlanGraphView({ plan = [], activeAgent = null }) {
  if (!plan || plan.length === 0) return null;

  return (
    <div className="w-full mb-6 bg-surface-container-low border border-outline-variant rounded-xl p-4 shadow-xl">
      <div className="pb-3 mb-4 border-b border-outline-variant/60 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-cyber-cyan text-sm">hub</span>
          <h3 className="font-mono text-xs font-bold text-cyber-cyan uppercase tracking-widest">
            Multi-Agent Plan & Dependency Graph
          </h3>
        </div>
        <span className="font-mono text-[10px] text-tertiary font-bold tracking-wider">
          {plan.length} SUB-TASKS DECOMPOSED
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {plan.map((task) => {
          const isCurrent = activeAgent && activeAgent.toLowerCase().includes(task.assigned_agent.toLowerCase());
          return (
            <div
              key={task.id || task.title}
              className={`p-3 rounded-lg border flex flex-col justify-between transition-all ${
                isCurrent
                  ? 'border-cyber-cyan bg-cyber-cyan/10 shadow-[0_0_12px_rgba(56,189,248,0.2)]'
                  : 'border-outline-variant/60 bg-surface'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-surface-variant text-on-surface-variant border border-outline-variant">
                    {task.id || 'TASK'}
                  </span>
                  <span className="w-2 h-2 rounded-full bg-tertiary shadow-[0_0_6px_rgba(86,229,169,0.8)]" />
                </div>
                <h4 className="text-xs font-bold text-on-surface leading-snug mb-2">{task.title}</h4>
              </div>
              <div className="pt-2 border-t border-outline-variant/40 flex justify-between items-center text-[10px] font-mono text-on-surface-variant">
                <span>{task.assigned_agent}</span>
                <span className="text-tertiary">✓ READY</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
