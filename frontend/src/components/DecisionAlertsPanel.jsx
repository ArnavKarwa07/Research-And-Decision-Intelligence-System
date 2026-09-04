import React, { useState, useEffect } from 'react';
import MaterialityDeltaViewer from './MaterialityDeltaViewer';
import { api } from '../lib/api';

export default function DecisionAlertsPanel({
  alerts: initialAlerts = null,
  activeSessionId = null,
  onAlertCountChange = null,
}) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedAlertForDelta, setSelectedAlertForDelta] = useState(null);

  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listDecisionAlerts({
        session_id: activeSessionId || undefined,
      });
      setAlerts(data || []);
      if (onAlertCountChange) {
        const unread = (data || []).filter((a) => a.status === 'UNREAD' || a.status === 'TRIGGERED').length;
        onAlertCountChange(unread);
      }
    } catch (e) {
      console.warn('Backend alerts endpoint offline or failed, using sample alerts:', e);
      // Fallback sample alerts for demo/offline resilience
      const fallback = [
        {
          id: 'alt-1',
          title: 'Critical Vendor SLA & Uptime Claim Drift Alert',
          message: 'Continuous audit detected a 0.78 materiality score shift in vendor uptime SLA parameters.',
          severity: 'CRITICAL',
          materiality_score: 0.78,
          status: 'UNREAD',
          webhook_status: 'SUCCESS',
          created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
          payload: {
            score_breakdown: {
              claims_delta_score: 0.75,
              sources_delta_score: 0.30,
              assumptions_delta_score: 0.80,
              recommendation_flip_score: 0.0,
              total_score: 0.78,
              materiality_level: 'CRITICAL',
            },
            claims_drift: [
              {
                claim: 'Vendor Uptime Guarantee',
                baseline_text: '99.9% uptime with 4h RTO',
                current_text: '99.5% uptime with 12h RTO',
                drift_score: 0.40,
                status: 'DRIFTED',
              },
            ],
            assumption_changes: [
              {
                key: 'EU Data Residency Compliance',
                baseline_status: 'VALIDATED',
                current_status: 'INVALIDATED',
                impact: 'New EU cross-border transfer restriction requires local datacenter',
                confidence_change: -0.50,
              },
            ],
          },
        },
        {
          id: 'alt-2',
          title: 'Moderate Source Reliability Score Decay',
          message: 'Primary technical disclosure source reliability decayed by -0.30.',
          severity: 'WARNING',
          materiality_score: 0.52,
          status: 'UNREAD',
          webhook_status: 'PENDING',
          created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
          payload: {},
        },
        {
          id: 'alt-3',
          title: 'Daily Baseline Audit Execution Passed',
          message: 'No significant material drift detected during scheduled 24h baseline audit.',
          severity: 'INFO',
          materiality_score: 0.08,
          status: 'ACKNOWLEDGED',
          webhook_status: 'SKIPPED',
          created_at: new Date(Date.now() - 1000 * 60 * 600).toISOString(),
          payload: {},
        },
      ];
      setAlerts(fallback);
      if (onAlertCountChange) {
        onAlertCountChange(2);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialAlerts) {
      setAlerts(initialAlerts);
    } else {
      fetchAlerts();
    }
  }, [activeSessionId, initialAlerts]);

  const handleAcknowledge = async (alertId) => {
    try {
      await api.acknowledgeDecisionAlert(alertId);
    } catch (e) {
      console.warn('API acknowledge warning:', e);
    }
    // Optimistic state update with functional callback to prevent stale references
    setAlerts((prev) => {
      const updated = prev.map((a) => (a.id === alertId ? { ...a, status: 'ACKNOWLEDGED' } : a));
      if (onAlertCountChange) {
        const remainingUnread = updated.filter(
          (a) => a.status === 'UNREAD' || a.status === 'TRIGGERED'
        ).length;
        onAlertCountChange(remainingUnread);
      }
      return updated;
    });
  };

  const getSeverityBadgeClass = (sev) => {
    switch (sev?.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-950/80 text-red-300 border-red-600/80 shadow-[0_0_8px_rgba(239,68,68,0.5)]';
      case 'HIGH':
        return 'bg-amber-950/80 text-amber-300 border-amber-600/80';
      case 'WARNING':
        return 'bg-yellow-950/80 text-yellow-300 border-yellow-600/80';
      case 'INFO':
      default:
        return 'bg-blue-950/80 text-blue-300 border-blue-600/80';
    }
  };

  const getWebhookBadgeClass = (status) => {
    switch (status?.toUpperCase()) {
      case 'SUCCESS':
      case 'DELIVERED':
        return 'bg-emerald-950 text-emerald-400 border-emerald-800';
      case 'FAILED':
        return 'bg-red-950 text-red-400 border-red-800';
      case 'PENDING':
        return 'bg-amber-950 text-amber-400 border-amber-800';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (severityFilter !== 'ALL' && a.severity?.toUpperCase() !== severityFilter) return false;
    if (statusFilter !== 'ALL' && a.status?.toUpperCase() !== statusFilter) return false;
    return true;
  });

  const unreadCount = alerts.filter((a) => a.status === 'UNREAD' || a.status === 'TRIGGERED').length;

  return (
    <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl space-y-4">
      {/* Panel Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/40 pb-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-cyber-cyan text-xl">notifications_active</span>
          <h3 className="font-mono text-sm font-bold text-cyber-cyan uppercase tracking-wider">
            Decision Intelligence Alerts Panel
          </h3>
          {unreadCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-red-500 text-black font-mono text-[10px] font-bold animate-pulse">
              {unreadCount} UNREAD
            </span>
          )}
        </div>

        <button
          onClick={fetchAlerts}
          disabled={loading}
          className="px-3 py-1 bg-surface border border-outline-variant rounded text-xs font-mono text-on-surface-variant hover:text-cyber-cyan hover:border-cyber-cyan transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <span className={`material-symbols-outlined text-sm ${loading ? 'animate-spin' : ''}`}>refresh</span>
          Refresh Alerts
        </button>
      </div>

      {/* Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className="text-on-surface-variant text-[11px]">Severity:</span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-surface border border-outline-variant rounded px-2 py-1 text-on-surface focus:outline-none focus:border-cyber-cyan"
          >
            <option value="ALL">ALL SEVERITIES</option>
            <option value="CRITICAL">🔴 CRITICAL</option>
            <option value="HIGH">🟠 HIGH</option>
            <option value="WARNING">🟡 WARNING</option>
            <option value="INFO">🔵 INFO</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-on-surface-variant text-[11px]">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-surface border border-outline-variant rounded px-2 py-1 text-on-surface focus:outline-none focus:border-cyber-cyan"
          >
            <option value="ALL">ALL STATUSES</option>
            <option value="UNREAD">UNREAD ONLY</option>
            <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
            <option value="RESOLVED">RESOLVED</option>
          </select>
        </div>
      </div>

      {/* Alerts List */}
      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
        {loading && alerts.length === 0 ? (
          <div className="p-8 text-center text-xs font-mono text-on-surface-variant space-y-2">
            <span className="material-symbols-outlined text-2xl text-cyber-cyan animate-spin">refresh</span>
            <p>Loading decision alerts stream...</p>
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="p-8 text-center bg-surface rounded-lg border border-outline-variant/40 space-y-2">
            <span className="material-symbols-outlined text-3xl text-emerald-400">verified</span>
            <h4 className="font-mono text-xs font-bold text-on-surface">No Active Alerts</h4>
            <p className="text-[11px] text-on-surface-variant">All research monitoring jobs are operating within baseline threshold limits.</p>
          </div>
        ) : (
          filteredAlerts.map((alert) => {
            const isUnread = alert.status === 'UNREAD' || alert.status === 'TRIGGERED';
            return (
              <div
                key={alert.id}
                className={`p-4 rounded-lg border transition-all space-y-3 ${
                  isUnread
                    ? 'bg-surface border-cyber-cyan/40 shadow-lg'
                    : 'bg-surface/50 border-outline-variant/40 opacity-85'
                }`}
              >
                {/* Alert Card Header */}
                <div className="flex flex-wrap items-start justify-between gap-2 font-mono">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getSeverityBadgeClass(
                        alert.severity
                      )}`}
                    >
                      {alert.severity}
                    </span>
                    <span className="text-xs font-bold text-on-surface">{alert.title}</span>
                  </div>

                  <div className="flex items-center gap-2 text-[10px]">
                    <span className="text-tertiary font-bold">
                      Score: {((alert.materiality_score ?? 0) * 100).toFixed(0)}%
                    </span>
                    <span className="text-on-surface-variant">
                      {new Date(alert.created_at || Date.now()).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>

                {/* Alert Body */}
                <p className="text-xs text-on-surface-variant font-body-main leading-relaxed">
                  {alert.message}
                </p>

                {/* Footer Info & Actions */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-outline-variant/30 font-mono text-[10px]">
                  <div className="flex items-center gap-2">
                    <span className="text-on-surface-variant">Webhook Delivery:</span>
                    <span
                      className={`px-2 py-0.5 rounded uppercase border font-bold ${getWebhookBadgeClass(
                        alert.webhook_status
                      )}`}
                    >
                      {alert.webhook_status || 'NOT_CONFIGURED'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {alert.payload && Object.keys(alert.payload).length > 0 && (
                      <button
                        onClick={() => setSelectedAlertForDelta(alert)}
                        className="px-2.5 py-1 bg-surface-container border border-cyber-cyan/40 text-cyber-cyan rounded hover:bg-cyber-cyan/20 transition-colors cursor-pointer flex items-center gap-1 font-bold"
                      >
                        <span className="material-symbols-outlined text-xs">compare</span>
                        Inspect Delta Diff
                      </button>
                    )}

                    {isUnread ? (
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
                        className="px-3 py-1 bg-emerald-500 text-black font-bold rounded hover:bg-emerald-400 transition-colors cursor-pointer flex items-center gap-1"
                      >
                        <span className="material-symbols-outlined text-xs">check_circle</span>
                        Acknowledge
                      </button>
                    ) : (
                      <span className="text-emerald-400 font-bold flex items-center gap-1">
                        <span className="material-symbols-outlined text-xs">done_all</span>
                        Acknowledged
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Materiality Delta Viewer Modal */}
      {selectedAlertForDelta && (
        <MaterialityDeltaViewer
          deltaSummary={selectedAlertForDelta.payload}
          materialityScore={selectedAlertForDelta.materiality_score}
          materialityLevel={selectedAlertForDelta.severity}
          onClose={() => setSelectedAlertForDelta(null)}
        />
      )}
    </div>
  );
}
