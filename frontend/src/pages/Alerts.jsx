import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCircle, ShieldAlert, Filter } from 'lucide-react';
import { api } from '../api/client';
import SeverityBadge from '../components/SeverityBadge';

function formatTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short',
    hour: '2-digit', minute: '2-digit', hour12: false
  });
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('active'); // 'active' | 'all'
  const navigate = useNavigate();

  const loadAlerts = async () => {
    try {
      const data = filter === 'active'
        ? await api.getAlerts()
        : await api.getAllAlerts();
      setAlerts(data);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    loadAlerts();
    const interval = setInterval(loadAlerts, 15000);
    return () => clearInterval(interval);
  }, [filter]);

  const handleAcknowledge = async (e, alertId) => {
    e.stopPropagation(); // prevent card click navigation
    try {
      await api.acknowledgeAlert(alertId, 'operator');
      loadAlerts();
    } catch (err) {
      console.error('Acknowledge failed:', err);
    }
  };

  const activeCount = alerts.filter(a => !a.acknowledged).length;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Bell size={24} style={{ color: 'var(--color-critical)' }} />
            Alerts Center
          </h2>
          <p>Medium and High-severity security events requiring operator review</p>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className={`btn ${filter === 'active' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter('active')}
          >
            <ShieldAlert size={16} />
            Active ({activeCount})
          </button>
          <button
            className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter('all')}
          >
            <Filter size={16} />
            All Escalated
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading alerts...</p>
        </div>
      ) : alerts.length === 0 ? (
        <div className="card empty-state">
          <CheckCircle size={48} style={{ color: 'var(--accent-emerald)', marginBottom: 12 }} />
          <h3>No {filter === 'active' ? 'active' : ''} alerts</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginTop: 4 }}>
            {filter === 'active'
              ? 'All escalated security events have been acknowledged.'
              : 'No escalated alerts found in system records.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`card alert-item ${alert.severity}`}
              style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                padding: '20px 24px',
              }}
              onClick={() => navigate(`/events/${alert.id}`)}
            >
              <div style={{ flex: 1, paddingRight: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  <SeverityBadge severity={alert.severity} />
                  <span
                    className="mono"
                    style={{
                      fontWeight: 800,
                      fontSize: '1.1rem',
                      color:
                        alert.severity === 'critical'
                          ? 'var(--color-critical)'
                          : alert.severity === 'high'
                          ? 'var(--color-high)'
                          : 'var(--color-medium)',
                    }}
                  >
                    Risk Score: {alert.risk_score}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    • {formatTime(alert.timestamp)}
                  </span>
                </div>

                <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                  {alert.event_type?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  {' — '}
                  <span style={{ color: 'var(--accent-cyan)' }}>
                    {alert.camera_name || alert.camera_id}
                  </span>
                </h3>

                {alert.description && (
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 10 }}>
                    {alert.description}
                  </p>
                )}

                <div style={{ display: 'flex', gap: 16, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  <span>Target: <strong style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{alert.object_class}</strong></span>
                  {alert.track_id && <span>Track: <code className="mono">{alert.track_id}</code></span>}
                  {alert.plate_text && (
                    <span>Plate: <code className="mono" style={{ color: 'var(--accent-cyan)' }}>{alert.plate_text}</code></span>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10, flexShrink: 0 }}>
                {!alert.acknowledged ? (
                  <button
                    className="btn btn-success"
                    onClick={(e) => handleAcknowledge(e, alert.id)}
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    <CheckCircle size={16} /> Acknowledge
                  </button>
                ) : (
                  <span
                    style={{
                      color: 'var(--accent-emerald)',
                      fontSize: '0.82rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      background: 'var(--accent-emerald-dim)',
                      padding: '6px 12px',
                      borderRadius: 'var(--radius-md)',
                    }}
                  >
                    <CheckCircle size={14} /> Acknowledged by {alert.acknowledged_by || 'Operator'}
                  </span>
                )}
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Click card for full details →
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
