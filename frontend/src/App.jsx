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
  const [sensitivityWeights, setSensitivityWeights] = useState({ baseWeight: 0.4, worstWeight: 0.2 });

  // Sync sensitivity weights with localStorage (checking session-specific first, then global fallback)
  useEffect(() => {
    try {
      if (activeSessionId) {
        const sessionSaved = localStorage.getItem(`radis_sensitivity_${activeSessionId}`);
        if (sessionSaved) {
          const parsed = JSON.parse(sessionSaved);
          if (parsed && typeof parsed.baseWeight === 'number' && typeof parsed.worstWeight === 'number') {
            setSensitivityWeights(parsed);
            return;
          }
        }
      }
      const globalSaved = localStorage.getItem('radis_sensitivity_global');
      if (globalSaved) {
        const parsed = JSON.parse(globalSaved);
        if (parsed && typeof parsed.baseWeight === 'number' && typeof parsed.worstWeight === 'number') {
          setSensitivityWeights(parsed);
          return;
        }
      }
    } catch (e) {
      console.warn('Failed to read sensitivity weights from localStorage:', e);
    }
  }, [activeSessionId]);

  const handleWeightChange = useCallback((newBase, newWorst) => {
    const updated = { baseWeight: newBase, worstWeight: newWorst };
    setSensitivityWeights(updated);
    try {
      localStorage.setItem('radis_sensitivity_global', JSON.stringify(updated));
      if (activeSessionId) {
        localStorage.setItem(`radis_sensitivity_${activeSessionId}`, JSON.stringify(updated));
      }
    } catch (e) {
      console.warn('Failed to save sensitivity weights to localStorage:', e);
    }
  }, [activeSessionId]);

  // ChatGPT-Style 3 Main View Tabs
  const [activeTab, setActiveTab] = useState('Conversation');
  const [errorMsg, setErrorMsg] = useState(null);
  const [showExportModal, setShowExportModal] = useState(false);

  const streamCleanupRef = useRef(null);
  const isInitialMountRef = useRef(true);

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
      try {
        localStorage.setItem('radis_active_session_id', newSession.id);
      } catch (e) {
        console.warn('Failed to save active session to localStorage:', e);
      }
      resetWorkspace();
    } catch (e) {
      console.error('Failed to create session:', e);
      setErrorMsg(`Failed to create session: ${e.message}`);
    }
  }, [resetWorkspace]);

  const loadSessionHistory = useCallback(async (sessionId) => {
    try {
      const queries = await api.getSessionQueries(sessionId);
      if (queries && queries.length > 0) {
        const completedQueries = queries.filter(q => q.research_plan || q.status === 'completed');
        const targetQuery = completedQueries.length > 0 ? completedQueries[completedQueries.length - 1] : queries[queries.length - 1];
        setCurrentQuery(targetQuery);
        if (targetQuery && targetQuery.research_plan) {
          try {
            const parsed = typeof targetQuery.research_plan === 'string' ? JSON.parse(targetQuery.research_plan) : targetQuery.research_plan;
            if (parsed.decision_matrix) setDecisionMatrix(parsed.decision_matrix);
            if (parsed.plan) setPlan(parsed.plan);
            if (parsed.evidence) setEvidence(parsed.evidence);
            if (parsed.claims) setClaims(parsed.claims);
            if (parsed.steps) setSteps(parsed.steps);
          } catch (err) {
            console.warn('Failed to parse saved research plan:', err);
          }
        }
      } else {
        resetWorkspace();
      }
    } catch (e) {
      console.warn('Failed to load session query history:', e);
    }
  }, [resetWorkspace]);

  useEffect(() => {
    if (!isInitialMountRef.current) return;
    isInitialMountRef.current = false;
    let isSubscribed = true;

    api.getSessions()
      .then((res) => {
        if (!isSubscribed) return;
        const fetchedSessions = res.items || [];
        if (fetchedSessions.length > 0) {
          setSessions(fetchedSessions);
          let targetSession = fetchedSessions[0];
          try {
            const savedActiveId = localStorage.getItem('radis_active_session_id');
            const matched = fetchedSessions.find((s) => s.id === savedActiveId);
            if (matched) targetSession = matched;
          } catch (e) {
            console.warn('Failed to read activeSessionId from localStorage:', e);
          }
          setActiveSessionId(targetSession.id);
          try {
            localStorage.setItem('radis_active_session_id', targetSession.id);
          } catch (e) {}
          loadSessionHistory(targetSession.id);
        } else {
          api.createSession({ title: 'New Research Workspace' }).then((newSession) => {
            if (!isSubscribed) return;
            setSessions([newSession]);
            setActiveSessionId(newSession.id);
            try {
              localStorage.setItem('radis_active_session_id', newSession.id);
            } catch (e) {}
          });
        }
      })
      .catch((e) => {
        if (!isSubscribed) return;
        console.error('Initial sessions fetch failed:', e);
      });

    return () => {
      isSubscribed = false;
      if (streamCleanupRef.current) streamCleanupRef.current();
    };
  }, [loadSessionHistory]);

  const handleSelectSession = (id) => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }
    setActiveSessionId(id);
    try {
      localStorage.setItem('radis_active_session_id', id);
    } catch (e) {}
    resetWorkspace();
    loadSessionHistory(id);
  };

  const handleDeleteSession = async (idToDelete) => {
    try {
      await api.deleteSession(idToDelete);
      const remaining = sessions.filter((s) => s.id !== idToDelete);
      setSessions(remaining);
      if (activeSessionId === idToDelete) {
        if (remaining.length > 0) {
          if (streamCleanupRef.current) {
            streamCleanupRef.current();
            streamCleanupRef.current = null;
          }
          const nextSession = remaining[0];
          setActiveSessionId(nextSession.id);
          try {
            localStorage.setItem('radis_active_session_id', nextSession.id);
          } catch (e) {}
          resetWorkspace();
          loadSessionHistory(nextSession.id);
        } else {
          handleNewSession();
        }
      }
    } catch (e) {
      console.error('Failed to delete session:', e);
      setErrorMsg(`Failed to delete thread: ${e.message}`);
    }
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

      // Update session title in sidebar list and persist to backend
      const shortTitle = text.length > 35 ? `${text.slice(0, 35)}...` : text;
      const formattedTitle = `Thread: "${shortTitle}"`;
      api.updateSession(activeSessionId, { title: formattedTitle }).catch((e) => {
        console.warn('Failed to persist session title to backend:', e);
      });
      setSessions((prev) =>
        prev.map((s) => (s.id === activeSessionId ? { ...s, title: formattedTitle, updated_at: new Date().toISOString() } : s))
      );

      const cleanup = connectToStream(queryRes.id, {
        onStep: (step) => {
          const normalizedStep = {
            ...step,
            agentType: step.agentType || step.agent_type || 'Agent',
            message: step.message || step.execution_log?.message || '',
            status: step.status || 'completed'
          };
          setSteps((prev) => [...prev, normalizedStep]);
        },
        onEvidence: (evidenceItem) => setEvidence((prev) => [...prev, evidenceItem]),
        onClaim: (claimItem) => setClaims((prev) => [...prev, claimItem]),
        onDecision: (matrix) => setDecisionMatrix(matrix),
        onComplete: (data) => {
          setIsResearching(false);
          if (data.decision_matrix) setDecisionMatrix(data.decision_matrix);
          if (data.plan) setPlan(data.plan);
          if (data.evidence) setEvidence(data.evidence);
          loadSessionHistory(activeSessionId);
        },
        onError: (err) => {
          console.error('Stream error:', err);
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
        onDeleteSession={handleDeleteSession}
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
        <main className="flex-1 overflow-y-auto p-6 pb-40 relative">
          {errorMsg && (
            <div className="p-3 mb-4 rounded-lg border border-error/40 bg-error-container/20 text-error flex justify-between items-center text-xs">
              <span>{errorMsg}</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setErrorMsg(null)}
                  title="Dismiss error message"
                  className="px-2 py-1 bg-surface-container border border-error/40 text-error font-bold rounded hover:bg-error/20 cursor-pointer text-xs flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-xs">close</span>
                  <span>Dismiss</span>
                </button>
              </div>
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
              baseWeight={sensitivityWeights.baseWeight}
              worstWeight={sensitivityWeights.worstWeight}
              onWeightChange={handleWeightChange}
              onExportTrigger={() => setShowExportModal(true)}
            />
          ) : (
            <KnowledgeMemoryView
              activeSessionId={activeSessionId}
            />
          )}

          {/* Floating Prompt Input Dock */}
          {activeTab === 'Conversation' && (
            <QueryInput
              onSubmit={handleSubmitQuery}
              isLoading={isResearching}
              disabled={!activeSessionId}
              activeTab={activeTab}
            />
          )}
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
