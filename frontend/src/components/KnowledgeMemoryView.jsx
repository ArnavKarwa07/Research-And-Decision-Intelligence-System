import React, { useState } from 'react';

export default function KnowledgeMemoryView({ activeSessionId = null }) {
  const [documents, setDocuments] = useState([
    { id: 'doc-1', filename: 'Architecture_Roadmap_2026.pdf', size: '2.4 MB', status: 'INDEXED', chunks: 14 },
    { id: 'doc-2', filename: 'Financial_Projections_Q3.csv', size: '480 KB', status: 'INDEXED', chunks: 8 },
  ]);

  const [memoryFacts, setMemoryFacts] = useState([
    { id: 'm-1', memory_type: 'FACT', text: 'Target Qdrant vector namespace segmentation per project collection.', status: 'APPROVED' },
    { id: 'm-2', memory_type: 'REUSABLE_ASSUMPTION', text: 'Max token budget per sub-task agent execution capped at 25,000 tokens.', status: 'APPROVED' },
    { id: 'm-3', memory_type: 'LESSON_LEARNED', text: 'Web search tool results must undergo untrusted content wrapping prior to synthesis.', status: 'APPROVED' },
  ]);

  const [newFact, setNewFact] = useState('');

  const handleFileUpload = (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    const newDoc = {
      id: `doc-${Date.now()}`,
      filename: file.name,
      size: `${(file.size / 1024).toFixed(1)} KB`,
      status: 'INDEXED',
      chunks: 6,
    };
    setDocuments((prev) => [newDoc, ...prev]);
  };

  const handleAddFact = (e) => {
    e.preventDefault();
    if (!newFact.trim()) return;
    setMemoryFacts((prev) => [
      { id: `m-${Date.now()}`, memory_type: 'FACT', text: newFact.trim(), status: 'APPROVED' },
      ...prev,
    ]);
    setNewFact('');
  };

  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto w-full text-on-surface pb-28 pt-2">
      
      {/* Document Knowledge Base Uploader */}
      <div className="bg-surface-container-low border border-outline-variant rounded-xl p-6 shadow-md">
        <h3 className="text-lg font-bold font-headline-md text-primary mb-1 flex items-center gap-2">
          <span className="material-symbols-outlined text-xl">folder_open</span>
          <span>Local Document Knowledge Base (RAG)</span>
        </h3>
        <p className="text-xs text-on-surface-variant mb-4">
          Upload PDF, DOCX, CSV, or TXT files to index into local Qdrant vector storage.
        </p>

        <label className="flex flex-col items-center justify-center border-2 border-dashed border-outline-variant hover:border-primary rounded-xl p-8 bg-surface-container cursor-pointer transition-all">
          <span className="material-symbols-outlined text-primary text-3xl mb-2">cloud_upload</span>
          <span className="text-xs font-bold text-primary">Click or drag files here to upload & index</span>
          <span className="text-[11px] text-outline mt-1 font-mono">PDF, DOCX, CSV, XLSX, TXT (up to 50MB)</span>
          <input type="file" onChange={handleFileUpload} className="hidden" />
        </label>

        {/* Indexed Document List */}
        <div className="mt-5 flex flex-col gap-2">
          {documents.map((doc) => (
            <div key={doc.id} className="flex justify-between items-center p-3.5 bg-surface-container border border-outline-variant/60 rounded-lg text-xs">
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-primary text-base">description</span>
                <div>
                  <span className="font-bold text-on-surface">{doc.filename}</span>
                  <span className="text-outline font-mono ml-2 text-[11px]">{doc.size}</span>
                </div>
              </div>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-tertiary-container/30 text-tertiary border border-tertiary/40">
                {doc.chunks} Chunks Indexed
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Persistent Project Memory Facts */}
      <div className="bg-surface-container-low border border-outline-variant rounded-xl p-6 shadow-md">
        <h3 className="text-lg font-bold font-headline-md text-primary mb-1 flex items-center gap-2">
          <span className="material-symbols-outlined text-xl">psychology</span>
          <span>Persistent Research Memory & Facts</span>
        </h3>
        <p className="text-xs text-on-surface-variant mb-4">
          Active facts and verified assumptions injected into research agent prompt contexts.
        </p>

        <form onSubmit={handleAddFact} className="flex gap-2 mb-5">
          <input
            type="text"
            value={newFact}
            onChange={(e) => setNewFact(e.target.value)}
            placeholder="Add durable project fact or assumption..."
            className="flex-1 px-4 py-2 bg-surface-container border border-outline-variant rounded-lg text-on-surface text-xs focus:outline-none focus:border-primary font-body-main"
          />
          <button type="submit" className="px-4 py-2 bg-primary/10 border border-primary/40 text-primary rounded-lg text-xs font-bold hover:bg-primary/20 transition-all cursor-pointer">
            + Add Fact
          </button>
        </form>

        <div className="flex flex-col gap-2.5">
          {memoryFacts.map((fact) => (
            <div key={fact.id} className="flex justify-between items-center p-3.5 bg-surface-container border border-outline-variant/60 rounded-lg text-xs">
              <div className="flex items-center gap-2.5">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-secondary-container/30 text-secondary border border-secondary/40">
                  {fact.memory_type}
                </span>
                <span className="text-on-surface">{fact.text}</span>
              </div>
              <span className="text-[11px] text-tertiary font-bold font-mono flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">check</span>
                <span>Verified</span>
              </span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
