# Module de Notification

## Structure du Module

Le module de notification (`app/services/notifier.py`) est responsable de l'envoi d'alertes par e-mail aux administrateurs en cas d'anomalies détectées lors du scan des sauvegardes. Il comprend :

- Une classe d'exception personnalisée `NotificationError`
- Une fonction `send_email_notification` pour l'envoi d'e-mails
- Une fonction `notify_backup_status_change` pour la gestion des notifications de statut

## Configuration

Les paramètres SMTP sont configurés via des variables d'environnement dans `config/settings.py` :

```python
EMAIL_HOST: str  # Serveur SMTP (ex: smtp.gmail.com)
EMAIL_PORT: int  # Port SMTP (ex: 587 pour TLS)
EMAIL_USERNAME: str  # Identifiant SMTP
EMAIL_PASSWORD: str  # Mot de passe SMTP
EMAIL_SENDER: str  # Adresse e-mail de l'expéditeur
ADMIN_EMAIL_RECIPIENT: str  # Adresse e-mail de l'administrateur
```

## Fonctionnalités

### Envoi d'E-mail (`send_email_notification`)

- Vérifie la présence des paramètres SMTP requis
- Établit une connexion SMTP sécurisée avec TLS
- Gère les erreurs de connexion et d'authentification
- Assure la fermeture propre de la connexion SMTP (même en cas d'erreur)
- Journalise les succès et les échecs

### Notification de Statut (`notify_backup_status_change`)

- Déclenche des notifications pour les statuts d'erreur :
  - FAILED
  - MISSING
  - HASH_MISMATCH
  - TRANSFER_INTEGRITY_FAILED
- Compose des messages détaillés incluant :
  - Informations sur le job de sauvegarde
  - Détails de l'entrée de sauvegarde
  - Messages d'erreur et logs
  - Comparaisons de hachage et de taille
- Gère les erreurs de notification sans bloquer le scanner

## Tests

Les tests unitaires (`tests/test_notifier.py`) couvrent :

### Tests d'Envoi d'E-mail
- Envoi réussi
- Gestion des erreurs SMTP
- Gestion des paramètres manquants

### Tests de Notification de Statut
- Notification pour statut FAILED
- Notification pour statut HASH_MISMATCH
- Absence de notification pour statut SUCCESS
- Gestion des erreurs de notification

## Journalisation

Le module utilise le logging pour tracer :
- Les tentatives d'envoi d'e-mail
- Les succès et échecs d'envoi
- Les déclenchements de notification
- Les erreurs de configuration
- Les erreurs de notification

## Sécurité

- Utilisation de TLS pour le chiffrement des communications SMTP
- Gestion sécurisée des identifiants via variables d'environnement
- Fermeture systématique des connexions SMTP
- Pas d'exposition des informations sensibles dans les logs

## Maintenance

### Points d'Attention
- Vérification régulière des paramètres SMTP
- Surveillance des logs pour détecter les problèmes d'envoi
- Mise à jour des dépendances de sécurité

### Améliorations Futures
- Support de plusieurs destinataires
- Templates de messages configurables
- Support d'autres protocoles de notification (SMS, Slack, etc.)
- Système de retry pour les échecs d'envoi
- Tests d'intégration avec le scanner

## Intégration

Le module s'intègre avec le scanner via la fonction `notify_backup_status_change`, qui est appelée lorsque :
- Un statut d'erreur est détecté
- Une incohérence de hachage est identifiée
- Un fichier de sauvegarde est manquant
- Une erreur d'intégrité de transfert survient

## Dernières Modifications

### Améliorations de Gestion des Erreurs
- Ajout d'un bloc `finally` pour garantir la fermeture des connexions SMTP
- Amélioration des messages de log pour le débogage
- Meilleure gestion des exceptions dans `notify_backup_status_change`

### Améliorations des Tests
- Tests plus robustes pour la gestion des erreurs SMTP
- Vérification des messages de log
- Tests de scénarios d'erreur plus complets

### Optimisations
- Initialisation de la variable `server` en dehors du bloc try
- Vérification de l'existence de `server` avant d'appeler `quit()`
- Messages de log plus détaillés pour le suivi des notifications

## 8. Intégration

Le service de notification est intégré au scanner via l'appel à `notify_backup_status_change` dans la méthode `_process_job_status` du scanner.

### Exemple d'Utilisation

```python
from app.services.notifier import notify_backup_status_change

# Dans le scanner
if backup_entry_status != BackupEntryStatus.SUCCESS:
    notify_backup_status_change(job, backup_entry)
```

## 9. Conclusion

Le service de notification fournit un mécanisme robuste et configurable pour alerter les administrateurs en cas de problèmes avec les sauvegardes. Il est conçu pour être :
- Fiable : gestion des erreurs et retry
- Configurable : paramètres SMTP flexibles
- Maintenable : tests complets et documentation
- Extensible : prêt pour des améliorations futures 