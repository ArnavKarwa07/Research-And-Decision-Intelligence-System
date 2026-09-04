import React, { useState, useEffect, useRef } from 'react';
import MonitoringJobModal from './MonitoringJobModal';
import MaterialityDeltaViewer from './MaterialityDeltaViewer';
import DecisionAlertsPanel from './DecisionAlertsPanel';
import { api } from '../lib/api';

export default function MonitoringDashboard({
  activeSessionId = null,
  activeQueryId = null,
  onAlertCountChange = null,
}) {
  const [jobs, setJobs] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [toastMsg, setToastMsg] = useState(null);
  const timerRef = useRef(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingJob, setEditingJob] = useState(null);
  const [selectedDeltaLog, setSelectedDeltaLog] = useState(null);
  const [selectedJobLogs, setSelectedJobLogs] = useState(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [jobsData, alertsData] = await Promise.all([
        api.listMonitoringJobs({ session_id: activeSessionId || undefined }).catch(() => null),
        api.listDecisionAlerts({ session_id: activeSessionId || undefined }).catch(() => null),
      ]);

      if (jobsData && Array.isArray(jobsData)) {
        setJobs(jobsData);
      } else {
        // Fallback sample jobs for offline/demo resilience
        setJobs([
          {
            id: 'job-101',
            name: 'Vendor SLA & Uptime Continuous Audit',
            schedule_type: 'INTERVAL',
            interval_seconds: 3600,
            cron_expression: null,
            status: 'ACTIVE',
            alert_threshold: 0.5,
            webhook_url: 'https://hooks.slack.com/services/RADIS/MONITORING',
            last_run_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
            next_run_at: new Date(Date.now() + 1000 * 60 * 15).toISOString(),
            run_count: 14,
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
          },
          {
            id: 'job-102',
            name: 'Daily Regulatory & Compliance Delta Monitor',
            schedule_type: 'CRON',
            cron_expression: '0 0 * * *',
            interval_seconds: null,
            status: 'ACTIVE',
            alert_threshold: 0.7,
            webhook_url: null,
            last_run_at: new Date(Date.now() - 1000 * 60 * 360).toISOString(),
            next_run_at: new Date(Date.now() + 1000 * 60 * 1080).toISOString(),
            run_count: 8,
            created_at: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
          },
        ]);
      }

      // Sample baseline snapshots
      setSnapshots([
        {
          id: 'snap-01',
          snapshot_label: 'Baseline v1.0 - Initial Vendor SLA Agreement',
          claims_snapshot: [{ id: 'c1' }, { id: 'c2' }],
          sources_snapshot: [{ id: 's1' }],
          assumptions_snapshot: [{ id: 'a1' }, { id: 'a2' }],
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
        },
      ]);

      // Sample execution logs
      setLogs([
        {
          id: 'log-201',
          job_id: 'job-101',
          status: 'ALERT_TRIGGERED',
          materiality_score: 0.78,
          materiality_level: 'CRITICAL',
          execution_duration_seconds: 2.4,
          executed_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
          delta_summary: {
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
                baseline_text: '99.9% uptime guaranteed',
                current_text: '99.5% uptime guaranteed',
                drift_score: 0.40,
                status: 'DRIFTED',
              },
            ],
            assumption_changes: [
              {
                key: 'EU Data Residency',
                baseline_status: 'VALIDATED',
                current_status: 'INVALIDATED',
                impact: 'Datacenter location transfer required',
                confidence_change: -0.5,
              },
            ],
          },
        },
        {
          id: 'log-202',
          job_id: 'job-102',
          status: 'COMPLETED',
          materiality_score: 0.12,
          materiality_level: 'NEGLIGIBLE',
          execution_duration_seconds: 1.8,
          executed_at: new Date(Date.now() - 1000 * 60 * 360).toISOString(),
          delta_summary: {},
        },
      ]);
    } catch (e) {
      console.error('Failed to load monitoring dashboard:', e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [activeSessionId]);

  const showToast = (msg) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    setToastMsg(msg);
    timerRef.current = setTimeout(() => {
      setToastMsg(null);
      timerRef.current = null;
    }, 3500);
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  const handleSaveJob = async (jobPayload) => {
    setError(null);
    try {
      if (editingJob) {
        await api.updateMonitoringJob(editingJob.id, jobPayload);
        showToast(`Updated job '${jobPayload.name}' successfully.`);
      } else {
        await api.createMonitoringJob(jobPayload);
        showToast(`Created new job '${jobPayload.name}' successfully.`);
      }
      setIsModalOpen(false);
      fetchDashboardData();
    } catch (err) {
      console.error('Failed to save monitoring job:', err);
      setError(err.message || 'Failed to save monitoring job');
    }
  };

  const handleTriggerRun = async (jobId) => {
    const safeJobId = String(jobId || '');
    setError(null);
    showToast(`Triggering manual run for job #${safeJobId.slice(0, 7)}...`);
    try {
      const log = await api.triggerMonitoringJobRun(jobId);
      showToast(`Execution completed! Score: ${log.materiality_score} (${log.materiality_level})`);
      fetchDashboardData();
    } catch (e) {
      console.error('Failed to trigger job run:', e);
      setError(e.message || 'Failed to trigger manual execution');
    }
  };

  const handleToggleStatus = async (job) => {
    const nextStatus = job.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    setError(null);
    try {
      await api.updateMonitoringJob(job.id, { status: nextStatus });
      setJobs((prev) => prev.map((j) => (j.id === job.id ? { ...j, status: nextStatus } : j)));
      showToast(`Job status updated to ${nextStatus}.`);
    } catch (e) {
      console.error('Failed to update job status:', e);
      setError(e.message || 'Failed to update job status');
    }
  };

  const handleDeleteJob = async (jobId) => {
    if (!window.confirm('Are you sure you want to delete this monitoring job?')) return;
    setError(null);
    try {
      await api.deleteMonitoringJob(jobId);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
      showToast('Monitoring job deleted.');
    } catch (e) {
      console.error('Failed to delete monitoring job:', e);
      setError(e.message || 'Failed to delete monitoring job');
    }
  };

  const handleCreateBaseline = async () => {
    const label = `Baseline Snapshot v1.${snapshots.length + 1} - ${new Date().toLocaleTimeString()}`;
    setError(null);
    try {
      await api.createBaselineSnapshot({
        snapshot_label: label,
        session_id: activeSessionId || undefined,
        query_id: activeQueryId || undefined,
      });
      showToast(`Baseline snapshot created: ${label}`);
      fetchDashboardData();
    } catch (e) {
      console.error('Failed to create baseline snapshot:', e);
      setError(e.message || 'Failed to create baseline snapshot');
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12 text-on-surface">
      {/* Toast Notification Banner */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 bg-cyber-cyan text-black px-4 py-2.5 rounded-lg shadow-2xl font-mono text-xs font-bold flex items-center gap-2 animate-bounce">
          <span className="material-symbols-outlined text-sm">notifications</span>
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Top Banner Header */}
      <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-xl p-5 shadow-xl flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-cyber-cyan text-2xl">radar</span>
            <h2 className="font-mono text-base font-bold text-cyber-cyan uppercase tracking-wider">
              Continuous Intelligence & Decision Monitoring Engine
            </h2>
          </div>
          <p className="text-xs text-on-surface-variant">
            Automated CRON/INTERVAL research audits, claim drift detection, materiality alert triggers, and baseline snapshots.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCreateBaseline}
            className="px-3.5 py-2 bg-surface border border-outline-variant text-on-surface hover:text-cyber-cyan hover:border-cyber-cyan rounded-lg text-xs font-mono font-bold transition-colors cursor-pointer flex items-center gap-1.5 shadow"
          >
            <span className="material-symbols-outlined text-sm text-tertiary">bookmarks</span>
            Create Baseline Snapshot
          </button>
          <button
            onClick={() => {
              setEditingJob(null);
              setIsModalOpen(true);
            }}
            className="px-4 py-2 bg-cyber-cyan text-black font-bold font-mono text-xs rounded-lg shadow-lg hover:bg-cyber-cyan/80 transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <span className="material-symbols-outlined text-sm">add_alarm</span>
            Create Monitoring Job
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-950/40 border border-red-500/50 rounded text-red-300 text-xs flex items-center gap-2 font-mono">
          <span className="material-symbols-outlined text-sm">error</span>
          <span>{error}</span>
        </div>
      )}

      {/* Main Monitoring Jobs List */}
      <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex justify-between items-center border-b border-outline-variant/40 pb-3 font-mono">
          <h3 className="text-xs font-bold text-cyber-cyan uppercase tracking-wider flex items-center gap-2">
            <span className="material-symbols-outlined text-sm">browse_activity</span>
            Active Research Monitoring Jobs ({jobs.length})
          </h3>
          <span className="text-[10px] text-on-surface-variant font-semibold">AUTOMATED SCHEDULE ENGINE</span>
        </div>

        {jobs.length === 0 ? (
          <div className="p-8 text-center bg-surface rounded-lg border border-outline-variant/40 space-y-2">
            <span className="material-symbols-outlined text-3xl text-outline-variant">alarm_off</span>
            <h4 className="font-mono text-xs font-bold text-on-surface">No Monitoring Jobs Configured</h4>
            <p className="text-[11px] text-on-surface-variant">Create a job to automatically audit your research baseline for material drift.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {jobs.map((job) => {
              const isCron = job.schedule_type === 'CRON';
              const isActive = job.status === 'ACTIVE';
              return (
                <div
                  key={job.id}
                  className={`p-4 bg-surface rounded-xl border transition-all space-y-3 relative ${
                    isActive ? 'border-outline-variant/80 hover:border-cyber-cyan/60 shadow-md' : 'border-outline-variant/40 opacity-70'
                  }`}
                >
                  {/* Job Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                            isCron ? 'bg-purple-950 text-purple-300 border border-purple-800' : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                          }`}
                        >
                          {job.schedule_type}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                            isActive ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-amber-950 text-amber-400 border border-amber-800'
                          }`}
                        >
                          {job.status}
                        </span>
                      </div>
                      <h4 className="font-mono text-xs font-bold text-on-surface">{job.name}</h4>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => {
                          setEditingJob(job);
                          setIsModalOpen(true);
                        }}
                        className="p-1 text-on-surface-variant hover:text-cyber-cyan transition-colors cursor-pointer"
                        title="Edit Job"
                      >
                        <span className="material-symbols-outlined text-sm">edit</span>
                      </button>
                      <button
                        onClick={() => handleDeleteJob(job.id)}
                        className="p-1 text-on-surface-variant hover:text-red-400 transition-colors cursor-pointer"
                        title="Delete Job"
                      >
                        <span className="material-symbols-outlined text-sm">delete</span>
                      </button>
                    </div>
                  </div>

                  {/* Schedule Specs */}
                  <div className="grid grid-cols-2 gap-2 bg-surface-container/60 p-2.5 rounded text-[11px] font-mono">
                    <div>
                      <span className="text-on-surface-variant block text-[10px]">Schedule Details</span>
                      <span className="text-tertiary font-bold">
                        {isCron ? job.cron_expression : `Every ${job.interval_seconds}s`}
                      </span>
                    </div>
                    <div>
                      <span className="text-on-surface-variant block text-[10px]">Alert Threshold</span>
                      <span className="text-cyber-cyan font-bold">
                        {(job.alert_threshold * 100).toFixed(0)}% Materiality
                      </span>
                    </div>
                  </div>

                  {/* Execution Telemetry Timestamps */}
                  <div className="flex justify-between items-center text-[10px] font-mono text-on-surface-variant pt-1">
                    <span>
                      Last Run:{' '}
                      <strong className="text-on-surface">
                        {job.last_run_at ? new Date(job.last_run_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Never'}
                      </strong>
                    </span>
                    <span>
                      Next Run:{' '}
                      <strong className="text-cyber-cyan">
                        {job.next_run_at ? new Date(job.next_run_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Scheduled'}
                      </strong>
                    </span>
                  </div>

                  {/* Action Controls */}
                  <div className="flex items-center justify-between gap-2 pt-2 border-t border-outline-variant/40">
                    <button
                      onClick={() => handleToggleStatus(job)}
                      className={`px-3 py-1 rounded text-xs font-mono cursor-pointer border ${
                        isActive
                          ? 'bg-amber-950/40 text-amber-300 border-amber-800 hover:bg-amber-900/60'
                          : 'bg-emerald-950/40 text-emerald-300 border-emerald-800 hover:bg-emerald-900/60'
                      }`}
                    >
                      {isActive ? 'Pause Job' : 'Resume Job'}
                    </button>

                    <button
                      onClick={() => handleTriggerRun(job.id)}
                      className="px-3.5 py-1 bg-cyber-cyan text-black font-bold font-mono text-xs rounded hover:bg-cyber-cyan/80 transition-colors cursor-pointer flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-xs">play_arrow</span>
                      Run Now
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Baseline Snapshots Section */}
      <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex justify-between items-center border-b border-outline-variant/40 pb-3 font-mono">
          <h3 className="text-xs font-bold text-cyber-cyan uppercase tracking-wider flex items-center gap-2">
            <span className="material-symbols-outlined text-sm text-tertiary">inventory_2</span>
            Research Baseline Snapshots ({snapshots.length})
          </h3>
          <span className="text-[10px] text-on-surface-variant">GROUND TRUTH ANCHORS</span>
        </div>

        <div className="space-y-3 font-mono text-xs">
          {snapshots.map((snap) => (
            <div key={snap.id} className="p-3 bg-surface rounded-lg border border-outline-variant/60 flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-0.5">
                <div className="font-bold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm text-tertiary">bookmark</span>
                  {snap.snapshot_label}
                </div>
                <div className="text-[10px] text-on-surface-variant flex items-center gap-3">
                  <span>Claims: {snap.claims_snapshot?.length || 0}</span>
                  <span>•</span>
                  <span>Sources: {snap.sources_snapshot?.length || 0}</span>
                  <span>•</span>
                  <span>Assumptions: {snap.assumptions_snapshot?.length || 0}</span>
                </div>
              </div>
              <span className="text-[10px] text-on-surface-variant">
                Created {new Date(snap.created_at || Date.now()).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Execution Logs Drawer / History Table */}
      <div className="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex justify-between items-center border-b border-outline-variant/40 pb-3 font-mono">
          <h3 className="text-xs font-bold text-cyber-cyan uppercase tracking-wider flex items-center gap-2">
            <span className="material-symbols-outlined text-sm">history_toggle_off</span>
            Recent Execution Audit Logs ({logs.length})
          </h3>
          <span className="text-[10px] text-on-surface-variant">EXECUTION TELEMETRY</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="border-b border-outline-variant/60 text-on-surface-variant text-[10px] uppercase">
                <th className="py-2 px-3">Log ID / Job</th>
                <th className="py-2 px-3">Executed At</th>
                <th className="py-2 px-3">Duration</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Materiality Score</th>
                <th className="py-2 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-surface-variant/20 transition-colors">
                  <td className="py-2.5 px-3 font-bold text-cyber-cyan">
                    #{String(log?.id || '').slice(0, 7)}
                    <span className="text-[10px] text-on-surface-variant block font-normal">Job: #{String(log?.job_id || '').slice(0, 7)}</span>
                  </td>
                  <td className="py-2.5 px-3 text-on-surface-variant">
                    {new Date(log.executed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </td>
                  <td className="py-2.5 px-3 text-on-surface-variant">{log.execution_duration_seconds}s</td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        log.status === 'ALERT_TRIGGERED'
                          ? 'bg-red-950 text-red-300 border border-red-800'
                          : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      }`}
                    >
                      {log.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-bold text-tertiary font-mono">
                    {(log.materiality_score * 100).toFixed(0)}% ({log.materiality_level})
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => setSelectedDeltaLog(log)}
                      className="px-2.5 py-1 bg-surface border border-cyber-cyan/40 text-cyber-cyan rounded hover:bg-cyber-cyan/20 transition-colors cursor-pointer text-[10px] font-bold"
                    >
                      View Delta Diff
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Decision Alerts Drawer Integration */}
      <DecisionAlertsPanel activeSessionId={activeSessionId} onAlertCountChange={onAlertCountChange} />

      {/* Monitoring Job Modal */}
      {isModalOpen && (
        <MonitoringJobModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSave={handleSaveJob}
          job={editingJob}
          activeSessionId={activeSessionId}
          activeQueryId={activeQueryId}
          baselineSnapshots={snapshots}
        />
      )}

      {/* Delta Inspector Modal */}
      {selectedDeltaLog && (
        <MaterialityDeltaViewer
          deltaSummary={selectedDeltaLog.delta_summary}
          materialityScore={selectedDeltaLog.materiality_score}
          materialityLevel={selectedDeltaLog.materiality_level}
          onClose={() => setSelectedDeltaLog(null)}
        />
      )}
    </div>
  );
}
