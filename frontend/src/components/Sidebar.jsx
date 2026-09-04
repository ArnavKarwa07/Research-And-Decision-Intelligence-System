import React from 'react';

export default function Sidebar({
  sessions,
  activeSessionId,
  onNewSession,
  onSelectSession,
  activeTab = 'Plan',
  onSelectTab = null,
  unreadAlertsCount = 0,
}) {
  return (
    <aside className="bg-surface-container-low text-primary font-body-main w-[280px] h-full flex-shrink-0 border-r border-outline-variant flex flex-col py-5 bg-grid-overlay relative z-40">
      {/* Header Section */}
      <div className="px-6 mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-surface-variant border border-outline-variant flex items-center justify-center rounded">
            <span className="material-symbols-outlined text-primary">radar</span>
          </div>
          <div>
            <h2 className="font-headline-md text-xl font-bold text-primary leading-tight">RADIS</h2>
            <p className="font-mono text-[10px] text-on-surface-variant tracking-widest mt-0.5">DECISION ENGINE v1.0</p>
          </div>
        </div>

        {/* Unread Alerts Counter Badge */}
        {unreadAlertsCount > 0 && (
          <div className="flex items-center gap-1 bg-red-950/80 border border-red-500/80 px-2 py-1 rounded-full animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.6)]">
            <span className="material-symbols-outlined text-red-400 text-xs">notifications_active</span>
            <span className="font-mono text-[10px] text-red-300 font-bold">{unreadAlertsCount}</span>
          </div>
        )}
      </div>

      {/* Primary CTA */}
      <div className="px-4 mb-4">
        <button
          type="button"
          onClick={onNewSession}
          className="w-full bg-primary/10 border border-primary/30 text-primary py-2.5 px-4 rounded hover:bg-primary/20 transition-colors flex items-center justify-center gap-2 font-semibold cursor-pointer active:scale-95 text-xs"
        >
          <span className="material-symbols-outlined text-sm">add</span>
          <span>New Session</span>
        </button>
      </div>

      {/* Continuous Intelligence Workspace Navigation Tabs */}
      {onSelectTab && (
        <div className="px-4 mb-4 space-y-1 font-mono text-xs" role="tablist" aria-label="Continuous Intelligence Navigation">
          <h3 className="text-[10px] font-bold text-on-surface-variant mb-2 uppercase border-b border-outline-variant pb-1 tracking-wider">
            Continuous Intelligence
          </h3>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'Monitoring'}
            onClick={() => onSelectTab('Monitoring')}
            className={`w-full flex items-center justify-between px-3 py-2 rounded transition-colors text-left font-bold cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyber-cyan/50 ${
              activeTab === 'Monitoring'
                ? 'bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/50 shadow'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">update</span>
              <span>Monitoring</span>
            </div>
            {unreadAlertsCount > 0 && (
              <span className="px-1.5 py-0.5 rounded-full bg-red-500 text-black text-[9px] font-bold">
                {unreadAlertsCount}
              </span>
            )}
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'Project Memory'}
            onClick={() => onSelectTab('Project Memory')}
            className={`w-full flex items-center gap-2 px-3 py-2 rounded transition-colors text-left font-bold cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyber-cyan/50 ${
              activeTab === 'Project Memory'
                ? 'bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/50 shadow'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
            }`}
          >
            <span className="material-symbols-outlined text-sm">neurology</span>
            <span>Project Memory</span>
          </button>
        </div>
      )}

      {/* Active Sessions List */}
      <div className="flex-1 overflow-y-auto px-4">
        <h3 className="font-mono text-[11px] font-bold text-on-surface-variant mb-3 uppercase border-b border-outline-variant pb-2 tracking-wider">
          Active Sessions ({sessions.length})
        </h3>
        <div className="space-y-2 mt-3 max-h-[calc(100vh-360px)] overflow-y-auto pr-1">
          {sessions.length === 0 ? (
            <p className="text-xs text-on-surface-variant italic py-2 text-center">No active sessions</p>
          ) : (
            sessions.map((session, index) => {
              const isActive = session.id === activeSessionId;
              const dateStr = session.createdAt ? new Date(session.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Active';
              const sessionCode = `#INV-${String(880 + (sessions.length - index)).padStart(3, '0')}`;

              return (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => onSelectSession(session.id)}
                  className={`w-full text-left p-3 bg-surface border rounded transition-colors group cursor-pointer ${
                    isActive ? 'border-primary bg-surface-container-high' : 'border-outline-variant hover:border-primary/50'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <div className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-tertiary shadow-[0_0_6px_rgba(86,229,169,0.8)]' : 'bg-outline-variant'}`} />
                      <span className="font-mono text-[10px] text-tertiary">{sessionCode}</span>
                    </div>
                    <span className="font-mono text-[10px] text-on-surface-variant">{dateStr}</span>
                  </div>
                  <p className="font-body-main text-xs text-on-surface group-hover:text-primary transition-colors truncate">
                    {session.title || 'Untitled Investigation'}
                  </p>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Telemetry Footer */}
      <div className="mt-auto pt-3 px-4 border-t border-outline-variant">
        <div className="flex items-center gap-2 py-1.5 px-3 bg-surface-container border border-outline-variant rounded">
          <div className="w-2 h-2 rounded-full bg-cyber-cyan animate-pulse-cyan shadow-[0_0_6px_rgba(56,189,248,0.6)] flex-shrink-0" />
          <span className="font-mono text-[10px] text-cyber-cyan font-semibold tracking-wider">SYS.OK · TELEMETRY ONLINE</span>
        </div>
      </div>
    </aside>
  );
}
