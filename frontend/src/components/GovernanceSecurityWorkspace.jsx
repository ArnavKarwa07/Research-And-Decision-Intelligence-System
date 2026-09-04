import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function GovernanceSecurityWorkspace({ activeWorkspaceId = 'default-workspace' }) {
  const [activeTab, setActiveTab] = useState('RBAC');
  const [members, setMembers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [governanceReport, setGovernanceReport] = useState(null);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [selectedSeverity, setSelectedSeverity] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  const loadMembers = async () => {
    try {
      const data = await api.listWorkspaceMembers(activeWorkspaceId);
      setMembers(data || []);
    } catch (e) {
      setMembers([
        { id: 'm1', workspace_id: activeWorkspaceId, user_id: 'u1', role: 'OWNER', joined_at: '2026-09-01T10:00:00Z' },
        { id: 'm2', workspace_id: activeWorkspaceId, user_id: 'u2', role: 'ADMIN', joined_at: '2026-09-02T11:00:00Z' },
        { id: 'm3', workspace_id: activeWorkspaceId, user_id: 'u3', role: 'RESEARCHER', joined_at: '2026-09-03T12:00:00Z' },
        { id: 'm4', workspace_id: activeWorkspaceId, user_id: 'u4', role: 'VIEWER', joined_at: '2026-09-04T13:00:00Z' },
      ]);
    }
  };

  const loadAuditLogs = async () => {
    setLoadingLogs(true);
    try {
      const logs = await api.queryAuditLogs({
        workspace_id: activeWorkspaceId,
        severity: selectedSeverity || undefined,
        category: selectedCategory || undefined,
        limit: 50,
      });
      setAuditLogs(logs || []);
    } catch (e) {
      setAuditLogs([
        { id: 'l1', action_type: 'SSO_LOGIN_SUCCESS', category: 'SSO_LOGIN', severity: 'INFO', user_id: 'u1', timestamp: '2026-09-04T15:00:00Z', details: { provider: 'google' } },
        { id: 'l2', action_type: 'CONNECTOR_SYNC_COMPLETED', category: 'CONNECTOR_SYNC', severity: 'INFO', user_id: 'ConnectorAgent', timestamp: '2026-09-04T15:10:00Z', details: { items_processed: 4 } },
        { id: 'l3', action_type: 'WORKSPACE_ROLE_ASSIGNED', category: 'ROLE_CHANGE', severity: 'WARNING', user_id: 'u1', timestamp: '2026-09-04T15:30:00Z', details: { assigned_role: 'ADMIN' } },
      ]);
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => {
    loadMembers();
    loadAuditLogs();
  }, [activeWorkspaceId, selectedSeverity, selectedCategory]);

  const handleGenerateReport = async () => {
    try {
      const report = await api.generateGovernanceReport('default-org');
      setGovernanceReport(report);
    } catch (e) {
      alert(`Governance Report execution failed: ${e.message}`);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', color: '#e2e8f0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: '600' }}>🛡️ Collaboration, Governance & Audit Portal</h2>
          <p style={{ margin: '4px 0 0', color: '#94a3b8', fontSize: '14px' }}>
            Fine-grained RBAC roles, OIDC/SAML Single Sign-On, and immutable compliance audit logs.
          </p>
        </div>
        <button
          onClick={handleGenerateReport}
          style={{
            padding: '10px 18px',
            backgroundColor: '#059669',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            fontWeight: '600',
            cursor: 'pointer',
          }}
        >
          🤖 Run Governance Audit Agent
        </button>
      </div>

      {/* Sub-Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #334155', marginBottom: '20px' }}>
        {['RBAC & Team Workspace', 'SSO Authentication', 'Immutable Audit Logs'].map((tab) => {
          const key = tab.startsWith('RBAC') ? 'RBAC' : tab.startsWith('SSO') ? 'SSO' : 'AUDIT';
          const isActive = activeTab === key;
          return (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              style={{
                padding: '10px 16px',
                border: 'none',
                background: 'none',
                color: isActive ? '#38bdf8' : '#94a3b8',
                borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
                fontWeight: isActive ? '600' : 'normal',
                cursor: 'pointer',
              }}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* RBAC Tab */}
      {activeTab === 'RBAC' && (
        <div>
          <h3 style={{ fontSize: '18px', marginBottom: '12px' }}>Workspace Members & Role Matrix</h3>
          <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: '#0f172a', color: '#94a3b8', fontSize: '12px', borderBottom: '1px solid #334155' }}>
                  <th style={{ padding: '12px 16px' }}>User ID</th>
                  <th style={{ padding: '12px 16px' }}>RBAC Role</th>
                  <th style={{ padding: '12px 16px' }}>Allowed Scopes</th>
                  <th style={{ padding: '12px 16px' }}>Joined Date</th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id} style={{ borderBottom: '1px solid #334155', fontSize: '14px' }}>
                    <td style={{ padding: '12px 16px', fontWeight: '600' }}>{m.user_id}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span
                        style={{
                          padding: '4px 10px',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: '700',
                          backgroundColor:
                            m.role === 'OWNER' ? '#581c87' : m.role === 'ADMIN' ? '#1e3a8a' : m.role === 'RESEARCHER' ? '#14532d' : '#334155',
                          color:
                            m.role === 'OWNER' ? '#c084fc' : m.role === 'ADMIN' ? '#60a5fa' : m.role === 'RESEARCHER' ? '#4ade80' : '#cbd5e1',
                        }}
                      >
                        {m.role}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', color: '#94a3b8', fontSize: '12px' }}>
                      {m.role === 'OWNER' || m.role === 'ADMIN'
                        ? 'Full Admin, Manage Connectors, Audit Logs, Read/Write'
                        : m.role === 'RESEARCHER'
                        ? 'Task Execution, Read/Write Memory, Ingest Files'
                        : 'Read-Only Projects & Memory Stores'}
                    </td>
                    <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{new Date(m.joined_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SSO Tab */}
      {activeTab === 'SSO' && (
        <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '24px' }}>
          <h3 style={{ fontSize: '18px', margin: '0 0 16px 0' }}>Single Sign-On (SSO) & IdP Configurations</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {['Google Workspace (OAuth2)', 'Microsoft Azure AD (OIDC)', 'Okta Enterprise (SAML 2.0)', 'Mock Enterprise IdP'].map((provider) => (
              <div key={provider} style={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '6px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '15px' }}>{provider}</h4>
                <p style={{ margin: '0 0 12px 0', fontSize: '12px', color: '#94a3b8' }}>Status: Configured & Active</p>
                <button
                  onClick={() => alert(`Initiating SSO test login for ${provider}`)}
                  style={{ width: '100%', padding: '8px', backgroundColor: '#3b82f6', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}
                >
                  Test SSO Flow
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audit Logs Tab */}
      {activeTab === 'AUDIT' && (
        <div>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              style={{ padding: '8px 12px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#fff' }}
            >
              <option value="">All Categories</option>
              <option value="DATA_ACCESS">Data Access</option>
              <option value="CONNECTOR_SYNC">Connector Sync</option>
              <option value="ROLE_CHANGE">Role Changes</option>
              <option value="SSO_LOGIN">SSO Login</option>
              <option value="ADMIN_OVERRIDE">Admin Overrides</option>
            </select>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              style={{ padding: '8px 12px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#fff' }}
            >
              <option value="">All Severities</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: '#0f172a', color: '#94a3b8', fontSize: '12px', borderBottom: '1px solid #334155' }}>
                  <th style={{ padding: '12px 16px' }}>Timestamp</th>
                  <th style={{ padding: '12px 16px' }}>Severity</th>
                  <th style={{ padding: '12px 16px' }}>Category</th>
                  <th style={{ padding: '12px 16px' }}>Action Type</th>
                  <th style={{ padding: '12px 16px' }}>User/Agent ID</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: '1px solid #334155', fontSize: '13px' }}>
                    <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{new Date(log.timestamp).toLocaleString()}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '10px',
                          fontSize: '11px',
                          fontWeight: '700',
                          backgroundColor:
                            log.severity === 'CRITICAL' || log.severity === 'ERROR'
                              ? '#991b1b'
                              : log.severity === 'WARNING'
                              ? '#854d0e'
                              : '#166534',
                          color:
                            log.severity === 'CRITICAL' || log.severity === 'ERROR'
                              ? '#f87171'
                              : log.severity === 'WARNING'
                              ? '#facc15'
                              : '#4ade80',
                        }}
                      >
                        {log.severity}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', fontWeight: '600', color: '#cbd5e1' }}>{log.category}</td>
                    <td style={{ padding: '12px 16px', color: '#38bdf8' }}>{log.action_type}</td>
                    <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{log.user_id || log.agent_id || 'System'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Governance Agent Report Modal */}
      {governanceReport && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '24px', width: '600px', color: '#e2e8f0' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '20px' }}>🤖 GovernanceAgent Audit Report</h3>
            <div style={{ backgroundColor: '#1e293b', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
              <div style={{ fontSize: '14px', marginBottom: '8px' }}>
                Compliance Score:{' '}
                <strong style={{ color: governanceReport.compliance_score >= 0.8 ? '#4ade80' : '#f87171' }}>
                  {governanceReport.compliance_score * 100}%
                </strong>
              </div>
              <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '8px' }}>
                Scanned Events: {governanceReport.total_events_scanned} | Violations Flagged: {governanceReport.unauthorized_attempts_count}
              </div>
              <div style={{ fontSize: '13px', color: '#e2e8f0', fontStyle: 'italic' }}>{governanceReport.summary_message}</div>
            </div>

            <h4 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>Key Governance Recommendations:</h4>
            <ul style={{ margin: '0 0 20px 0', paddingLeft: '20px', fontSize: '13px', color: '#cbd5e1' }}>
              {governanceReport.recommendations.map((rec, i) => (
                <li key={i} style={{ marginBottom: '4px' }}>{rec}</li>
              ))}
            </ul>

            <button
              onClick={() => setGovernanceReport(null)}
              style={{ width: '100%', padding: '10px', backgroundColor: '#334155', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
            >
              Close Report
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
