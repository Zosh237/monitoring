import sqlite3

def check_table_schema():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Récupérer le schéma de la table
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='expected_backup_jobs'")
    schema = cursor.fetchone()
    
    if schema:
        print("Schéma de la table expected_backup_jobs :")
        print(schema[0])
    else:
        print("La table expected_backup_jobs n'existe pas")
    
    conn.close()

if __name__ == "__main__":
    check_table_schema() 