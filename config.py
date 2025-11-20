# config.py
import os

SETTINGS_FILE = "settings.json"
DEFAULT_KOVAAKS_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Scenarios"

# --- MASTER MODIFIER CONFIGURATION ---
MODIFIER_CONFIG = {
    "SIZE": { "display_name": "Size", "tag_text": "Size", "mod_type": "Multiplier", "scope": "Character Profile", "properties": ["MainBBRadius", "MainBBHeadRadius"], "condition": None, "suffix": "%", "value_key": "size_percentages" },
    "SPEED": { "display_name": "Speed", "tag_text": "Speed", "mod_type": "Multiplier", "scope": "Character Profile", "properties": ["MaxSpeed", "MaxCrouchSpeed"], "condition": "value > 0", "suffix": "%", "value_key": "speed_percentages" },
    "TIMESCALE": { "display_name": "Timescale", "tag_text": "tScale", "mod_type": "Multiplier", "scope": "Global", "properties": ["Timescale"], "condition": None, "suffix": "%", "value_key": "timescale_percentages" },
    "DURATION": { "display_name": "Duration", "tag_text": "Dur", "mod_type": "Direct", "scope": "Global", "properties": ["Timelimit"], "condition": None, "suffix": "s", "value_key": "durations" },
    "HP": { "display_name": "HP", "tag_text": "HP", "mod_type": "Multiplier", "scope": "Character Profile", "properties": ["MaxHealth"], "condition": None, "suffix": "%", "value_key": "hp_percentages" },
    "REGEN_RATE": { "display_name": "Regen", "tag_text": "Regen", "mod_type": "Calculated", "scope": "Character Profile", "properties": ["HealthRegenPerSec"], "calculation_base": "MaxHealth", "condition": None, "suffix": "%", "value_key": "regen_percentages" }
}