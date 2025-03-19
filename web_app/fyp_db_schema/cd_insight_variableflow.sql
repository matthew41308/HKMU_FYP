-- MySQL dump 10.13  Distrib 8.0.36, for Win64 (x86_64)
--
-- Host: localhost    Database: cd_insight
-- ------------------------------------------------------
-- Server version	8.0.36

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `variableflow`
--

DROP TABLE IF EXISTS `variableflow`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `variableflow` (
  `flow_id` int NOT NULL AUTO_INCREMENT,
  `source_variable_id` int DEFAULT NULL,
  `target_variable_id` int DEFAULT NULL,
  `source_method_id` int DEFAULT NULL,
  `target_method_id` int DEFAULT NULL,
  `flow_type` enum('assignment','parameter_passing','return_value','reference') COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`flow_id`),
  KEY `source_variable_id` (`source_variable_id`),
  KEY `target_variable_id` (`target_variable_id`),
  KEY `source_method_id` (`source_method_id`),
  KEY `target_method_id` (`target_method_id`),
  CONSTRAINT `variableflow_ibfk_1` FOREIGN KEY (`source_variable_id`) REFERENCES `variables` (`variable_id`),
  CONSTRAINT `variableflow_ibfk_2` FOREIGN KEY (`target_variable_id`) REFERENCES `variables` (`variable_id`),
  CONSTRAINT `variableflow_ibfk_3` FOREIGN KEY (`source_method_id`) REFERENCES `methods` (`method_id`),
  CONSTRAINT `variableflow_ibfk_4` FOREIGN KEY (`target_method_id`) REFERENCES `methods` (`method_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-01-18 15:15:55
