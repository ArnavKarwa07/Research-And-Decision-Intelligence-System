import React, { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import QueryInput from './components/QueryInput';
import EmptyHeroState from './components/EmptyHeroState';
import PlanViewTab from './components/PlanViewTab';
import EvidenceViewTab from './components/EvidenceViewTab';
import DecisionViewTab from './components/DecisionViewTab';
import AgentActivityTab from './components/AgentActivityTab';
import SourcesRepositoryTab from './components/SourcesRepositoryTab';
import ClaimsGraphTab from './components/ClaimsGraphTab';
import ExportArtifactModal from './components/ExportArtifactModal';
import MonitoringDashboard from './components/MonitoringDashboard';
import ProjectMemoryWorkspace from './components/ProjectMemoryWorkspace';
import EnterpriseConnectorsWorkspace from './components/EnterpriseConnectorsWorkspace';
import GovernanceSecurityWorkspace from './components/GovernanceSecurityWorkspace';
import HeaderAuthBar from './components/HeaderAuthBar';
import { api } from './lib/api';
import { connectToStream } from './lib/sse';

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState('default-workspace');
  const [currentQuery, setCurrentQuery] = useState(null);

  const [isResearching, setIsResearching] = useState(false);
  const [steps, setSteps] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [plan, setPlan] = useState([]);
  const [decisionMatrix, setDecisionMatrix] = useState(null);
  const [claims, setClaims] = useState([]);
  const [contradictions, setContradictions] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], stats: {} });
  
  // Phase 13 Enterprise Workspace Navigation Tabs
  const [activeTab, setActiveTab] = useState('Plan');
  const [unreadAlertsCount, setUnreadAlertsCount] = useState(2);
  const [errorMsg, setErrorMsg] = useState(null);
  const [showExportModal, setShowExportModal] = useState(false);

  const streamCleanupRef = useRef(null);

  const resetWorkspace = useCallback(() => {
    setSteps([]);
    setEvidence([]);
    setPlan([]);
    setDecisionMatrix(null);
    setClaims([]);
    setContradictions([]);
    setGraphData({ nodes: [], edges: [], stats: {} });
    setIsResearching(false);
    setCurrentQuery(null);
    setErrorMsg(null);
    setActiveTab('Plan');
  }, []);

  const handleNewSession = useCallback(async () => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }
    setErrorMsg(null);
    try {
      const newSession = await api.createSession({ title: 'New Research Workspace' });
      setSessions(prev => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      resetWorkspace();
    } catch (e) {
      console.error('Failed to create research session:', e);
      setErrorMsg(`Failed to create session: ${e.message}`);
    }
  }, [resetWorkspace]);

  useEffect(() => {
    let isSubscribed = true;
    api.createSession({ title: 'New Research Workspace' })
      .then(newSession => {
        if (!isSubscribed) return;
        setSessions([newSession]);
        setActiveSessionId(newSession.id);
      })
      .catch((e) => {
        if (!isSubscribed) return;
        console.error('Initial session creation failed:', e);
        setErrorMsg(`Unable to connect to backend server: ${e.message}`);
      });

    api.listDecisionAlerts()
      .then(alerts => {
        if (!isSubscribed || !alerts) return;
        const unread = alerts.filter(a => a.status === 'UNREAD' || a.status === 'TRIGGERED').length;
        setUnreadAlertsCount(unread);
      })
      .catch(() => {});

    return () => {
      isSubscribed = false;
      if (streamCleanupRef.current) streamCleanupRef.current();
    };
  }, []);

  const handleSelectSession = (id) => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }
    setActiveSessionId(id);
    resetWorkspace();
  };

  const handleSubmitQuery = async (text, mode = 'deep') => {
    if (!activeSessionId) return;

    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }

    setIsResearching(true);
    setSteps([]);
    setEvidence([]);
    setPlan([]);
    setDecisionMatrix(null);
    setClaims([]);
    setContradictions([]);
    setErrorMsg(null);
    setActiveTab('Plan');

    try {
      const queryRes = await api.submitQuery(activeSessionId, text, mode);
      setCurrentQuery(queryRes);

      const cleanup = connectToStream(activeSessionId, {
        onStep: (step) => {
          setSteps(prev => [...prev, step]);
          if (step.agentType === 'planner' && step.details?.plan) {
            setPlan(step.details.plan);
          }
        },
        onEvidence: (evidenceItem) => setEvidence(prev => [...prev, evidenceItem]),
        onClaim: (claimItem) => setClaims(prev => [...prev, claimItem]),
        onContradiction: (con) => setContradictions(prev => [...prev, con]),
        onDecision: (matrix) => setDecisionMatrix(matrix),
        onComplete: (data) => {
          setIsResearching(false);
          if (data.decision_matrix) setDecisionMatrix(data.decision_matrix);
        },
        onError: (err) => {
          console.error('Stream error:', err);
          setErrorMsg(`Research run error: ${err.message}`);
          setIsResearching(false);
        },
      });

      streamCleanupRef.current = cleanup;
    } catch (e) {
      console.error('Failed to submit research query:', e);
      setErrorMsg(`Submission failed: ${e.message}`);
      setIsResearching(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-surface-container-lowest text-primary overflow-hidden font-body-main">
      <header className="h-14 border-b border-outline-variant bg-surface-container-low px-6 flex items-center justify-between shrink-0 z-50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-xl font-bold">radar</span>
            <span className="font-headline-md font-bold text-lg text-primary tracking-tight">RADIS</span>
          </div>
          <span className="text-outline text-xs">|</span>
          <span className="font-mono text-xs text-on-surface-variant bg-surface-variant/50 px-2 py-0.5 rounded">
            Research & Decision Intelligence System (Phase 13)
          </span>
        </div>

        <div className="flex items-center gap-4">
          <HeaderAuthBar />
          <button
            type="button"
            onClick={() => setShowExportModal(true)}
            disabled={!currentQuery}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-bold bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30 hover:bg-cyber-cyan/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            Export Package (ZIP)
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onNewSession={handleNewSession}
          onSelectSession={handleSelectSession}
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          unreadAlertsCount={unreadAlertsCount}
          activeWorkspaceId={activeWorkspaceId}
          onSelectWorkspace={setActiveWorkspaceId}
        />

        <main className="flex-1 flex flex-col overflow-hidden bg-surface relative">
          <section className="flex-1 flex flex-col relative z-10 p-6 overflow-y-auto max-w-6xl mx-auto w-full">
            {errorMsg && (
              <div className="p-3 mb-4 rounded border border-error/40 bg-error-container/20 text-error flex justify-between items-center text-xs">
                <span>⚠️ {errorMsg}</span>
                <button
                  type="button"
                  onClick={handleNewSession}
                  className="px-3 py-1 bg-error text-black font-bold rounded cursor-pointer"
                >
                  Retry Session
                </button>
              </div>
            )}

            <div className="flex flex-wrap gap-2 border-b border-outline-variant mb-6 pb-2 text-xs font-mono font-bold shrink-0" role="tablist" aria-label="Research Workspace Views">
              {[
                { id: 'Plan', label: '🗺️ Plan View' },
                { id: 'Evidence', label: '🔍 Evidence View' },
                { id: 'Decision', label: '⚖️ Decision View' },
                { id: 'Agent Activity', label: '⏱️ Agent Activity' },
                { id: 'Sources', label: '📂 Sources Repository' },
                { id: 'Claims Graph', label: '🕸️ Claims Graph' },
                { id: 'Monitoring', label: `🛰️ Monitoring ${unreadAlertsCount > 0 ? `(${unreadAlertsCount})` : ''}` },
                { id: 'Project Memory', label: '🧠 Project Memory' },
                { id: 'Connectors', label: '🔌 Enterprise Connectors' },
                { id: 'Governance', label: '🛡️ Admin Governance' },
              ].map(tab => (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-3 py-1.5 rounded-xl transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyber-cyan/50 ${
                    activeTab === tab.id
                      ? 'bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/50 shadow-md font-bold'
                      : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === 'Monitoring' ? (
              <div className="flex-1 overflow-y-auto pb-28">
                <MonitoringDashboard
                  activeSessionId={activeSessionId}
                  activeQueryId={currentQuery?.id}
                  onAlertCountChange={setUnreadAlertsCount}
                />
              </div>
            ) : activeTab === 'Project Memory' ? (
              <div className="flex-1 overflow-y-auto pb-28">
                <ProjectMemoryWorkspace
                  activeSessionId={activeSessionId}
                  activeQueryId={currentQuery?.id}
                />
              </div>
            ) : activeTab === 'Connectors' ? (
              <div className="flex-1 overflow-y-auto pb-28">
                <EnterpriseConnectorsWorkspace
                  activeWorkspaceId={activeWorkspaceId}
                />
              </div>
            ) : activeTab === 'Governance' ? (
              <div className="flex-1 overflow-y-auto pb-28">
                <GovernanceSecurityWorkspace
                  activeWorkspaceId={activeWorkspaceId}
                />
              </div>
            ) : steps.length === 0 && evidence.length === 0 && claims.length === 0 ? (
              <EmptyHeroState onSubmitQuery={handleSubmitQuery} />
            ) : (
              <div className="flex-1 flex flex-col w-full h-full">
                <div className="flex-1 overflow-y-auto pb-28">
                  {activeTab === 'Plan' && (
                    <PlanViewTab plan={plan} activeAgent={steps[steps.length - 1]?.agentType} steps={steps} />
                  )}

                  {activeTab === 'Evidence' && (
                    <EvidenceViewTab evidence={evidence} queryId={currentQuery?.id} />
                  )}

                  {activeTab === 'Decision' && (
                    <DecisionViewTab
                      decisionMatrix={decisionMatrix}
                      confidence={currentQuery?.confidence}
                      onExportTrigger={() => setShowExportModal(true)}
                    />
                  )}

                  {activeTab === 'Agent Activity' && (
                    <AgentActivityTab
                      steps={steps}
                      queryId={currentQuery?.id}
                      runId={currentQuery?.id}
                      isResearching={isResearching}
                    />
                  )}

                  {activeTab === 'Sources' && (
                    <SourcesRepositoryTab queryId={currentQuery?.id} initialSources={[]} />
                  )}

                  {activeTab === 'Claims Graph' && (
                    <ClaimsGraphTab claims={claims} graphData={graphData} />
                  )}
                </div>
              </div>
            )}

            <QueryInput
              onSubmit={handleSubmitQuery}
              isLoading={isResearching}
              disabled={!activeSessionId}
            />
          </section>
        </main>
      </div>

      {/* Multi-Format Export Package Modal */}
      {showExportModal && (
        <ExportArtifactModal
          queryId={currentQuery?.id}
          onClose={() => setShowExportModal(false)}
        />
      )}
    </div>
  );
}
