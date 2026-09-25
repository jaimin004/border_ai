import { useNavigate } from 'react-router-dom';
import SeverityBadge from './SeverityBadge';

function formatTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

export default function EventTable({ events = [], showCamera = true }) {
  const navigate = useNavigate();

  if (events.length === 0) {
    return <div className="empty-state"><p>No events found</p></div>;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Event ID</th>
          <th>Type</th>
          {showCamera && <th>Camera</th>}
          <th>Severity</th>
          <th>Risk</th>
          <th>Object</th>
          <th>Time</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {events.map((evt) => (
          <tr key={evt.id} onClick={() => navigate(`/events/${evt.id}`)}>
            <td>{evt.id}</td>
            <td style={{ textTransform: 'capitalize' }}>
              {evt.event_type?.replace(/_/g, ' ')}
            </td>
            {showCamera && (
              <td style={{ color: 'var(--text-primary)' }}>
                {evt.camera_name || evt.camera_id}
              </td>
            )}
            <td><SeverityBadge severity={evt.severity} /></td>
            <td>
              <span className="mono" style={{
                fontWeight: 700,
                color: evt.risk_score > 80 ? 'var(--color-critical)'
                  : evt.risk_score > 60 ? 'var(--color-high)'
                  : evt.risk_score > 30 ? 'var(--color-medium)'
                  : 'var(--color-low)'
              }}>
                {evt.risk_score}
              </span>
            </td>
            <td style={{ textTransform: 'capitalize' }}>{evt.object_class}</td>
            <td style={{ whiteSpace: 'nowrap' }}>{formatTime(evt.timestamp)}</td>
            <td>
              {evt.acknowledged ? (
                <span style={{ color: 'var(--accent-emerald)', fontSize: '0.78rem' }}>✓ Ack</span>
              ) : evt.escalated ? (
                <span style={{ color: 'var(--color-critical)', fontSize: '0.78rem' }}>⚠ Active</span>
              ) : (
                <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>—</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
