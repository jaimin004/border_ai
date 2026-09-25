-- =========================================================================
-- BORDER-AI — PostgreSQL Schema & Seed Data with New Threat Alerts
-- =========================================================================

-- ---------------------------------------------------------------------------
-- SCHEMA
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS cameras (
    id            VARCHAR(20) PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    location      VARCHAR(200),
    latitude      DOUBLE PRECISION,
    longitude     DOUBLE PRECISION,
    status        VARCHAR(20) DEFAULT 'online',   -- online | offline | maintenance
    stream_url    VARCHAR(300),
    zone_type     VARCHAR(50),                     -- sensitive_area | restricted_zone | checkpoint | perimeter | port_gate
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    id            VARCHAR(30) PRIMARY KEY,
    camera_id     VARCHAR(20) REFERENCES cameras(id),
    track_id      VARCHAR(30),
    object_class  VARCHAR(30),                     -- person | vehicle | motorcycle | abandoned_object
    event_type    VARCHAR(50),                     -- zone_intrusion | loitering | abandoned_object | anpr_read | face_match
    timestamp     TIMESTAMPTZ NOT NULL,
    risk_score    INTEGER DEFAULT 0,
    severity      VARCHAR(20),                     -- low | medium | high | critical
    breakdown     JSONB DEFAULT '[]',              -- [{factor, points}, ...]
    snapshot_path VARCHAR(300),
    face_match    JSONB DEFAULT '{"matched": false, "confidence": 0.0}',
    plate_text    VARCHAR(30),
    plate_confidence DOUBLE PRECISION,
    correlated_camera_ids TEXT[] DEFAULT '{}',
    synced        BOOLEAN DEFAULT TRUE,
    escalated     BOOLEAN DEFAULT FALSE,
    acknowledged  BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(50),
    acknowledged_at TIMESTAMPTZ,
    description   TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    role          VARCHAR(20) NOT NULL,            -- admin | operator | supervisor | auditor
    full_name     VARCHAR(100),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id),
    action        VARCHAR(50) NOT NULL,
    target_type   VARCHAR(30),
    target_id     VARCHAR(50),
    details       JSONB,
    ip_address    VARCHAR(45),
    timestamp     TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast dashboard queries
CREATE INDEX IF NOT EXISTS idx_events_severity   ON events(severity);
CREATE INDEX IF NOT EXISTS idx_events_camera     ON events(camera_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp  ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_escalated  ON events(escalated);

-- ---------------------------------------------------------------------------
-- SEED DATA — Cameras in Sensitive & Field Surveillance Zones
-- ---------------------------------------------------------------------------

INSERT INTO cameras (id, name, location, latitude, longitude, status, stream_url, zone_type) VALUES
('cam_01', 'Colaba Coastal Security Watch',  'Colaba Coastal Perimeter, Sector 1',       18.9180, 72.8310, 'online',  'rtsp://10.0.1.1:554/stream1', 'sensitive_area'),
('cam_02', 'Gateway Perimeter Guard',       'Gateway of India High Security Gate',      18.9220, 72.8347, 'online',  'rtsp://10.0.1.2:554/stream1', 'sensitive_area'),
('cam_03', 'Colaba Defense Station Watch',   'Colaba Defense & Naval Zone Perimeter',    18.9120, 72.8270, 'online',  'rtsp://10.0.1.3:554/stream1', 'sensitive_area'),
('cam_04', 'Marine Drive Promenade Watch',   'Marine Drive Sector 4 Plaza',              18.9438, 72.8232, 'online',  'rtsp://10.0.2.1:554/stream1', 'perimeter'),
('cam_05', 'Bandra Sea Link Toll Post',      'Bandra-Worli Sea Link Toll Gate',          19.0330, 72.8185, 'online',  'rtsp://10.0.3.1:554/stream1', 'checkpoint'),
('cam_06', 'Trombay High-Security Post',     'Trombay Restricted Perimeter Gate',        19.0200, 72.9150, 'online',  'rtsp://10.0.4.1:554/stream1', 'sensitive_area'),
('cam_07', 'JNPT Port Container Guard',      'JNPT Port Terminal Gate 1',                18.9500, 72.9500, 'offline', 'rtsp://10.0.5.1:554/stream1', 'port_gate'),
('cam_08', 'Versova Landing Patrol Post',    'Versova Coastal Patrol Station',           19.1350, 72.8120, 'online',  'rtsp://10.0.6.1:554/stream1', 'waterway')
ON CONFLICT (id) DO NOTHING;

-- Seed users
INSERT INTO users (username, role, full_name) VALUES
('admin',      'admin',      'System Administrator'),
('op_sharma',  'operator',   'Constable R. Sharma'),
('op_singh',   'operator',   'Constable P. Singh'),
('sup_verma',  'supervisor', 'Inspector A. Verma'),
('auditor_hq', 'auditor',    'HQ Audit Officer')
ON CONFLICT (username) DO NOTHING;

-- ---------------------------------------------------------------------------
-- NEW SEED THREAT ALERTS — Real-time Active Alerts across Sensitive Nodes
-- ---------------------------------------------------------------------------

INSERT INTO events (id, camera_id, track_id, object_class, event_type, timestamp, risk_score, severity, breakdown, snapshot_path, face_match, plate_text, plate_confidence, escalated, acknowledged, description) VALUES
-- Critical Alert 1: Night coastal intrusion at Colaba Sensitive Area
('evt_crit_01', 'cam_01', 'trk_1001', 'person', 'zone_intrusion',
 NOW() - INTERVAL '5 minutes', 92, 'critical',
 '[{"factor":"person_detected","points":5},{"factor":"restricted_zone_entry","points":30},{"factor":"loitering","points":20},{"factor":"movement_toward_boundary","points":22},{"factor":"multi_person_coordination","points":15}]',
 '/evidence/cam01_evt_crit_01.jpg',
 '{"matched": false, "confidence": 0.0}', NULL, NULL,
 TRUE, FALSE,
 'CRITICAL THREAT: Two unidentified individuals breached restricted fence line near Colaba Coastal Sensitive Area. Thermal sensors detected coordinated movement toward boundary.'),

-- Critical Alert 2: Unauthorized vehicle breach at Sea Link Checkpoint
('evt_crit_02', 'cam_05', 'trk_1002', 'vehicle', 'zone_intrusion',
 NOW() - INTERVAL '14 minutes', 89, 'critical',
 '[{"factor":"person_detected","points":5},{"factor":"restricted_zone_entry","points":30},{"factor":"loitering","points":20},{"factor":"anpr_hotlist_match","points":24},{"factor":"multi_person_coordination","points":10}]',
 '/evidence/cam05_evt_crit_02.jpg',
 '{"matched": false, "confidence": 0.0}', 'MH02EK9911', 94.6,
 TRUE, FALSE,
 'CRITICAL THREAT: Black SUV plate MH02EK9911 bypassed Bandra Sea Link toll barrier without stopping. Vehicle matched security hotlist.'),

-- High Alert 1: Watchlist Face Match at Gateway Sensitive Perimeter
('evt_high_01', 'cam_02', 'trk_1003', 'person', 'face_match',
 NOW() - INTERVAL '22 minutes', 78, 'high',
 '[{"factor":"person_detected","points":5},{"factor":"restricted_zone_entry","points":30},{"factor":"watchlist_face_match","points":25},{"factor":"loitering","points":18}]',
 '/evidence/cam02_evt_high_01.jpg',
 '{"matched": true, "confidence": 0.86, "name": "Ravi Kumar"}', NULL, NULL,
 TRUE, FALSE,
 'HIGH ALERT: Facial recognition matched suspect "Ravi Kumar" (86% confidence) near Gateway of India High Security Gate.'),

-- High Alert 2: Abandoned Package at Trombay Restricted Perimeter
('evt_high_02', 'cam_06', 'trk_1004', 'abandoned_object', 'abandoned_object',
 NOW() - INTERVAL '31 minutes', 72, 'high',
 '[{"factor":"abandoned_object","points":35},{"factor":"restricted_zone_entry","points":25},{"factor":"loitering","points":12}]',
 '/evidence/cam06_evt_high_02.jpg',
 '{"matched": false, "confidence": 0.0}', NULL, NULL,
 TRUE, FALSE,
 'HIGH ALERT: Unattended backpack detected near Trombay Restricted Perimeter Gate. Object has remained stationary for >240 seconds.'),

-- Medium Alert 1: Loitering near Colaba Defense Station
('evt_med_01', 'cam_03', 'trk_1005', 'person', 'loitering',
 NOW() - INTERVAL '48 minutes', 52, 'medium',
 '[{"factor":"person_detected","points":5},{"factor":"loitering","points":25},{"factor":"movement_toward_boundary","points":22}]',
 '/evidence/cam03_evt_med_01.jpg',
 '{"matched": false, "confidence": 0.0}', NULL, NULL,
 TRUE, TRUE,
 'MEDIUM ALERT: Individual observed loitering near Colaba Defense & Naval Zone Perimeter for >180 seconds.'),

-- Medium Alert 2: ANPR Read at Versova Patrol Station
('evt_med_02', 'cam_08', 'trk_1006', 'vehicle', 'anpr_read',
 NOW() - INTERVAL '1 hour', 48, 'medium',
 '[{"factor":"person_detected","points":5},{"factor":"restricted_zone_entry","points":25},{"factor":"anpr_flagged","points":18}]',
 '/evidence/cam08_evt_med_02.jpg',
 '{"matched": false, "confidence": 0.0}', 'MH04AB3344', 92.1,
 TRUE, TRUE,
 'MEDIUM ALERT: Commercial van plate MH04AB3344 passed Versova Coastal Patrol Station. Flagged for routine verification.'),

-- Low Event 1: Normal Pedestrian Transit
('evt_low_01', 'cam_04', 'trk_1007', 'person', 'zone_intrusion',
 NOW() - INTERVAL '2 hours', 10, 'low',
 '[{"factor":"person_detected","points":5},{"factor":"normal_movement","points":5}]',
 '/evidence/cam04_evt_low_01.jpg',
 '{"matched": false, "confidence": 0.0}', NULL, NULL,
 FALSE, FALSE,
 'Pedestrian walking along Marine Drive Promenade. Normal transit pattern.'),

-- Low Event 2: Vehicle Pass-Through
('evt_low_02', 'cam_05', 'trk_1008', 'vehicle', 'anpr_read',
 NOW() - INTERVAL '3 hours', 5, 'low',
 '[{"factor":"person_detected","points":5}]',
 '/evidence/cam05_evt_low_02.jpg',
 '{"matched": false, "confidence": 0.0}', 'MH01CD1234', 97.4,
 FALSE, FALSE,
 'Authorized patrol car MH01CD1234 transited Sea Link toll plaza.'),

-- =========================================================================
-- NEW THREAT ALERTS — Additional Diverse Scenarios
-- =========================================================================

-- Critical Alert 3: Drone intrusion over Trombay Restricted Zone
('evt_crit_03', 'cam_06', 'trk_2001', 'person', 'zone_intrusion',
 NOW() - INTERVAL '8 minutes', 95, 'critical',
 '[{"factor":"drone_detected","points":35},{"factor":"restricted_airspace","points":30},{"factor":"coordinated_activity","points":20},{"factor":"night_operation","points":10}]',
 '/evidence/cam06_evt_crit_03.jpg',
 '{"matched": false, "confidence": 0.0}', NULL, NULL,
 TRUE, FALSE,
 'CRITICAL THREAT: Unmanned aerial vehicle (drone) detected flying over Trombay Restricted Perimeter at low altitude. Possible surveillance or payload delivery attempt.'),

-- Critical Alert 4: Coordinated breach at Colaba Coastal Perimeter
('evt_crit_04', 'cam_01', 'trk_2002', 'person', 'zone_intrusion',
 NOW() - INTERVAL '3 minutes', 97, 'critical',
 '[{"factor":"multiple_persons","points":25},{"factor":"restricted_zone_entry","points":30},{"factor":"coordinated_movement","points":25},{"factor":"fence_breach","points":17}]',
 '/evidence/cam01_evt_crit_04.jpg',
 '{"matched": false, "confidence": 0.0}', NULL, NULL,
 TRUE, FALSE,
 'CRITICAL THREAT: Three individuals detected breaching perimeter fence simultaneously at Colaba Coastal Sensitive Area. Coordinated entry pattern suggests planned intrusion.'),

-- High Alert 3: Suspicious vessel near Versova Landing
('evt_high_03', 'cam_08', 'trk_2003', 'vehicle', 'zone_intrusion',
 NOW() - INTERVAL '18 minutes', 74, 'high',
 '[{"factor":"unregistered_vessel","points":30},{"factor":"approach_pattern","points":20},{"factor":"night_movement","points":15},{"factor":"no_ais_signal","points":9}]',
 '/evidence/cam08_evt_high_03.jpg',
 '{"matched": false, "confidence": 0.0}', NULL, NULL,
 TRUE, FALSE,
 'HIGH ALERT: Unregistered fishing vessel approaching Versova Coastal Patrol Station from the southwest. No AIS transponder signal. Vessel speed and approach angle consistent with smuggling pattern.'),

-- High Alert 4: Tailgating at Bandra Sea Link Checkpoint
('evt_high_04', 'cam_05', 'trk_2004', 'vehicle', 'zone_intrusion',
 NOW() - INTERVAL '10 minutes', 70, 'high',
 '[{"factor":"tailgating_detected","points":25},{"factor":"checkpoint_violation","points":25},{"factor":"high_speed_approach","points":15},{"factor":"evasion_behavior","points":5}]',
 '/evidence/cam05_evt_high_04.jpg',
 '{"matched": false, "confidence": 0.0}', 'MH01ZZ7890', 89.3,
 TRUE, FALSE,
 'HIGH ALERT: White sedan (plate MH01ZZ7890) tailgated through Bandra Sea Link toll barrier behind authorized vehicle. Possible evasion attempt.'),

-- Medium Alert 3: Face match at JNPT Port Gate
('evt_med_03', 'cam_07', 'trk_2005', 'person', 'face_match',
 NOW() - INTERVAL '35 minutes', 58, 'medium',
 '[{"factor":"person_detected","points":5},{"factor":"face_partial_match","points":28},{"factor":"restricted_area_proximity","points":20},{"factor":"loitering","points":5}]',
 '/evidence/cam07_evt_med_03.jpg',
 '{"matched": true, "confidence": 0.71, "name": "Ashok Deshmukh"}', NULL, NULL,
 TRUE, FALSE,
 'MEDIUM ALERT: Partial facial match (71% confidence) for "Ashok Deshmukh" near JNPT Port Terminal Gate 1. Individual observed photographing container yard layout.'),

-- Medium Alert 4: Night thermal movement at Gateway Perimeter
('evt_med_04', 'cam_02', 'trk_2006', 'person', 'loitering',
 NOW() - INTERVAL '42 minutes', 55, 'medium',
 '[{"factor":"thermal_signature","points":20},{"factor":"loitering","points":18},{"factor":"night_activity","points":12},{"factor":"perimeter_proximity","points":5}]',
 '/evidence/cam02_evt_med_04.jpg',
 '{"matched": false, "confidence": 0.0}', NULL, NULL,
 TRUE, FALSE,
 'MEDIUM ALERT: Thermal imaging detected individual near Gateway of India High Security Gate during restricted hours. Subject has been stationary for >300 seconds, exhibiting reconnaissance behavior.')
ON CONFLICT (id) DO NOTHING;
