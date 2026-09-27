
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '';

--
-- Table structure for table `admin_tokens`
--

DROP TABLE IF EXISTS `admin_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin_tokens` (
  `token_id` int NOT NULL AUTO_INCREMENT,
  `admin_id` int NOT NULL,
  `token` varchar(64) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`token_id`),
  UNIQUE KEY `token` (`token`),
  KEY `fk_tokens_admins` (`admin_id`),
  CONSTRAINT `fk_tokens_admins` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `admins`
--

DROP TABLE IF EXISTS `admins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admins` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `email` varchar(150) NOT NULL,
  `password` text,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `data_loads`
--

DROP TABLE IF EXISTS `data_loads`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `data_loads` (
  `load_id` int NOT NULL AUTO_INCREMENT,
  `data_source` varchar(50) NOT NULL,
  `file_name` varchar(255) DEFAULT NULL,
  `load_date` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `loaded_by` varchar(50) NOT NULL,
  `processed_records` int DEFAULT '0',
  `load_status` varchar(20) DEFAULT 'PENDING',
  PRIMARY KEY (`load_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `donation_assignments`
--

DROP TABLE IF EXISTS `donation_assignments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `donation_assignments` (
  `assignment_id` int NOT NULL AUTO_INCREMENT,
  `request_id` int NOT NULL,
  `equipment_id` int NOT NULL,
  `delivery_date` date NOT NULL,
  `donation_deed_ref` varchar(100) NOT NULL,
  `estimated_beneficiaries_impact` int DEFAULT '0',
  PRIMARY KEY (`assignment_id`),
  UNIQUE KEY `equipment_id` (`equipment_id`),
  KEY `fk_assignments_requests` (`request_id`),
  CONSTRAINT `fk_assignments_equipments` FOREIGN KEY (`equipment_id`) REFERENCES `equipments` (`equipment_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_assignments_requests` FOREIGN KEY (`request_id`) REFERENCES `donation_requests` (`request_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `donation_requests`
--

DROP TABLE IF EXISTS `donation_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `donation_requests` (
  `request_id` int NOT NULL AUTO_INCREMENT,
  `entity_id` int NOT NULL,
  `request_type` varchar(30) NOT NULL,
  `request_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `requested_quantity` int NOT NULL,
  `need_description` text NOT NULL,
  `request_status` varchar(30) DEFAULT 'ON_HOLD',
  PRIMARY KEY (`request_id`),
  KEY `fk_requests_entities` (`entity_id`),
  CONSTRAINT `fk_requests_entities` FOREIGN KEY (`entity_id`) REFERENCES `entities` (`entity_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `entities`
--

DROP TABLE IF EXISTS `entities`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `entities` (
  `entity_id` int NOT NULL AUTO_INCREMENT,
  `tax_id` varchar(20) NOT NULL,
  `company_name` varchar(150) NOT NULL,
  `entity_type` varchar(50) NOT NULL,
  `address` varchar(200) NOT NULL,
  `contact_name` varchar(100) NOT NULL,
  `contact_email` varchar(100) NOT NULL,
  `contact_phone` varchar(20) DEFAULT NULL,
  `verification_status` varchar(20) DEFAULT 'PENDING',
  `registration_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `user_id` int NOT NULL,
  PRIMARY KEY (`entity_id`),
  UNIQUE KEY `tax_id` (`tax_id`),
  UNIQUE KEY `uk_entities_user` (`user_id`),
  CONSTRAINT `fk_entities_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `equipments`
--

DROP TABLE IF EXISTS `equipments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `equipments` (
  `equipment_id` int NOT NULL AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `load_id` int NOT NULL,
  `serial_number` varchar(100) NOT NULL,
  `acquisition_date` date NOT NULL,
  `end_of_useful_life` date NOT NULL,
  `current_market_value` decimal(10,2) DEFAULT '0.00',
  `life_cycle_status` varchar(30) DEFAULT 'IN_USE',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`equipment_id`),
  UNIQUE KEY `serial_number` (`serial_number`),
  KEY `fk_equipments_data_loads` (`load_id`),
  KEY `idx_equipments_life_status` (`end_of_useful_life`,`life_cycle_status`),
  KEY `idx_equipments_product` (`product_id`,`equipment_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16384 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `procedure_execution_logs`
--

DROP TABLE IF EXISTS `procedure_execution_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `procedure_execution_logs` (
  `log_id` int NOT NULL AUTO_INCREMENT,
  `load_id` int DEFAULT NULL,
  `procedure_name` varchar(100) DEFAULT 'sp_importar_excel',
  `log_level` varchar(20) DEFAULT NULL,
  `step_description` varchar(255) DEFAULT NULL,
  `message` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `products`
--

DROP TABLE IF EXISTS `products`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `products` (
  `product_id` int NOT NULL AUTO_INCREMENT,
  `product_code` varchar(50) NOT NULL,
  `name` varchar(150) NOT NULL,
  `url_image` text,
  `description` text,
  `category` varchar(50) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`product_id`),
  UNIQUE KEY `product_code` (`product_code`)
) ENGINE=InnoDB AUTO_INCREMENT=16384 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `technical_evaluations`
--

DROP TABLE IF EXISTS `technical_evaluations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `technical_evaluations` (
  `evaluation_id` int NOT NULL AUTO_INCREMENT,
  `equipment_id` int NOT NULL,
  `evaluation_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `reusability_score` decimal(5,2) NOT NULL,
  `is_operational` tinyint(1) DEFAULT '1',
  `requires_refurbishment` tinyint(1) DEFAULT '0',
  `estimated_repair_cost` decimal(10,2) DEFAULT '0.00',
  `final_verdict` varchar(30) NOT NULL,
  `remarks` text,
  PRIMARY KEY (`evaluation_id`),
  KEY `idx_evaluations_verdict` (`equipment_id`,`is_operational`,`final_verdict`),
  CONSTRAINT `fk_evaluations_equipments` FOREIGN KEY (`equipment_id`) REFERENCES `equipments` (`equipment_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=12286 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `email` varchar(150) NOT NULL,
  `password` text,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
