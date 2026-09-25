import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Camera, FileText, Bell, Map, BarChart3, Shield, Activity, Radio
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../api/client';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/cameras', icon: Camera, label: 'Cameras' },
  { to: '/events', icon: FileText, label: 'Events Log' },
  { to: '/map', icon: Map, label: 'Map View' },
  { to: '/alerts', icon: Bell, label: 'Alerts', showBadge: true },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
];

export default function Navbar() {
  const [alertCount, setAlertCount] = useState(0);
  const [time, setTime] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    const updateStats = () => {
      api.getStats()
        .then((data) => setAlertCount(data.active_alerts || 0))
        .catch(() => {});
    };

    updateStats();
    const statsInterval = setInterval(updateStats, 10000);
    const clockInterval = setInterval(() => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }, 1000);

    return () => {
      clearInterval(statsInterval);
      clearInterval(clockInterval);
    };
  }, []);

  return (
    <header className="top-navbar">
      <div className="navbar-container">
        {/* Brand Logo & Sector Tag */}
        <div className="navbar-brand">
          <div className="brand-icon-wrapper">
            <Shield className="brand-icon" size={22} />
            <Radio className="brand-pulse-icon" size={12} />
          </div>
          <div className="brand-text">
            <div className="brand-title">
              BORDER<span>-AI</span>
            </div>
            <div className="brand-subtitle">MUMBAI SURVEILLANCE SECTOR</div>
          </div>
        </div>

        {/* Center Navigation Links */}
        <nav className="navbar-links">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-item-link${isActive ? ' active' : ''}`
              }
              end={item.to === '/'}
            >
              <item.icon className="nav-item-icon" size={18} />
              <span>{item.label}</span>
              {item.showBadge && alertCount > 0 && (
                <span className="nav-badge-count">{alertCount}</span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Right Status & Threat Level Indicator */}
        <div className="navbar-actions">
          <div className="threat-pill">
            <Activity size={14} className="threat-icon" />
            <span className="threat-label">THREAT LEVEL:</span>
            <span className="threat-value">ELEVATED</span>
          </div>

          <div className="system-status-chip">
            <span className="status-live-dot" />
            <span className="status-text">ONLINE</span>
            <span className="status-clock">{time}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
