CREATE TABLE IF NOT EXISTS sms_message (
  id VARCHAR(96) NOT NULL,
  source VARCHAR(64) NOT NULL DEFAULT '',
  event VARCHAR(128) NOT NULL DEFAULT '',
  sender VARCHAR(128) NOT NULL DEFAULT '',
  recipient VARCHAR(128) NOT NULL DEFAULT '',
  device_id VARCHAR(128) NOT NULL DEFAULT '',
  sim_number VARCHAR(32) NOT NULL DEFAULT '',
  message TEXT NOT NULL,
  code VARCHAR(16) NOT NULL DEFAULT '',
  received_at VARCHAR(64) NOT NULL DEFAULT '',
  created_at VARCHAR(64) NOT NULL DEFAULT '',
  raw_json JSON NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_received_at (received_at),
  KEY idx_sender (sender),
  KEY idx_recipient (recipient),
  KEY idx_device_sim (device_id, sim_number),
  KEY idx_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_card (
  card VARCHAR(128) NOT NULL,
  phone_id VARCHAR(64) NOT NULL DEFAULT '',
  country_code VARCHAR(16) NOT NULL DEFAULT '+86',
  phone_number VARCHAR(32) NOT NULL DEFAULT '',
  expires_at VARCHAR(64) NOT NULL DEFAULT '',
  receive_limit INT NOT NULL DEFAULT 2,
  used_count INT NOT NULL DEFAULT 0,
  wait_seconds INT NOT NULL DEFAULT 60,
  service_name VARCHAR(128) NOT NULL DEFAULT '腾讯视频APP',
  keywords_json JSON NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (card),
  KEY idx_phone_id (phone_id),
  KEY idx_phone_number (phone_number),
  KEY idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS phone_pool (
  id VARCHAR(64) NOT NULL,
  country_code VARCHAR(16) NOT NULL DEFAULT '+86',
  phone_number VARCHAR(32) NOT NULL DEFAULT '',
  device_id VARCHAR(128) NOT NULL DEFAULT '',
  sim_number VARCHAR(32) NOT NULL DEFAULT '',
  label VARCHAR(128) NOT NULL DEFAULT '',
  provider VARCHAR(128) NOT NULL DEFAULT '',
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  note TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_phone_number (phone_number),
  KEY idx_device_sim (device_id, sim_number),
  KEY idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS card_message_claim (
  message_id VARCHAR(96) NOT NULL,
  card VARCHAR(128) NOT NULL,
  claimed_at VARCHAR(64) NOT NULL DEFAULT '',
  PRIMARY KEY (message_id),
  KEY idx_card (card),
  KEY idx_claimed_at (claimed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS xgj_order (
  order_no VARCHAR(128) NOT NULL,
  out_order_no VARCHAR(128) NOT NULL DEFAULT '',
  order_type INT NOT NULL DEFAULT 2,
  goods_no VARCHAR(128) NOT NULL DEFAULT '',
  goods_name VARCHAR(255) NOT NULL DEFAULT '',
  buy_quantity INT NOT NULL DEFAULT 1,
  order_status INT NOT NULL DEFAULT 20,
  order_amount BIGINT NOT NULL DEFAULT 0,
  order_time INT NOT NULL DEFAULT 0,
  end_time INT NOT NULL DEFAULT 0,
  card_items_json JSON NULL,
  request_json JSON NULL,
  remark TEXT NULL,
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (order_no),
  UNIQUE KEY uk_out_order_no (out_order_no),
  KEY idx_goods_no (goods_no),
  KEY idx_order_status (order_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS xgj_goods (
  goods_no VARCHAR(128) NOT NULL,
  goods_name VARCHAR(255) NOT NULL DEFAULT '',
  delivery_mode VARCHAR(32) NOT NULL DEFAULT 'stock_code',
  price BIGINT NOT NULL DEFAULT 0,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  note TEXT NULL,
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (goods_no),
  KEY idx_delivery_mode (delivery_mode),
  KEY idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS xgj_stock_item (
  id VARCHAR(64) NOT NULL,
  goods_no VARCHAR(128) NOT NULL,
  card_no VARCHAR(255) NOT NULL DEFAULT '',
  card_pwd TEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'available',
  order_no VARCHAR(128) NOT NULL DEFAULT '',
  sold_at VARCHAR(64) NOT NULL DEFAULT '',
  note TEXT NULL,
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_goods_status (goods_no, status),
  KEY idx_order_no (order_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_profile (
  id VARCHAR(64) NOT NULL,
  name VARCHAR(128) NOT NULL DEFAULT '',
  contact VARCHAR(128) NOT NULL DEFAULT '',
  rate_percent INT NOT NULL DEFAULT 0,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  note TEXT NULL,
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_enabled (enabled),
  KEY idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
