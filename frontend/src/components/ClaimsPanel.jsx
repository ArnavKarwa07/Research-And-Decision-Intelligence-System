import React, { useState } from 'react';
import styles from './ClaimsPanel.module.css';

export default function ClaimsPanel({ claims }) {
  const [filterType, setFilterType] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [expandedId, setExpandedId] = useState(null);

  const filteredClaims = (claims || []).filter(c => {
    if (filterType !== 'ALL' && c.claim_type !== filterType) return false;
    if (filterStatus !== 'ALL' && c.status !== filterStatus) return false;
    return true;
  });

  return (
    <div className={styles.container}>
      <div className={styles.filters}>
        <select aria-label="Filter by Type" value={filterType} onChange={e => setFilterType(e.target.value)} className={styles.select}>
          <option value="ALL">All Types</option>
          <option value="FACT">Fact</option>
          <option value="CALCULATION">Calculation</option>
          <option value="INFERENCE">Inference</option>
        </select>
        <select aria-label="Filter by Status" value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className={styles.select}>
          <option value="ALL">All Statuses</option>
          <option value="VERIFIED">Verified</option>
          <option value="DISPUTED">Disputed</option>
          <option value="UNVERIFIED">Unverified</option>
        </select>
      </div>

      <div className={styles.list}>
        {filteredClaims.map(claim => (
          <div key={claim.id} className={styles.card}>
            <div className={styles.header}>
              <span className={`${styles.badge} ${styles[claim.claim_type] || ''}`}>{claim.claim_type}</span>
              <span className={`${styles.statusBadge} ${styles[claim.status] || ''}`}>{claim.status}</span>
              {/* Confidence Bar */}
              <div className={styles.confidenceContainer}>
                <div className={styles.confidenceBar}>
                  <div
                    className={styles.confidenceFill}
                    style={{ width: `${((claim.confidence || 0) * 100).toFixed(0)}%` }}
                  />
                </div>
                <span className={styles.confidenceText}>
                  {((claim.confidence || 0) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <div className={styles.content}>{claim.content}</div>
            <button
              className={styles.expandBtn}
              onClick={() => setExpandedId(expandedId === claim.id ? null : claim.id)}
              aria-expanded={expandedId === claim.id}
            >
              {expandedId === claim.id ? 'Hide Sources' : `View Sources (${claim.sources?.length || 0})`}
            </button>
            {expandedId === claim.id && (
              <div className={styles.sources}>
                {(claim.sources || []).map((src, i) => (
                  <div key={i} className={styles.sourceItem}>
                    <p>"{src?.excerpt}"</p>
                    {src?.excerpt_location && <span>Location: {src.excerpt_location}</span>}
                    <a href={src?.url} target="_blank" rel="noreferrer">Provenance Link</a>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
