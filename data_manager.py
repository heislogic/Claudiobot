import json
import os
import threading
from typing import Dict, Any, Optional

DATA_FILE = "data.json"
_lock = threading.Lock()

def _carregar_arquivo() -> Dict[str, Any]:
    """Carrega o JSON do disco, retorna estrutura padrão se não existir."""
    if not os.path.exists(DATA_FILE):
        return {"formularios_pendentes": {}, "tickets_ativos": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # Se corrompido, retorna vazio (pode perder dados, mas evita crash)
        return {"formularios_pendentes": {}, "tickets_ativos": {}}

def _salvar_arquivo(dados: Dict[str, Any]) -> None:
    """Salva os dados no JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

# --- Operações com formulários pendentes ---
def adicionar_formulario_pendente(message_id: int, channel_id: int, user_id: int, nickname: str, classe: str) -> None:
    with _lock:
        dados = _carregar_arquivo()
        key = f"{message_id}_{channel_id}"  # chave única
        dados["formularios_pendentes"][key] = {
            "message_id": message_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "nickname": nickname,
            "classe": classe
        }
        _salvar_arquivo(dados)

def remover_formulario_pendente(message_id: int, channel_id: int) -> None:
    with _lock:
        dados = _carregar_arquivo()
        key = f"{message_id}_{channel_id}"
        if key in dados["formularios_pendentes"]:
            del dados["formularios_pendentes"][key]
            _salvar_arquivo(dados)

def listar_formularios_pendentes() -> Dict[str, Dict]:
    with _lock:
        dados = _carregar_arquivo()
        return dados["formularios_pendentes"].copy()

# --- Operações com tickets ativos ---
def adicionar_ticket_ativo(channel_id: int, dono_id: int, message_id: int) -> None:
    with _lock:
        dados = _carregar_arquivo()
        key = f"{channel_id}_{dono_id}"
        dados["tickets_ativos"][key] = {
            "channel_id": channel_id,
            "dono_id": dono_id,
            "message_id": message_id
        }
        _salvar_arquivo(dados)

def remover_ticket_ativo(channel_id: int, dono_id: int) -> None:
    with _lock:
        dados = _carregar_arquivo()
        key = f"{channel_id}_{dono_id}"
        if key in dados["tickets_ativos"]:
            del dados["tickets_ativos"][key]
            _salvar_arquivo(dados)

def listar_tickets_ativos() -> Dict[str, Dict]:
    with _lock:
        dados = _carregar_arquivo()
        return dados["tickets_ativos"].copy()