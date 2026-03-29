import os
from pathlib import Path
from dotenv import load_dotenv
from agno.models.openai import OpenAIResponses

def _is_placeholder(value: str | None) -> bool:
    if not value:
        return False
    v = value.strip()
    return v.startswith("${") and v.endswith("}")

_dotenv_path = Path(__file__).resolve().parents[2] / ".env"
_override = _is_placeholder(os.getenv("OPENAI_API_KEY"))
if _dotenv_path.exists():
    load_dotenv(dotenv_path=_dotenv_path, override=_override)
else:
    load_dotenv(override=_override)

def _try_load_openai_key_from_windows_registry():
    if os.name != "nt":
        return
    current = os.getenv("OPENAI_API_KEY")
    if current and not _is_placeholder(current):
        return
    try:
        import winreg
    except Exception:
        return

    def _read(hive, subkey: str) -> str | None:
        try:
            with winreg.OpenKey(hive, subkey) as k:
                val, typ = winreg.QueryValueEx(k, "OPENAI_API_KEY")
                if not isinstance(val, str) or not val.strip():
                    return None
                if typ == winreg.REG_EXPAND_SZ:
                    val = os.path.expandvars(val)
                return val.strip()
        except Exception:
            return None

    value = _read(winreg.HKEY_CURRENT_USER, r"Environment") or _read(
        winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    )
    if value and not _is_placeholder(value):
        os.environ["OPENAI_API_KEY"] = value

_try_load_openai_key_from_windows_registry()

def obter_modelo_openai():
    return OpenAIResponses(id=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"))
