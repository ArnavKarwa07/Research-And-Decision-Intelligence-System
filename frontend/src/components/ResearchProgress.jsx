import React from 'react';

export default function ResearchProgress({ steps = [], isActive = false }) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="w-full max-w-4xl mx-auto mb-6 bg-surface-container-low border border-outline-variant rounded-xl p-4 shadow-xl scanline">
      {/* Telemetry Inline Header */}
      <div className="pb-3 mb-4 border-b border-outline-variant/60 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-cyber-cyan text-sm">terminal</span>
          <h3 className="font-mono text-xs font-bold text-cyber-cyan uppercase tracking-widest">
            Live Telemetry Stream
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isActive ? 'bg-cyber-cyan animate-pulse-cyan shadow-[0_0_8px_rgba(56,189,248,0.8)]' : 'bg-tertiary'}`} />
          <span className="font-mono text-[10px] text-tertiary font-bold tracking-wider">
            {isActive ? 'EXECUTION IN PROGRESS' : 'EXECUTION COMPLETE'}
          </span>
        </div>
      </div>

      {/* Telemetry Stream Nodes */}
      <div className="space-y-4 max-h-[360px] overflow-y-auto pr-1">
        {steps.map((step, idx) => {
          const isCompleted = step.status === 'completed';
          const isFailed = step.status === 'failed';
          const isRunning = step.status === 'running';
          const isLast = idx === steps.length - 1;
          const stepKey = step.id || step.timestamp || step.message;
          const timeStr = step.timestamp ? new Date(step.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '00:00:00';

          return (
            <div key={stepKey} className="relative pl-6">
              {!isLast && <div className="absolute left-1.5 top-2.5 bottom-[-16px] w-px bg-outline-variant/60" />}
              
              <div
                className={`absolute left-0 top-1.5 w-3 h-3 rounded-full border-2 border-surface-container ${
                  isCompleted ? 'bg-tertiary shadow-[0_0_6px_rgba(86,229,169,0.8)]' : isFailed ? 'bg-error shadow-[0_0_6px_rgba(244,63,94,0.8)]' : 'bg-cyber-cyan animate-pulse shadow-[0_0_8px_rgba(56,189,248,0.8)]'
                }`}
              />

              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-[10px] text-on-surface-variant">{timeStr}</span>
                <span className={`font-mono text-[10px] font-bold px-1.5 py-0.2 rounded border ${isRunning ? 'bg-cyber-cyan/10 text-cyber-cyan border-cyber-cyan/30' : 'bg-surface-variant text-on-surface-variant border-outline-variant'}`}>
                  [{step.agentType?.toUpperCase() || 'AGENT'}]
                </span>
              </div>

              <div className={`bg-surface border rounded-lg p-3 text-xs ${isRunning ? 'border-cyber-cyan/60 shadow-[0_0_15px_rgba(56,189,248,0.08)]' : 'border-outline-variant/60'}`}>
                <p className="text-on-surface leading-relaxed font-medium">{step.message}</p>

                {isRunning && (
                  <div className="mt-2.5 w-full bg-surface-container-high h-1 rounded overflow-hidden">
                    <div className="bg-cyber-cyan h-full w-[75%] relative">
                      <div className="absolute inset-0 bg-white/30 animate-pulse" />
                    </div>
                  </div>
                )}

                <div className="mt-2 flex justify-between items-center text-[10px] font-mono">
                  {isCompleted && (
                    <span className="text-tertiary flex items-center gap-1 font-bold">
                      <span className="material-symbols-outlined text-[12px]">check</span> Success
                    </span>
                  )}
                  {isFailed && (
                    <span className="text-error flex items-center gap-1 font-bold">
                      <span className="material-symbols-outlined text-[12px]">error</span> Error
                    </span>
                  )}
                  {isRunning && (
                    <span className="text-cyber-cyan flex items-center gap-1 font-bold">
                      <span className="material-symbols-outlined text-[12px] animate-spin">sync</span> RUNNING
                    </span>
                  )}
                  <span className="text-outline-variant">0.4s</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
