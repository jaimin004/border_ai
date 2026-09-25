import { useState, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polygon, Circle, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Camera, AlertTriangle, Shield, MapPin, Eye, Zap, AlertCircle, Key, Maximize2, Minimize2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// =========================================================================
// CARTO API KEY CONFIGURATION
// =========================================================================
const CARTO_API_KEY = 'cb1_2ysw_1_aa15f0a82fa2d749f78199ae';

// Default Fallback Surveillance Cameras (Guarantees camera points are visible even if API loading/offline)
const DEFAULT_SECTOR_CAMERAS = [
  { id: 'cam_01', name: 'Colaba Coastal Security Watch', location: 'Colaba Coastal Perimeter, Sector 1', latitude: 18.9180, longitude: 72.8310, status: 'online', active_alerts: 1, zone_type: 'sensitive_area' },
  { id: 'cam_02', name: 'Gateway Perimeter Guard', location: 'Gateway of India High Security Gate', latitude: 18.9220, longitude: 72.8347, status: 'online', active_alerts: 2, zone_type: 'sensitive_area' },
  { id: 'cam_03', name: 'Colaba Defense Station Watch', location: 'Colaba Defense & Naval Zone Perimeter', latitude: 18.9120, longitude: 72.8270, status: 'online', active_alerts: 1, zone_type: 'sensitive_area' },
  { id: 'cam_04', name: 'Marine Drive Promenade Watch', location: 'Marine Drive Sector 4 Plaza', latitude: 18.9438, longitude: 72.8232, status: 'online', active_alerts: 0, zone_type: 'perimeter' },
  { id: 'cam_05', name: 'Bandra Sea Link Toll Post', location: 'Bandra-Worli Sea Link Toll Gate', latitude: 19.0330, longitude: 72.8185, status: 'online', active_alerts: 1, zone_type: 'checkpoint' },
  { id: 'cam_06', name: 'Trombay High-Security Post', location: 'Trombay Restricted Perimeter Gate', latitude: 19.0200, longitude: 72.9150, status: 'online', active_alerts: 1, zone_type: 'sensitive_area' },
  { id: 'cam_07', name: 'JNPT Port Container Guard', location: 'JNPT Port Terminal Gate 1', latitude: 18.9500, longitude: 72.9500, status: 'offline', active_alerts: 0, zone_type: 'port_gate' },
  { id: 'cam_08', name: 'Versova Landing Patrol Post', location: 'Versova Coastal Patrol Station', latitude: 19.1350, longitude: 72.8120, status: 'online', active_alerts: 1, zone_type: 'waterway' },
];

// Custom Leaflet Marker Icon Generator using L.divIcon
function createCustomMarkerIcon(status, activeAlerts = 0, isHovered = false) {
  const hasAlert = activeAlerts > 0;
  const isOffline = status === 'offline';
  
  let borderColor = '#22d3ee'; // cyan default
  let bgColor = 'rgba(34, 211, 238, 0.35)';
  let glowColor = 'rgba(34, 211, 238, 0.7)';
  let pulseClass = 'marker-pulse-normal';

  if (hasAlert) {
    borderColor = '#ef4444'; // red
    bgColor = 'rgba(239, 68, 68, 0.45)';
    glowColor = 'rgba(239, 68, 68, 0.9)';
    pulseClass = 'marker-pulse-alert';
  } else if (isOffline) {
    borderColor = '#94a3b8'; // slate
    bgColor = 'rgba(100, 116, 139, 0.3)';
    glowColor = 'none';
    pulseClass = '';
  }

  const size = isHovered ? 36 : 30;

  const html = `
    <div class="custom-map-marker ${pulseClass}" style="
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      background: ${bgColor};
      border: 2px solid ${borderColor};
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 16px ${glowColor};
      transition: all 0.2s ease-in-out;
      cursor: pointer;
      position: relative;
    ">
      <div style="
        width: ${isHovered ? '12px' : '10px'};
        height: ${isHovered ? '12px' : '10px'};
        border-radius: 50%;
        background: ${borderColor};
      "></div>
      ${hasAlert ? `<div class="alert-count-badge">${activeAlerts}</div>` : ''}
    </div>
  `;

  return L.divIcon({
    html: html,
    className: 'leaflet-custom-div-icon',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -18],
  });
}

export default function MapView({ cameras = [], onCameraClick, compact = false, onFullViewClick }) {
  const [hoveredCamId, setHoveredCamId] = useState(null);
  const [filter, setFilter] = useState('all'); // all | alerts | online | sensitive
  const [isFullscreen, setIsFullscreen] = useState(false);
  const navigate = useNavigate();

  // Use provided cameras or fallback to sector cameras if empty
  const activeCameras = useMemo(() => {
    return cameras && cameras.length > 0 ? cameras : DEFAULT_SECTOR_CAMERAS;
  }, [cameras]);

  // Dynamically calculate map center lat/lng from camera coordinates
  const mapCenter = useMemo(() => {
    if (activeCameras.length === 0) return [18.9800, 72.8500];
    const avgLat = activeCameras.reduce((sum, c) => sum + c.latitude, 0) / activeCameras.length;
    const avgLng = activeCameras.reduce((sum, c) => sum + c.longitude, 0) / activeCameras.length;
    return [avgLat, avgLng];
  }, [activeCameras]);

  // Filter cameras based on sensitive_area / restricted_zone types
  const sensitiveCameras = useMemo(() => {
    return activeCameras.filter(c => 
      c.zone_type === 'sensitive_area' || 
      c.zone_type === 'restricted_zone'
    );
  }, [activeCameras]);

  // Dynamically calculate sensitive perimeter polygon boundary around sensitive camera points
  // with an expanded buffer zone to create a visible "around the map" effect
  const sensitivePolygonCoords = useMemo(() => {
    if (sensitiveCameras.length >= 3) {
      const centerLat = sensitiveCameras.reduce((sum, c) => sum + c.latitude, 0) / sensitiveCameras.length;
      const centerLng = sensitiveCameras.reduce((sum, c) => sum + c.longitude, 0) / sensitiveCameras.length;
      
      // Sort sensitive camera points radially to construct clean boundary polygon
      const sorted = [...sensitiveCameras].sort((a, b) => {
        const angleA = Math.atan2(a.latitude - centerLat, a.longitude - centerLng);
        const angleB = Math.atan2(b.latitude - centerLat, b.longitude - centerLng);
        return angleA - angleB;
      });

      // Expand each point outward from center by a buffer offset (~800m)
      const BUFFER = 0.008;
      return sorted.map(c => {
        const angle = Math.atan2(c.latitude - centerLat, c.longitude - centerLng);
        return [
          c.latitude + Math.sin(angle) * BUFFER,
          c.longitude + Math.cos(angle) * BUFFER,
        ];
      });
    }
    return [];
  }, [sensitiveCameras]);

  // Outer warning boundary — even larger perimeter for "around the map" marking
  const outerBoundaryCoords = useMemo(() => {
    if (sensitiveCameras.length >= 3) {
      const centerLat = sensitiveCameras.reduce((sum, c) => sum + c.latitude, 0) / sensitiveCameras.length;
      const centerLng = sensitiveCameras.reduce((sum, c) => sum + c.longitude, 0) / sensitiveCameras.length;
      
      const sorted = [...sensitiveCameras].sort((a, b) => {
        const angleA = Math.atan2(a.latitude - centerLat, a.longitude - centerLng);
        const angleB = Math.atan2(b.latitude - centerLat, b.longitude - centerLng);
        return angleA - angleB;
      });

      const OUTER_BUFFER = 0.016; // ~1.6km expanded outer ring
      return sorted.map(c => {
        const angle = Math.atan2(c.latitude - centerLat, c.longitude - centerLng);
        return [
          c.latitude + Math.sin(angle) * OUTER_BUFFER,
          c.longitude + Math.cos(angle) * OUTER_BUFFER,
        ];
      });
    }
    return [];
  }, [sensitiveCameras]);

  // Filter cameras based on active selection filter pill
  const filteredCameras = useMemo(() => {
    return activeCameras.filter(cam => {
      if (filter === 'alerts') return (cam.active_alerts || 0) > 0;
      if (filter === 'online') return cam.status === 'online';
      if (filter === 'sensitive') return cam.zone_type === 'sensitive_area' || cam.zone_type === 'restricted_zone';
      return true;
    });
  }, [activeCameras, filter]);

  // CARTO Tile URL with exact API Key parameter
  const cartoTileUrl = useMemo(() => {
    return `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${CARTO_API_KEY}`;
  }, []);

  // Handle Full View Action
  const handleFullView = () => {
    if (onFullViewClick) {
      onFullViewClick();
    } else if (compact) {
      navigate('/map');
    } else {
      setIsFullscreen(!isFullscreen);
    }
  };

  // Map height: compact square box mode (300px) vs full view (540px / fullscreen)
  const mapHeight = isFullscreen ? 'calc(100vh - 120px)' : (compact ? '300px' : '540px');

  // Statistics
  const totalCams = activeCameras.length;
  const alertCams = activeCameras.filter(c => (c.active_alerts || 0) > 0).length;
  const sensitiveCount = sensitiveCameras.length;

  return (
    <div className={`map-wrapper-card ${compact ? 'compact-square-box' : ''} ${isFullscreen ? 'map-fullscreen-overlay' : ''}`}>
      {/* Map Control Bar Overlay */}
      <div className="map-toolbar">
        <div className="map-title-section">
          <div className="map-badge">
            <Zap size={14} className="pulse-icon" />
            <span>FIELD SURVEILLANCE SECTOR</span>
          </div>
          <h3 className="map-heading">{compact ? 'Live Surveillance Map' : 'Sector Surveillance & Field Sensitive Perimeter'}</h3>
        </div>

        {/* Action Controls & Filter Pills */}
        <div className="map-filter-group" style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {!compact && (
            <>
              <button
                className={`map-filter-btn ${filter === 'all' ? 'active' : ''}`}
                onClick={() => setFilter('all')}
              >
                All ({totalCams})
              </button>
              <button
                className={`map-filter-btn sensitive-pill ${filter === 'sensitive' ? 'active' : ''}`}
                onClick={() => setFilter('sensitive')}
              >
                <Shield size={12} style={{ marginRight: 4 }} />
                Sensitive ({sensitiveCount})
              </button>
              <button
                className={`map-filter-btn alert-pill ${filter === 'alerts' ? 'active' : ''}`}
                onClick={() => setFilter('alerts')}
              >
                <AlertTriangle size={12} style={{ marginRight: 4 }} />
                Threats ({alertCams})
              </button>
            </>
          )}

          {/* Full View Button */}
          <button
            className="map-filter-btn full-view-btn"
            onClick={handleFullView}
            title={isFullscreen ? 'Exit Fullscreen' : 'Open Full Map View'}
            style={{
              background: 'var(--accent-cyan-dim)',
              borderColor: 'var(--accent-cyan)',
              color: 'var(--accent-cyan)',
              fontWeight: 600,
              padding: compact ? '4px 10px' : '6px 14px',
            }}
          >
            {isFullscreen ? <Minimize2 size={13} style={{ marginRight: 4 }} /> : <Maximize2 size={13} style={{ marginRight: 4 }} />}
            <span>{isFullscreen ? 'Exit' : 'Full View'}</span>
          </button>
        </div>
      </div>

      {/* Main Interactive Leaflet Map Container */}
      <div className="leaflet-map-container" style={{ height: mapHeight, transition: 'height 0.3s ease' }}>
        <MapContainer
          center={mapCenter}
          zoom={compact ? 11 : 12}
          scrollWheelZoom={true}
          style={{ width: '100%', height: '100%', borderRadius: '12px' }}
        >
          {/* CARTO Basemap with API Key */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url={cartoTileUrl}
            maxZoom={19}
            subdomains="abcd"
          />

          {/* Outer Warning Boundary — larger amber perimeter "around the map" */}
          {outerBoundaryCoords.length >= 3 && (
            <Polygon
              positions={outerBoundaryCoords}
              pathOptions={{
                color: '#f59e0b',
                fillColor: '#f59e0b',
                fillOpacity: 0.08,
                weight: 1.5,
                dashArray: '12, 8',
              }}
            >
              <Tooltip permanent direction="top" className="sensitive-zone-label" offset={[0, -30]}>
                <div className="outer-boundary-tag">
                  <Shield size={11} />
                  <span>RESTRICTED PERIMETER ZONE</span>
                </div>
              </Tooltip>
            </Polygon>
          )}

          {/* Inner Sensitive Zone Polygon Wrapping Sensitive Camera Locations */}
          {sensitivePolygonCoords.length >= 3 && (
            <Polygon
              positions={sensitivePolygonCoords}
              pathOptions={{
                color: '#ef4444',
                fillColor: '#ef4444',
                fillOpacity: 0.18,
                weight: 2.5,
                dashArray: '8, 6',
              }}
            >
              <Tooltip permanent direction="center" className="sensitive-zone-label">
                <div className="sensitive-tag">
                  <AlertCircle size={12} />
                  <span>SENSITIVE SURVEILLANCE ZONE</span>
                </div>
              </Tooltip>
            </Polygon>
          )}

          {/* Individual Sensitive Zone Radius around each sensitive camera */}
          {sensitiveCameras.map((cam) => (
            <Circle
              key={`zone-${cam.id}`}
              center={[cam.latitude, cam.longitude]}
              radius={500}
              pathOptions={{
                color: '#f59e0b',
                fillColor: '#f59e0b',
                fillOpacity: 0.1,
                weight: 1,
                dashArray: '6, 4',
              }}
            />
          ))}

          {/* Render Camera Markers on the Map */}
          {filteredCameras.map((cam) => {
            if (!cam.latitude || !cam.longitude) return null;
            const hasAlert = (cam.active_alerts || 0) > 0;
            const isHovered = hoveredCamId === cam.id;
            const isSensitive = cam.zone_type === 'sensitive_area' || cam.zone_type === 'restricted_zone';
            const markerIcon = createCustomMarkerIcon(cam.status, cam.active_alerts || 0, isHovered);

            return (
              <div key={cam.id}>
                {/* Visual Alert / Sensitive Perimeter Circle */}
                {(hasAlert || isSensitive) && (
                  <Circle
                    center={[cam.latitude, cam.longitude]}
                    radius={isSensitive ? 350 : 200}
                    pathOptions={{
                      color: hasAlert ? '#ef4444' : '#f59e0b',
                      fillColor: hasAlert ? '#ef4444' : '#f59e0b',
                      fillOpacity: 0.15,
                      weight: 1.5,
                      dashArray: '4, 4',
                    }}
                  />
                )}

                <Marker
                  position={[cam.latitude, cam.longitude]}
                  icon={markerIcon}
                  eventHandlers={{
                    mouseover: () => setHoveredCamId(cam.id),
                    mouseout: () => setHoveredCamId(null),
                  }}
                >
                  {/* ON HOVER TOOLTIP DISPLAYING CAMERA NUMBER & NAME DETAILS */}
                  <Tooltip
                    direction="top"
                    offset={[0, -22]}
                    opacity={1}
                    sticky={true}
                    className="hover-cam-tooltip"
                  >
                    <div className="hover-tooltip-card">
                      <div className="tooltip-cam-header">
                        <span className="tooltip-cam-number">{cam.id.toUpperCase()}</span>
                        <span className={`status-dot-mini ${cam.status}`} />
                      </div>
                      <div className="tooltip-cam-name">{cam.name}</div>
                      <div className="tooltip-cam-location">{cam.location}</div>
                      {isSensitive && (
                        <div style={{ fontSize: '0.66rem', color: '#f59e0b', fontWeight: 700, marginTop: 2 }}>
                          🛡 Sensitive Field Area
                        </div>
                      )}
                      {hasAlert && (
                        <div className="tooltip-alert-flag">
                          <AlertTriangle size={11} /> {cam.active_alerts} Active Threat{cam.active_alerts > 1 ? 's' : ''}
                        </div>
                      )}
                    </div>
                  </Tooltip>

                  {/* ON CLICK POPUP WITH FULL TELEMETRY */}
                  <Popup className="tactical-popup">
                    <div className="popup-card">
                      <div className="popup-header">
                        <div className="popup-title-area">
                          <Camera size={16} className="popup-icon" />
                          <h4 className="popup-title">{cam.name}</h4>
                        </div>
                        <span className={`status-badge-sm ${cam.status}`}>
                          {cam.status.toUpperCase()}
                        </span>
                      </div>

                      <div className="popup-body">
                        <div className="popup-detail-row">
                          <span className="detail-label">Camera Number:</span>
                          <strong className="detail-value mono">{cam.id.toUpperCase()}</strong>
                        </div>
                        <div className="popup-detail-row">
                          <MapPin size={13} className="detail-icon" />
                          <span>{cam.location}</span>
                        </div>
                        <div className="popup-detail-row">
                          <Shield size={13} className="detail-icon" />
                          <span>Zone Type: <strong style={{ textTransform: 'capitalize' }}>{cam.zone_type?.replace('_', ' ')}</strong></span>
                        </div>
                        <div className="popup-detail-row">
                          <AlertTriangle size={13} className="detail-icon" />
                          <span>Active Threats: <strong className={hasAlert ? 'text-red' : 'text-emerald'}>{cam.active_alerts || 0}</strong></span>
                        </div>
                        <div className="popup-coordinates">
                          LAT: {cam.latitude.toFixed(4)} N | LNG: {cam.longitude.toFixed(4)} E
                        </div>
                      </div>

                      <div className="popup-footer">
                        <button
                          className="popup-action-btn"
                          onClick={() => onCameraClick?.(cam)}
                        >
                          <Eye size={14} />
                          <span>Inspect Node Feed</span>
                        </button>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              </div>
            );
          })}
        </MapContainer>
      </div>

      {/* Map Legend Overlay */}
      <div className="map-legend-bar">
        <div className="legend-item">
          <span className="legend-dot dot-normal" />
          <span>Camera Node</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot dot-alert" />
          <span>Active Threat</span>
        </div>
        <div className="legend-item">
          <span className="legend-box box-sensitive" />
          <span>Sensitive Field Area</span>
        </div>
        <div className="legend-item legend-info">
          <Key size={12} style={{ marginRight: 4 }} />
          <span>CARTO Basemap</span>
        </div>
      </div>
    </div>
  );
}
