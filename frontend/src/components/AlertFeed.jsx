import { useNavigate } from 'react-router-dom';
import SeverityBadge from './SeverityBadge';

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
  return d.toLocaleDateString();
}

export default function AlertFeed({ alerts = [] }) {
  const navigate = useNavigate();

  if (alerts.length === 0) {
    return (
      <div className="empty-state">
        <p>No active alerts</p>
      </div>
    );
  }

  return (
    <div className="alert-feed">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`alert-item ${alert.severity}`}
          onClick={() => navigate(`/events/${alert.id}`)}
        >
          <div className={`alert-score ${alert.severity}`}>
            {alert.risk_score}
          </div>
          <div className="alert-content">
            <div className="alert-title">
              {alert.event_type?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
              {' — '}
              {alert.camera_name || alert.camera_id}
            </div>
            <div className="alert-meta">
              <SeverityBadge severity={alert.severity} />
              <span>{alert.object_class}</span>
              <span>{formatTime(alert.timestamp)}</span>
            </div>
            {alert.description && (
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.4 }}>
                {alert.description.length > 120
                  ? alert.description.substring(0, 120) + '...'
                  : alert.description}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
