import React from 'react';
import styles from './SourceScoringCard.module.css';

export default function SourceScoringCard({ source }) {
  if (!source) return null;
  
  const getFreshnessStyle = (freshness) => {
    switch (freshness) {
      case 'FRESH': return styles.fresh;
      case 'RECENT': return styles.recent;
      case 'AGING': return styles.aging;
      case 'STALE': return styles.stale;
      case 'ARCHIVAL': return styles.archival;
      default: return '';
    }
  };

  const getCredibilityColor = (cred) => {
    if (cred >= 0.8) return '#4caf50';
    if (cred >= 0.5) return '#ffeb3b';
    return '#f44336';
  };

  const credibilityPercent = (source.credibility || 0) * 100;

  let domain = source.domain;
  if (!domain && source.url) {
    try {
      domain = new URL(source.url).hostname;
    } catch (e) {
      domain = 'Unknown Domain';
    }
  }

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.domain}>{domain}</span>
        <div className={styles.badges}>
          <span className={`${styles.badge} ${getFreshnessStyle(source.freshness)}`}>
            {source.freshness === 'STALE' ? '⚠️ ' : ''}{source.freshness}
          </span>
          {source.independence_group && (
            <span className={styles.badgeGrp}>Grp: {source.independence_group}</span>
          )}
        </div>
      </div>
      
      <div className={styles.credibility}>
        <div className={styles.credLabel}>
          <span>Credibility Score</span>
          <span>{credibilityPercent.toFixed(0)}%</span>
        </div>
        <div className={styles.barBg}>
          <div 
            className={styles.barFill} 
            style={{ width: `${credibilityPercent}%`, background: getCredibilityColor(source.credibility) }}
          />
        </div>
      </div>
      
      {source.title && <div className={styles.title}>{source.title}</div>}
    </div>
  );
}
