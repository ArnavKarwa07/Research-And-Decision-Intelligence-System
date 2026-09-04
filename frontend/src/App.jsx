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
import { api } from './lib/api';
import { connectToStream } from './lib/sse';

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [currentQuery, setCurrentQuery] = useState(null);

  const [isResearching, setIsResearching] = useState(false);
  const [steps, setSteps] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [plan, setPlan] = useState([]);
  const [decisionMatrix, setDecisionMatrix] = useState(null);
  const [claims, setClaims] = useState([]);
  const [contradictions, setContradictions] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], stats: {} });
  
  // 6 Dedicated Research Workspace Navigation Tabs
  const [activeTab, setActiveTab] = useState('Plan');
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

    return () => {
      isSubscribed = false;
      if (streamCleanupRef.current) streamCleanupRef.current();
    };
  }, []);

  const handleSelectSession = (id) => {
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
    setErrorMsg(null);

    const initialStep = {
      id: `step-${Date.now()}`,
      message: `Decomposing research objective for ${mode === 'adversarial' ? 'adversarial stress-test' : 'deep investigation'}...`,
      status: 'running',
      timestamp: new Date().toISOString(),
      agentType: 'Supervisor'
    };
    setSteps([initialStep]);

    try {
      const query = await api.submitQuery(activeSessionId, text, mode);
      setCurrentQuery(query);

      streamCleanupRef.current = connectToStream(query.id, {
        onStep: (stepData) => {
          setSteps(prev => {
            const updated = prev.map(p => p.status === 'running' ? { ...p, status: 'completed' } : p);
            return [...updated, {
              id: stepData.id || `step-${Date.now()}-${Math.random()}`,
              message: stepData.data?.message || 'Executing agent subtask...',
              status: 'running',
              timestamp: stepData.timestamp || new Date().toISOString(),
              agentType: stepData.data?.agent_type || 'Agent'
            }];
          });
        },
        onComplete: (resultData) => {
          setIsResearching(false);
          setSteps(prev => prev.map(p => p.status === 'running' ? { ...p, status: 'completed' } : p));
          if (resultData.data?.evidence) setEvidence(resultData.data.evidence);
          if (resultData.data?.plan) setPlan(resultData.data.plan);
          if (resultData.data?.decision_matrix) setDecisionMatrix(resultData.data.decision_matrix);
          if (resultData.data?.claims) setClaims(resultData.data.claims);
          if (resultData.data?.contradictions) setContradictions(resultData.data.contradictions);
          if (resultData.data?.graphData) setGraphData(resultData.data.graphData);

          if (streamCleanupRef.current) streamCleanupRef.current();
          streamCleanupRef.current = null;
        },
        onPhase3Event: (eventType, data) => {
          if (eventType.startsWith('claim:')) {
            setClaims(prev => {
              const existing = prev.find(c => c.id === data.id);
              if (existing) return prev.map(c => c.id === data.id ? { ...c, ...data } : c);
              return [...prev, data];
            });
          } else if (eventType.startsWith('contradiction:')) {
            setContradictions(prev => {
              const existing = prev.find(c => c.id === data.id);
              if (existing) return prev.map(c => c.id === data.id ? { ...c, ...data } : c);
              return [...prev, data];
            });
          } else if (eventType === 'evidence:graph_updated') {
            setGraphData(data.graphData || data);
          }
        },
        onError: (err) => {
          console.error('SSE Stream Error:', err);
          setIsResearching(false);
          setSteps(prev => {
            const updated = prev.map(p => p.status === 'running' ? { ...p, status: 'failed' } : p);
            return [...updated, {
              id: `err-${Date.now()}`,
              message: 'Research stream connection lost or interrupted.',
              status: 'failed',
              timestamp: new Date().toISOString(),
              agentType: 'System'
            }];
          });
          if (streamCleanupRef.current) streamCleanupRef.current();
          streamCleanupRef.current = null;
        }
      });

    } catch (e) {
      console.error('Failed to submit query:', e);
      setIsResearching(false);
      setErrorMsg(`Submission failed: ${e.message}`);
    }
  };

  const activeSession = sessions.find(s => s.id === activeSessionId);
  const breadcrumbText = currentQuery ? currentQuery.text : (activeSession?.title || 'New Research Workspace');

  return (
    <div className="h-screen w-screen flex flex-col bg-surface text-on-surface font-body-main overflow-hidden">
      {/* Top Application Bar Header */}
      <header className="bg-surface/90 backdrop-blur-md h-16 w-full flex items-center justify-between px-6 border-b border-outline-variant shrink-0 z-50">
        <div className="flex items-center gap-4">
          <span className="font-bold text-xl text-primary tracking-tight font-headline-md">RADIS</span>
          <div className="h-4 w-px bg-outline-variant mx-2" />
          <nav className="flex gap-2 font-mono text-xs uppercase items-center">
            <span className="text-primary font-bold">Research Workspace</span>
            <span className="text-outline-variant">/</span>
            <span className="text-on-surface-variant truncate max-w-[280px]">
              {breadcrumbText}
            </span>
          </nav>
          <div className="ml-4 flex items-center gap-2 border border-cyber-cyan/30 rounded-full px-3 py-1 bg-cyber-cyan/10">
            <div className="w-2 h-2 rounded-full bg-cyber-cyan animate-pulse-cyan shadow-[0_0_8px_rgba(56,189,248,0.6)]" />
            <span className="font-mono text-[10px] text-cyber-cyan tracking-wider font-bold">
              {isResearching ? 'LIVE AGENT WORKSTREAM' : 'ENTERPRISE WORKSPACE'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowExportModal(true)}
            className="bg-cyber-cyan text-black font-mono font-bold px-3.5 py-1.5 rounded-lg text-xs hover:bg-cyber-cyan/80 transition-colors cursor-pointer flex items-center gap-1.5 shadow-md"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            Export Package (ZIP)
          </button>
        </div>
      </header>

      {/* Main Application Shell */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onNewSession={handleNewSession}
          onSelectSession={handleSelectSession}
        />

        {/* Center Workspace Canvas */}
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

            {steps.length === 0 && evidence.length === 0 && claims.length === 0 ? (
              <EmptyHeroState onSubmitQuery={handleSubmitQuery} />
            ) : (
              /* Enterprise Research Workspace Engine */
              <div className="flex-1 flex flex-col w-full h-full">
                
                {/* 6 Dedicated View Navigation Tabs Bar */}
                <div className="flex gap-2 border-b border-outline-variant mb-6 pb-2 text-xs font-mono font-bold">
                  {[
                    { id: 'Plan', label: '🗺️ Plan View' },
                    { id: 'Evidence', label: '🔍 Evidence View' },
                    { id: 'Decision', label: '⚖️ Decision View' },
                    { id: 'Agent Activity', label: '⏱️ Agent Activity' },
                    { id: 'Sources', label: '📂 Sources Repository' },
                    { id: 'Claims Graph', label: '🕸️ Claims Graph' },
                  ].map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`px-3.5 py-2 rounded-xl transition-all ${
                        activeTab === tab.id
                          ? 'bg-primary/20 text-primary border border-primary/40 shadow-md'
                          : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab View Container */}
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

            {/* Floating Query Console Bar */}
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
