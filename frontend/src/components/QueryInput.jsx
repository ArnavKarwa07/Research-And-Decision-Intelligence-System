import React, { useState, useRef } from 'react';

export default function QueryInput({ onSubmit, isLoading, disabled, activeTab, onUploadDocument, onAddFact }) {
  const [text, setText] = useState('');
  const [mode, setMode] = useState('deep');
  const [showPlusMenu, setShowPlusMenu] = useState(false);
  const [showFactInput, setShowFactInput] = useState(false);
  const [factText, setFactText] = useState('');

  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || isLoading || disabled) return;
    onSubmit(text.trim(), mode);
    setText('');
    setShowPlusMenu(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      if (onUploadDocument) onUploadDocument(files[0]);
      setShowPlusMenu(false);
    }
  };

  const handleFactSubmit = (e) => {
    e.preventDefault();
    if (factText.trim() && onAddFact) {
      onAddFact(factText.trim());
      setFactText('');
      setShowFactInput(false);
      setShowPlusMenu(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="fixed bottom-6 left-[calc(50%+130px)] -translate-x-1/2 w-full max-w-4xl z-50 px-4 box-border"
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
        accept=".pdf,.docx,.csv,.xlsx,.txt"
      />

      <div className="bg-surface-container-low/95 border border-outline-variant rounded-2xl shadow-2xl backdrop-blur-md p-3.5 flex flex-col gap-2.5 relative">
        
        {/* Plus Action Popover Menu */}
        {showPlusMenu && (
          <div className="absolute bottom-full mb-3 left-4 bg-surface-container-high border border-outline-variant rounded-xl p-2 shadow-2xl z-50 flex flex-col gap-1 w-64 text-xs font-mono">
            {activeTab !== 'Knowledge' && (
              <>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-surface-container text-on-surface hover:text-primary transition-all text-left cursor-pointer font-bold"
                >
                  <span className="material-symbols-outlined text-base text-primary">cloud_upload</span>
                  <span>Upload Document (RAG)</span>
                </button>

                <button
                  type="button"
                  onClick={() => setShowFactInput(!showFactInput)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-surface-container text-on-surface hover:text-primary transition-all text-left cursor-pointer font-bold"
                >
                  <span className="material-symbols-outlined text-base text-primary">psychology</span>
                  <span>Add Project Fact</span>
                </button>
              </>
            )}

            <div className="border-t border-outline-variant/60 my-1 pt-1 text-[10px] text-outline px-3 uppercase tracking-wider font-bold">
              Research Mode
            </div>

            {[
              { id: 'deep', label: 'Deep Research', icon: 'search' },
              { id: 'adversarial', label: 'Adversarial Audit', icon: 'shield' },
              { id: 'data_analyst', label: 'Data Analyst', icon: 'analytics' },
              { id: 'quick', label: 'Quick Answer', icon: 'bolt' },
            ].map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => {
                  setMode(m.id);
                  setShowPlusMenu(false);
                }}
                className={`flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer ${
                  mode === m.id ? 'bg-primary/20 text-primary font-bold' : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-xs">{m.icon}</span>
                  <span>{m.label}</span>
                </div>
                {mode === m.id && <span className="material-symbols-outlined text-xs">check</span>}
              </button>
            ))}
          </div>
        )}

        {/* Quick Fact Popover Form */}
        {showFactInput && (
          <div className="p-3 bg-surface-container rounded-xl border border-primary/40 flex gap-2 text-xs">
            <input
              type="text"
              value={factText}
              onChange={(e) => setFactText(e.target.value)}
              placeholder="Enter durable project fact or assumption..."
              className="flex-1 px-3 py-1.5 bg-surface-container-low border border-outline-variant rounded-lg text-on-surface text-xs outline-none focus:border-primary font-body-main"
            />
            <button
              type="button"
              onClick={handleFactSubmit}
              className="px-3 py-1.5 bg-primary text-on-primary font-bold rounded-lg cursor-pointer"
            >
              Add
            </button>
          </div>
        )}

        {/* Top Dock Header: Plus Button & Mode Selector Pills */}
        <div className="flex items-center justify-between font-mono text-xs">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowPlusMenu(!showPlusMenu)}
              className={`w-7 h-7 rounded-full flex items-center justify-center transition-all cursor-pointer border ${
                showPlusMenu
                  ? 'bg-primary text-on-primary border-primary rotate-45'
                  : 'bg-surface-container border-outline-variant text-on-surface hover:text-primary hover:border-primary/50'
              }`}
              title="Upload data, add facts, or change options"
            >
              <span className="material-symbols-outlined text-base">add</span>
            </button>

            <span className="text-xs font-bold text-primary px-2 py-0.5 bg-primary/10 border border-primary/20 rounded-md ml-1 shadow-sm flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[14px]">
                {mode === 'deep' ? 'search' : mode === 'adversarial' ? 'shield' : mode === 'data_analyst' ? 'analytics' : 'bolt'}
              </span>
              {mode === 'deep' ? 'Deep Research' : mode === 'adversarial' ? 'Adversarial Audit' : mode === 'data_analyst' ? 'Data Analyst' : 'Quick Answer'}
            </span>
          </div>
        </div>

        {/* Input Textarea & Icon-Only Submit CTA (No 'Send' Text) */}
        <div className="flex items-end gap-3">
          <textarea
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              if (showPlusMenu) setShowPlusMenu(false);
            }}
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
            className="w-10 h-10 rounded-full bg-primary text-on-primary border border-primary/40 flex items-center justify-center hover:bg-primary-container active:scale-95 transition-all cursor-pointer flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
            title="Submit Query"
          >
            {isLoading ? (
              <span className="w-4 h-4 border-2 border-on-primary border-t-transparent rounded-full animate-spin" />
            ) : (
              <span className="material-symbols-outlined text-lg">arrow_upward</span>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
