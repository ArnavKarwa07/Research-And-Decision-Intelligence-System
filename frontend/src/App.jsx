import React, { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import QueryInput from './components/QueryInput';
import EmptyHeroState from './components/EmptyHeroState';
import ChatConversationView from './components/ChatConversationView';
import DecisionAnalyticsView from './components/DecisionAnalyticsView';
import KnowledgeMemoryView from './components/KnowledgeMemoryView';
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

  // ChatGPT-Style 3 Main View Tabs
  const [activeTab, setActiveTab] = useState('Conversation');
  const [errorMsg, setErrorMsg] = useState(null);
  const [showExportModal, setShowExportModal] = useState(false);

  const streamCleanupRef = useRef(null);

  const resetWorkspace = useCallback(() => {
    setSteps([]);
    setEvidence([]);
    setPlan([]);
    setDecisionMatrix(null);
    setClaims([]);
    setIsResearching(false);
    setCurrentQuery(null);
    setErrorMsg(null);
    setActiveTab('Conversation');
  }, []);

  const handleNewSession = useCallback(async () => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }
    setErrorMsg(null);
    try {
      const newSession = await api.createSession({ title: 'New Research Workspace' });
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      resetWorkspace();
    } catch (e) {
      console.error('Failed to create session:', e);
      setErrorMsg(`Failed to create session: ${e.message}`);
    }
  }, [resetWorkspace]);

  useEffect(() => {
    let isSubscribed = true;
    api.createSession({ title: 'New Research Workspace' })
      .then((newSession) => {
        if (!isSubscribed) return;
        setSessions([newSession]);
        setActiveSessionId(newSession.id);
      })
      .catch((e) => {
        if (!isSubscribed) return;
        console.error('Initial session creation failed:', e);
        setErrorMsg(`Backend server offline or connecting: ${e.message}`);
      });

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
    setErrorMsg(null);
    setActiveTab('Conversation');

    try {
      const queryRes = await api.submitQuery(activeSessionId, text, mode);
      setCurrentQuery(queryRes);

      const cleanup = connectToStream(activeSessionId, {
        onStep: (step) => {
          setSteps((prev) => [...prev, step]);
          if (step.agentType === 'planner' && step.details?.plan) {
            setPlan(step.details.plan);
          }
        },
        onEvidence: (evidenceItem) => setEvidence((prev) => [...prev, evidenceItem]),
        onClaim: (claimItem) => setClaims((prev) => [...prev, claimItem]),
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
    <div className="flex w-screen h-screen bg-surface text-on-surface font-body-main overflow-hidden antialiased">
      
      {/* Left Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
      />

      {/* Main Center Canvas */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative bg-surface">
        
        {/* Sleek Top Header Navigation Bar */}
        <header className="h-14 border-b border-outline-variant bg-surface-container-low/90 backdrop-blur-md flex items-center justify-between px-6 shrink-0 z-50">
          <div className="flex items-center gap-3">
            <span className="font-bold text-sm text-primary font-headline-md tracking-tight">
              {currentQuery?.text ? `Thread: "${currentQuery.text.slice(0, 35)}..."` : 'Research Workspace'}
            </span>
          </div>

          {/* ChatGPT-Style 3-Tab View Switcher */}
          <div className="flex bg-surface-container p-1 rounded-lg border border-outline-variant text-xs font-mono font-bold">
            {[
              { id: 'Conversation', label: 'Research Stream', icon: 'chat' },
              { id: 'Analytics', label: 'Decision Analytics', icon: 'analytics' },
              { id: 'Knowledge', label: 'Knowledge & Memory', icon: 'folder_open' },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md transition-all cursor-pointer ${
                    isActive
                      ? 'bg-primary/20 text-primary border border-primary/40 shadow-sm'
                      : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high/40'
                  }`}
                >
                  <span className="material-symbols-outlined text-sm">{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Export Action CTA */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowExportModal(true)}
              disabled={!currentQuery}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono font-bold bg-primary/10 text-primary border border-primary/30 hover:bg-primary/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              <span className="material-symbols-outlined text-sm">download</span>
              <span>Export Package (ZIP)</span>
            </button>
          </div>
        </header>

        {/* View Canvas Body */}
        <main className="flex-1 overflow-y-auto p-6 relative">
          {errorMsg && (
            <div className="p-3 mb-4 rounded-lg border border-error/40 bg-error-container/20 text-error flex justify-between items-center text-xs">
              <span>{errorMsg}</span>
              <button onClick={handleNewSession} className="px-3 py-1 bg-error text-on-error font-bold rounded cursor-pointer">
                Reset Session
              </button>
            </div>
          )}

          {activeTab === 'Conversation' ? (
            steps.length === 0 && !currentQuery ? (
              <EmptyHeroState onSubmitQuery={handleSubmitQuery} />
            ) : (
              <ChatConversationView
                steps={steps}
                evidence={evidence}
                claims={claims}
                decisionMatrix={decisionMatrix}
                isResearching={isResearching}
                currentQuery={currentQuery}
              />
            )
          ) : activeTab === 'Analytics' ? (
            <DecisionAnalyticsView
              decisionMatrix={decisionMatrix}
              onExportTrigger={() => setShowExportModal(true)}
            />
          ) : (
            <KnowledgeMemoryView
              activeSessionId={activeSessionId}
            />
          )}

          {/* Floating Prompt Input Dock */}
          <QueryInput
            onSubmit={handleSubmitQuery}
            isLoading={isResearching}
            disabled={!activeSessionId}
          />
        </main>
      </div>

      {/* Export Modal */}
      {showExportModal && (
        <ExportArtifactModal
          queryId={currentQuery?.id}
          onClose={() => setShowExportModal(false)}
        />
      )}
    </div>
  );
}
