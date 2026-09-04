import React, { useState } from 'react';

export default function ApprovalGateCard({ gate, onResolve }) {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!gate) return null;

  const handleAction = async (action) => {
    setIsSubmitting(true);
    try {
      if (onResolve) {
        await onResolve(gate.id, action, feedback);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const isPending = gate.status === 'pending';

  return (
    <div style={{
      border: '1px solid var(--border-color, #e0e0e0)',
      borderRadius: '8px',
      padding: '16px',
      backgroundColor: 'var(--card-bg, #ffffff)',
      marginBottom: '16px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
      borderLeft: gate.risk_level === 'high' ? '4px solid #e53935' : '4px solid #fb8c00'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: '#1a1a1a' }}>
          🛡️ Action Required: Human Approval Gate
        </h4>
        <span style={{
          fontSize: '0.75rem',
          padding: '2px 8px',
          borderRadius: '4px',
          fontWeight: 'bold',
          textTransform: 'uppercase',
          backgroundColor: gate.risk_level === 'high' ? '#ffebee' : '#fff3e0',
          color: gate.risk_level === 'high' ? '#c62828' : '#e65100'
        }}>
          Risk: {gate.risk_level}
        </span>
      </div>

      <p style={{ margin: '8px 0', fontSize: '0.9rem', color: '#424242' }}>
        {gate.description}
      </p>

      <div style={{ fontSize: '0.85rem', color: '#616161', backgroundColor: '#f5f5f5', padding: '8px', borderRadius: '4px', marginBottom: '12px' }}>
        <div><strong>Tool:</strong> <code>{gate.tool_name}</code></div>
        <div><strong>Agent:</strong> {gate.agent_id}</div>
        <div><strong>Auto-kill Timeout:</strong> {gate.timeout_seconds || 300}s (5 minutes)</div>
      </div>

      {isPending ? (
        <div>
          <input
            type="text"
            placeholder="Optional user feedback or guidance..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ccc',
              marginBottom: '10px',
              fontSize: '0.85rem'
            }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => handleAction('approve')}
              disabled={isSubmitting}
              style={{
                backgroundColor: '#2e7d32',
                color: 'white',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 500
              }}
            >
              Approve Tool Call
            </button>
            <button
              onClick={() => handleAction('reject')}
              disabled={isSubmitting}
              style={{
                backgroundColor: '#d32f2f',
                color: 'white',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 500
              }}
            >
              Reject Action
            </button>
            <button
              onClick={() => handleAction('kill')}
              disabled={isSubmitting}
              style={{
                backgroundColor: '#616161',
                color: 'white',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 500
              }}
            >
              Kill Task (5m Timeout)
            </button>
          </div>
        </div>
      ) : (
        <div style={{ fontSize: '0.85rem', color: gate.status === 'approved' ? '#2e7d32' : '#c62828', fontWeight: 600 }}>
          Status: {gate.status.toUpperCase()} {gate.user_feedback && `(${gate.user_feedback})`}
        </div>
      )}
    </div>
  );
}
