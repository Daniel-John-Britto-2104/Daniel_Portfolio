"""
Configuration helper for the LiveKit Real-Time Gemini Voice Agent.
Loads environment variables safely and deterministically regardless of
the current working directory.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv


AGENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AGENT_DIR.parent


def find_project_root(start_dir: Optional[Path] = None) -> Path:
    """
    Locates the project root directory containing manage.py or .env.
    """
    current = (start_dir or Path.cwd()).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "manage.py").exists() or (parent / "portfolio" / "settings.py").exists():
            return parent
    return PROJECT_ROOT


def find_root_env_file(start_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Locates the root .env file regardless of current working directory.
    """
    root = find_project_root(start_dir)
    env_path = root / ".env"
    if env_path.is_file():
        return env_path

    # Fallback check in AGENT_DIR / .env
    agent_env = AGENT_DIR / ".env"
    if agent_env.is_file():
        return agent_env

    return None


@dataclass
class AgentConfig:
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    google_api_key: str = ""
    gemini_live_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    gemini_live_voice: str = "Puck"
    enable_webrtc_voice: bool = True
    env_file_loaded: Optional[str] = None
    missing_required_keys: List[str] = field(default_factory=list)

    @property
    def is_configured(self) -> bool:
        return len(self.missing_required_keys) == 0


def load_agent_config(env_file_path: Optional[Path] = None, override: bool = False) -> AgentConfig:
    """
    Loads agent configuration from environment and .env file.
    Preserves explicitly set OS environment variables when override=False.
    """
    target_env = env_file_path or find_root_env_file()
    if target_env and target_env.is_file():
        load_dotenv(target_env, override=override)
        loaded_str = str(target_env)
    else:
        loaded_str = None

    url = os.environ.get("LIVEKIT_URL", "").strip()
    api_key = os.environ.get("LIVEKIT_API_KEY", "").strip()
    api_secret = os.environ.get("LIVEKIT_API_SECRET", "").strip()
    google_key = (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip()
    model = os.environ.get("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025").strip()
    voice = os.environ.get("GEMINI_LIVE_VOICE", "Puck").strip()
    enable_webrtc = os.environ.get("ENABLE_WEBRTC_VOICE", "True").lower() in {"true", "1", "yes"}

    missing = []
    if not url:
        missing.append("LIVEKIT_URL")
    if not api_key:
        missing.append("LIVEKIT_API_KEY")
    if not api_secret:
        missing.append("LIVEKIT_API_SECRET")
    if not google_key:
        missing.append("GOOGLE_API_KEY")

    return AgentConfig(
        livekit_url=url,
        livekit_api_key=api_key,
        livekit_api_secret=api_secret,
        google_api_key=google_key,
        gemini_live_model=model,
        gemini_live_voice=voice,
        enable_webrtc_voice=enable_webrtc,
        env_file_loaded=loaded_str,
        missing_required_keys=missing,
    )
