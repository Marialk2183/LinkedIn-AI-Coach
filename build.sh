#!/usr/bin/env bash
# One-shot production build: install deps, train the ML model, build the frontend.
# Run this once before starting the server (see Procfile). Requires Python + Node.
set -euo pipefail

echo "==> Backend: installing Python dependencies"
cd backend
pip install -r requirements.txt

echo "==> ML: training model.pkl"
python -m ml.train

echo "==> Frontend: installing dependencies and building"
cd ../frontend
npm ci
npm run build

echo "==> Build complete. Start with: cd backend && uvicorn main:app --host 0.0.0.0 --port \$PORT"
