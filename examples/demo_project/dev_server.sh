#!/bin/bash
# This script automates the process of reinstalling the library and running the server.

# Uninstall the package without confirmation
python -m pip uninstall -y django-solana-payments

python -m pip install python-dotenv
# Install the package in editable mode
python -m pip install -e "../../.[drf,dev,django-payments,docs]"

# Run the development server
python manage.py runserver
