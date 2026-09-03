import React, { useState, useEffect } from 'react';
import styles from './UserResolutionModal.module.css';

export default function UserResolutionModal({ contradiction, onClose, onSubmit }) {
  const [resolutionChoice, setResolutionChoice] = useState('');
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !isSubmitting) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, isSubmitting]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!resolutionChoice) return;
    
    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        resolution_choice: resolutionChoice,
        notes: resolutionNotes
      });
    } catch (err) {
      setError(err.message || 'Failed to submit resolution. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!contradiction) return null;

  return (
    <div className={styles.overlay}>
      <div 
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className={styles.header}>
          <h2 id="modal-title">Resolve Contradiction</h2>
          <button 
            className={styles.closeBtn} 
            onClick={onClose}
            aria-label="Close modal"
            disabled={isSubmitting}
          >
            &times;
          </button>
        </div>

        <div className={styles.comparison}>
          <div className={styles.claimColumn}>
            <h3>Claim A</h3>
            <p className={styles.claimContent}>{contradiction.claim_a?.content}</p>
            <div className={styles.sources}>
              <h4>Sources:</h4>
              {(contradiction.claim_a?.sources || []).map((src, i) => (
                <blockquote key={i}>"{src.excerpt}"</blockquote>
              ))}
            </div>
          </div>
          <div className={styles.claimColumn}>
            <h3>Claim B</h3>
            <p className={styles.claimContent}>{contradiction.claim_b?.content}</p>
            <div className={styles.sources}>
              <h4>Sources:</h4>
              {(contradiction.claim_b?.sources || []).map((src, i) => (
                <blockquote key={i}>"{src.excerpt}"</blockquote>
              ))}
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.choices}>
            <label>
              <input type="radio" value="resolved_a" checked={resolutionChoice === 'resolved_a'} onChange={e => setResolutionChoice(e.target.value)} />
              Claim A is correct
            </label>
            <label>
              <input type="radio" value="resolved_b" checked={resolutionChoice === 'resolved_b'} onChange={e => setResolutionChoice(e.target.value)} />
              Claim B is correct
            </label>
            <label>
              <input type="radio" value="resolved_both" checked={resolutionChoice === 'resolved_both'} onChange={e => setResolutionChoice(e.target.value)} />
              Both are valid
            </label>
            <label>
              <input type="radio" value="escalated" checked={resolutionChoice === 'escalated'} onChange={e => setResolutionChoice(e.target.value)} />
              Escalate
            </label>
          </div>

          <div className={styles.notes}>
            <label>Resolution Notes</label>
            <textarea 
              rows="3" 
              value={resolutionNotes} 
              onChange={e => setResolutionNotes(e.target.value)} 
              placeholder="Provide reasoning..." 
              required={resolutionChoice === 'escalated'}
            />
          </div>

          {error && <div className={styles.error} style={{ color: 'red', marginBottom: '16px' }}>{error}</div>}

          <div className={styles.actions}>
            <button type="button" onClick={onClose} className={styles.cancelBtn} disabled={isSubmitting}>Cancel</button>
            <button type="submit" disabled={!resolutionChoice || isSubmitting} className={styles.submitBtn}>
              {isSubmitting ? 'Submitting...' : 'Submit Resolution'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
