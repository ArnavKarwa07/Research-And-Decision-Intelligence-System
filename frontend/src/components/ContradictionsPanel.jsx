import React, { useState } from 'react';
import styles from './ContradictionsPanel.module.css';
import UserResolutionModal from './UserResolutionModal';

export default function ContradictionsPanel({ contradictions, onResolve }) {
  const [selectedContradiction, setSelectedContradiction] = useState(null);

  const getSeverityClass = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return styles.severityCritical;
      case 'high': return styles.severityHigh;
      case 'medium': return styles.severityMedium;
      case 'low': return styles.severityLow;
      default: return styles.severityLow;
    }
  };

  return (
    <div className={styles.container}>
      {(contradictions || []).length > 0 ? (
        (contradictions || []).map(c => (
          <div key={c.id} className={styles.card}>
            <div className={styles.header}>
              <span className={styles.typeBadge}>{c.contradiction_type}</span>
              <span className={`${styles.badge} ${getSeverityClass(c.severity)}`}>
                {c.severity}
              </span>
              <span className={styles.statusBadge}>{c.resolution_status}</span>
            </div>
            
            <div className={styles.comparison}>
              <div className={styles.claimBox}>
                <strong>Claim A</strong>
                <p>{c.claim_a?.content}</p>
              </div>
              <div className={styles.vs}>VS</div>
              <div className={styles.claimBox}>
                <strong>Claim B</strong>
                <p>{c.claim_b?.content}</p>
              </div>
            </div>

            <div className={styles.actions}>
              <button 
                className={styles.resolveBtn}
                onClick={() => setSelectedContradiction(c)}
              >
                Resolve
              </button>
            </div>
          </div>
        ))
      ) : (
        <div className={styles.emptyState}>No contradictions detected.</div>
      )}

      {selectedContradiction && (
        <UserResolutionModal 
          contradiction={selectedContradiction} 
          onClose={() => setSelectedContradiction(null)}
          onSubmit={async (resolutionData) => {
            if(onResolve) await onResolve(selectedContradiction.id, resolutionData);
            setSelectedContradiction(null);
          }}
        />
      )}
    </div>
  );
}
