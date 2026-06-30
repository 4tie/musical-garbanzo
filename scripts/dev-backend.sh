#!/bin/bash
# Development script to start the HER backend server

# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH to include backend directory
export PYTHONPATH=/home/mohs/Desktop/her/backend

# Run uvicorn with hot reload
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
