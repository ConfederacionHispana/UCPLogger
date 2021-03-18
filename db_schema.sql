-- --------------------------------------------------------
-- Versión del servidor:         10.3.23-MariaDB-cll-lve - MariaDB Server
-- SO del servidor:              Linux
-- HeidiSQL Versión:             11.1.0.6116
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

-- Volcando estructura para tabla nozomi_ucplogger.wikis
CREATE TABLE IF NOT EXISTS `wikis` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT COMMENT 'wiki id, used internally',
  `wiki_url` varchar(1024) NOT NULL DEFAULT '0' COMMENT 'base wiki url, including language path if needed',
  `webhook` varchar(512) NOT NULL DEFAULT '0' COMMENT 'discord webhook, in the ''id/token'' format',
  `lang` varchar(8) NOT NULL DEFAULT 'en' COMMENT 'language for messages, defaults to ''en''',
  `display` bit(1) NOT NULL DEFAULT b'0' COMMENT 'display mode. 0 = compact / 1 = embed',
  `rcid` int(11) DEFAULT 0 COMMENT 'last MW change id processed',
  `postid` bigint(20) DEFAULT NULL COMMENT 'last feeds message processed',
  PRIMARY KEY (`id`),
  KEY `webhook` (`webhook`),
  KEY `wiki_url` (`wiki_url`(768))
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COMMENT='configured wikis are stored in this table.';

-- La exportación de datos fue deseleccionada.

/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
