.PHONY: help build up down restart logs shell shell-django shell-db migrate makemigrations createsuperuser test clean prune

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

build: ## Build tous les services
	sudo docker compose build

up: ## Démarre tous les services
	sudo docker compose up -d

down: ## Arrête tous les services
	sudo docker compose down

restart: ## Redémarre tous les services
	sudo docker compose restart

logs: ## Affiche les logs de tous les services
	sudo docker compose logs -f

logs-django: ## Affiche les logs de Django
	sudo docker compose logs -f django

logs-celery: ## Affiche les logs de Celery
	sudo docker compose logs -f celery

logs-nextjs: ## Affiche les logs de Next.js
	sudo docker compose logs -f nextjs

shell: ## Ouvre un shell dans le container Django
	sudo docker compose exec django /bin/bash

shell-django: ## Ouvre le shell Django
	sudo docker compose exec django python manage.py shell

shell-db: ## Ouvre le shell PostgreSQL
	sudo docker compose exec postgres psql -U altiusfidu_user -d altiusfidu

migrate: ## Exécute les migrations Django
	sudo docker compose exec django python manage.py migrate

makemigrations: ## Crée les migrations Django
	sudo docker compose exec django python manage.py makemigrations

createsuperuser: ## Crée un superuser Django
	sudo docker compose exec django python manage.py createsuperuser

collectstatic: ## Collecte les fichiers statiques
	sudo docker compose exec django python manage.py collectstatic --noinput

test: ## Exécute les tests Django
	sudo docker compose exec django python manage.py test

test-coverage: ## Exécute les tests avec coverage
	sudo docker compose exec django coverage run --source='.' manage.py test
	sudo docker compose exec django coverage report

ps: ## Liste les containers en cours d'exécution
	sudo docker compose ps

clean: ## Arrête et supprime les containers et volumes (garde les images)
	@echo "🧹 Nettoyage des containers et volumes..."
	-sudo docker compose down -v 2>/dev/null || true
	-sudo docker compose rm -f -v 2>/dev/null || true
	@echo "✅ Nettoyage terminé"

clean-all: ## Nettoie tout (containers, volumes, images non utilisées)
	@echo "🧹 Nettoyage complet (containers, volumes, images)..."
	-sudo docker compose down -v --rmi local 2>/dev/null || true
	-sudo docker system prune -f 2>/dev/null || true
	@echo "✅ Nettoyage complet terminé"

prune: ## Nettoie TOUT Docker (⚠️ ATTENTION: supprime tout, même autres projets)
	@echo "⚠️  ATTENTION: Ceci va supprimer TOUS les containers, volumes et images Docker"
	@echo "   (même ceux d'autres projets)"
	@read -p "Êtes-vous sûr? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "🧹 Nettoyage complet de Docker..."; \
		sudo docker compose down -v --rmi all 2>/dev/null || true; \
		sudo docker system prune -af --volumes; \
		echo "✅ Nettoyage total terminé"; \
	else \
		echo "❌ Annulé"; \
	fi

rebuild: ## Rebuild et redémarre les services
	@echo "🔄 Rebuild complet..."
	sudo docker compose down
	sudo docker compose build --no-cache
	sudo docker compose up -d
	@echo "✅ Rebuild terminé"

init: ## Initialise le projet (première installation)
	@echo "📦 Initialisation du projet AltiusFidu..."
	@if [ ! -f .env ]; then \
		echo "📄 Copie du fichier .env..."; \
		cp .env.example .env 2>/dev/null || echo "⚠️  Fichier .env.example non trouvé"; \
	else \
		echo "✅ Fichier .env existe déjà"; \
	fi
	@echo "🏗️  Build des images Docker..."
	sudo docker compose build
	@echo "🚀 Démarrage des services..."
	sudo docker compose up -d
	@echo "⏳ Attente du démarrage de la base de données..."
	sleep 10
	@echo "🔄 Exécution des migrations..."
	sudo docker compose exec django python manage.py migrate
	@echo "📊 Collecte des fichiers statiques..."
	sudo docker compose exec django python manage.py collectstatic --noinput
	@echo "✅ Projet initialisé avec succès!"
	@echo "👤 Créez maintenant un superuser avec: make createsuperuser"

backup-db: ## Sauvegarde la base de données
	@mkdir -p backups
	sudo docker compose exec postgres pg_dump -U altiusfidu_user altiusfidu > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup créé dans backups/"

restore-db: ## Restaure la base de données (BACKUP_FILE=chemin/vers/backup.sql)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ Erreur: Spécifiez BACKUP_FILE=chemin/vers/backup.sql"; \
		exit 1; \
	fi
	sudo docker compose exec -T postgres psql -U altiusfidu_user altiusfidu < $(BACKUP_FILE)
	@echo "✅ Backup restauré"

dev: ## Mode développement avec hot-reload
	sudo docker compose -f docker-compose.yml -f docker-compose.dev.yml up

prod: ## Mode production
	sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

status: ## Affiche le statut des services
	@echo "📊 Status des services AltiusFidu:"
	@sudo docker compose ps

# health: ## Vérifie la santé des services
# 	@echo "🏥 Vérification de la santé des services..."
# 	@sudo docker compose exec django python manage.py check || echo "❌ Django n'est pas prêt"
# 	@curl -f http://localhost:8000/health/ 2>/dev/null || echo "❌ Django n'est pas accessible"
# 	@curl -f http://localhost:3000/ 2>/dev/null || echo "❌ Next.js n'est pas accessible"
# 	@sudo docker compose exec redis redis-cli ping || echo "❌ Redis n'est pas accessible"

install-hooks: ## Installe les pre-commit hooks
	@echo "🎣 Installation des pre-commit hooks..."
	pip install pre-commit
	pre-commit install
	@echo "✅ Hooks installés"

format: ## Formate le code Python avec black et isort
	sudo docker compose exec django black .
	sudo docker compose exec django isort .

lint: ## Vérifie la qualité du code
	sudo docker compose exec django flake8 .
	sudo docker compose exec django pylint apps/

# Commandes de dépannage
stop-all: ## Force l'arrêt de tous les containers du projet
	@echo "🛑 Arrêt forcé de tous les containers..."
	-sudo docker stop $$(sudo docker ps -q --filter "name=altiusfidu") 2>/dev/null || true
	@echo "✅ Tous les containers arrêtés"

remove-all: ## Supprime tous les containers du projet (même arrêtés)
	@echo "🗑️  Suppression de tous les containers AltiusFidu..."
	-sudo docker rm -f $$(sudo docker ps -aq --filter "name=altiusfidu") 2>/dev/null || true
	@echo "✅ Tous les containers supprimés"

remove-volumes: ## Supprime tous les volumes du projet
	@echo "🗑️  Suppression des volumes AltiusFidu..."
	-sudo docker volume rm $$(sudo docker volume ls -q --filter "name=altiusfidu") 2>/dev/null || true
	@echo "✅ Tous les volumes supprimés"

remove-images: ## Supprime toutes les images du projet
	@echo "🗑️  Suppression des images AltiusFidu..."
	-sudo docker rmi $$(sudo docker images -q "altiusfidu*") 2>/dev/null || true
	@echo "✅ Toutes les images supprimées"

reset: ## Reset complet du projet (⚠️ supprime tout: containers, volumes, images)
	@echo "⚠️  ATTENTION: Reset complet du projet AltiusFidu"
	@read -p "Êtes-vous sûr? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(MAKE) stop-all; \
		$(MAKE) remove-all; \
		$(MAKE) remove-volumes; \
		$(MAKE) remove-images; \
		echo "✅ Reset complet terminé"; \
		echo "💡 Utilisez 'make init' pour réinitialiser"; \
	else \
		echo "❌ Annulé"; \
	fi