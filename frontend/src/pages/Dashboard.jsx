import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Bell, Camera, AlertTriangle, MapPin, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';
import KPICard from '../components/KPICard';
import AlertFeed from '../components/AlertFeed';
import MapView from '../components/MapView';
import { TimelineChart, SeverityPieChart } from '../components/Charts';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [severityDist, setSeverityDist] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        const [s, a, c, t, sd] = await Promise.all([
          api.getStats(),
          api.getAlerts(),
          api.getCameras().catch(() => []),
          api.getTimeline(24),
          api.getSeverityDistribution(),
        ]);
        setStats(s);
        setAlerts(a);
        setCameras(c);
        setTimeline(t);
        setSeverityDist(sd);
      } catch (err) {
        console.error('Dashboard load error:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="loading-state"><div className="spinner" /><p>Loading Command Dashboard Telemetry...</p></div>;
  }

  return (
    <div className="page-container">
      {/* Top Header */}
      <div className="page-header flex-between">
        <div>
          <h2>Command Dashboard</h2>
          <p>Real-time surveillance intelligence, field camera locations & active threat telemetry</p>
        </div>
        <div className="sector-info-badge">
          <ShieldCheck size={16} />
          <span>Surveillance Sector: 8 Active Nodes</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <KPICard
          icon={Activity}
          value={stats?.total_events || 0}
          label="Total Events"
          accent="cyan"
        />
        <KPICard
          icon={Bell}
          value={stats?.active_alerts || 0}
          label="Active Threats"
          accent="red"
        />
        <KPICard
          icon={Camera}
          value={`${stats?.cameras_online || cameras.filter(c => c.status === 'online').length || 7}/${stats?.cameras_total || cameras.length || 8}`}
          label="Cameras Online"
          accent="emerald"
        />
        <KPICard
          icon={AlertTriangle}
          value={stats?.critical_count || 0}
          label="Critical Threats"
          accent="amber"
        />
      </div>

      {/* Dashboard Section: Compact Map View (Small Box) + Camera Nodes Telemetry */}
      <div className="grid-2" style={{ marginBottom: 28 }}>
        {/* Compact Square Map View */}
        <div>
          <MapView
            cameras={cameras}
            compact={true}
            onCameraClick={(cam) => navigate(`/cameras/${cam.id}`)}
            onFullViewClick={() => navigate('/map')}
          />
        </div>

        {/* Camera Nodes Quick Details */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              Surveillance Camera Field Nodes
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 310, overflowY: 'auto' }}>
            {(cameras.length > 0 ? cameras : [
              { id: 'cam_01', name: 'Colaba Coastal Security Watch', location: 'Colaba Coastal Perimeter', status: 'online', active_alerts: 1, zone_type: 'sensitive_area' },
              { id: 'cam_02', name: 'Gateway Perimeter Guard', location: 'Gateway High Security Gate', status: 'online', active_alerts: 2, zone_type: 'sensitive_area' },
              { id: 'cam_03', name: 'Colaba Defense Station Watch', location: 'Colaba Defense Perimeter', status: 'online', active_alerts: 1, zone_type: 'sensitive_area' },
              { id: 'cam_04', name: 'Marine Drive Promenade Watch', location: 'Marine Drive Sector 4', status: 'online', active_alerts: 0, zone_type: 'perimeter' },
              { id: 'cam_05', name: 'Bandra Sea Link Toll Post', location: 'Sea Link Toll Gate', status: 'online', active_alerts: 1, zone_type: 'checkpoint' },
              { id: 'cam_06', name: 'Trombay High-Security Post', location: 'Trombay Restricted Gate', status: 'online', active_alerts: 1, zone_type: 'sensitive_area' },
              { id: 'cam_07', name: 'JNPT Port Container Guard', location: 'JNPT Port Terminal', status: 'offline', active_alerts: 0, zone_type: 'port_gate' },
              { id: 'cam_08', name: 'Versova Landing Patrol Post', location: 'Versova Patrol Station', status: 'online', active_alerts: 1, zone_type: 'waterway' },
            ]).map((cam) => {
              const hasAlert = (cam.active_alerts || 0) > 0;
              const isSensitive = cam.zone_type === 'sensitive_area' || cam.zone_type === 'restricted_zone';
              return (
                <div
                  key={cam.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                  }}
                  onClick={() => navigate(`/cameras/${cam.id}`)}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="cam-id-pill">{cam.id.toUpperCase()}</span>
                      <strong style={{ fontSize: '0.84rem', color: 'var(--text-primary)' }}>{cam.name}</strong>
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: 2, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <MapPin size={11} /> {cam.location}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {isSensitive && (
                      <span style={{ fontSize: '0.65rem', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.15)', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>
                        Sensitive
                      </span>
                    )}
                    {hasAlert ? (
                      <span className="cam-alert-badge">
                        <AlertTriangle size={11} /> {cam.active_alerts} Alert
                      </span>
                    ) : (
                      <span className="cam-normal-badge">
                        <Activity size={11} /> Normal
                      </span>
                    )}
                    <span className={`status-badge-sm ${cam.status}`}>{cam.status.toUpperCase()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main grid: charts + alerts */}
      <div className="grid-2" style={{ marginBottom: 28 }}>
        <div className="chart-card">
          <div className="card-title">Events Timeline (24h)</div>
          <TimelineChart data={timeline} />
        </div>
        <div className="chart-card">
          <div className="card-title">Severity Distribution</div>
          <SeverityPieChart data={severityDist} />
        </div>
      </div>

      {/* Active Threat Alerts feed */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            Active Threat Alerts
            {alerts.length > 0 && (
              <span className="nav-badge" style={{ marginLeft: 8 }}>{alerts.length}</span>
            )}
          </div>
        </div>
        <AlertFeed alerts={alerts} />
      </div>
    </div>
  );
}
