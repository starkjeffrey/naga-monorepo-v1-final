#!/bin/bash
# Create backend worktree and start development
git worktree add ../naga-backend-worktree main
cd ../naga-backend-worktree/backend
pip install -r requirements/local.txt
python manage.py runserver
