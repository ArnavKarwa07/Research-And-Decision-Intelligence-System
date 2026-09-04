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
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="fixed bottom-6 left-[calc(50%+130px)] -translate-x-1/2 w-full max-w-4xl z-50 px-4 box-border"
    >
      <div className="bg-surface-container-low/95 border border-outline-variant rounded-2xl shadow-2xl backdrop-blur-md p-3.5 flex flex-col gap-2.5">
        
        {/* Mode Selector Pill Buttons */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-[10px] font-bold text-outline uppercase tracking-wider mr-1">
            Mode:
          </span>
          {[
            { id: 'deep', label: 'Deep Research', icon: 'microscope' },
            { id: 'adversarial', label: 'Adversarial Audit', icon: 'shield' },
            { id: 'data_analyst', label: 'Data Analyst', icon: 'analytics' },
            { id: 'quick', label: 'Quick Answer', icon: 'bolt' },
          ].map((m) => {
            const isActive = mode === m.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => setMode(m.id)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                  isActive
                    ? 'bg-primary/20 text-primary border border-primary/50 shadow-sm font-bold'
                    : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container/50 border border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-xs">{m.icon}</span>
                <span>{m.label}</span>
              </button>
            );
          })}
        </div>

        {/* Input Textarea & Send CTA */}
        <div className="flex items-end gap-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isLoading}
            placeholder={
              disabled
                ? 'Select or create a research thread to begin...'
                : 'Ask anything or describe a complex decision problem... (Press Enter to submit)'
            }
            rows={2}
            className="flex-1 bg-transparent border-none text-on-surface text-sm leading-relaxed resize-none outline-none font-body-main placeholder:text-outline p-1"
          />

          <button
            type="submit"
            disabled={!text.trim() || isLoading || disabled}
            className="px-5 py-2.5 bg-primary/20 text-primary border border-primary/40 rounded-xl text-xs font-bold hover:bg-primary/30 active:scale-95 transition-all cursor-pointer flex items-center gap-1.5 flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
          >
            {isLoading ? (
              <span>Running...</span>
            ) : (
              <>
                <span>Send</span>
                <span className="material-symbols-outlined text-sm">send</span>
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
