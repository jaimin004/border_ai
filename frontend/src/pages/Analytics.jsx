import { useEffect, useState } from 'react';
import { api } from '../api/client';
import {
  TimelineChart, SeverityPieChart, CameraBarChart,
  RiskDistributionChart, EventTypeChart
} from '../components/Charts';

export default function Analytics() {
  const [timeline, setTimeline] = useState([]);
  const [severity, setSeverity] = useState([]);
  const [cameraActivity, setCameraActivity] = useState([]);
  const [riskDist, setRiskDist] = useState([]);
  const [eventTypes, setEventTypes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [t, s, c, r, e] = await Promise.all([
          api.getTimeline(24),
          api.getSeverityDistribution(),
          api.getCameraActivity(),
          api.getRiskDistribution(),
          api.getEventTypes(),
        ]);
        setTimeline(t);
        setSeverity(s);
        setCameraActivity(c);
        setRiskDist(r);
        setEventTypes(e);
      } catch (err) {
        console.error('Analytics load error:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <div className="loading-state"><div className="spinner" /><p>Loading analytics...</p></div>;
  }

  return (
    <div>
      <div className="page-header">
        <h2>Analytics</h2>
        <p>Event intelligence and performance metrics</p>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="chart-card">
          <div className="card-title">Events Timeline (24h)</div>
          <TimelineChart data={timeline} />
        </div>
        <div className="chart-card">
          <div className="card-title">Severity Distribution</div>
          <SeverityPieChart data={severity} />
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="chart-card">
          <div className="card-title">Camera Activity</div>
          <CameraBarChart data={cameraActivity} />
        </div>
        <div className="chart-card">
          <div className="card-title">Risk Score Distribution</div>
          <RiskDistributionChart data={riskDist} />
        </div>
      </div>

      <div className="chart-card">
        <div className="card-title">Event Types</div>
        <EventTypeChart data={eventTypes} />
      </div>
    </div>
  );
}
