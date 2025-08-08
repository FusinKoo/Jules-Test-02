from pathlib import Path
import os
import json

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "configs"


def get_config(profile: str | None = None) -> dict:
    """Load configuration with priority: ENV > YAML defaults."""
    with open(CONFIG_DIR / "defaults.yaml", "r", encoding="utf-8") as f:
        config = json.load(f)

    # Determine profile
    profile = profile or os.getenv("MIX_PROFILE") or config.get("quality_profile")
    if profile:
        qp_path = CONFIG_DIR / "quality_profiles.yaml"
        if qp_path.exists():
            with open(qp_path, "r", encoding="utf-8") as f:
                profiles = json.load(f)
            config.update(profiles.get(profile, {}))
        config["quality_profile"] = profile

    # Environment overrides
    if (env_tracks := os.getenv("MIX_TRACKS")):
        config["tracks"] = [x.strip() for x in env_tracks.split(",") if x.strip()]
    if (env_track := os.getenv("MIX_TRACK_LUFS")) is not None:
        config["track_lufs"] = float(env_track)
    if (env_mix := os.getenv("MIX_MIX_LUFS")) is not None:
        config["mix_lufs"] = float(env_mix)

    return config
