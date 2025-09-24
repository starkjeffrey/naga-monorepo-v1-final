# Makefile
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make local       - Start local development environment"
	@echo "  make local-tools - Start local with dev tools (mailpit, pgadmin)"
	@echo "  make staging     - Build for staging deployment"
	@echo "  make test        - Run tests in Docker"
	@echo "  make clean       - Stop and remove all containers"
	@echo "  make reset       - Clean + remove volumes (fresh start)"

local:
	docker-compose -f docker-compose.yml -f docker-compose.local.yml up

local-tools:
	docker-compose -f docker-compose.yml -f docker-compose.local.yml --profile tools up

staging:
	docker-compose -f docker-compose.yml -f docker-compose.staging.yml build

test:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml run --rm django pytest

clean:
	docker-compose down --remove-orphans

reset:
	docker-compose down --volumes --remove-orphans
	docker system prune -f

logs:
	docker-compose logs -f

shell:
	docker-compose exec django python manage.py shell

makemigrations:
	docker-compose exec django python manage.py makemigrations

migrate:
	docker-compose exec django python manage.py migrate

build:
	docker-compose build --no-cache
