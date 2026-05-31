import sqlite3
import os
from typing import Dict, Any, List, Optional

DB_PATH = "data/bot.db"

class DatabaseManager:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Garante que o diretório data existe e cria as tabelas necessárias."""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Tabela de formulários pendentes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS formularios_pendentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                nickname TEXT NOT NULL,
                classe TEXT NOT NULL
            )
        """)

        # Tabela de tickets ativos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets_ativos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                dono_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        print("Banco de dados SQLite inicializado em", DB_PATH)

    # --- Formulários pendentes ---
    def adicionar_formulario_pendente(self, message_id: int, channel_id: int, user_id: int, nickname: str, classe: str) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO formularios_pendentes (message_id, channel_id, user_id, nickname, classe)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, channel_id, user_id, nickname, classe))
        conn.commit()
        conn.close()

    def remover_formulario_pendente(self, message_id: int, channel_id: int) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM formularios_pendentes WHERE message_id = ? AND channel_id = ?
        """, (message_id, channel_id))
        conn.commit()
        conn.close()

    def listar_formularios_pendentes(self) -> Dict[str, Dict]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT message_id, channel_id, user_id, nickname, classe FROM formularios_pendentes")
        rows = cursor.fetchall()
        conn.close()
        result = {}
        for row in rows:
            key = f"{row[0]}_{row[1]}"
            result[key] = {
                "message_id": row[0],
                "channel_id": row[1],
                "user_id": row[2],
                "nickname": row[3],
                "classe": row[4]
            }
        return result

    # --- Tickets ativos ---
    def adicionar_ticket_ativo(self, channel_id: int, dono_id: int, message_id: int) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickets_ativos (channel_id, dono_id, message_id)
            VALUES (?, ?, ?)
        """, (channel_id, dono_id, message_id))
        conn.commit()
        conn.close()

    def remover_ticket_ativo(self, channel_id: int, dono_id: int) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM tickets_ativos WHERE channel_id = ? AND dono_id = ?
        """, (channel_id, dono_id))
        conn.commit()
        conn.close()

    def listar_tickets_ativos(self) -> Dict[str, Dict]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, dono_id, message_id FROM tickets_ativos")
        rows = cursor.fetchall()
        conn.close()
        result = {}
        for row in rows:
            key = f"{row[0]}_{row[1]}"
            result[key] = {
                "channel_id": row[0],
                "dono_id": row[1],
                "message_id": row[2]
            }
        return result

# Instância global para fácil importação
db = DatabaseManager()