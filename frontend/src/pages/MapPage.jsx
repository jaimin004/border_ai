import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import MapView from '../components/MapView';
import { Camera, MapPin, AlertTriangle, ShieldCheck, Activity } from 'lucide-react';

export default function MapPage() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.getCameras()
      .then(setCameras)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Loading Sector Map & Node Telemetry...</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Top Header */}
      <div className="page-header flex-between">
        <div>
          <h2>Surveillance Sector Map</h2>
          <p>Real-time spatial visualization of camera nodes & field sensitive perimeters</p>
        </div>
        <div className="sector-info-badge">
          <ShieldCheck size={16} />
          <span>Sector Nodes: 8 Active Nodes</span>
        </div>
      </div>

      {/* Main Map View */}
      <MapView
        cameras={cameras}
        onCameraClick={(cam) => navigate(`/cameras/${cam.id}`)}
      />

      {/* Camera Grid Overview Below Map */}
      <div className="section-container" style={{ marginTop: '2rem' }}>
        <div className="section-title">
          <Camera size={18} className="text-cyan" />
          <h3>Field Surveillance Camera Nodes Overview</h3>
        </div>

        <div className="map-cam-grid">
          {cameras.map((cam) => {
            const hasAlert = (cam.active_alerts || 0) > 0;
            return (
              <div
                key={cam.id}
                className={`map-cam-card ${hasAlert ? 'has-alert' : ''}`}
                onClick={() => navigate(`/cameras/${cam.id}`)}
              >
                <div className="cam-card-header">
                  <div className="cam-id-pill">{cam.id.toUpperCase()}</div>
                  <span className={`status-badge-sm ${cam.status}`}>
                    {cam.status.toUpperCase()}
                  </span>
                </div>

                <h4 className="cam-card-title">{cam.name}</h4>

                <div className="cam-card-location">
                  <MapPin size={13} />
                  <span>{cam.location}</span>
                </div>

                <div className="cam-card-footer">
                  <div className="cam-coords">
                    {cam.latitude?.toFixed(4)}°N, {cam.longitude?.toFixed(4)}°E
                  </div>

                  {hasAlert ? (
                    <span className="cam-alert-badge">
                      <AlertTriangle size={12} />
                      {cam.active_alerts} Alert{cam.active_alerts > 1 ? 's' : ''}
                    </span>
                  ) : (
                    <span className="cam-normal-badge">
                      <Activity size={12} />
                      Normal
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
