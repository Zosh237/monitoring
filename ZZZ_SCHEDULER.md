# Implémentation du Scheduler

## 1. Structure du Module

Le module `app/core/scheduler.py` implémente un planificateur de tâches utilisant APScheduler en mode BackgroundScheduler. Il est responsable de l'exécution périodique du scanner de sauvegardes.

### Composants Principaux

- **BackgroundScheduler** : Planificateur qui s'exécute en arrière-plan
- **run_scanner_job** : Fonction wrapper qui gère l'exécution du scanner
- **start_scheduler** : Fonction de démarrage du planificateur
- **shutdown_scheduler** : Fonction d'arrêt propre du planificateur

## 2. Configuration

### Paramètres

- `SCANNER_INTERVAL_MINUTES` : Intervalle d'exécution du scanner (défaut : 15 minutes)
- `MISFIRE_GRACE_TIME` : Tolérance pour les exécutions manquées (60 secondes)

### Intégration

Le scheduler est intégré à l'application FastAPI via les événements de démarrage et d'arrêt :

```python
@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()
```

## 3. Tests

### Structure des Tests

Les tests sont organisés dans `tests/test_scheduler.py` et couvrent les aspects suivants :

1. **Démarrage et Arrêt**
   - Vérification du démarrage correct du scheduler
   - Vérification de l'arrêt propre
   - Gestion des cas où le scheduler est déjà en cours/arrêté

2. **Exécution des Jobs**
   - Vérification de l'ajout correct du job
   - Vérification de l'exécution du job avec les bons paramètres
   - Gestion des sessions de base de données

3. **Gestion des Erreurs**
   - Vérification de la gestion des exceptions
   - Vérification de la journalisation des erreurs
   - Vérification de la fermeture des ressources en cas d'erreur

### Fixtures

```python
@pytest.fixture(autouse=True)
def reset_scheduler_state():
    """Réinitialise l'état du scheduler avant et après chaque test"""
    if scheduler.running:
        scheduler.shutdown(wait=True)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=True)

@pytest.fixture
def mock_db_session():
    """Mock d'une session SQLAlchemy"""
    return MagicMock(spec=Session)

@pytest.fixture
def mock_session_local(mock_db_session):
    """Mock de SessionLocal"""
    with patch('app.core.scheduler.SessionLocal') as mock:
        mock.return_value = mock_db_session
        yield mock

@pytest.fixture
def mock_run_scanner():
    """Mock de la fonction run_scanner"""
    with patch('app.core.scheduler.run_scanner') as mock:
        yield mock

@pytest.fixture
def mock_settings():
    """Mock des paramètres de configuration"""
    with patch('app.core.scheduler.settings') as mock_settings:
        mock_settings.SCANNER_INTERVAL_MINUTES = 0.1
        yield mock_settings
```

### Améliorations Récentes

1. **Correction des Chemins de Patching**
   - Utilisation des chemins corrects pour les mocks (`app.core.scheduler` au lieu de `app.services.scanner`)
   - Meilleure isolation des tests

2. **Simplification des Tests**
   - Appel direct de `run_scanner_job()` pour les tests unitaires
   - Suppression des vérifications redondantes
   - Meilleure gestion des assertions

3. **Gestion de la Base de Données**
   - Initialisation correcte de la base de données avec le schéma complet
   - Support de la colonne `neighborhood` dans le modèle `ExpectedBackupJob`

4. **Robustesse**
   - Utilisation de `wait=True` pour le shutdown du scheduler
   - Meilleure gestion des délais d'attente
   - Vérifications plus strictes des conditions

## 4. Journalisation

Le module utilise le logging pour tracer son activité :

```python
logger = logging.getLogger(__name__)
```

Les événements importants sont journalisés :
- Démarrage/arrêt du scheduler
- Ajout de jobs
- Exécution de jobs
- Erreurs et exceptions

## 5. Sécurité

- Le scheduler s'exécute dans un thread séparé
- Les sessions de base de données sont correctement fermées
- Les exceptions sont capturées et journalisées
- Les ressources sont libérées proprement

## 6. Maintenance

### Points d'Attention

1. **Configuration**
   - Vérifier les paramètres d'intervalle selon les besoins
   - Ajuster le `misfire_grace_time` si nécessaire

2. **Tests**
   - Maintenir la couverture de tests
   - Vérifier les mocks lors des modifications
   - S'assurer que la base de données est correctement initialisée

3. **Monitoring**
   - Surveiller les logs pour détecter les problèmes
   - Vérifier l'état du scheduler dans l'application

### Améliorations Futures

1. **Tests**
   - Ajouter des tests de performance
   - Implémenter des tests de charge
   - Améliorer la couverture des cas d'erreur

2. **Fonctionnalités**
   - Ajouter la possibilité de modifier l'intervalle à chaud
   - Implémenter un système de retry pour les jobs échoués
   - Ajouter des métriques de monitoring

3. **Documentation**
   - Ajouter des exemples d'utilisation
   - Documenter les cas d'erreur courants
   - Maintenir la documentation des tests à jour

## 7. Prochaines Étapes Possibles

1. **Améliorations**
   - Ajout de métriques de performance
   - Implémentation de retry policies
   - Support de jobs multiples

2. **Monitoring**
   - Intégration avec un système de monitoring
   - Alertes automatiques
   - Tableau de bord de statut

3. **Documentation**
   - Guide d'utilisation détaillé
   - Exemples de configuration
   - Procédures de troubleshooting

## 8. Conclusion

L'implémentation du scheduler répond aux besoins de base tout en restant extensible pour des fonctionnalités futures. La robustesse et la maintenabilité ont été privilégiées, avec une attention particulière portée aux tests et à la documentation. 