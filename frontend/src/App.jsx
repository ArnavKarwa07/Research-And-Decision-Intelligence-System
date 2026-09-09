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

const isDuplicateStep = (existingList, newStep) => {
  return existingList.some((s) => {
    if (s.id && newStep.id) {
      return s.id === newStep.id;
    }
    return s.message === newStep.message && s.agentType === newStep.agentType;
  });
};

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [currentQuery, setCurrentQuery] = useState(null);
  const [queryHistory, setQueryHistory] = useState([]);

  const [isResearching, setIsResearching] = useState(false);
  const [steps, setSteps] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [plan, setPlan] = useState([]);
  const [decisionMatrix, setDecisionMatrix] = useState(null);
  const [claims, setClaims] = useState([]);
  const [sensitivityWeights, setSensitivityWeights] = useState({ baseWeight: 0.4, worstWeight: 0.2 });

  // Sync sensitivity weights with localStorage
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

  // Main View Tabs
  const [activeTab, setActiveTab] = useState('Conversation');
  const [errorMsg, setErrorMsg] = useState(null);
  const [showExportModal, setShowExportModal] = useState(false);
  const [isLoadingInitial, setIsLoadingInitial] = useState(true);

  const streamCleanupRef = useRef(null);
  const activeSessionIdRef = useRef(activeSessionId);
  const loadingSessionIdRef = useRef(null);

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  const resetWorkspace = useCallback((keepTab = false) => {
    setQueryHistory([]);
    setSteps([]);
    setEvidence([]);
    setPlan([]);
    setDecisionMatrix(null);
    setClaims([]);
    setIsResearching(false);
    setCurrentQuery(null);
    setErrorMsg(null);
    if (!keepTab) {
      setActiveTab('Conversation');
    }
  }, []);

  const handleNewSession = useCallback(() => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }
    setErrorMsg(null);
    setActiveSessionId(null);
    activeSessionIdRef.current = null;
    loadingSessionIdRef.current = null;
    try {
      localStorage.removeItem('radis_active_session_id');
    } catch (e) {}
    resetWorkspace();
  }, [resetWorkspace]);

  const loadSessionHistory = useCallback(async (sessionId, keepTab = false) => {
    if (!sessionId) return;
    loadingSessionIdRef.current = sessionId;
    activeSessionIdRef.current = sessionId;
    try {
      if (!keepTab) {
        resetWorkspace(false);
      }
      const queries = await api.getSessionQueries(sessionId);
      if (loadingSessionIdRef.current !== sessionId) return;

      if (queries && queries.length > 0) {
        const normalizedQueries = queries.map((q) => {
          let parsed = null;
          if (q.research_plan) {
            try {
              parsed = typeof q.research_plan === 'string' ? JSON.parse(q.research_plan) : q.research_plan;
            } catch (err) {
              console.warn('Failed to parse saved research plan:', err);
            }
          }

          const decMatrix = parsed?.decision_matrix || (q.summary ? {
            recommendation: q.summary,
            confidence: q.confidence ?? 0.91,
            rationale: 'Retrieved from research session history log.',
            alternatives: []
          } : null);

          const stepsList = (parsed?.steps && parsed.steps.length > 0)
            ? parsed.steps
            : (q.summary || q.text ? [{
                id: q.id,
                agentType: 'supervisor',
                status: q.status || 'completed',
                message: q.summary || `Research completed for query: "${q.text}"`,
                timestamp: q.created_at
              }] : []);

          return {
            id: q.id,
            text: q.text,
            status: q.status,
            summary: q.summary,
            confidence: q.confidence,
            created_at: q.created_at,
            decisionMatrix: decMatrix,
            plan: parsed?.plan || [],
            evidence: parsed?.evidence || [],
            claims: parsed?.claims || [],
            steps: stepsList
          };
        });

        if (loadingSessionIdRef.current !== sessionId) return;
        setQueryHistory(normalizedQueries);
        const targetQuery = queries[queries.length - 1];
        setCurrentQuery(targetQuery);

        if (targetQuery) {
          const latestNormalized = normalizedQueries[normalizedQueries.length - 1];
          if (latestNormalized) {
            setDecisionMatrix(latestNormalized.decisionMatrix);
            setPlan(latestNormalized.plan);
            setEvidence(latestNormalized.evidence);
            setClaims(latestNormalized.claims);
            setSteps(latestNormalized.steps);
          }

          // If current query is running/pending, reconnect SSE stream gracefully
          if (targetQuery.status === 'running' || targetQuery.status === 'pending') {
            setIsResearching(true);
            let hasReceivedEvent = false;

            // Failsafe timer: if no SSE data arrives within 8s, query is inactive or finished
            const staleTimer = setTimeout(() => {
              if (!hasReceivedEvent && loadingSessionIdRef.current === sessionId) {
                console.info('No active SSE stream detected for historical query, resetting researching state');
                setIsResearching(false);
              }
            }, 8000);

            const cleanup = connectToStream(targetQuery.id, {
              onStep: (step) => {
                hasReceivedEvent = true;
                clearTimeout(staleTimer);
                if (loadingSessionIdRef.current !== sessionId) return;
                const normalizedStep = {
                  ...step,
                  agentType: step.agentType || step.agent_type || 'Agent',
                  message: step.message || step.execution_log?.message || '',
                  status: step.status || 'completed'
                };
                setSteps((prev) => {
                  if (isDuplicateStep(prev, normalizedStep)) return prev;
                  return [...prev, normalizedStep];
                });
                setQueryHistory((prev) => {
                  if (prev.length === 0) return prev;
                  const copy = [...prev];
                  const last = { ...copy[copy.length - 1] };
                  const prevSteps = last.steps || [];
                  if (isDuplicateStep(prevSteps, normalizedStep)) return copy;
                  last.steps = [...prevSteps, normalizedStep];
                  copy[copy.length - 1] = last;
                  return copy;
                });
              },
              onEvidence: (evidenceItem) => {
                hasReceivedEvent = true;
                clearTimeout(staleTimer);
                if (loadingSessionIdRef.current !== sessionId) return;
                setEvidence((prev) => [...prev, evidenceItem]);
                setQueryHistory((prev) => {
                  if (prev.length === 0) return prev;
                  const copy = [...prev];
                  const last = { ...copy[copy.length - 1] };
                  last.evidence = [...(last.evidence || []), evidenceItem];
                  copy[copy.length - 1] = last;
                  return copy;
                });
              },
              onClaim: (claimItem) => {
                hasReceivedEvent = true;
                clearTimeout(staleTimer);
                if (loadingSessionIdRef.current !== sessionId) return;
                setClaims((prev) => [...prev, claimItem]);
                setQueryHistory((prev) => {
                  if (prev.length === 0) return prev;
                  const copy = [...prev];
                  const last = { ...copy[copy.length - 1] };
                  last.claims = [...(last.claims || []), claimItem];
                  copy[copy.length - 1] = last;
                  return copy;
                });
              },
              onDecision: (matrix) => {
                hasReceivedEvent = true;
                clearTimeout(staleTimer);
                if (loadingSessionIdRef.current !== sessionId) return;
                setDecisionMatrix(matrix);
                setQueryHistory((prev) => {
                  if (prev.length === 0) return prev;
                  const copy = [...prev];
                  const last = { ...copy[copy.length - 1] };
                  last.decisionMatrix = matrix;
                  copy[copy.length - 1] = last;
                  return copy;
                });
              },
              onComplete: (data) => {
                hasReceivedEvent = true;
                clearTimeout(staleTimer);
                if (loadingSessionIdRef.current !== sessionId) return;
                setIsResearching(false);
                loadSessionHistory(sessionId, true);
              },
              onError: (err) => {
                clearTimeout(staleTimer);
                if (loadingSessionIdRef.current !== sessionId) return;
                console.warn('Stream ended or inactive for historical query:', err);
                setIsResearching(false);
              },
            });

            streamCleanupRef.current = () => {
              clearTimeout(staleTimer);
              cleanup();
            };
          }
        }
      }
    } catch (e) {
      console.warn('Failed to load session query history:', e);
      setErrorMsg('Failed to load session history. Please try again.');
    }
  }, [resetWorkspace]);

  // StrictMode-compliant workspace initialization on mount
  useEffect(() => {
    let isSubscribed = true;

    async function initializeWorkspace() {
      try {
        setIsLoadingInitial(true);
        const res = await api.getSessions(50);
        if (!isSubscribed) return;

        let fetchedSessions = res?.items || [];
        const savedActiveId = localStorage.getItem('radis_active_session_id');

        let targetSession = null;

        if (savedActiveId) {
          const found = fetchedSessions.find((s) => s.id === savedActiveId);
          if (found) {
            targetSession = found;
          } else {
            try {
              const specificSession = await api.getSession(savedActiveId);
              if (specificSession && specificSession.id) {
                targetSession = specificSession;
                fetchedSessions = [specificSession, ...fetchedSessions];
              }
            } catch (err) {
              console.warn('Saved active session not found on server, falling back:', err);
              try { localStorage.removeItem('radis_active_session_id'); } catch (_) {}
            }
          }
        }

        if (!targetSession && fetchedSessions.length > 0) {
          targetSession = fetchedSessions[0];
        }

        if (!isSubscribed) return;

        setSessions(fetchedSessions);

        if (targetSession) {
          setActiveSessionId(targetSession.id);
          activeSessionIdRef.current = targetSession.id;
          loadingSessionIdRef.current = targetSession.id;
          try {
            localStorage.setItem('radis_active_session_id', targetSession.id);
          } catch (e) {}
          await loadSessionHistory(targetSession.id);
        } else {
          setActiveSessionId(null);
          activeSessionIdRef.current = null;
          loadingSessionIdRef.current = null;
          try { localStorage.removeItem('radis_active_session_id'); } catch (e) {}
          resetWorkspace();
        }
      } catch (e) {
        if (!isSubscribed) return;
        console.error('Initial sessions fetch failed:', e);
        setErrorMsg('Failed to load recent threads from server. Please verify backend connection.');
      } finally {
        if (isSubscribed) {
          setIsLoadingInitial(false);
        }
      }
    }

    initializeWorkspace();

    return () => {
      isSubscribed = false;
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
        streamCleanupRef.current = null;
      }
    };
  }, [loadSessionHistory, resetWorkspace]);

  const handleSelectSession = (id) => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }
    setActiveSessionId(id);
    activeSessionIdRef.current = id;
    loadingSessionIdRef.current = id;
    try {
      localStorage.setItem('radis_active_session_id', id);
    } catch (e) {}
    resetWorkspace();
    loadSessionHistory(id);
  };

  const handleDeleteSession = async (idToDelete) => {
    if (typeof window !== 'undefined' && !window.confirm('Are you sure you want to delete this research thread?')) {
      return;
    }
    try {
      if (activeSessionId === idToDelete && streamCleanupRef.current) {
        streamCleanupRef.current();
        streamCleanupRef.current = null;
      }
      await api.deleteSession(idToDelete);
      const remaining = sessions.filter((s) => s.id !== idToDelete);
      setSessions(remaining);
      if (activeSessionId === idToDelete) {
        if (remaining.length > 0) {
          const nextSession = remaining[0];
          setActiveSessionId(nextSession.id);
          activeSessionIdRef.current = nextSession.id;
          loadingSessionIdRef.current = nextSession.id;
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
    let sessionToUse = activeSessionId;

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
      const shortTitle = text.length > 35 ? `${text.slice(0, 35)}...` : text;
      const formattedTitle = `Thread: "${shortTitle}"`;

      if (!sessionToUse) {
        const newSession = await api.createSession({ title: formattedTitle });
        sessionToUse = newSession.id;
        setActiveSessionId(newSession.id);
        activeSessionIdRef.current = newSession.id;
        loadingSessionIdRef.current = newSession.id;
        setSessions((prev) => [newSession, ...prev]);
        try {
          localStorage.setItem('radis_active_session_id', newSession.id);
        } catch (e) {}
      } else {
        const currentSession = sessions.find((s) => s.id === sessionToUse);
        const isDefaultTitle = !currentSession?.title || currentSession.title === 'New Research Workspace' || currentSession.title === 'Untitled Task';
        if (isDefaultTitle) {
          api.updateSession(sessionToUse, { title: formattedTitle }).catch((e) => {
            console.warn('Failed to persist session title to backend:', e);
          });
          setSessions((prev) =>
            prev.map((s) => (s.id === sessionToUse ? { ...s, title: formattedTitle, updated_at: new Date().toISOString() } : s))
          );
        }
      }

      const queryRes = await api.submitQuery(sessionToUse, text, mode);
      if (activeSessionIdRef.current !== sessionToUse) return;
      setCurrentQuery(queryRes);

      const newHistoryItem = {
        id: queryRes.id,
        text: text,
        status: 'running',
        summary: null,
        confidence: null,
        created_at: new Date().toISOString(),
        decisionMatrix: null,
        plan: [],
        evidence: [],
        claims: [],
        steps: []
      };

      setQueryHistory((prev) => [...prev, newHistoryItem]);

      const cleanup = connectToStream(queryRes.id, {
        onStep: (step) => {
          if (activeSessionIdRef.current !== sessionToUse) return;
          const normalizedStep = {
            ...step,
            agentType: step.agentType || step.agent_type || 'Agent',
            message: step.message || step.execution_log?.message || '',
            status: step.status || 'completed'
          };
          setSteps((prev) => {
            if (isDuplicateStep(prev, normalizedStep)) return prev;
            return [...prev, normalizedStep];
          });
          setQueryHistory((prev) => {
            if (prev.length === 0) return prev;
            const copy = [...prev];
            const last = { ...copy[copy.length - 1] };
            const prevSteps = last.steps || [];
            if (isDuplicateStep(prevSteps, normalizedStep)) return copy;
            last.steps = [...prevSteps, normalizedStep];
            copy[copy.length - 1] = last;
            return copy;
          });
        },
        onEvidence: (evidenceItem) => {
          if (activeSessionIdRef.current !== sessionToUse) return;
          setEvidence((prev) => [...prev, evidenceItem]);
          setQueryHistory((prev) => {
            if (prev.length === 0) return prev;
            const copy = [...prev];
            const last = { ...copy[copy.length - 1] };
            last.evidence = [...(last.evidence || []), evidenceItem];
            copy[copy.length - 1] = last;
            return copy;
          });
        },
        onClaim: (claimItem) => {
          if (activeSessionIdRef.current !== sessionToUse) return;
          setClaims((prev) => [...prev, claimItem]);
          setQueryHistory((prev) => {
            if (prev.length === 0) return prev;
            const copy = [...prev];
            const last = { ...copy[copy.length - 1] };
            last.claims = [...(last.claims || []), claimItem];
            copy[copy.length - 1] = last;
            return copy;
          });
        },
        onDecision: (matrix) => {
          if (activeSessionIdRef.current !== sessionToUse) return;
          setDecisionMatrix(matrix);
          setQueryHistory((prev) => {
            if (prev.length === 0) return prev;
            const copy = [...prev];
            const last = { ...copy[copy.length - 1] };
            last.decisionMatrix = matrix;
            copy[copy.length - 1] = last;
            return copy;
          });
        },
        onComplete: (data) => {
          if (activeSessionIdRef.current !== sessionToUse) return;
          setIsResearching(false);
          if (data.decision_matrix) setDecisionMatrix(data.decision_matrix);
          if (data.plan) setPlan(data.plan);
          if (data.evidence) setEvidence(data.evidence);
          loadSessionHistory(sessionToUse, true);
        },
        onError: (err) => {
          if (activeSessionIdRef.current !== sessionToUse) return;
          console.error('Stream error:', err);
          setIsResearching(false);
          setErrorMsg(`Research error: ${err?.message || (typeof err === 'string' ? err : 'Stream connection interrupted.')}`);
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

          {isLoadingInitial ? (
            <div className="flex flex-col items-center justify-center h-full max-w-md mx-auto text-center gap-3 py-24 select-none">
              <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              <span className="font-mono text-xs text-on-surface-variant font-medium">Restoring research workspace...</span>
            </div>
          ) : activeTab === 'Conversation' ? (
            queryHistory.length === 0 && steps.length === 0 && !currentQuery ? (
              <EmptyHeroState onSubmitQuery={handleSubmitQuery} />
            ) : (
              <ChatConversationView
                queryHistory={queryHistory}
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
          {activeTab === 'Conversation' && !isLoadingInitial && (
            <QueryInput
              onSubmit={handleSubmitQuery}
              isLoading={isResearching}
              disabled={false}
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
