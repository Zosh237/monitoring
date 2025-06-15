#!/usr/bin/env python3
"""
Script de test indépendant pour BackupScanner
Crée un environnement temporaire avec 7 scénarios capitaux et données réelles
"""

import os
import sys
import json
import tempfile
import shutil
import hashlib
import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import gzip
import random
import string

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scanner_test.log')
    ]
)
logger = logging.getLogger(__name__)


class TestEnvironmentGenerator:
    """Générateur d'environnement de test pour BackupScanner"""
    
    def __init__(self, base_dir: Optional[str] = None, cleanup: bool = True):
        """
        Initialize test environment generator
        
        Args:
            base_dir: Répertoire de base (si None, utilise tempfile)
            cleanup: Si True, nettoie automatiquement après les tests
        """
        self.cleanup_enabled = cleanup
        self.base_dir = base_dir or tempfile.mkdtemp(prefix="backup_scanner_test_")
        self.backup_root = os.path.join(self.base_dir, "backups")
        self.validated_root = os.path.join(self.base_dir, "validated")
        
        # Données de test réalistes
        self.companies = [
            {"name": "ACME", "city": "PARIS", "agent": "ACME_PARIS_CENTRE"},
            {"name": "GLOBEX", "city": "LYON", "agent": "GLOBEX_LYON_EST"},
            {"name": "INITECH", "city": "MARSEILLE", "agent": "INITECH_MARSEILLE_SUD"},
            {"name": "UMBRELLA", "city": "TOULOUSE", "agent": "UMBRELLA_TOULOUSE_NORD"},
            {"name": "WAYNETECH", "city": "NICE", "agent": "WAYNETECH_NICE_CENTRE"}
        ]
        
        self.databases = ["production_db", "analytics_db", "backup_db", "reporting_db"]
        
        logger.info(f"Environnement de test créé dans: {self.base_dir}")
        
    def __enter__(self):
        """Context manager entry"""
        self.setup_directories()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit avec nettoyage optionnel"""
        if self.cleanup_enabled:
            self.cleanup()
        else:
            logger.info(f"Environnement conservé dans: {self.base_dir}")
            
    def setup_directories(self):
        """Crée la structure de répertoires de base"""
        logger.info("Création de la structure de répertoires...")
        
        # Répertoires principaux
        os.makedirs(self.backup_root, exist_ok=True)
        os.makedirs(self.validated_root, exist_ok=True)
        
        # Répertoires par agent
        for company in self.companies:
            agent_dir = os.path.join(self.backup_root, company["agent"])
            os.makedirs(os.path.join(agent_dir, "log"), exist_ok=True)
            os.makedirs(os.path.join(agent_dir, "database"), exist_ok=True)
            os.makedirs(os.path.join(agent_dir, "archive"), exist_ok=True)
            
        # Répertoires validated par année/compagnie/ville
        for company in self.companies:
            validated_path = os.path.join(
                self.validated_root, 
                "2025", 
                company["name"], 
                company["city"]
            )
            os.makedirs(validated_path, exist_ok=True)
            
    def generate_checksum(self, data: bytes) -> str:
        """Génère un checksum SHA256 pour des données"""
        return hashlib.sha256(data).hexdigest()
        
    def create_backup_file(self, filepath: str, size_mb: float = 1.0) -> Tuple[str, int]:
        """
        Crée un fichier de sauvegarde réaliste
        
        Returns:
            Tuple[checksum, size_bytes]
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Génère du contenu SQL réaliste
        sql_content = self._generate_sql_content()
        target_size = int(size_mb * 1024 * 1024)
        
        # Répète le contenu pour atteindre la taille cible
        content_bytes = sql_content.encode('utf-8')
        repetitions = max(1, target_size // len(content_bytes))
        remainder = target_size % len(content_bytes)
        
        # Crée le fichier compressé
        with gzip.open(filepath, 'wb') as f:
            for _ in range(repetitions):
                f.write(content_bytes)
            if remainder > 0:
                f.write(content_bytes[:remainder])
                
        # Calcule le checksum du fichier compressé
        with open(filepath, 'rb') as f:
            file_data = f.read()
            checksum = self.generate_checksum(file_data)
            actual_size = len(file_data)
            
        return checksum, actual_size
        
    def _generate_sql_content(self) -> str:
        """Génère du contenu SQL réaliste"""
        tables = ["users", "orders", "products", "customers", "transactions"]
        sql_lines = [
            "-- Database backup generated on " + datetime.now().isoformat(),
            "SET FOREIGN_KEY_CHECKS=0;",
            "SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';",
            ""
        ]
        
        for table in tables:
            sql_lines.extend([
                f"DROP TABLE IF EXISTS `{table}`;",
                f"CREATE TABLE `{table}` (",
                "  `id` int(11) NOT NULL AUTO_INCREMENT,",
                "  `name` varchar(255) NOT NULL,",
                f"  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,",
                "  PRIMARY KEY (`id`)",
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
                ""
            ])
            
            # Ajoute quelques données d'exemple
            for i in range(10):
                value = ''.join(random.choices(string.ascii_letters, k=10))
                sql_lines.append(f"INSERT INTO `{table}` (`name`) VALUES ('{value}');")
            sql_lines.append("")
            
        return '\n'.join(sql_lines)
        
    def create_status_file(self, agent: str, timestamp: datetime, databases: List[str], 
                          scenario_type: str = "success") -> str:
        """
        Crée un fichier STATUS.json selon le scénario
        
        Args:
            agent: ID de l'agent
            timestamp: Timestamp de l'opération
            databases: Liste des bases de données
            scenario_type: Type de scénario (success, failed, partial, etc.)
        """
        log_dir = os.path.join(self.backup_root, agent, "log")
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{agent}.json"
        filepath = os.path.join(log_dir, filename)
        
        status_data = {
            "agent_id": agent,
            "operation_start_time": (timestamp - timedelta(hours=2)).isoformat(),
            "operation_end_time": timestamp.isoformat(),
            "overall_status": "SUCCESS" if scenario_type == "success" else "FAILED",
            "databases": {}
        }
        
        for db_name in databases:
            if scenario_type == "success":
                status_data["databases"][db_name] = self._create_successful_db_status(db_name, timestamp)
            elif scenario_type == "backup_failed":
                status_data["databases"][db_name] = self._create_failed_backup_status(db_name, timestamp)
            elif scenario_type == "transfer_failed":
                status_data["databases"][db_name] = self._create_transfer_failed_status(db_name, timestamp)
            elif scenario_type == "hash_mismatch":
                status_data["databases"][db_name] = self._create_hash_mismatch_status(db_name, timestamp)
            elif scenario_type == "partial":
                # Mélange de succès et d'échecs
                if random.choice([True, False]):
                    status_data["databases"][db_name] = self._create_successful_db_status(db_name, timestamp)
                else:
                    status_data["databases"][db_name] = self._create_failed_backup_status(db_name, timestamp)
                    
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
            
        return filepath
        
    def _create_successful_db_status(self, db_name: str, end_time: datetime) -> Dict:
        """Crée un statut de DB réussi"""
        backup_time = end_time - timedelta(hours=1, minutes=30)
        compress_time = end_time - timedelta(minutes=45)
        transfer_time = end_time - timedelta(minutes=15)
        
        return {
            "staged_file_name": f"backup_{end_time.strftime('%Y%m%d_%H%M%S')}.sql.gz",
            "BACKUP": {
                "status": True,
                "start_time": backup_time.isoformat(),
                "end_time": (backup_time + timedelta(minutes=45)).isoformat(),
                "sha256_checksum": hashlib.sha256(f"backup_{db_name}_{backup_time}".encode()).hexdigest(),
                "size": random.randint(1024000, 5120000)
            },
            "COMPRESS": {
                "status": True,
                "start_time": compress_time.isoformat(),
                "end_time": (compress_time + timedelta(minutes=20)).isoformat(),
                "sha256_checksum": hashlib.sha256(f"compressed_{db_name}_{compress_time}".encode()).hexdigest(),
                "size": random.randint(512000, 2560000)
            },
            "TRANSFER": {
                "status": True,
                "start_time": transfer_time.isoformat(),
                "end_time": end_time.isoformat(),
                "destination_path": f"/validated/2025/COMPANY/CITY/{db_name}",
                "transfer_checksum": hashlib.sha256(f"transfer_{db_name}_{transfer_time}".encode()).hexdigest()
            },
            "logs_summary": f"Backup of {db_name} completed successfully"
        }
        
    def _create_failed_backup_status(self, db_name: str, end_time: datetime) -> Dict:
        """Crée un statut de backup échoué"""
        backup_time = end_time - timedelta(hours=1)
        
        return {
            "staged_file_name": f"backup_{end_time.strftime('%Y%m%d_%H%M%S')}.sql.gz",
            "BACKUP": {
                "status": False,
                "start_time": backup_time.isoformat(),
                "end_time": (backup_time + timedelta(minutes=30)).isoformat(),
                "error": "Connection to database failed",
                "size": 0
            },
            "COMPRESS": {
                "status": False,
                "error": "No backup file to compress"
            },
            "TRANSFER": {
                "status": False,
                "error": "No compressed file to transfer"
            },
            "logs_summary": f"Backup of {db_name} failed - database connection error"
        }
        
    def _create_transfer_failed_status(self, db_name: str, end_time: datetime) -> Dict:
        """Crée un statut d'échec de transfert"""
        status = self._create_successful_db_status(db_name, end_time)
        status["TRANSFER"]["status"] = False
        status["TRANSFER"]["error"] = "Network timeout during transfer"
        status["logs_summary"] = f"Backup of {db_name} failed during transfer"
        return status
        
    def _create_hash_mismatch_status(self, db_name: str, end_time: datetime) -> Dict:
        """Crée un statut avec erreur de checksum"""
        status = self._create_successful_db_status(db_name, end_time)
        # Crée un hash différent pour simuler l'erreur
        status["TRANSFER"]["transfer_checksum"] = "mismatch_" + status["COMPRESS"]["sha256_checksum"]
        status["logs_summary"] = f"Backup of {db_name} completed but checksum mismatch detected"
        return status


class ScenarioGenerator:
    """Générateur des 7 scénarios capitaux"""
    
    def __init__(self, env_gen: TestEnvironmentGenerator):
        self.env = env_gen
        self.scenarios = []
        
    def generate_all_scenarios(self) -> List[Dict]:
        """Génère tous les scénarios de test"""
        logger.info("Génération des 7 scénarios capitaux...")
        
        scenarios = [
            self.scenario_1_successful_backup(),
            self.scenario_2_backup_failure(),
            self.scenario_3_missing_files(),
            self.scenario_4_hash_mismatch(),
            self.scenario_5_transfer_failure(),
            self.scenario_6_old_status_files(),
            self.scenario_7_partial_success()
        ]
        
        self.scenarios = scenarios
        return scenarios
        
    def scenario_1_successful_backup(self) -> Dict:
        """Scénario 1: Sauvegarde complètement réussie"""
        logger.info("Génération du Scénario 1: Sauvegarde réussie")
        
        company = self.env.companies[0]
        agent = company["agent"]
        db_name = "production_db"
        timestamp = datetime.now(timezone.utc).replace(minute=30, second=0, microsecond=0)
        
        # Crée le fichier de sauvegarde
        staged_file = os.path.join(
            self.env.backup_root, agent, "database",
            f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        )
        checksum, size = self.env.create_backup_file(staged_file, 2.5)
        
        # Crée le fichier de statut
        status_file = self.env.create_status_file(agent, timestamp, [db_name], "success")
        
        # Crée le fichier final validé
        final_path = os.path.join(
            self.env.validated_root, "2025", company["name"], company["city"], db_name,
            f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        )
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        shutil.copy2(staged_file, final_path)
        
        return {
            "name": "Successful Backup",
            "description": "Sauvegarde complètement réussie avec tous les fichiers présents",
            "agent": agent,
            "database": db_name,
            "status_file": status_file,
            "staged_file": staged_file,
            "final_file": final_path,
            "expected_result": "SUCCESS",
            "checksum": checksum,
            "size": size
        }
        
    def scenario_2_backup_failure(self) -> Dict:
        """Scénario 2: Échec de sauvegarde"""
        logger.info("Génération du Scénario 2: Échec de sauvegarde")
        
        company = self.env.companies[1]
        agent = company["agent"]
        db_name = "analytics_db"
        timestamp = datetime.now(timezone.utc).replace(minute=30, second=0, microsecond=0)
        
        # Crée seulement le fichier de statut (échec)
        status_file = self.env.create_status_file(agent, timestamp, [db_name], "backup_failed")
        
        return {
            "name": "Backup Failure",
            "description": "Échec de la sauvegarde, pas de fichier généré",
            "agent": agent,
            "database": db_name,
            "status_file": status_file,
            "staged_file": None,
            "final_file": None,
            "expected_result": "BACKUP_FAILED"
        }
        
    def scenario_3_missing_files(self) -> Dict:
        """Scénario 3: Fichiers manquants"""
        logger.info("Génération du Scénario 3: Fichiers manquants")
        
        company = self.env.companies[2]
        agent = company["agent"]
        db_name = "backup_db"
        
        # Crée seulement la structure de répertoires, pas de fichiers
        agent_dir = os.path.join(self.env.backup_root, agent)
        os.makedirs(os.path.join(agent_dir, "log"), exist_ok=True)
        os.makedirs(os.path.join(agent_dir, "database"), exist_ok=True)
        
        return {
            "name": "Missing Files",
            "description": "Aucun fichier de statut ni de sauvegarde présent",
            "agent": agent,
            "database": db_name,
            "status_file": None,
            "staged_file": None,
            "final_file": None,
            "expected_result": "MISSING"
        }
        
    def scenario_4_hash_mismatch(self) -> Dict:
        """Scénario 4: Erreur de checksum"""
        logger.info("Génération du Scénario 4: Erreur de checksum")
        
        company = self.env.companies[3]
        agent = company["agent"]
        db_name = "reporting_db"
        timestamp = datetime.now(timezone.utc).replace(minute=30, second=0, microsecond=0)
        
        # Crée le fichier de sauvegarde
        staged_file = os.path.join(
            self.env.backup_root, agent, "database",
            f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        )
        checksum, size = self.env.create_backup_file(staged_file, 1.8)
        
        # Crée le fichier de statut avec hash mismatch
        status_file = self.env.create_status_file(agent, timestamp, [db_name], "hash_mismatch")
        
        # Crée un fichier final avec un contenu différent (pour simuler la corruption)
        final_path = os.path.join(
            self.env.validated_root, "2025", company["name"], company["city"], db_name,
            f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        )
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        # Copie et modifie légèrement le fichier
        shutil.copy2(staged_file, final_path)
        with open(final_path, 'ab') as f:
            f.write(b'corrupted_data')
            
        return {
            "name": "Hash Mismatch",
            "description": "Sauvegarde avec erreur de checksum",
            "agent": agent,
            "database": db_name,
            "status_file": status_file,
            "staged_file": staged_file,
            "final_file": final_path,
            "expected_result": "HASH_MISMATCH",
            "original_checksum": checksum,
            "size": size
        }
        
    def scenario_5_transfer_failure(self) -> Dict:
        """Scénario 5: Échec de transfert"""
        logger.info("Génération du Scénario 5: Échec de transfert")
        
        company = self.env.companies[4]
        agent = company["agent"]
        db_name = "production_db"
        timestamp = datetime.now(timezone.utc).replace(minute=30, second=0, microsecond=0)
        
        # Crée le fichier de sauvegarde
        staged_file = os.path.join(
            self.env.backup_root, agent, "database",
            f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        )
        checksum, size = self.env.create_backup_file(staged_file, 3.2)
        
        # Crée le fichier de statut avec échec de transfert
        status_file = self.env.create_status_file(agent, timestamp, [db_name], "transfer_failed")
        
        # Pas de fichier final (transfert échoué)
        
        return {
            "name": "Transfer Failure",
            "description": "Sauvegarde réussie mais échec du transfert",
            "agent": agent,
            "database": db_name,
            "status_file": status_file,
            "staged_file": staged_file,
            "final_file": None,
            "expected_result": "TRANSFER_FAILED",
            "checksum": checksum,
            "size": size
        }
        
    def scenario_6_old_status_files(self) -> Dict:
        """Scénario 6: Fichiers de statut anciens"""
        logger.info("Génération du Scénario 6: Fichiers de statut anciens")
        
        company = self.env.companies[0]  # Réutilise le premier agent
        agent = company["agent"]
        db_name = "old_backup_db"
        
        # Crée des fichiers de statut anciens (il y a 10 jours)
        old_timestamp = datetime.now(timezone.utc) - timedelta(days=10)
        old_status_file = self.env.create_status_file(
            agent, old_timestamp, [db_name], "success"
        )
        
        # Crée aussi un fichier stagé ancien
        old_staged_file = os.path.join(
            self.env.backup_root, agent, "database",
            f"backup_{old_timestamp.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        )
        checksum, size = self.env.create_backup_file(old_staged_file, 1.0)
        
        return {
            "name": "Old Status Files",
            "description": "Fichiers de statut anciens à archiver",
            "agent": agent,
            "database": db_name,
            "status_file": old_status_file,
            "staged_file": old_staged_file,
            "final_file": None,
            "expected_result": "TO_ARCHIVE",
            "age_days": 10,
            "checksum": checksum,
            "size": size
        }
        
    def scenario_7_partial_success(self) -> Dict:
        """Scénario 7: Succès partiel (plusieurs DB, résultats mixtes)"""
        logger.info("Génération du Scénario 7: Succès partiel")
        
        company = self.env.companies[1]  # Réutilise le deuxième agent
        agent = company["agent"]
        databases = ["db1", "db2", "db3"]
        timestamp = datetime.now(timezone.utc).replace(minute=30, second=0, microsecond=0)
        
        # Crée le fichier de statut avec succès partiel
        status_file = self.env.create_status_file(agent, timestamp, databases, "partial")
        
        # Crée quelques fichiers de sauvegarde (pas tous)
        staged_files = []
        for i, db_name in enumerate(databases[:2]):  # Seulement les 2 premiers
            staged_file = os.path.join(
                self.env.backup_root, agent, "database",
                f"backup_{db_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.sql.gz"
            )
            checksum, size = self.env.create_backup_file(staged_file, 1.5)
            staged_files.append((staged_file, checksum, size))
            
        return {
            "name": "Partial Success",
            "description": "Succès partiel avec plusieurs bases de données",
            "agent": agent,
            "databases": databases,
            "status_file": status_file,
            "staged_files": staged_files,
            "final_file": None,
            "expected_result": "PARTIAL_SUCCESS"
        }


def run_scanner_simulation(test_env: TestEnvironmentGenerator, scenarios: List[Dict]):
    """Simule l'exécution du scanner sur les scénarios générés"""
    logger.info("=== SIMULATION D'EXÉCUTION DU SCANNER ===")
    
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        logger.info(f"\n--- Scénario {i}: {scenario['name']} ---")
        logger.info(f"Description: {scenario['description']}")
        
        # Analyse des fichiers présents
        analysis = {
            "scenario": scenario['name'],
            "files_found": {},
            "expected_result": scenario.get('expected_result', 'UNKNOWN')
        }
        
        # Vérifie les fichiers de statut
        if scenario.get('status_file') and os.path.exists(scenario['status_file']):
            analysis['files_found']['status'] = True
            with open(scenario['status_file'], 'r') as f:
                status_data = json.load(f)
                analysis['status_content'] = {
                    'overall_status': status_data.get('overall_status'),
                    'databases_count': len(status_data.get('databases', {})),
                    'agent_id': status_data.get('agent_id')
                }
        else:
            analysis['files_found']['status'] = False
            
        # Vérifie les fichiers stagés
        staged_files = scenario.get('staged_files', [])
        if scenario.get('staged_file'):
            staged_files = [(scenario['staged_file'], None, None)]
            
        analysis['files_found']['staged_count'] = 0
        for staged_info in staged_files:
            staged_file = staged_info[0] if isinstance(staged_info, tuple) else staged_info
            if os.path.exists(staged_file):
                analysis['files_found']['staged_count'] += 1
                
        # Vérifie les fichiers finaux
        if scenario.get('final_file') and os.path.exists(scenario['final_file']):
            analysis['files_found']['final'] = True
        else:
            analysis['files_found']['final'] = False
            
        # Évaluation du résultat attendu
        if analysis['files_found']['status'] and analysis['files_found']['staged_count'] > 0:
            if analysis['files_found']['final']:
                predicted_result = "SUCCESS"
            else:
                predicted_result = "TRANSFER_PENDING"
        elif analysis['files_found']['status']:
            predicted_result = "BACKUP_FAILED"
        else:
            predicted_result = "MISSING"
            
        analysis['predicted_result'] = predicted_result
        
        logger.info(f"Fichiers trouvés: {analysis['files_found']}")
        logger.info(f"Résultat attendu: {analysis['expected_result']}")
        logger.info(f"Résultat prédit: {predicted_result}")
        
        results.append(analysis)
    
    return results


def generate_test_report(scenarios: List[Dict], results: List[Dict], output_file: str):
    """Génère un rapport de test détaillé"""
    logger.info(f"Génération du rapport de test: {output_file}")
    
    report = {
        "test_execution": {
            "timestamp": datetime.now().isoformat(),
            "total_scenarios": len(scenarios),
            "environment_path": scenarios[0].get('agent', 'N/A') if scenarios else 'N/A'
        },
        "scenarios": [],
        "summary": {
            "files_created": 0,
            "status_files": 0,
            "staged_files": 0,
            "final_files": 0
        }
    }
    
    for scenario, result in zip(scenarios, results):
        scenario_report = {
            "name": scenario['name'],
            "description": scenario['description'],
            "files": {
                "status_file": scenario.get('status_file'),
                "staged_file": scenario.get('staged_file'),
                "final_file": scenario.get('final_file')
            },
            "analysis": result,
            "metadata": {
                "agent": scenario.get('agent'),
                "database": scenario.get('database'),
                "checksum": scenario.get('checksum'),
                "size": scenario.get('size')
            }
        }
        
        report["scenarios"].append(scenario_report)
        
        # Mise à jour des statistiques
        if scenario.get('status_file'):
            report["summary"]["status_files"] += 1
        if scenario.get('staged_file'):
            report["summary"]["staged_files"] += 1
        if scenario.get('final_file'):
            report["summary"]["final_files"] += 1
            
    report["summary"]["files_created"] = (
        report["summary"]["status_files"] + 
        report["summary"]["staged_files"] + 
        report["summary"]["final_files"]
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Rapport généré: {output_file}")
    return report


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Générateur d'environnement de test pour BackupScanner"
    )
    parser.add_argument(
        "--base-dir", 
        help="Répertoire de base pour l'environnement de test"
    )
    parser.add_argument(
        "--no-cleanup", 
        action="store_true",
        help="Ne pas nettoyer l'environnement après les tests"
    )
    parser.add_argument(
        "--report-file",
        default="test_report.json",
        help="Fichier de rapport de test (défaut: test_report.json)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbose"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=== GÉNÉRATEUR D'ENVIRONNEMENT DE TEST BACKUPSCANNER ===")
    logger.info(f"Nettoyage automatique: {'NON' if args.no_cleanup else 'OUI'}")
    
    try:
        # Crée l'environnement de test
        with TestEnvironmentGenerator(
            base_dir=args.base_dir,
            cleanup=not args.no_cleanup
        ) as test_env:
            
            logger.info(f"Environnement créé dans: {test_env.base_dir}")
            
            # Génère les scénarios
            scenario_gen = ScenarioGenerator(test_env)
            scenarios = scenario_gen.generate_all_scenarios()
            
            logger.info(f"✓ {len(scenarios)} scénarios générés")
            
            # Affiche un résumé des fichiers créés
            total_files = 0
            for scenario in scenarios:
                if scenario.get('status_file'):
                    total_files += 1
                if scenario.get('staged_file'):
                    total_files += 1
                if scenario.get('staged_files'):
                    total_files += len(scenario['staged_files'])
                if scenario.get('final_file'):
                    total_files += 1
                    
            logger.info(f"✓ {total_files} fichiers créés au total")
            
            # Simule l'exécution du scanner
            results = run_scanner_simulation(test_env, scenarios)
            
            # Génère le rapport
            report = generate_test_report(scenarios, results, args.report_file)
            
            # Affiche le résumé final
            logger.info("\n=== RÉSUMÉ FINAL ===")
            logger.info(f"Environnement: {test_env.base_dir}")
            logger.info(f"Scénarios générés: {len(scenarios)}")
            logger.info(f"Fichiers STATUS: {report['summary']['status_files']}")
            logger.info(f"Fichiers stagés: {report['summary']['staged_files']}")
            logger.info(f"Fichiers finaux: {report['summary']['final_files']}")
            logger.info(f"Total fichiers: {report['summary']['files_created']}")
            logger.info(f"Rapport: {args.report_file}")
            
            if args.no_cleanup:
                logger.info(f"\n⚠️  ENVIRONNEMENT CONSERVÉ: {test_env.base_dir}")
                logger.info("Pour nettoyer manuellement:")
                logger.info(f"  rm -rf {test_env.base_dir}")
                
                # Crée un script de nettoyage
                cleanup_script = os.path.join(test_env.base_dir, "cleanup.sh")
                with open(cleanup_script, 'w') as f:
                    f.write("#!/bin/bash\n")
                    f.write(f"# Script de nettoyage pour l'environnement de test\n")
                    f.write(f"echo 'Nettoyage de {test_env.base_dir}...'\n")
                    f.write(f"rm -rf {test_env.base_dir}\n")
                    f.write("echo 'Nettoyage terminé.'\n")
                os.chmod(cleanup_script, 0o755)
                logger.info(f"Script de nettoyage créé: {cleanup_script}")
                
                # Crée un fichier README pour l'environnement
                readme_file = os.path.join(test_env.base_dir, "README.md")
                with open(readme_file, 'w', encoding='utf-8') as f:
                    f.write("# Environnement de Test BackupScanner\n\n")
                    f.write(f"Créé le: {datetime.now().isoformat()}\n\n")
                    f.write("## Structure\n\n")
                    f.write("```\n")
                    f.write(f"{test_env.base_dir}/\n")
                    f.write("├── backups/          # Fichiers de sauvegarde et status\n")
                    f.write("├── validated/        # Fichiers validés\n")
                    f.write("├── test_report.json  # Rapport de test\n")
                    f.write("├── cleanup.sh        # Script de nettoyage\n")
                    f.write("└── README.md         # Ce fichier\n")
                    f.write("```\n\n")
                    f.write("## Scénarios générés\n\n")
                    for i, scenario in enumerate(scenarios, 1):
                        f.write(f"{i}. **{scenario['name']}**: {scenario['description']}\n")
                    f.write("\n## Utilisation\n\n")
                    f.write("Pour tester le BackupScanner avec cet environnement:\n\n")
                    f.write("```python\n")
                    f.write("from app.services.scanner import BackupScanner\n")
                    f.write("# Configurer BACKUP_STORAGE_ROOT et VALIDATED_BACKUPS_BASE_PATH\n")
                    f.write(f"# BACKUP_STORAGE_ROOT = '{test_env.backup_root}'\n")
                    f.write(f"# VALIDATED_BACKUPS_BASE_PATH = '{test_env.validated_root}'\n")
                    f.write("```\n\n")
                    f.write("## Nettoyage\n\n")
                    f.write("```bash\n")
                    f.write("./cleanup.sh\n")
                    f.write("```\n")
                    
                logger.info(f"Documentation créée: {readme_file}")
            
            logger.info("\n✅ Génération d'environnement terminée avec succès!")
            
    except Exception as e:
        logger.error(f"Erreur lors de la génération: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    return 0


def inspect_environment(base_dir: str):
    """Fonction utilitaire pour inspecter un environnement existant"""
    logger.info(f"=== INSPECTION DE L'ENVIRONNEMENT: {base_dir} ===")
    
    if not os.path.exists(base_dir):
        logger.error(f"Répertoire non trouvé: {base_dir}")
        return
        
    backup_root = os.path.join(base_dir, "backups")
    validated_root = os.path.join(base_dir, "validated")
    
    # Compte les fichiers
    status_files = []
    staged_files = []
    final_files = []
    
    if os.path.exists(backup_root):
        for root, dirs, files in os.walk(backup_root):
            for file in files:
                filepath = os.path.join(root, file)
                if file.endswith('.json'):
                    status_files.append(filepath)
                elif file.endswith('.sql.gz'):
                    staged_files.append(filepath)
                    
    if os.path.exists(validated_root):
        for root, dirs, files in os.walk(validated_root):
            for file in files:
                if file.endswith('.sql.gz'):
                    final_files.append(os.path.join(root, file))
                    
    logger.info(f"Fichiers STATUS trouvés: {len(status_files)}")
    logger.info(f"Fichiers stagés trouvés: {len(staged_files)}")
    logger.info(f"Fichiers finaux trouvés: {len(final_files)}")
    
    # Affiche les détails
    if status_files:
        logger.info("\n--- Fichiers STATUS ---")
        for sf in status_files:
            try:
                with open(sf, 'r') as f:
                    data = json.load(f)
                    agent = data.get('agent_id', 'UNKNOWN')
                    status = data.get('overall_status', 'UNKNOWN')
                    db_count = len(data.get('databases', {}))
                    logger.info(f"  {os.path.basename(sf)}: {agent} - {status} ({db_count} DB)")
            except Exception as e:
                logger.warning(f"  {os.path.basename(sf)}: Erreur lecture - {e}")
                
    if staged_files:
        logger.info("\n--- Fichiers stagés ---")
        for sf in staged_files[:5]:  # Limite à 5 pour l'affichage
            size = os.path.getsize(sf)
            logger.info(f"  {os.path.basename(sf)}: {size/1024:.1f} KB")
        if len(staged_files) > 5:
            logger.info(f"  ... et {len(staged_files) - 5} autres")
            
    if final_files:
        logger.info("\n--- Fichiers finaux ---")
        for ff in final_files[:5]:  # Limite à 5 pour l'affichage
            size = os.path.getsize(ff)
            logger.info(f"  {os.path.basename(ff)}: {size/1024:.1f} KB")
        if len(final_files) > 5:
            logger.info(f"  ... et {len(final_files) - 5} autres")


if __name__ == "__main__":
    # Ajoute une commande d'inspection
    if len(sys.argv) > 1 and sys.argv[1] == "inspect":
        if len(sys.argv) > 2:
            inspect_environment(sys.argv[2])
        else:
            print("Usage: python script.py inspect <chemin_environnement>")
        sys.exit(0)
        
    sys.exit(main())