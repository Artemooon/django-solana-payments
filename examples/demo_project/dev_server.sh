#!/bin/bash
# This script automates the process of reinstalling the library and running the server.

# Uninstall the package without confirmation
pip3 uninstall -y django-solana-payments

# Install the package in editable mode
pip3 install -e ../../.

# Run the development server
python manage.py runserver
