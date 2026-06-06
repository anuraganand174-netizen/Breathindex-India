-- SQLite / portable schema for AQI India project

CREATE TABLE IF NOT EXISTS States (
  state_id INTEGER PRIMARY KEY AUTOINCREMENT,
  state_name VARCHAR(128) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Cities (
  city_id INTEGER PRIMARY KEY AUTOINCREMENT,
  city_name VARCHAR(128) NOT NULL,
  state_id INTEGER NOT NULL,
  latitude REAL NULL,
  longitude REAL NULL,
  UNIQUE (city_name, state_id),
  FOREIGN KEY (state_id) REFERENCES States(state_id)
);

CREATE TABLE IF NOT EXISTS AQI_Data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  city_id INTEGER NOT NULL,
  "timestamp" DATETIME NOT NULL,
  pm25 REAL NULL,
  pm10 REAL NULL,
  no2 REAL NULL,
  so2 REAL NULL,
  co REAL NULL,
  o3 REAL NULL,
  aqi_value INTEGER NULL,
  aqi_category VARCHAR(32) NULL,
  source VARCHAR(64) NULL,
  FOREIGN KEY (city_id) REFERENCES Cities(city_id)
);

CREATE INDEX IF NOT EXISTS idx_aqi_city_time ON AQI_Data(city_id, "timestamp");

CREATE TABLE IF NOT EXISTS Health_Impact (
  aqi_range VARCHAR(32) PRIMARY KEY,
  min_aqi INTEGER NOT NULL,
  max_aqi INTEGER NOT NULL,
  category VARCHAR(32) NOT NULL,
  health_effect TEXT NOT NULL,
  precautions TEXT NOT NULL
);
