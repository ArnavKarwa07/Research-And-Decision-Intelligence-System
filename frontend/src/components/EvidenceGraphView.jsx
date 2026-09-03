import React, { useRef, useEffect } from 'react';
import styles from './EvidenceGraphView.module.css';

export default function EvidenceGraphView({ graphData }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!graphData || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    ctx.clearRect(0, 0, width, height);
    
    // Simple mock layout
    const nodes = graphData.nodes || [];
    const edges = graphData.edges || [];
    
    const layout = {};
    nodes.forEach((node, i) => {
      layout[node.id] = {
        x: (i % 5 + 1) * (width / 6),
        y: (Math.floor(i / 5) + 1) * (height / 4)
      };
    });

    // Draw edges
    edges.forEach(edge => {
      const src = layout[edge.source];
      const tgt = layout[edge.target];
      if (!src || !tgt) return;

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      if (edge.type === 'contradiction') {
        ctx.strokeStyle = 'red';
        ctx.setLineDash([5, 5]);
      } else {
        ctx.strokeStyle = 'green';
        ctx.setLineDash([]);
      }
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    // Draw nodes
    ctx.setLineDash([]);
    nodes.forEach(node => {
      const pos = layout[node.id];
      if (!pos) return;

      if (node.type === 'claim') {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 15, 0, 2 * Math.PI);
        ctx.fillStyle = node.claim_type === 'FACT' ? '#4caf50' : '#2196f3';
        ctx.fill();
        ctx.stroke();
      } else if (node.type === 'source') {
        const size = 20 * (node.credibility || 0.5);
        ctx.fillStyle = '#ff9800';
        ctx.fillRect(pos.x - size/2, pos.y - size/2, size, size);
        ctx.strokeRect(pos.x - size/2, pos.y - size/2, size, size);
      }
    });

  }, [graphData]);

  const stats = graphData?.stats || {};

  return (
    <div className={styles.container}>
      <div className={styles.statsBar}>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Claims</span>
          <span className={styles.statValue}>{stats?.totalClaims || 0}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Verified</span>
          <span className={styles.statValue}>{stats?.verifiedPercent || 0}%</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Avg Conf</span>
          <span className={styles.statValue}>{((stats?.avgConfidence || 0) * 100).toFixed(0)}%</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Contradictions</span>
          <span className={styles.statValue}>{stats?.contradictions || 0}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Independence</span>
          <span className={styles.statValue}>{(stats?.independenceScore || 0).toFixed(1)}</span>
        </div>
      </div>
      
      <div className={styles.canvasContainer}>
        <canvas 
          ref={canvasRef} 
          width={800} 
          height={600} 
          className={styles.canvas}
        />
      </div>
    </div>
  );
}
