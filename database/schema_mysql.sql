-- MySQL schema (Render / Railway managed database)

CREATE TABLE IF NOT EXISTS States (
  state_id INT AUTO_INCREMENT PRIMARY KEY,
  state_name VARCHAR(128) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS Cities (
  city_id INT AUTO_INCREMENT PRIMARY KEY,
  city_name VARCHAR(128) NOT NULL,
  state_id INT NOT NULL,
  latitude DOUBLE NULL,
  longitude DOUBLE NULL,
  UNIQUE KEY uq_city_state (city_name, state_id),
  FOREIGN KEY (state_id) REFERENCES States(state_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS AQI_Data (
  id INT AUTO_INCREMENT PRIMARY KEY,
  city_id INT NOT NULL,
  `timestamp` DATETIME NOT NULL,
  pm25 DOUBLE NULL,
  pm10 DOUBLE NULL,
  no2 DOUBLE NULL,
  so2 DOUBLE NULL,
  co DOUBLE NULL,
  o3 DOUBLE NULL,
  aqi_value INT NULL,
  aqi_category VARCHAR(32) NULL,
  source VARCHAR(64) NULL,
  FOREIGN KEY (city_id) REFERENCES Cities(city_id),
  INDEX idx_aqi_city_time (city_id, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS Health_Impact (
  aqi_range VARCHAR(32) PRIMARY KEY,
  min_aqi INT NOT NULL,
  max_aqi INT NOT NULL,
  category VARCHAR(32) NOT NULL,
  health_effect TEXT NOT NULL,
  precautions TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
