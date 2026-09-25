import { useEffect, useState } from 'react';
import { api } from '../api/client';
import EventTable from '../components/EventTable';

export default function Events() {
  const [data, setData] = useState({ events: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    severity: '',
    event_type: '',
    camera_id: '',
  });
  const [cameras, setCameras] = useState([]);

  useEffect(() => {
    api.getCameras().then(setCameras).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (filters.severity) params.severity = filters.severity;
    if (filters.event_type) params.event_type = filters.event_type;
    if (filters.camera_id) params.camera_id = filters.camera_id;
    params.limit = 50;

    api.getEvents(params)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [filters]);

  return (
    <div>
      <div className="page-header">
        <h2>Events Log</h2>
        <p>All detected events across the camera network</p>
      </div>

      <div className="filters-bar">
        <select
          className="filter-select"
          value={filters.severity}
          onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select
          className="filter-select"
          value={filters.event_type}
          onChange={(e) => setFilters({ ...filters, event_type: e.target.value })}
        >
          <option value="">All Event Types</option>
          <option value="zone_intrusion">Zone Intrusion</option>
          <option value="loitering">Loitering</option>
          <option value="abandoned_object">Abandoned Object</option>
          <option value="anpr_read">ANPR Read</option>
          <option value="face_match">Face Match</option>
        </select>

        <select
          className="filter-select"
          value={filters.camera_id}
          onChange={(e) => setFilters({ ...filters, camera_id: e.target.value })}
        >
          <option value="">All Cameras</option>
          {cameras.map((cam) => (
            <option key={cam.id} value={cam.id}>{cam.name}</option>
          ))}
        </select>

        {(filters.severity || filters.event_type || filters.camera_id) && (
          <button
            className="btn btn-secondary"
            onClick={() => setFilters({ severity: '', event_type: '', camera_id: '' })}
          >
            Clear Filters
          </button>
        )}
      </div>

      <div className="card" style={{ padding: 0, overflow: 'auto' }}>
        {loading ? (
          <div className="loading-state"><div className="spinner" /></div>
        ) : (
          <>
            <EventTable events={data.events} />
            <div style={{
              padding: '12px 16px',
              fontSize: '0.78rem',
              color: 'var(--text-muted)',
              borderTop: '1px solid var(--border-subtle)',
            }}>
              Showing {data.events.length} of {data.total} events
            </div>
          </>
        )}
      </div>
    </div>
  );
}
