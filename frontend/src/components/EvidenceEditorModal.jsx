import React, { useState } from 'react';

export default function EvidenceEditorModal({ claim, onClose, onSave }) {
  const [status, setStatus] = useState(claim?.status || 'supported');
  const [notes, setNotes] = useState(claim?.metadata_?.user_notes || '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!claim) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSave(claim.id, status, notes);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '24px',
        borderRadius: '8px',
        maxWidth: '500px',
        width: '100%',
        boxShadow: '0 4px 16px rgba(0,0,0,0.2)'
      }}>
        <h3 style={{ marginTop: 0, color: '#1a1a1a' }}> Correct Evidence Claim</h3>

        <div style={{ fontSize: '0.9rem', color: '#555', marginBottom: '16px', backgroundColor: '#f9f9f9', padding: '10px', borderRadius: '4px' }}>
          <strong>Claim:</strong> "{claim.content}"
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '4px' }}>
              Verification Status Override
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              <option value="supported">Supported</option>
              <option value="partially_supported">Partially Supported</option>
              <option value="contradicted">Contradicted</option>
              <option value="inferred">Inferred</option>
              <option value="unverified">Unverified</option>
            </select>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '4px' }}>
              User Override Rationale / Notes
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Explain why this claim's status is being manually overridden..."
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc', fontSize: '0.85rem' }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{ padding: '8px 16px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{ padding: '8px 16px', border: 'none', borderRadius: '4px', background: '#1976d2', color: 'white', cursor: 'pointer', fontWeight: 500 }}
            >
              Save Override
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
