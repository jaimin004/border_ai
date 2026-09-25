import { Camera, Wifi, WifiOff } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function CameraCard({ camera }) {
  const navigate = useNavigate();
  const isOnline = camera.status === 'online';

  return (
    <div className="camera-card" onClick={() => navigate(`/cameras/${camera.id}`)}>
      <div className="camera-thumbnail">
        <Camera className="cam-icon" size={40} />
        <div className={`camera-status-dot ${camera.status}`} />
        {camera.active_alerts > 0 && (
          <div style={{
            position: 'absolute', top: 12, left: 12,
            background: 'var(--color-critical)',
            color: 'white',
            fontSize: '0.68rem',
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: 10,
          }}>
            {camera.active_alerts} alert{camera.active_alerts > 1 ? 's' : ''}
          </div>
        )}
      </div>
      <div className="camera-info">
        <div className="camera-name">{camera.name}</div>
        <div className="camera-location">{camera.location}</div>
        <div className="camera-meta">
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {isOnline ? <Wifi size={12} /> : <WifiOff size={12} />}
            {camera.status}
          </span>
          <span>{camera.zone_type?.replace(/_/g, ' ')}</span>
          {camera.last_event_at && (
            <span>Last: {new Date(camera.last_event_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</span>
          )}
        </div>
      </div>
    </div>
  );
}
