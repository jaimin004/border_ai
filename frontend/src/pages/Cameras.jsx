import { useEffect, useState } from 'react';
import { api } from '../api/client';
import CameraCard from '../components/CameraCard';

export default function Cameras() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    api.getCameras()
      .then(setCameras)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === 'all'
    ? cameras
    : cameras.filter((c) => c.status === filter);

  if (loading) {
    return <div className="loading-state"><div className="spinner" /><p>Loading cameras...</p></div>;
  }

  return (
    <div>
      <div className="page-header">
        <h2>Camera Network</h2>
        <p>{cameras.length} cameras deployed across the border sector</p>
      </div>

      <div className="filters-bar">
        <select
          className="filter-select"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="all">All Cameras ({cameras.length})</option>
          <option value="online">Online ({cameras.filter(c => c.status === 'online').length})</option>
          <option value="offline">Offline ({cameras.filter(c => c.status === 'offline').length})</option>
        </select>
      </div>

      <div className="camera-grid">
        {filtered.map((cam) => (
          <CameraCard key={cam.id} camera={cam} />
        ))}
      </div>
    </div>
  );
}
