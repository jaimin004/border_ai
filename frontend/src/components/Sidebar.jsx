import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Camera, FileText, Bell, Map, BarChart3, Shield
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../api/client';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/cameras', icon: Camera, label: 'Cameras' },
  { to: '/events', icon: FileText, label: 'Events Log' },
  { to: '/alerts', icon: Bell, label: 'Alerts', showBadge: true },
  { to: '/map', icon: Map, label: 'Map View' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
];

export default function Sidebar() {
  const location = useLocation();
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    api.getStats()
      .then((data) => setAlertCount(data.active_alerts || 0))
      .catch(() => {});
    const interval = setInterval(() => {
      api.getStats()
        .then((data) => setAlertCount(data.active_alerts || 0))
        .catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>BORDER-AI</h1>
        <p>Command Dashboard</p>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Operations</div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `nav-link${isActive ? ' active' : ''}`
            }
            end={item.to === '/'}
          >
            <item.icon className="nav-icon" />
            <span>{item.label}</span>
            {item.showBadge && alertCount > 0 && (
              <span className="nav-badge">{alertCount}</span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <p>
          <span className="status-dot" />
          System Online
        </p>
        <p style={{ marginTop: 4, fontSize: '0.68rem' }}>
          <Shield size={12} style={{ marginRight: 4, opacity: 0.5 }} />
          Operator Access
        </p>
      </div>
    </aside>
  );
}
