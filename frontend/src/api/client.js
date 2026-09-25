/**
 * BORDER-AI — API Client
 * Centralized API calls to the FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export const api = {
  // Stats
  getStats: () => request('/api/stats'),

  // Cameras
  getCameras: () => request('/api/cameras'),
  getCamera: (id) => request(`/api/cameras/${id}`),

  // Events
  getEvents: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.severity) qs.set('severity', params.severity);
    if (params.camera_id) qs.set('camera_id', params.camera_id);
    if (params.event_type) qs.set('event_type', params.event_type);
    if (params.limit) qs.set('limit', params.limit);
    if (params.offset) qs.set('offset', params.offset);
    const query = qs.toString();
    return request(`/api/events${query ? '?' + query : ''}`);
  },
  getEvent: (id) => request(`/api/events/${id}`),

  // Alerts
  getAlerts: () => request('/api/alerts'),
  getAllAlerts: () => request('/api/alerts/all'),
  acknowledgeAlert: (id, by = 'operator') =>
    request(`/api/alerts/${id}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ acknowledged_by: by }),
    }),

  // Analytics
  getTimeline: (hours = 24) => request(`/api/analytics/timeline?hours=${hours}`),
  getSeverityDistribution: () => request('/api/analytics/severity-distribution'),
  getCameraActivity: () => request('/api/analytics/camera-activity'),
  getEventTypes: () => request('/api/analytics/event-types'),
  getRiskDistribution: () => request('/api/analytics/risk-distribution'),
};
