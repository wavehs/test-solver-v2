import json
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "trigger_hotkey": "<ctrl>+<alt>+z",
    "reveal_hotkey": "<alt>", # This is actually just the key name, logic handles press/release
    "overlay_position": "Top-Right",
    "overlay_offset_x": 50,
    "overlay_offset_y": 20,
    "overlay_opacity": 0.8,
    "overlay_size": 12,
    "overlay_font_size": 12,
    "overlay_text_color": "#00FF00",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-pro"
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            # Merge with defaults in case of missing keys
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        logger.info("Config saved.")
    except Exception as e:
        logger.error(f"Error saving config: {e}")
