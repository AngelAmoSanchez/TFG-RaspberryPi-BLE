-- Schema de base de datos SQLite

-- Tabla de deteccionees
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_hash TEXT NOT NULL,
    rssi INTEGER NOT NULL,
    zone TEXT NOT NULL CHECK(zone IN ('near', 'medium', 'far')),
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_timestamp ON detections(timestamp);
CREATE INDEX IF NOT EXISTS idx_device_hash ON detections(device_hash);
CREATE INDEX IF NOT EXISTS idx_zone ON detections(zone);
CREATE INDEX IF NOT EXISTS idx_device_time ON detections(device_hash, timestamp);

-- Tabla de configuración
CREATE TABLE IF NOT EXISTS configuration (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Valores por defecto
INSERT OR IGNORE INTO configuration (key, value, description) VALUES 
    ('rssi_near_threshold', '-50', 'RSSI threshold for near zone (dBm)'),
    ('rssi_medium_threshold', '-70', 'RSSI threshold for medium zone (dBm)'),
    ('min_permanence_minutes', '2', 'Minimum permanence time in minutes'),
    ('scan_duration', '10', 'BLE scan duration in seconds'),
    ('scan_interval', '30', 'Interval between scans in seconds');
