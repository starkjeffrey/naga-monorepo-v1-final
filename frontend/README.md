
# PUCSR Student Information System

A comprehensive student information system for language schools and universities, consisting of a Django backend API and Vue 3 frontend application.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Project Structure

```
naga/
├── backend/          # Django backend (API & web interface)
│   ├── apps/         # Django applications
│   ├── api/          # API endpoints
│   ├── config/       # Django configuration
│   ├── manage.py     # Django management
│   └── docker-compose.local.yml
├── frontend/         # Vue 3 frontend application
│   ├── src/          # Vue source code (to be copied)
│   └── Dockerfile
└── README.md         # This file
```

## Getting Started

### Backend (Django)

1. Navigate to the backend directory:
   ```bash
   cd backend/
   ```

2. Start the development environment:
   ```bash
   docker compose -f docker-compose.local.yml up
   ```

3. Run migrations (first time setup):
   ```bash
   docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
   ```

The backend will be available at:
- **Web Interface**: http://localhost:8000
- **API**: http://localhost:8000/api/
- **Admin**: http://localhost:8000/admin/

### Frontend (Vue 3)

1. Copy your existing Vue 3 project files into the `frontend/` directory
2. Navigate to the frontend directory and follow Vue 3 setup instructions

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Testing

### Running Unit and Integration Tests

The project uses pytest with PostgreSQL test containers for comprehensive testing. Tests are configured to run against a PostgreSQL database to match the production environment.

#### Quick Test Run (Local Development)

```bash
cd backend/
pytest
```

#### Running Tests with Test Containers

For isolated testing with clean containers:

```bash
cd backend/
docker compose -f docker-compose.test.yml run --rm test_runner
```

This will:
- Start PostgreSQL and Redis test containers
- Wait for database to be ready
- Run migrations on test database
- Execute all tests with pytest
- Clean up containers after completion

#### Test Configuration

- **Test Database**: PostgreSQL (matches production)
- **Test Settings**: `config.settings.test`
- **Coverage**: Enabled by default with `--cov=naga`
- **Auto DB Access**: All tests have database access enabled automatically

#### Running Specific Test Suites

**Financial Models Tests:**
```bash
cd backend/
docker compose -f docker-compose.test.yml run --rm django pytest apps/finance/tests/ -v
```

**Individual Test Files:**
```bash
cd backend/
docker compose -f docker-compose.test.yml run --rm django pytest apps/finance/tests/test_models/test_discount_models.py -v
```

#### Test Coverage Report

```bash
cd backend/
pytest --cov=naga --cov-report=html
open htmlcov/index.html
```

### Test Environment Variables

When running tests manually, ensure these are set:
- `DJANGO_SETTINGS_MODULE=config.settings.test`
- `DATABASE_URL` points to test database

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    $ mypy naga

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html#using-webpack-or-gulp).

### Celery

This app comes with Celery.

To run a celery worker:

```bash
cd naga
celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important _where_ the celery commands are run. If you are in the same folder with _manage.py_, you should be right.

To run [periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html), you'll need to start the celery beat scheduler service. You can start it as a standalone process:

```bash
cd naga
celery -A config.celery_app beat
```

or you can embed the beat service inside a worker with the `-B` option (not recommended for production use):

```bash
cd naga
celery -A config.celery_app worker -B -l info
```

### Email Server

In development, it is often nice to be able to see emails that are being sent from your application. For that reason local SMTP server [Mailpit](https://github.com/axllent/mailpit) with a web interface is available as docker container.

Container mailpit will start automatically when you will run all docker containers.
Please check [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally-docker.html) for more details how to start all containers.

With Mailpit running, to view messages that are sent by your application, open your browser and go to `http://127.0.0.1:8025`

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).
# Test push without pre-commit hooks
