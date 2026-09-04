import React, { useState, useEffect } from 'react';

function isValidCronExpression(expr) {
  const trimmed = expr.trim();
  const shorthands = ['@hourly', '@daily', '@weekly', '@monthly', '@yearly', '@annually'];
  if (shorthands.includes(trimmed.toLowerCase())) {
    return true;
  }

  const parts = trimmed.split(/\s+/);
  if (parts.length !== 5) {
    return false;
  }

  const fieldRanges = [
    { min: 0, max: 59 }, // minute
    { min: 0, max: 23 }, // hour
    { min: 1, max: 31 }, // day-of-month
    { min: 1, max: 12 }, // month
    { min: 0, max: 7 },  // day-of-week
  ];

  for (let i = 0; i < 5; i++) {
    const field = parts[i];
    const { min, max } = fieldRanges[i];

    if (!/^[0-9*\/,\-]+$/.test(field)) {
      return false;
    }

    const numbers = field.match(/\d+/g);
    if (numbers) {
      for (const numStr of numbers) {
        const val = parseInt(numStr, 10);
        if (val < min || val > max) {
          return false;
        }
      }
    }
  }

  return true;
}

export default function MonitoringJobModal({
  isOpen,
  onClose,
  onSave,
  job = null,
  activeSessionId = null,
  activeQueryId = null,
  baselineSnapshots = [],
}) {
  const [name, setName] = useState('');
  const [scheduleType, setScheduleType] = useState('INTERVAL');
  const [cronExpression, setCronExpression] = useState('0 */6 * * *');
  const [intervalSeconds, setIntervalSeconds] = useState(3600);
  const [alertThreshold, setAlertThreshold] = useState(0.5);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [baselineSnapshotId, setBaselineSnapshotId] = useState('');
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (job) {
      setName(job.name || '');
      setScheduleType(job.schedule_type || 'INTERVAL');
      setCronExpression(job.cron_expression || '0 */6 * * *');
      setIntervalSeconds(job.interval_seconds || 3600);
      setAlertThreshold(job.alert_threshold ?? 0.5);
      setWebhookUrl(job.webhook_url || '');
      setBaselineSnapshotId(job.baseline_snapshot_id || '');
    } else {
      setName('Continuous Research Audit Job');
      setScheduleType('INTERVAL');
      setCronExpression('0 */6 * * *');
      setIntervalSeconds(3600);
      setAlertThreshold(0.5);
      setWebhookUrl('');
      setBaselineSnapshotId(baselineSnapshots[0]?.id || '');
    }
    setError(null);
  }, [job, isOpen, baselineSnapshots]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Job name cannot be empty.');
      return;
    }

    let parsedInterval = null;
    if (scheduleType === 'CRON') {
      if (!isValidCronExpression(cronExpression)) {
        setError('Invalid CRON expression. Must be 5 fields with valid ranges (0-59 min, 0-23 hr, 1-31 day, 1-12 month, 0-7 weekday).');
        return;
      }
    } else if (scheduleType === 'INTERVAL') {
      parsedInterval = typeof intervalSeconds === 'number' ? intervalSeconds : parseInt(intervalSeconds, 10);
      if (isNaN(parsedInterval) || parsedInterval < 10) {
        setError('Interval must be a valid number of at least 10 seconds.');
        return;
      }
    }

    const parsedThreshold = typeof alertThreshold === 'number' ? alertThreshold : parseFloat(alertThreshold);
    if (isNaN(parsedThreshold) || parsedThreshold < 0 || parsedThreshold > 1) {
      setError('Alert threshold must be a valid number between 0.0 and 1.0.');
      return;
    }

    if (webhookUrl && webhookUrl.trim()) {
      try {
        const parsedUrl = new URL(webhookUrl.trim());
        if (parsedUrl.protocol !== 'http:' && parsedUrl.protocol !== 'https:') {
          setError('Webhook URL must use http or https protocol.');
          return;
        }
        if (!parsedUrl.hostname) {
          setError('Webhook URL must contain a valid hostname.');
          return;
        }
      } catch {
        setError('Webhook URL must be a valid URL (e.g. https://hooks.slack.com/...).');
        return;
      }
    }

    const payload = {
      name: name.trim(),
      schedule_type: scheduleType,
      cron_expression: scheduleType === 'CRON' ? cronExpression.trim() : null,
      interval_seconds: scheduleType === 'INTERVAL' ? parsedInterval : null,
      alert_threshold: parsedThreshold,
      webhook_url: webhookUrl.trim() || null,
      baseline_snapshot_id: baselineSnapshotId || null,
      session_id: activeSessionId || null,
      query_id: activeQueryId || null,
    };

    setIsSubmitting(true);
    try {
      await onSave(payload);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save monitoring job');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getThresholdColor = (val) => {
    if (val >= 0.8) return 'text-red-400 accent-red-500';
    if (val >= 0.5) return 'text-amber-400 accent-amber-500';
    return 'text-emerald-400 accent-emerald-500';
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="monitoring-job-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto"
    >
      <div className="bg-surface-container-low border border-cyber-cyan/40 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-5 text-on-surface relative">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-outline-variant pb-3">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-cyber-cyan text-xl">update</span>
            <h2 id="monitoring-job-modal-title" className="font-mono text-sm font-bold text-cyber-cyan uppercase tracking-wider">
              {job ? 'Edit Continuous Monitoring Job' : 'Create Monitoring Job'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-950/40 border border-red-500/50 rounded text-red-300 text-xs flex items-center gap-2">
            <span className="material-symbols-outlined text-sm">error</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs font-body-main">
          {/* Job Name */}
          <div>
            <label className="block font-mono text-[11px] uppercase tracking-wider text-on-surface-variant mb-1 font-semibold">
              Monitoring Job Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Daily Vendor Risk Baseline Audit"
              className="w-full bg-surface border border-outline-variant rounded px-3 py-2 text-on-surface focus:outline-none focus:border-cyber-cyan"
              required
            />
          </div>

          {/* Baseline Snapshot Picker */}
          {baselineSnapshots.length > 0 && (
            <div>
              <label className="block font-mono text-[11px] uppercase tracking-wider text-on-surface-variant mb-1 font-semibold">
                Baseline Snapshot Anchor
              </label>
              <select
                value={baselineSnapshotId}
                onChange={(e) => setBaselineSnapshotId(e.target.value)}
                className="w-full bg-surface border border-outline-variant rounded px-3 py-2 text-on-surface focus:outline-none focus:border-cyber-cyan font-mono"
              >
                <option value="">-- Active Query Snapshot --</option>
                {baselineSnapshots.map((snap) => (
                  <option key={snap.id} value={snap.id}>
                    {snap.snapshot_label} ({new Date(snap.created_at || Date.now()).toLocaleDateString()})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Schedule Type Selection */}
          <div>
            <label className="block font-mono text-[11px] uppercase tracking-wider text-on-surface-variant mb-1 font-semibold">
              Execution Schedule Type
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setScheduleType('INTERVAL')}
                className={`py-2 px-3 rounded border text-center font-mono text-xs transition-all cursor-pointer ${
                  scheduleType === 'INTERVAL'
                    ? 'bg-cyber-cyan/20 border-cyber-cyan text-cyber-cyan font-bold shadow-md'
                    : 'bg-surface border-outline-variant text-on-surface-variant hover:border-cyber-cyan/50'
                }`}
              >
                ⏱️ INTERVAL (Seconds)
              </button>
              <button
                type="button"
                onClick={() => setScheduleType('CRON')}
                className={`py-2 px-3 rounded border text-center font-mono text-xs transition-all cursor-pointer ${
                  scheduleType === 'CRON'
                    ? 'bg-cyber-cyan/20 border-cyber-cyan text-cyber-cyan font-bold shadow-md'
                    : 'bg-surface border-outline-variant text-on-surface-variant hover:border-cyber-cyan/50'
                }`}
              >
                📅 CRON Expression
              </button>
            </div>
          </div>

          {/* Schedule Config Details */}
          {scheduleType === 'INTERVAL' ? (
            <div className="p-3 bg-surface rounded border border-outline-variant/60 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-mono text-[11px] text-on-surface-variant">Interval (Seconds):</span>
                <span className="font-mono text-xs text-cyber-cyan font-bold">
                  {intervalSeconds || 0}s ({Math.round((intervalSeconds || 0) / 60)} min / {((intervalSeconds || 0) / 3600).toFixed(1)} hrs)
                </span>
              </div>
              <input
                type="number"
                min="10"
                step="10"
                value={intervalSeconds}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === '') {
                    setIntervalSeconds('');
                  } else {
                    const parsed = parseInt(val, 10);
                    setIntervalSeconds(isNaN(parsed) ? 0 : parsed);
                  }
                }}
                className="w-full bg-surface-container border border-outline-variant rounded px-3 py-1.5 font-mono text-on-surface focus:outline-none focus:border-cyber-cyan"
              />
              <div className="flex gap-1.5 pt-1">
                {[
                  { label: '5m', sec: 300 },
                  { label: '1h', sec: 3600 },
                  { label: '6h', sec: 21600 },
                  { label: '24h', sec: 86400 },
                ].map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => setIntervalSeconds(preset.sec)}
                    className="px-2 py-1 bg-surface-container-high border border-outline-variant rounded text-[10px] font-mono text-on-surface-variant hover:text-cyber-cyan hover:border-cyber-cyan cursor-pointer"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-3 bg-surface rounded border border-outline-variant/60 space-y-2">
              <label className="block font-mono text-[11px] text-on-surface-variant font-semibold">
                CRON Expression (5 fields)
              </label>
              <input
                type="text"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                placeholder="0 */6 * * *"
                className="w-full bg-surface-container border border-outline-variant rounded px-3 py-1.5 font-mono text-on-surface focus:outline-none focus:border-cyber-cyan"
              />
              <p className="text-[10px] text-on-surface-variant font-mono">
                Format: <code className="text-tertiary">min hour day-of-month month day-of-week</code> (e.g. <code className="text-cyber-cyan">0 0 * * *</code> for midnight daily)
              </p>
              <div className="flex gap-1.5 flex-wrap pt-1">
                {[
                  { label: 'Every 6h', cron: '0 */6 * * *' },
                  { label: 'Daily Midnight', cron: '0 0 * * *' },
                  { label: 'Weekly Mon', cron: '0 0 * * 1' },
                ].map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => setCronExpression(preset.cron)}
                    className="px-2 py-1 bg-surface-container-high border border-outline-variant rounded text-[10px] font-mono text-on-surface-variant hover:text-cyber-cyan hover:border-cyber-cyan cursor-pointer"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Materiality Alert Threshold Slider */}
          <div className="p-3 bg-surface rounded border border-outline-variant/60 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-mono text-[11px] text-on-surface-variant font-semibold">
                Alert Materiality Threshold (0.0 - 1.0)
              </span>
              <span className={`font-mono text-xs font-bold ${getThresholdColor(alertThreshold)}`}>
                {((alertThreshold || 0) * 100).toFixed(0)}% ({alertThreshold})
              </span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={alertThreshold}
              onChange={(e) => {
                const parsed = parseFloat(e.target.value);
                setAlertThreshold(isNaN(parsed) ? 0.5 : parsed);
              }}
              className={`w-full cursor-pointer ${getThresholdColor(alertThreshold)}`}
            />
            <div className="flex justify-between text-[10px] font-mono text-on-surface-variant">
              <span>0.0 (Sensitive / Low Drift)</span>
              <span>0.5 (Moderate)</span>
              <span>1.0 (Critical Flips Only)</span>
            </div>
          </div>

          {/* Alert Webhook URL */}
          <div>
            <label className="block font-mono text-[11px] uppercase tracking-wider text-on-surface-variant mb-1 font-semibold">
              Alert Notification Webhook URL (Optional)
            </label>
            <input
              type="url"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              className="w-full bg-surface border border-outline-variant rounded px-3 py-2 text-on-surface font-mono text-xs focus:outline-none focus:border-cyber-cyan"
            />
          </div>

          {/* Form Actions */}
          <div className="flex justify-end gap-2 pt-3 border-t border-outline-variant/60">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-surface-container border border-outline-variant text-on-surface-variant rounded hover:text-on-surface font-mono text-xs cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-cyber-cyan text-black font-bold font-mono text-xs rounded hover:bg-cyber-cyan/80 transition-colors cursor-pointer flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
                  Saving...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-sm">save</span>
                  Save Monitoring Job
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
