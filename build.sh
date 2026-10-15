#!/usr/bin/env bash
# Exit immediately if a critical command exits with a non-zero status
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations (auto-seeds portfolio tables & resume knowledge via data migrations)
python manage.py migrate

# Seed portfolio website data (profile, skills, projects, experience, etc.)
python manage.py seed_data || true

# Seed verified resume knowledge chunks into database
python manage.py load_resume_knowledge || true

