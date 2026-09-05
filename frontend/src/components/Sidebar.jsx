import React from 'react';

export default function Sidebar({
  sessions = [],
  activeSessionId = null,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  activeTab = 'Conversation',
  onSelectTab = null,
}) {
  return (
    <aside className="bg-surface-container-low text-on-surface font-body-main w-[260px] h-full flex-shrink-0 border-r border-outline-variant flex flex-col py-5 bg-grid-overlay relative z-40">
      
      {/* Brand Header */}
      <div className="px-5 mb-5 flex items-center gap-3">
        <div className="w-10 h-10 bg-surface-container border border-outline-variant flex items-center justify-center rounded-lg shadow-md">
          <span className="material-symbols-outlined text-primary text-2xl">radar</span>
        </div>
        <div>
          <h2 className="font-headline-md text-xl font-bold text-primary leading-tight tracking-tight">RADIS</h2>
          <p className="font-mono text-[10px] text-on-surface-variant tracking-widest mt-0.5 font-semibold">DECISION ENGINE v1.0</p>
        </div>
      </div>

      {/* New Research Task Button */}
      <div className="px-4 mb-4">
        <button
          type="button"
          onClick={onNewSession}
          className="w-full bg-primary/10 border border-primary/40 text-primary py-2.5 px-4 rounded-lg hover:bg-primary/20 transition-all flex items-center justify-center gap-2 font-bold cursor-pointer active:scale-95 text-xs shadow-sm"
        >
          <span className="material-symbols-outlined text-sm">add</span>
          <span>New Task</span>
        </button>
      </div>


      {/* Threads List */}
      <div className="flex-1 overflow-y-auto px-4">
        <h3 className="font-mono text-[10px] font-bold text-outline mb-2 uppercase border-b border-outline-variant pb-1 tracking-wider">
          Recent Threads ({sessions.length})
        </h3>
        <div className="space-y-1 mt-2 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
          {sessions.length === 0 ? (
            <p className="text-xs text-on-surface-variant italic py-2 text-center">No active threads</p>
          ) : (
            sessions.map((s) => {
              const isSelected = s.id === activeSessionId;
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => onSelectSession(s.id)}
                  className={`group w-full text-left px-3 py-2 rounded-md transition-all text-xs flex items-center justify-between font-medium cursor-pointer ${
                    isSelected
                      ? 'bg-surface-container-high text-primary font-bold border border-outline-variant'
                      : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container/40'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate flex-1 min-w-0">
                    <span className="material-symbols-outlined text-xs text-outline shrink-0">forum</span>
                    <span className="truncate">{s.title || 'Untitled Task'}</span>
                  </div>
                  {onDeleteSession && (
                    <span
                      role="button"
                      tabIndex={0}
                      title="Delete thread"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(s.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-on-surface-variant hover:text-error hover:bg-surface-container-highest rounded transition-all shrink-0 ml-1 cursor-pointer flex items-center justify-center"
                    >
                      <span className="material-symbols-outlined text-xs leading-none">delete</span>
                    </span>
                  )}
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-5 pt-3 mt-auto border-t border-outline-variant/60 flex items-center justify-between font-mono text-[10px] text-outline">
        <span>Desktop Workspace</span>
        <div className="flex items-center gap-1.5 text-tertiary font-bold">
          <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse" />
          <span>Active</span>
        </div>
      </div>

    </aside>
  );
}
