# nexoradb-social-network-analysis

A complete external application for managing a live social graph using NexoraDB.

## Features

- **File Import** — Upload three-column relationship files
- **User Management** — Create, update, delete users
- **Relationship Management** — Create/delete two-way relationships
- **Live Graph** — Interactive graph visualization with PyVis
- **12 Graph Algorithms** — Lock and Job algorithms with separate buttons

## Architecture
Streamlit UI → FastAPI → NexoraDB Driver → NexoraDB API

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run FastAPI backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8100

# Run Streamlit UI (in another terminal)
streamlit run ui/Home.py
