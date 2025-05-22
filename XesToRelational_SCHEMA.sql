DROP TABLE IF EXISTS `log`;
CREATE TABLE `log` (
  `id` char(36) NOT NULL,
  `name` text DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `classifier`;
CREATE TABLE `classifier` (
  `id` char(36) NOT NULL,
  `name` varchar(45) DEFAULT NULL,
  `attr_keys` text DEFAULT NULL,
  `log_id` char(36) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `classifier_fk1` (`log_id`),
  CONSTRAINT `classifier_fk1` FOREIGN KEY (`log_id`) REFERENCES `log` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `trace`;
CREATE TABLE `trace` (
  `id` char(36) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `log_has_trace`;
CREATE TABLE `log_has_trace` (
  `log_id` char(36) NOT NULL,
  `trace_id` char(36) NOT NULL,
  `sequence` int(11) DEFAULT NULL,
  PRIMARY KEY (`log_id`,`trace_id`),
  KEY `log_has_trace_fk2` (`trace_id`),
  CONSTRAINT `log_has_trace_fk1` FOREIGN KEY (`log_id`) REFERENCES `log` (`id`),
  CONSTRAINT `log_has_trace_fk2` FOREIGN KEY (`trace_id`) REFERENCES `trace` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `event`;
CREATE TABLE `event` (
  `id` char(36) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `trace_has_event`;
CREATE TABLE `trace_has_event` (
  `trace_id` char(36) NOT NULL,
  `event_id` char(36) NOT NULL,
  `sequence` int(11) DEFAULT NULL,
  PRIMARY KEY (`trace_id`,`event_id`),
  KEY `trace_has_event_fk2` (`event_id`),
  CONSTRAINT `trace_has_event_fk1` FOREIGN KEY (`trace_id`) REFERENCES `trace` (`id`),
  CONSTRAINT `trace_has_event_fk2` FOREIGN KEY (`event_id`) REFERENCES `event` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `extension`;
CREATE TABLE `extension` (
  `id` char(36) NOT NULL,
  `name` varchar(45) DEFAULT NULL,
  `prefix` varchar(45) DEFAULT NULL,
  `uri` text DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `attribute`;
CREATE TABLE `attribute` (
  `id` char(36) NOT NULL,
  `attr_key` text NOT NULL,
  `attr_type` text DEFAULT NULL,
  `parent_id` char(36) DEFAULT NULL,
  `extension_id` char(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `attribute_fk1` (`extension_id`),
  CONSTRAINT `attribute_fk1` FOREIGN KEY (`extension_id`) REFERENCES `extension` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `log_has_attribute`;
CREATE TABLE `log_has_attribute` (
  `log_id` char(36) NOT NULL,
  `trace_global` tinyint(1) NOT NULL,
  `event_global` tinyint(1) NOT NULL,
  `attribute_id` char(36) NOT NULL,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`log_id`,`event_global`,`attribute_id`,`trace_global`),
  KEY `log_has_attribute_fk2` (`attribute_id`),
  CONSTRAINT `log_has_attribute_fk1` FOREIGN KEY (`log_id`) REFERENCES `log` (`id`),
  CONSTRAINT `log_has_attribute_fk2` FOREIGN KEY (`attribute_id`) REFERENCES `attribute` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `trace_has_attribute`;
CREATE TABLE `trace_has_attribute` (
  `trace_id` char(36) NOT NULL,
  `attribute_id` char(36) NOT NULL,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`trace_id`,`attribute_id`),
  KEY `trace_has_attribute_fk2` (`attribute_id`),
  CONSTRAINT `trace_has_attribute_fk1` FOREIGN KEY (`trace_id`) REFERENCES `trace` (`id`),
  CONSTRAINT `trace_has_attribute_fk2` FOREIGN KEY (`attribute_id`) REFERENCES `attribute` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

DROP TABLE IF EXISTS `event_has_attribute`;
CREATE TABLE `event_has_attribute` (
  `event_id` char(36) NOT NULL,
  `attribute_id` char(36) NOT NULL,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`event_id`,`attribute_id`),
  KEY `event_has_attribute_fk2` (`attribute_id`),
  CONSTRAINT `event_has_attribute_fk1` FOREIGN KEY (`event_id`) REFERENCES `event` (`id`),
  CONSTRAINT `event_has_attribute_fk2` FOREIGN KEY (`attribute_id`) REFERENCES `attribute` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
