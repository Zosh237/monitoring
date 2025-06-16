# Variables d'Environnement pour le Service de Notification

## Configuration SMTP

Les variables suivantes doivent être configurées dans le fichier `.env` pour activer les notifications par e-mail :

```env
# Configuration des notifications par e-mail
EMAIL_HOST=smtp.example.com        # Hôte SMTP (ex: smtp.gmail.com)
EMAIL_PORT=587                     # Port SMTP (587 pour TLS)
EMAIL_USERNAME=your_username       # Nom d'utilisateur SMTP
EMAIL_PASSWORD=your_password       # Mot de passe SMTP
EMAIL_SENDER=noreply@example.com   # Adresse e-mail de l'expéditeur
ADMIN_EMAIL_RECIPIENT=admin@example.com  # Adresse e-mail du destinataire
```

## Exemples de Configuration

### Gmail
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your.email@gmail.com
EMAIL_PASSWORD=your_app_password  # Utiliser un mot de passe d'application
EMAIL_SENDER=your.email@gmail.com
ADMIN_EMAIL_RECIPIENT=admin@yourcompany.com
```

### Office 365
```env
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USERNAME=your.email@yourcompany.com
EMAIL_PASSWORD=your_password
EMAIL_SENDER=your.email@yourcompany.com
ADMIN_EMAIL_RECIPIENT=admin@yourcompany.com
```

## Notes de Sécurité

1. Ne jamais commiter le fichier `.env` dans le contrôle de version
2. Utiliser des mots de passe d'application pour Gmail
3. S'assurer que les ports SMTP sont ouverts dans le pare-feu
4. Utiliser TLS pour le chiffrement des communications

## Dépannage

Si les notifications ne fonctionnent pas :

1. Vérifier que toutes les variables sont correctement définies
2. Tester la connexion SMTP avec un client e-mail
3. Vérifier les logs pour les erreurs SMTP
4. S'assurer que le serveur SMTP autorise l'authentification 