"""Constantes du projet et lecture de l'environnement."""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Sources de données ---
# Option A (préférée) : dépôt Git Tricoteuses, URL fixée au spike J0.
TRICOTEUSES_REPO_URL = os.getenv("TRICOTEUSES_REPO_URL", "")
# Option B (fallback) : dump quotidien officiel de la législature.
AN_DUMP_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository/17/"
    "loi/amendements_div_legis/Amendements.json.zip"
)

# --- Albert API ---
ALBERT_BASE_URL = "https://albert.api.etalab.gouv.fr/v1"
ALBERT_API_KEY = os.getenv("ALBERT_API_KEY", "")
TOP_K = int(os.getenv("TOP_K", "10"))
EMBED_MAX_CHARS = 8_000

# --- Grist ---
GRIST_BASE_URL = os.getenv("GRIST_BASE_URL", "https://grist.numerique.gouv.fr")
GRIST_API_KEY = os.getenv("GRIST_API_KEY", "")
GRIST_DOC_ID = os.getenv("GRIST_DOC_ID", "")

# --- Tchap ---
TCHAP_HOMESERVER = os.getenv("TCHAP_HOMESERVER", "")
TCHAP_BOT_MATRIX_ID = os.getenv("TCHAP_BOT_MATRIX_ID", "")
TCHAP_BOT_PWD = os.getenv("TCHAP_BOT_PWD", "")
TCHAP_ROOM_ID = os.getenv("TCHAP_ROOM_ID", "")

# --- Cache local ---
DATA_DIR = "data"
