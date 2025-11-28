# scenario_logic.py
import os
import re
import json
from config import MODIFIER_CONFIG, SETTINGS_FILE, DEFAULT_KOVAAKS_PATH

def get_variant_tag(tag_text, suffix, value):
    if suffix == "s": return f"{tag_text} {value}s"
    else: return f"{tag_text} {value}%"

def get_base_scenario_name(full_name, current_tags):
    base_name = full_name
    for tag in current_tags:
        pattern = r' (\b' + re.escape(tag) + r'\b .*?)(?=( \b[A-Z][a-z]*\b|$))'
        base_name = re.split(pattern, base_name, maxsplit=1)[0]
    return base_name.strip()

def calculate_target_filename(base_name, variant_type, value, variant_configs):
    """Calculates the final filename using the Swap vs Stack logic."""
    config = MODIFIER_CONFIG[variant_type.upper()]
    ui_config = variant_configs[variant_type.upper()]
    variant_tag = get_variant_tag(ui_config['tag_text'], ui_config['suffix'], value)
    
    current_tag_text = ui_config['tag_text']
    existing_tag_pattern = r' (\b' + re.escape(current_tag_text) + r'\b \d+s?)'
    if ui_config['suffix'] == '%':
         existing_tag_pattern = r' (\b' + re.escape(current_tag_text) + r'\b \d+%)'
    
    match = re.search(existing_tag_pattern, base_name)
    
    # LOGIC: Swap ONLY if Direct (Duration), otherwise Stack
    if match and config['mod_type'] == 'Direct':
        new_name = base_name.replace(match.group(1), f" {variant_tag}")
    else:
        new_name = f"{base_name} {variant_tag}"
        
    return new_name

def get_default_profile():
    # 1. Define the available values
    # (Updated Timescale list to start with 40 as requested)
    size_vals = [50, 60, 70, 80, 90, 110, 120, 130, 140, 150, 200]
    speed_vals = [50, 60, 70, 80, 90, 110, 120, 130, 140, 150, 200]
    timescale_vals = [40, 50, 60, 70, 80, 90, 110, 120, 130, 150, 200]
    dur_vals = [15, 30, 45, 60, 90, 120]
    hp_vals = [20, 50, 80, 90, 110, 130, 150, 200, 300]
    regen_vals = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    profile = {
        "folder_path": DEFAULT_KOVAAKS_PATH,
        "size_percentages": size_vals,
        "speed_percentages": speed_vals,
        "timescale_percentages": timescale_vals,
        "durations": dur_vals,
        "hp_percentages": hp_vals,
        "regen_percentages": regen_vals,
        "checkboxes": {}, 
        "variant_tags": {key: config['tag_text'] for key, config in MODIFIER_CONFIG.items()}
    }

    # 2. Define exactly which values should be CHECKED by default.
    # If a value is in this list, the box will be checked. If not, it's unchecked.
    defaults_to_check = {
        "SIZE": [50, 70, 90, 110, 130, 150, 200],
        "SPEED": [50, 70, 90, 110],
        "TIMESCALE": [40, 60, 80, 90],
        "DURATION": [15, 30, 90],
        "HP": [],           # All unchecked
        "REGEN_RATE": []    # All unchecked
    }

    # 3. Generate the checkboxes dictionary based on the rules above
    for key, config in MODIFIER_CONFIG.items():
        value_list = profile[config['value_key']]
        for i, value in enumerate(value_list):
            # Is this value in our "Approved" list?
            is_checked = value in defaults_to_check.get(key, [])
            profile["checkboxes"][f"{key}_{i}"] = is_checked
            
    return profile

def save_settings(settings_data):
    try:
        for profile in settings_data.get("profiles", {}).values():
            if "legacy_timescale_mode" in profile: del profile["legacy_timescale_mode"]
            if "percentages" in profile: del profile["percentages"]
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f: json.dump(settings_data, f, indent=4)
        print("Settings saved.")
    except Exception as e: print(f"Error saving settings: {e}")

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            
            # 1. Basic Global Checks
            if "language" not in settings: settings["language"] = "EN"
            if "last_active_profile" not in settings: settings["last_active_profile"] = "Default"
            if "profiles" not in settings: settings["profiles"] = {"Default": get_default_profile()}
            
            # 2. Migration & Repair Logic
            default_profile = get_default_profile()
            
            for pname, profile in settings["profiles"].items():
                # Migration: Old "percentages" to specific keys
                if "percentages" in profile and "size_percentages" not in profile:
                    print(f"Migrating old settings for profile '{pname}'...")
                    profile["size_percentages"] = profile.get("percentages", default_profile["size_percentages"])
                    profile["speed_percentages"] = profile.get("percentages", default_profile["speed_percentages"])
                    profile["timescale_percentages"] = profile.get("percentages", default_profile["timescale_percentages"])
                
                # Repair: Fill in ANY missing keys from the default profile
                # This prevents crashes if we add new features (like checkboxes or regen_percentages)
                for key, default_val in default_profile.items():
                    if key not in profile:
                        profile[key] = default_val
                    elif isinstance(default_val, dict) and isinstance(profile[key], dict):
                        # Nested dictionary repair (specifically for "checkboxes" and "variant_tags")
                        for sub_key, sub_val in default_val.items():
                            if sub_key not in profile[key]:
                                profile[key][sub_key] = sub_val

            return settings
            
    except (FileNotFoundError, json.JSONDecodeError):
        # Fresh start
        return {"language": "EN", "last_active_profile": "Default", "profiles": {"Default": get_default_profile()}}

def parse_scenario_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f: lines = f.readlines()
    except Exception: return None
    
    extracted_data = { 
        "all_lines": lines, 
        "scenario_name": "N/A", 
        "player_profile_name": None, 
        "character_profiles": {}, 
        "global_properties": {} 
    }
    
    in_any_section = False
    
    for line in lines:
        line_strip = line.strip()
        if line_strip.startswith('['): in_any_section = True
        if '=' not in line: continue
        
        key_part, value_part = line.split('=', 1)
        key = key_part.strip().lower()
        value = value_part.strip()
        
        if key == "playercharacters": extracted_data["player_profile_name"] = value.split('.')[0]
        
        if not in_any_section:
            if key == "name": extracted_data["scenario_name"] = value
            
            # --- START UPDATE: Capture Type 1 & Type 2 Specifics ---
            if key == "scorepertime": extracted_data['global_properties']["ScorePerTime"] = float(value)
            
            for mod_key, config in MODIFIER_CONFIG.items():
                if config['scope'] == 'Global':
                    for prop in config['properties']:
                        if key == prop.lower(): extracted_data['global_properties'][prop] = float(value)
            
            # Scoring metrics
            if key == "scoreperhit": extracted_data['global_properties']["ScorePerHit"] = float(value)
            elif key == "scoreperdamage": extracted_data['global_properties']["ScorePerDamage"] = float(value)
            elif key == "scoreperkill": extracted_data['global_properties']["ScorePerKill"] = float(value)
            # --- END UPDATE ---

    current_profile_name = None
    in_char_profile_section = False
    
    for line in lines:
        line_strip = line.strip()
        if line_strip.lower() == "[character profile]": 
            in_char_profile_section = True
            current_profile_name = None
            continue
        if in_char_profile_section and line_strip.startswith('['): 
            in_char_profile_section = False
            current_profile_name = None
            continue
            
        if in_char_profile_section:
            if '=' not in line_strip: continue
            key, value = line_strip.split('=', 1)
            key, value = key.strip(), value.strip()
            
            if key.lower() == "name":
                current_profile_name = value
                if current_profile_name not in extracted_data["character_profiles"]: 
                    extracted_data["character_profiles"][current_profile_name] = {}
            
            if current_profile_name:
                all_char_props = set()
                for cfg in MODIFIER_CONFIG.values():
                    if cfg['scope'] == 'Character Profile':
                        all_char_props.update(cfg['properties'])
                        if cfg.get('calculation_base'): all_char_props.add(cfg['calculation_base'])
                
                # --- START UPDATE: Capture Regen & Respawn Delays ---
                if key.lower() == "healthregenpersec":
                    extracted_data["character_profiles"][current_profile_name]["HealthRegenPerSec"] = float(value)
                if key.lower() == "minrespawndelay":
                    extracted_data["character_profiles"][current_profile_name]["MinRespawnDelay"] = float(value)
                if key.lower() == "maxrespawndelay":
                    extracted_data["character_profiles"][current_profile_name]["MaxRespawnDelay"] = float(value)
                # --- END UPDATE ---

                if key in all_char_props:
                    extracted_data["character_profiles"][current_profile_name][key] = float(value)
                    
    return extracted_data

def create_variant_file(base_data, folder_path, variant_type_key, new_value, variant_configs, selected_bots):
    user_provided_name = base_data['user_provided_name'].strip()
    internal_name_to_replace = base_data['scenario_name'].strip()
    multiplier = new_value / 100.0
    config = MODIFIER_CONFIG[variant_type_key.upper()]
    v_key_upper = variant_type_key.upper()
    
    # --- DETECT SCENARIO TYPES ---
    # Type 1: Score-Based Gauntlet (ScorePerTime != 0)
    is_score_gauntlet = base_data['global_properties'].get("ScorePerTime", 0) != 0
    
    # Type 2: Degeneration Gauntlet (HealthRegenPerSec < 0 on ANY selected bot)
    is_degen_gauntlet = False
    for bot_name in selected_bots:
        bot_regen = base_data["character_profiles"].get(bot_name, {}).get("HealthRegenPerSec", 0)
        if bot_regen < 0:
            is_degen_gauntlet = True
            break
            
    # --- SKIP LOGIC ---
    if is_score_gauntlet:
        if v_key_upper == "DURATION":
            print(f"   ⏩ Skipped DURATION for {user_provided_name} (Type 1: Score Gauntlet)")
            return "skipped_incompatible"
        if v_key_upper == "HP":
            print(f"   ⏩ Skipped HP for {user_provided_name} (Type 1: Score Gauntlet)")
            return "skipped_incompatible"

    if is_degen_gauntlet:
        if v_key_upper == "HP" or v_key_upper == "REGEN_RATE":
            print(f"   ⏩ Skipped {v_key_upper} for {user_provided_name} (Type 2: Degen Gauntlet)")
            return "skipped_incompatible"

    # --- SETUP FILENAMES ---
    new_scenario_name = calculate_target_filename(user_provided_name, variant_type_key, new_value, variant_configs)
    new_filename = os.path.join(folder_path, new_scenario_name + ".sce")
    
    lines = base_data["all_lines"][:]
    found_name = False
    current_profile_name = None
    in_char_profile_section = False
    in_any_section = False
    player_name = base_data.get("player_profile_name")
    
    new_timelimit_value = 0
    score_ratio = 1.0 
    
    # --- PRE-CALCULATIONS ---
    if v_key_upper == "DURATION":
        base_timelimit = base_data['global_properties'].get("Timelimit", 0)
        base_timescale = base_data['global_properties'].get("Timescale", 1.0)
        
        if base_timelimit <= 0: return "error_timelimit"
        
        # Logic for existing Timescale in base scenario
        if base_timescale > 0 and base_timescale != 1.0:
            base_perceived_duration = base_timelimit / base_timescale
            score_ratio = base_perceived_duration / new_value if new_value > 0 else 1.0
            duration_multiplier = new_value / base_perceived_duration if base_perceived_duration > 0 else 1.0
            new_timelimit_value = base_timelimit * duration_multiplier
        else:
            score_ratio = base_timelimit / new_value if new_value > 0 else 1.0
            new_timelimit_value = float(new_value)
            
    # --- PROCESS LINES ---
    for i, line in enumerate(lines):
        line_strip = line.strip()
        if line_strip.startswith('['):
            in_any_section = True
            if line_strip.lower() == "[character profile]": 
                in_char_profile_section = True
                current_profile_name = None
            else: 
                in_char_profile_section = False
            continue
            
        if '=' not in line: continue
        key_raw, value_raw = line.split('=', 1)
        key_strip = key_raw.strip()
        key_lower = key_strip.lower()
        
        # 1. Update Scenario Name
        if not in_any_section and key_lower == "name" and value_raw.strip().lower() == internal_name_to_replace.lower():
            lines[i] = f"{key_strip}={new_scenario_name}\n"
            found_name = True
            continue
            
        # 2. Global Properties
        if not in_any_section:
            # DURATION
            if v_key_upper == "DURATION":
                if key_lower == "timelimit": 
                    lines[i] = f"{key_strip}={new_timelimit_value:.1f}\n"
                if key_lower in ["scoreperhit", "scoreperdamage", "scoreperkill"]:
                    base_val = base_data['global_properties'].get(key_strip, 0)
                    if base_val > 0: lines[i] = f"{key_strip}={base_val * score_ratio:.3f}\n"
            
            # TIMESCALE
            elif v_key_upper == "TIMESCALE":
                if key_lower in [p.lower() for p in config['properties']]:
                    base_val = base_data['global_properties'].get(key_strip, 1.0)
                    lines[i] = f"{key_strip}={base_val * multiplier:.3f}\n"
                elif key_lower == "timelimit":
                    base_val = base_data['global_properties'].get("Timelimit", 0)
                    if base_val > 0: lines[i] = f"{key_strip}={base_val * multiplier:.1f}\n"
                
                # Type 1 Fix: ScorePerTime
                elif key_lower == "scorepertime" and is_score_gauntlet and multiplier > 0:
                     base_val = base_data['global_properties'].get("ScorePerTime", 0)
                     lines[i] = f"{key_strip}={base_val / multiplier:.3f}\n"

                # Standard Scoring
                elif key_lower in ["scoreperhit", "scoreperdamage", "scoreperkill"] and multiplier > 0:
                    base_val = base_data['global_properties'].get(key_strip, 0)
                    if base_val > 0: lines[i] = f"{key_strip}={base_val / multiplier:.3f}\n"

        # 3. Character Profile Logic
        # We separate checking if we ARE in a bot section vs if we should apply STANDARD logic
        is_target_bot = False
        if in_char_profile_section:
            if key_lower == "name": current_profile_name = value_raw.strip()
            if current_profile_name and current_profile_name != player_name and current_profile_name in selected_bots:
                is_target_bot = True

        if is_target_bot:
            # A. Standard Logic (Only if config scope matches)
            if config['scope'] == 'Character Profile':
                # Skip MaxHealth standard edit if we are overriding it below
                should_skip_standard = False
                if key_lower == "maxhealth":
                    if (is_score_gauntlet and v_key_upper == "TIMESCALE") or (is_degen_gauntlet and v_key_upper == "DURATION"):
                        should_skip_standard = True

                if not should_skip_standard and key_lower in [p.lower() for p in config['properties']]:
                    if config['mod_type'] == 'Multiplier':
                        base_val = base_data["character_profiles"].get(current_profile_name, {}).get(key_strip, 0)
                        should_modify = not (config['condition'] == "value > 0" and not base_val > 0)
                        if should_modify: lines[i] = f"{key_strip}={base_val * multiplier:.5f}\n"
                    elif config['mod_type'] == 'Calculated':
                        calc_base_prop = config['calculation_base']
                        base_val = base_data["character_profiles"].get(current_profile_name, {}).get(calc_base_prop, 0)
                        lines[i] = f"{key_strip}={base_val * multiplier:.5f}\n"

            # B. Special Logic: Type 1 (Score Gauntlet) + Timescale
            # We explicitly check the Variant Key, independent of config scope
            if is_score_gauntlet and v_key_upper == "TIMESCALE" and multiplier > 0:
                if key_lower == "maxhealth":
                    base_hp = base_data["character_profiles"].get(current_profile_name, {}).get("MaxHealth", 0)
                    # CORRECTION: Multiply HP (Slow down = Lower HP)
                    lines[i] = f"{key_strip}={base_hp * multiplier:.5f}\n"
                elif key_lower in ["minrespawndelay", "maxrespawndelay"]:
                    base_delay = base_data["character_profiles"].get(current_profile_name, {}).get(key_strip, 0)
                    # Delay is multiplied (Slow down = Longer wait in game time to equal Real Time)
                    lines[i] = f"{key_strip}={base_delay * multiplier:.5f}\n"

            # C. Special Logic: Type 2 (Degen Gauntlet)
            if is_degen_gauntlet:
                if v_key_upper == "TIMESCALE" and multiplier > 0:
                    if key_lower == "healthregenpersec":
                        base_regen = base_data["character_profiles"].get(current_profile_name, {}).get("HealthRegenPerSec", 0)
                        if base_regen < 0:
                            lines[i] = f"{key_strip}={base_regen / multiplier:.5f}\n"
                    elif key_lower in ["minrespawndelay", "maxrespawndelay"]:
                        base_delay = base_data["character_profiles"].get(current_profile_name, {}).get(key_strip, 0)
                        lines[i] = f"{key_strip}={base_delay * multiplier:.5f}\n"
                
                # Duration -> Scale HP & Delays (Preserve Density)
                elif v_key_upper == "DURATION":
                    compression_ratio = 1.0 / score_ratio if score_ratio > 0 else 1.0
                    
                    if key_lower == "maxhealth":
                        base_hp = base_data["character_profiles"].get(current_profile_name, {}).get("MaxHealth", 0)
                        lines[i] = f"{key_strip}={base_hp * compression_ratio:.5f}\n"
                    elif key_lower in ["minrespawndelay", "maxrespawndelay"]:
                        base_delay = base_data["character_profiles"].get(current_profile_name, {}).get(key_strip, 0)
                        lines[i] = f"{key_strip}={base_delay * compression_ratio:.5f}\n"

    if not found_name:
         return "name_not_found"
    try:
        with open(new_filename, 'w', encoding='utf-8') as f: f.writelines(lines)
        print(f"✅ Created: {new_scenario_name}.sce")
        return "success"
    except Exception as e:
        print(f"❌ ERROR creating {new_filename}: {e}")
        return "error"