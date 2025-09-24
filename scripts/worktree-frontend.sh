#!/bin/bash
# Create frontend worktree and start development
git worktree add ../naga-frontend-worktree main
cd ../naga-frontend-worktree/frontend
npm install
npm run dev
