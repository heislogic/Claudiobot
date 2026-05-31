import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Canais e cargos (IDs fixos)
CANAL_STAFF_ID = 1509687523268493510
CARGO_STAFF_ID = 1450345042202853408

# Categorias por classe
CATEGORIAS_POR_CLASSE = {
    "DPS": 1510032279865655387,
    "HEALER": 1510032296680362034,
    "TANK": 1510032314854408282
}

# Emojis por classe
EMOJIS_POR_CLASSE = {
    "DPS": "🔪",
    "HEALER": "🚑",
    "TANK": "🔰"
}

# Build leaders por classe
BUILD_LEADER_POR_CLASSE = {
    "DPS": 1510042154947313724,
    "HEALER": 1510042369406402580,
    "TANK": 1510042326125248534
}