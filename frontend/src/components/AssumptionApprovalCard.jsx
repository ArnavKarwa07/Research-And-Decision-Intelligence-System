import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function AssumptionApprovalCard({ item, onStatusUpdated = null }) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentApprovalStatus, setCurrentApprovalStatus] = useState(
    item?.human_approval_status || 'PENDING'
  );
  const [error, setError] = useState(null);

  useEffect(() => {
    setCurrentApprovalStatus(item?.human_approval_status || 'PENDING');
    setError(null);
  }, [item?.id, item?.human_approval_status]);

  const handleApprovalAction = async (targetStatus) => {
    setIsSubmitting(true);
    setError(null);
    try {
      await api.approveMemoryItem(item.id, targetStatus);
      setCurrentApprovalStatus(targetStatus);
      if (onStatusUpdated) {
        onStatusUpdated(item.id, targetStatus);
      }
    } catch (e) {
      console.error('Failed to update approval status:', e);
      setError(e.message || 'Failed to update approval status');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isPending = currentApprovalStatus === 'PENDING';
  const isApproved = currentApprovalStatus === 'APPROVED';
  const isRejected = currentApprovalStatus === 'REJECTED';

  const getStatusBadgeClass = () => {
    if (isApproved) return 'bg-emerald-950 text-emerald-300 border-emerald-700';
    if (isRejected) return 'bg-red-950 text-red-300 border-red-700';
    return 'bg-amber-950 text-amber-300 border-amber-700 animate-pulse';
  };

  return (
    <div className="p-4 bg-surface rounded-xl border border-outline-variant/60 shadow-md space-y-3 font-body-main text-xs">
      {/* Top Header */}
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-outline-variant/30 pb-2">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-amber-400 text-sm">hypothesis</span>
            <span className="font-mono text-xs font-bold text-on-surface">{item.key}</span>
          </div>
          <span className="text-[10px] font-mono text-on-surface-variant block">
            Memory Type: <strong className="text-cyber-cyan">{item.memory_type}</strong>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-tertiary font-bold">
            {(item.confidence * 100).toFixed(0)}% Confidence
          </span>
          <span
            className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase border ${getStatusBadgeClass()}`}
          >
            {currentApprovalStatus}
          </span>
        </div>
      </div>

      {/* Summary Text */}
      <p className="text-xs text-on-surface-variant leading-relaxed">{item.summary}</p>

      {/* Content details if present */}
      {item.content && Object.keys(item.content).length > 0 && (
        <div className="p-2.5 bg-surface-container/60 rounded border border-outline-variant/40 font-mono text-[11px] text-on-surface-variant space-y-1">
          <span className="text-[10px] uppercase font-bold text-cyber-cyan">Assumed Parameter Scope</span>
          <pre className="whitespace-pre-wrap font-mono text-[10px] text-on-surface">
            {JSON.stringify(item.content, null, 2)}
          </pre>
        </div>
      )}

      {error && (
        <div className="p-2 bg-red-950/40 border border-red-500/50 rounded text-red-300 text-[10px]">
          ⚠️ {error}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-outline-variant/30 font-mono">
        <div className="text-[10px] text-on-surface-variant">
          Validity: <span className="text-emerald-400 font-bold">{item.validity_status || 'ACTIVE'}</span>
        </div>

        <div className="flex items-center gap-2">
          {isPending ? (
            <>
              <button
                disabled={isSubmitting}
                onClick={() => handleApprovalAction('REJECTED')}
                className="px-3 py-1 bg-red-950/60 text-red-300 border border-red-800 rounded hover:bg-red-900 transition-colors cursor-pointer text-xs font-bold flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-xs">close</span>
                Reject
              </button>
              <button
                disabled={isSubmitting}
                onClick={() => handleApprovalAction('APPROVED')}
                className="px-3.5 py-1 bg-emerald-500 text-black rounded hover:bg-emerald-400 transition-colors cursor-pointer text-xs font-bold flex items-center gap-1 shadow"
              >
                <span className="material-symbols-outlined text-xs">check</span>
                Approve
              </button>
            </>
          ) : (
            <button
              onClick={() => setCurrentApprovalStatus('PENDING')}
              className="px-2.5 py-1 bg-surface-container border border-outline-variant text-on-surface-variant rounded hover:text-on-surface text-[10px] cursor-pointer"
            >
              Re-evaluate Approval
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
