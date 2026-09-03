import React, { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import QueryInput from './components/QueryInput';
import ResearchProgress from './components/ResearchProgress';
import EvidenceCard from './components/EvidenceCard';
import EmptyHeroState from './components/EmptyHeroState';
import TerminalLogsModal from './components/TerminalLogsModal';
import { api } from './lib/api';
import { connectToStream } from './lib/sse';

function handleExportPdf() {
  window.print();
}

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [currentQuery, setCurrentQuery] = useState(null);
  
  const [isResearching, setIsResearching] = useState(false);
  const [steps, setSteps] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);
  const [showLogsModal, setShowLogsModal] = useState(false);
  
  const resultsEndRef = useRef(null);
  const streamCleanupRef = useRef(null);

  const resetWorkspace = useCallback(() => {
    setSteps([]);
    setEvidence([]);
    setIsResearching(false);
    setCurrentQuery(null);
    setErrorMsg(null);
  }, []);

  const handleNewSession = useCallback(async () => {
    setErrorMsg(null);
    try {
      const newSession = await api.createSession({ title: 'New Investigation' });
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
    api.createSession({ title: 'New Investigation' })
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

  const scrollToBottom = () => {
    setTimeout(() => {
      resultsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
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
      message: `Analyzing intent structure for ${mode === 'adversarial' ? 'adversarial audit' : 'deep research'}...`,
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
              message: stepData.data?.message || 'Executing step...',
              status: 'running',
              timestamp: stepData.timestamp || new Date().toISOString(),
              agentType: stepData.data?.agent_type || 'Agent'
            }];
          });
          scrollToBottom();
        },
        onComplete: (resultData) => {
          setIsResearching(false);
          setSteps(prev => prev.map(p => p.status === 'running' ? { ...p, status: 'completed' } : p));
          if (resultData.data?.evidence) {
            setEvidence(resultData.data.evidence);
          }
          if (streamCleanupRef.current) streamCleanupRef.current();
          streamCleanupRef.current = null;
        },
        onError: (err) => {
          console.error('SSE Stream Error:', err);
          setIsResearching(false);
          setSteps(prev => {
            const updated = prev.map(p => p.status === 'running' ? { ...p, status: 'failed' } : p);
            return [...updated, {
              id: `err-${Date.now()}`,
              message: 'Research process disconnected or encountered an error.',
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
      setSteps(prev => [
        {
          id: `err-${Date.now()}`,
          message: `Query submission failed: ${e.message}`,
          status: 'failed',
          timestamp: new Date().toISOString(),
          agentType: 'System'
        }
      ]);
    }
  };

  const activeSession = sessions.find(s => s.id === activeSessionId);
  const breadcrumbText = currentQuery ? currentQuery.text : (activeSession?.title || 'New Investigation');

  return (
    <div className="h-screen w-screen flex flex-col bg-surface text-on-surface font-body-main overflow-hidden">
      {/* Top Navigation App Bar */}
      <header className="bg-surface/80 backdrop-blur-md h-16 w-full flex items-center justify-between px-6 border-b border-outline-variant shrink-0 z-50">
        <div className="flex items-center gap-4">
          <span className="font-bold text-xl text-primary tracking-tight font-headline-md">RADIS</span>
          <div className="h-4 w-px bg-outline-variant mx-2" />
          <nav className="flex gap-4 font-mono text-xs uppercase">
            <span className="text-primary border-b border-primary pb-0.5">Workspace</span>
            <span className="text-outline-variant">/</span>
            <span className="text-on-surface-variant truncate max-w-[240px]">
              {breadcrumbText}
            </span>
          </nav>
          <div className="ml-6 flex items-center gap-2 border border-cyber-cyan/30 rounded-full px-3 py-1 bg-cyber-cyan/10">
            <div className="w-2 h-2 rounded-full bg-cyber-cyan animate-pulse-cyan shadow-[0_0_8px_rgba(56,189,248,0.6)]" />
            <span className="font-mono text-[10px] text-cyber-cyan tracking-wider font-bold">
              {isResearching ? 'LIVE AGENT STREAM' : 'TELEMETRY READY'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleExportPdf}
            className="border border-outline-variant hover:border-primary px-3.5 py-1.5 rounded text-xs text-on-surface transition-colors cursor-pointer"
          >
            Export PDF
          </button>
          <div className="h-4 w-px bg-outline-variant mx-1" />
          <button
            type="button"
            aria-label="Open terminal telemetry logs"
            onClick={() => setShowLogsModal(true)}
            className="material-symbols-outlined text-on-surface-variant hover:text-primary cursor-pointer transition-colors text-xl bg-transparent border-none p-1"
          >
            terminal
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

        {/* Main Center Workspace Canvas */}
        <main className="flex-1 flex flex-col overflow-hidden bg-surface relative">
          <section className="flex-1 flex flex-col relative z-10 p-6 overflow-y-auto max-w-4xl mx-auto w-full">
            {errorMsg && (
              <div className="p-3 mb-4 rounded border border-error/40 bg-error-container/20 text-error flex justify-between items-center text-xs">
                <span>⚠️ {errorMsg}</span>
                <button
                  type="button"
                  onClick={handleNewSession}
                  className="px-3 py-1 bg-error text-black font-bold rounded cursor-pointer"
                >
                  Retry Connection
                </button>
              </div>
            )}

            {steps.length === 0 && evidence.length === 0 ? (
              <EmptyHeroState onSubmitQuery={handleSubmitQuery} />
            ) : (
              /* Inline Results Stream View */
              <div className="flex-1 flex flex-col w-full">
                {/* Inline Telemetry Stream */}
                <ResearchProgress steps={steps} isActive={isResearching} />

                {/* Verified Findings & Evidence */}
                {evidence.length > 0 && (
                  <div className="mb-6">
                    <div className="flex items-center justify-between pb-2 mb-4 border-b border-outline-variant">
                      <h3 className="font-bold text-base text-on-surface">Verified Findings & Evidence</h3>
                      <span className="font-mono text-xs font-bold text-tertiary">{evidence.length} FACT CHECKED</span>
                    </div>
                    {evidence.map(ev => (
                      <EvidenceCard key={ev.id} evidence={ev} />
                    ))}
                  </div>
                )}
                <div ref={resultsEndRef} />
              </div>
            )}

            {/* Floating Prompt Console */}
            <QueryInput
              onSubmit={handleSubmitQuery}
              isLoading={isResearching}
              disabled={!activeSessionId}
            />
          </section>
        </main>
      </div>

      {/* Terminal Logs Modal */}
      {showLogsModal && (
        <TerminalLogsModal steps={steps} onClose={() => setShowLogsModal(false)} />
      )}
    </div>
  );
}
