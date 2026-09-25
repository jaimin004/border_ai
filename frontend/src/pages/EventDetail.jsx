import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, MapPin, Clock, User, Car } from 'lucide-react';
import { api } from '../api/client';
import SeverityBadge from '../components/SeverityBadge';
import RiskBreakdown from '../components/RiskBreakdown';

function formatTimestamp(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  });
}

export default function EventDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getEvent(id)
      .then(setEvent)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  const handleAcknowledge = async () => {
    try {
      await api.acknowledgeAlert(id, 'operator');
      setEvent((prev) => ({ ...prev, acknowledged: true, acknowledged_by: 'operator' }));
    } catch (err) {
      console.error('Acknowledge failed:', err);
    }
  };

  if (loading) {
    return <div className="loading-state"><div className="spinner" /><p>Loading event...</p></div>;
  }

  if (!event || event.error) {
    return (
      <div className="empty-state">
        <p>Event not found</p>
        <button className="btn btn-secondary mt-2" onClick={() => navigate('/events')}>
          ← Back to Events
        </button>
      </div>
    );
  }

  const breakdown = Array.isArray(event.breakdown)
    ? event.breakdown
    : typeof event.breakdown === 'string'
      ? JSON.parse(event.breakdown)
      : [];

  const faceMatch = typeof event.face_match === 'string'
    ? JSON.parse(event.face_match)
    : event.face_match;

  return (
    <div>
      <button className="back-link" onClick={() => navigate(-1)}>
        <ArrowLeft size={16} /> Back
      </button>

      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {event.event_type?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            <SeverityBadge severity={event.severity} />
          </h2>
          <p>{event.camera_name || event.camera_id} — {event.camera_location || ''}</p>
        </div>
        {event.escalated && !event.acknowledged && (
          <button className="btn btn-success" onClick={handleAcknowledge}>
            <CheckCircle size={16} /> Acknowledge Alert
          </button>
        )}
        {event.acknowledged && (
          <span style={{
            color: 'var(--accent-emerald)',
            fontSize: '0.85rem',
            fontWeight: 600,
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <CheckCircle size={16} /> Acknowledged by {event.acknowledged_by}
          </span>
        )}
      </div>

      <div className="event-detail-grid">
        {/* Left column: info */}
        <div>
          {/* Description */}
          {event.description && (
            <div className="detail-section">
              <h3>AI Summary</h3>
              <div className="card" style={{
                background: 'var(--bg-surface)',
                lineHeight: 1.6,
                fontSize: '0.9rem',
                color: 'var(--text-secondary)',
              }}>
                {event.description}
              </div>
            </div>
          )}

          {/* Event Details */}
          <div className="detail-section">
            <h3>Event Details</h3>
            <div className="card" style={{ background: 'var(--bg-surface)', padding: '4px 16px' }}>
              <div className="detail-field">
                <span className="detail-field-label">Event ID</span>
                <span className="detail-field-value mono">{event.id}</span>
              </div>
              <div className="detail-field">
                <span className="detail-field-label">Track ID</span>
                <span className="detail-field-value mono">{event.track_id || '—'}</span>
              </div>
              <div className="detail-field">
                <span className="detail-field-label">Object Class</span>
                <span className="detail-field-value" style={{ textTransform: 'capitalize' }}>
                  {event.object_class === 'person' ? '👤 Person' : event.object_class === 'vehicle' ? '🚗 Vehicle' : event.object_class}
                </span>
              </div>
              <div className="detail-field">
                <span className="detail-field-label">
                  <Clock size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                  Timestamp
                </span>
                <span className="detail-field-value">{formatTimestamp(event.timestamp)}</span>
              </div>
              <div className="detail-field">
                <span className="detail-field-label">
                  <MapPin size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                  Camera
                </span>
                <span className="detail-field-value">{event.camera_name}</span>
              </div>
              <div className="detail-field">
                <span className="detail-field-label">Zone Type</span>
                <span className="detail-field-value" style={{ textTransform: 'capitalize' }}>
                  {event.zone_type?.replace(/_/g, ' ') || '—'}
                </span>
              </div>
            </div>
          </div>

          {/* ANPR */}
          {event.plate_text && (
            <div className="detail-section">
              <h3>
                <Car size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                ANPR Result
              </h3>
              <div className="card" style={{ background: 'var(--bg-surface)', padding: '4px 16px' }}>
                <div className="detail-field">
                  <span className="detail-field-label">Plate Number</span>
                  <span className="detail-field-value mono" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    {event.plate_text}
                  </span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">OCR Confidence</span>
                  <span className="detail-field-value">{event.plate_confidence}%</span>
                </div>
              </div>
            </div>
          )}

          {/* Face Match */}
          {faceMatch?.matched && (
            <div className="detail-section">
              <h3>
                <User size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                Watchlist Match
              </h3>
              <div className="card" style={{
                background: 'var(--color-high-bg)',
                border: '1px solid var(--color-high-border)',
                padding: '4px 16px',
              }}>
                <div className="detail-field">
                  <span className="detail-field-label">Matched Name</span>
                  <span className="detail-field-value" style={{ color: 'var(--color-high)', fontWeight: 700 }}>
                    {faceMatch.name}
                  </span>
                </div>
                <div className="detail-field">
                  <span className="detail-field-label">Confidence</span>
                  <span className="detail-field-value">
                    {(faceMatch.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={{ padding: '8px 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  ⚠ Possible match only — requires mandatory human verification
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right column: risk breakdown */}
        <div>
          <div className="detail-section">
            <h3>Risk Score Breakdown</h3>
            <RiskBreakdown
              breakdown={breakdown}
              totalScore={event.risk_score}
              severity={event.severity}
            />
          </div>

          <div className="detail-section">
            <h3>Metadata</h3>
            <div className="card" style={{ background: 'var(--bg-surface)', padding: '4px 16px' }}>
              <div className="detail-field">
                <span className="detail-field-label">Escalated</span>
                <span className="detail-field-value">
                  {event.escalated ? '✓ Yes' : '✗ No'}
                </span>
              </div>
              <div className="detail-field">
                <span className="detail-field-label">Synced</span>
                <span className="detail-field-value">
                  {event.synced ? '✓ Yes' : '✗ Pending'}
                </span>
              </div>
              <div className="detail-field" style={{ borderBottom: 'none' }}>
                <span className="detail-field-label">Coordinates</span>
                <span className="detail-field-value mono" style={{ fontSize: '0.78rem' }}>
                  {event.latitude && event.longitude
                    ? `${event.latitude.toFixed(4)}, ${event.longitude.toFixed(4)}`
                    : '—'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
