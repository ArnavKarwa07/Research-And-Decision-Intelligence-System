import React, { useState } from 'react';

export default function QueryInput({ onSubmit, isLoading, disabled }) {
  const [text, setText] = useState('');
  const [mode, setMode] = useState('deep');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || isLoading || disabled) return;
    onSubmit(text.trim(), mode);
    setText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit(e);
    }
  };

  return (
    <form className="w-full max-w-4xl mx-auto pt-2 pb-2 sticky bottom-0 z-20" onSubmit={handleSubmit}>
      <div className="bg-surface-container-low/90 backdrop-blur-md border border-outline-variant rounded-xl shadow-2xl overflow-hidden">
        {/* Console Mode Tabs */}
        <div className="flex border-b border-outline-variant bg-surface-container px-4">
          <button
            type="button"
            onClick={() => setMode('deep')}
            className={`px-4 py-2.5 font-mono text-xs font-bold transition-colors cursor-pointer ${
              mode === 'deep' ? 'border-b-2 border-primary text-primary' : 'border-b-2 border-transparent text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Deep Research
          </button>
          <button
            type="button"
            onClick={() => setMode('adversarial')}
            className={`px-4 py-2.5 font-mono text-xs font-bold transition-colors cursor-pointer ${
              mode === 'adversarial' ? 'border-b-2 border-primary text-primary' : 'border-b-2 border-transparent text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Adversarial Audit
          </button>
        </div>

        {/* Input Text Area */}
        <div className="p-4 relative">
          <textarea
            className="w-full bg-transparent border-none text-on-surface font-body-main text-sm focus:outline-none focus:ring-0 resize-none h-20 placeholder:text-outline p-0"
            aria-label="Research query parameters prompt"
            placeholder="Define investigation parameters, target entities, or specific anomalies to track..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isLoading}
            rows={3}
          />

          <div className="flex items-center justify-between pt-2 border-t border-outline-variant/40 mt-1">
            <span className="font-mono text-[10px] text-outline-variant bg-surface px-2 py-1 border border-outline-variant rounded">
              Ctrl + Enter
            </span>

            <button
              type="submit"
              disabled={!text.trim() || isLoading || disabled}
              className="bg-primary text-black font-bold px-6 py-2 rounded hover:bg-primary-container transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed text-xs"
            >
              {isLoading ? (
                <>
                  <span className="material-symbols-outlined text-sm animate-spin">sync</span>
                  <span>Initializing...</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-sm">send</span>
                  <span>Initialize ({mode === 'deep' ? 'Deep' : 'Audit'})</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
