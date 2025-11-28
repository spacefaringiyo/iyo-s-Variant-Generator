# config.py
import os
import sys
from pathlib import Path

# Determine if we are running as a script or a frozen exe
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

def detect_kovaaks_path():
    """Iterates through common Steam installation roots to find the scenarios folder."""
    home = Path.home()
    
    # The fixed path inside any Steam Library
    # Note: KovaaK's has a double 'FPSAimTrainer' folder structure
    game_path_suffix = Path("steamapps/common/FPSAimTrainer/FPSAimTrainer/Saved/SaveGames/Scenarios")
    
    # Potential Steam Roots (The part that varies by OS/Drive)
    steam_roots = [
        # Windows - Standard
        Path(r"C:\Program Files (x86)\Steam"),
        # Windows - Common Secondary Drive
        Path(r"D:\SteamLibrary"),
        
        # Linux - Native Steam (Debian/Arch/Fedora etc)
        home / ".steam/steam",
        home / ".local/share/Steam",
        
        # Linux - Flatpak (Steam Deck / Mint / PopOS)
        home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
        home / ".var/app/com.valvesoftware.Steam/.steam/steam",

        # Linux - Snap (Ubuntu)
        home / "snap/steam/common/.local/share/Steam",

        # Linux - Custom Mounts
        Path("/mnt/Games/SteamLibrary"),
    ]

    for root in steam_roots:
        full_path = root / game_path_suffix
        if full_path.exists():
            return str(full_path)
            
    # Fallback: Return the standard Windows path even if it doesn't exist
    return str(steam_roots[0] / game_path_suffix)

DEFAULT_KOVAAKS_PATH = detect_kovaaks_path()


# --- MASTER MODIFIER CONFIGURATION ---
MODIFIER_CONFIG = {
    "SIZE": { "display_name": "Size", "tag_text": "Size", "mod_type": "Multiplier", "scope": "Character Profile", "properties": ["MainBBRadius", "MainBBHeadRadius"], "condition": None, "suffix": "%", "value_key": "size_percentages" },
    "SPEED": { "display_name": "Speed", "tag_text": "Speed", "mod_type": "Multiplier", "scope": "Character Profile", "properties": ["MaxSpeed", "MaxCrouchSpeed"], "condition": "value > 0", "suffix": "%", "value_key": "speed_percentages" },
    "TIMESCALE": { "display_name": "Timescale", "tag_text": "tScale", "mod_type": "Multiplier", "scope": "Global", "properties": ["Timescale"], "condition": None, "suffix": "%", "value_key": "timescale_percentages" },
    "DURATION": { "display_name": "Duration", "tag_text": "Dur", "mod_type": "Direct", "scope": "Global", "properties": ["Timelimit"], "condition": None, "suffix": "s", "value_key": "durations" },
    "HP": { "display_name": "HP", "tag_text": "HP", "mod_type": "Multiplier", "scope": "Character Profile", "properties": ["MaxHealth"], "condition": None, "suffix": "%", "value_key": "hp_percentages" },
    "REGEN_RATE": { "display_name": "Regen", "tag_text": "Regen", "mod_type": "Calculated", "scope": "Character Profile", "properties": ["HealthRegenPerSec"], "calculation_base": "MaxHealth", "condition": None, "suffix": "%", "value_key": "regen_percentages" }
}