import React, { useEffect, useState } from 'react';

export default function SecurityAuditLogModal({ isOpen, onClose }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
    }
  }, [isOpen]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/safety/audit-logs?limit=30');
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (e) {
      console.error("Failed to fetch audit logs:", e);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: '#1e1e1e',
        color: '#d4d4d4',
        padding: '24px',
        borderRadius: '8px',
        maxWidth: '800px',
        width: '90%',
        maxHeight: '80vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        fontFamily: 'monospace'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #333', paddingBottom: '8px' }}>
          <h3 style={{ margin: 0, color: '#4ec9b0', fontSize: '1.1rem' }}>
            🔒 Security Audit Log Viewer
          </h3>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#888', fontSize: '1.2rem', cursor: 'pointer' }}>
            ✖
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', fontSize: '0.82rem', lineHeight: '1.5' }}>
          {loading ? (
            <div>Loading security audit events...</div>
          ) : logs.length === 0 ? (
            <div style={{ color: '#888' }}>No security audit log entries recorded yet.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #444', color: '#569cd6' }}>
                  <th style={{ padding: '6px' }}>Timestamp</th>
                  <th style={{ padding: '6px' }}>Severity</th>
                  <th style={{ padding: '6px' }}>Action Type</th>
                  <th style={{ padding: '6px' }}>Agent / Run</th>
                  <th style={{ padding: '6px' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: '1px solid #2a2a2a' }}>
                    <td style={{ padding: '6px', color: '#888', whitespace: 'nowrap' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'N/A'}
                    </td>
                    <td style={{ padding: '6px' }}>
                      <span style={{
                        color: log.severity === 'ERROR' || log.severity === 'CRITICAL' ? '#f44336' :
                               log.severity === 'WARNING' ? '#ff9800' : '#4caf50',
                        fontWeight: 'bold'
                      }}>
                        {log.severity}
                      </span>
                    </td>
                    <td style={{ padding: '6px', color: '#ce9178' }}>{log.action_type}</td>
                    <td style={{ padding: '6px', color: '#9cdcfe' }}>{log.agent_id || 'system'}</td>
                    <td style={{ padding: '6px', color: '#dcdcaa', wordBreak: 'break-all' }}>
                      {JSON.stringify(log.details)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
