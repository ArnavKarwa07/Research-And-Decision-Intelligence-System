import React from 'react';
import styles from '../App.module.css';

export default function TerminalLogsModal({ steps, onClose }) {
  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalBox} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <span className={styles.modalTitle}>💻 RAW AGENT TELEMETRY LOGS</span>
          <button
            type="button"
            className={styles.closeBtn}
            aria-label="Close terminal logs modal"
            onClick={onClose}
          >
            ✕
          </button>
        </div>
        <div className={styles.modalBody}>
          {steps.length === 0 ? (
            <div className={styles.logLine}>[SYSTEM] Telemetry log stream initialized. Awaiting agent events...</div>
          ) : (
            steps.map((st) => {
              const logKey = st.id || `${st.timestamp}-${st.agentType}-${st.message}`;
              return (
                <div key={logKey} className={styles.logLine}>
                  [{st.timestamp || new Date().toISOString()}] [{st.agentType || 'AGENT'}] [{st.status.toUpperCase()}] {st.message}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
