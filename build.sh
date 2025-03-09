#!/bin/bash

# Exit on error
set -o errexit

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Applying any necessary fixes..."
python manage.py check

echo "Build process completed successfully!"
