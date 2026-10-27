#!/bin/sh
# Aplica as migrações do banco e inicia a aplicação.
set -eu
safecat migrate
exec streamlit run /app/streamlit_app.py \
    --server.port="${PORT:-8502}" \
    --server.address=0.0.0.0 \
    --server.headless=true
