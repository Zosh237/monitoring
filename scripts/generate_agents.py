#!/usr/bin/env python3
"""
Ce script génère la structure suivante dans un emplacement passé en paramètre :

<chemin_racine>/
    agent_1/
         log/
             2025-06-12T12-56-06_agent_1.json    # fichier JSON simulant un rapport de statut
         databases/
             <db1>.sql              # fichiers de backup simulés
             <db2>.sql
    agent_2/
         log/
         databases/
    ...

Le fichier JSON généré respecte la nomenclature :
    horodatage_agent_id
Exemple pour un agent dont l'id est "sirpacam_douala_newbell" :
    2025-06-12T12-56-06_sirpacam_douala_newbell.json
"""

import os
import argparse
import json
import random
from datetime import datetime

def generate_agent_status(agent_id: str) -> dict:
    """
    Génère le contenu du fichier JSON de statut pour un agent.
    Pour simuler la présence de plusieurs bases, on génère entre 1 et 3 bases.
    """
    status = {
        "operation_start_time": datetime.utcnow().isoformat() + "Z",
        "operation_end_time": datetime.utcnow().isoformat() + "Z",
        "agent_id": agent_id,
        "overall_status": "completed",
        "databases": {}
    }

    # Génère entre 1 et 3 bases de données pour l'agent.
    nb_databases = random.randint(1, 3)
    for i in range(1, nb_databases + 1):
        # Construire un nom de base en majuscules, qui pourrait refléter entreprise, ville, quartier et année
        db_name = f"{agent_id.upper()}_DB_{i}_2025"
        status["databases"][db_name] = {
            "BACKUP": {
                "status": True,
                "start_time": datetime.utcnow().isoformat() + "Z",
                "end_time": datetime.utcnow().isoformat() + "Z",
                "sha256_checksum": "dummychecksum_backup",
                "size": random.randint(10_000_000, 50_000_000)
            },
            "COMPRESS": {
                "status": True,
                "start_time": datetime.utcnow().isoformat() + "Z",
                "end_time": datetime.utcnow().isoformat() + "Z",
                "sha256_checksum": "dummychecksum_compress",
                "size": random.randint(1_000_000, 10_000_000)
            },
            "TRANSFER": {
                "status": True,
                "start_time": datetime.utcnow().isoformat() + "Z",
                "end_time": datetime.utcnow().isoformat() + "Z",
                "error_message": None
            },
            "staged_file_name": f"{db_name.lower()}.sql.gz"
        }

    return status

def create_agent_structure(root_path: str, agent_id: str):
    """
    Crée la structure d'un agent dans root_path.
      - Crée le répertoire de l'agent.
      - Crée les sous-dossiers 'log' et 'databases'.
      - Génère un fichier JSON dans 'log' qui respecte la nomenclature "horodatage_agent_id".
      - Pour chaque base dans le JSON, crée un fichier dummy dans 'databases'.
    """
    # Chemin de l'agent
    agent_dir = os.path.join(root_path, agent_id)
    os.makedirs(agent_dir, exist_ok=True)

    # Création des sous-dossiers log et databases
    log_dir = os.path.join(agent_dir, "log")
    databases_dir = os.path.join(agent_dir, "databases")
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(databases_dir, exist_ok=True)

    # Génération du contenu JSON de statut pour l'agent
    status = generate_agent_status(agent_id)

    # Pour respecter la nomenclature, on utilise l'heure de fin de l'opération.
    # On convertit les ":" en "-" pour éviter d'éventuels problèmes sur certains OS.
    operation_end_time = status["operation_end_time"].replace(":", "-")
    json_filename = f"{operation_end_time}_{agent_id}.json"
    json_filepath = os.path.join(log_dir, json_filename)
    
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=4)
    
    # Dans le dossier databases, créer un fichier dummy pour chaque base présente dans le rapport.
    for db_name in status["databases"].keys():
        backup_filename = f"{db_name.lower()}.sql"  # fichier SQL simulé
        backup_filepath = os.path.join(databases_dir, backup_filename)
        with open(backup_filepath, "w", encoding="utf-8") as f:
            f.write("-- Contenu simulé du backup SQL\n")
    
    print(f"Structure de l'agent '{agent_id}' générée dans {agent_dir}")

def main():
    parser = argparse.ArgumentParser(description="Génère la structure des agents avec dossiers et fichiers.")
    parser.add_argument("root", help="Chemin racine où créer les répertoires d'agents")
    parser.add_argument("--num_agents", type=int, default=5, help="Nombre d'agents à générer (défaut 5)")
    args = parser.parse_args()

    root_path = os.path.abspath(args.root)
    os.makedirs(root_path, exist_ok=True)
    
    print(f"Création des répertoires d'agents dans : {root_path}")
    for i in range(1, args.num_agents + 1):
        # Pour cet exemple, on nomme les agents sous la forme "agent_1", "agent_2", etc.
        agent_id = f"agent_{i}"
        create_agent_structure(root_path, agent_id)
    print("Génération terminée.")

if __name__ == "__main__":
    main()
