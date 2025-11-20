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
            if "language" not in settings: settings["language"] = "EN"
            if "profiles" in settings and "last_active_profile" in settings:
                for pname, profile in settings["profiles"].items():
                    if "percentages" in profile and "size_percentages" not in profile:
                        print(f"Migrating old settings for profile '{pname}'...")
                        profile["size_percentages"] = profile.get("percentages", get_default_profile()["size_percentages"])
                        profile["speed_percentages"] = profile.get("percentages", get_default_profile()["speed_percentages"])
                        profile["timescale_percentages"] = profile.get("percentages", get_default_profile()["timescale_percentages"])
                return settings
            else:
                print("Old or invalid settings file detected. Creating a fresh one.")
                migrated_profile = get_default_profile()
                if "folder_path" in settings: migrated_profile["folder_path"] = settings["folder_path"]
                return {"language": "EN", "last_active_profile": "Default", "profiles": {"Default": migrated_profile}}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"language": "EN", "last_active_profile": "Default", "profiles": {"Default": get_default_profile()}}

def parse_scenario_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f: lines = f.readlines()
    except Exception: return None
    extracted_data = { "all_lines": lines, "scenario_name": "N/A", "player_profile_name": None, "character_profiles": {}, "global_properties": {} }
    in_any_section = False
    for line in lines:
        if line.strip().startswith('['): in_any_section = True
        if '=' not in line: continue
        key_part, value_part = line.split('=', 1); key = key_part.strip().lower(); value = value_part.strip()
        if key == "playercharacters": extracted_data["player_profile_name"] = value.split('.')[0]
        if not in_any_section and key == "name": extracted_data["scenario_name"] = value
        for mod_key, config in MODIFIER_CONFIG.items():
            if config['scope'] == 'Global':
                if not in_any_section:
                    for prop in config['properties']:
                        if key == prop.lower(): extracted_data['global_properties'][prop] = float(value)
                if key == "scoreperhit": extracted_data['global_properties']["ScorePerHit"] = float(value)
                elif key == "scoreperdamage": extracted_data['global_properties']["ScorePerDamage"] = float(value)
                elif key == "scoreperkill": extracted_data['global_properties']["ScorePerKill"] = float(value)
    current_profile_name = None; in_char_profile_section = False
    for line in lines:
        line_strip = line.strip()
        if line_strip.lower() == "[character profile]": in_char_profile_section = True; current_profile_name = None; continue
        if in_char_profile_section and line_strip.startswith('['): in_char_profile_section = False; current_profile_name = None; continue
        if in_char_profile_section:
            if '=' not in line_strip: continue
            key, value = line_strip.split('=', 1); key, value = key.strip(), value.strip()
            if key.lower() == "name":
                current_profile_name = value
                if current_profile_name not in extracted_data["character_profiles"]: extracted_data["character_profiles"][current_profile_name] = {}
            if current_profile_name:
                all_char_props = set()
                for cfg in MODIFIER_CONFIG.values():
                    if cfg['scope'] == 'Character Profile':
                        all_char_props.update(cfg['properties'])
                        if cfg.get('calculation_base'): all_char_props.add(cfg['calculation_base'])
                if key in all_char_props:
                    extracted_data["character_profiles"][current_profile_name][key] = float(value)
    return extracted_data

def create_variant_file(base_data, folder_path, variant_type_key, new_value, variant_configs, selected_bots):
    user_provided_name = base_data['user_provided_name'].strip()
    internal_name_to_replace = base_data['scenario_name'].strip()
    multiplier = new_value / 100.0
    config = MODIFIER_CONFIG[variant_type_key.upper()]
    
    new_scenario_name = calculate_target_filename(user_provided_name, variant_type_key, new_value, variant_configs)
    new_filename = os.path.join(folder_path, new_scenario_name + ".sce")
    
    lines = base_data["all_lines"][:]
    found_name = False
    current_profile_name = None
    in_char_profile_section = False
    in_any_section = False
    player_name = base_data.get("player_profile_name")
    v_key_upper = variant_type_key.upper()
    
    new_timelimit_value = 0
    score_ratio = 1.0
    
    if v_key_upper == "DURATION":
        base_timelimit = base_data['global_properties'].get("Timelimit", 0)
        base_timescale = base_data['global_properties'].get("Timescale", 1.0)
        if base_timelimit <= 0: return "error_timelimit"
        if base_timescale > 0 and base_timescale != 1.0:
            base_perceived_duration = base_timelimit / base_timescale
            score_ratio = base_perceived_duration / new_value if new_value > 0 else 1.0
            duration_multiplier = new_value / base_perceived_duration if base_perceived_duration > 0 else 1.0
            new_timelimit_value = base_timelimit * duration_multiplier
        else:
            score_ratio = base_timelimit / new_value if new_value > 0 else 1.0
            new_timelimit_value = float(new_value)
            
    for i, line in enumerate(lines):
        line_strip = line.strip()
        if line_strip.startswith('['):
            in_any_section = True
            if line_strip.lower() == "[character profile]": in_char_profile_section = True; current_profile_name = None
            else: in_char_profile_section = False
            continue
        if '=' not in line: continue
        key_raw, value_raw = line.split('=', 1); key_strip = key_raw.strip(); key_lower = key_strip.lower()
        
        if not in_any_section and key_lower == "name" and value_raw.strip().lower() == internal_name_to_replace.lower():
            lines[i] = f"{key_strip}={new_scenario_name}\n"; found_name = True; continue
            
        if v_key_upper == "DURATION" and not in_any_section:
            if key_lower == "timelimit": lines[i] = f"{key_strip}={new_timelimit_value:.1f}\n"
            if key_lower == "scoreperhit" and base_data['global_properties'].get("ScorePerHit", 0) > 0: lines[i] = f"{key_strip}={base_data['global_properties']['ScorePerHit'] * score_ratio:.3f}\n"
            if key_lower == "scoreperdamage" and base_data['global_properties'].get("ScorePerDamage", 0) > 0: lines[i] = f"{key_strip}={base_data['global_properties']['ScorePerDamage'] * score_ratio:.3f}\n"
            if key_lower == "scoreperkill" and base_data['global_properties'].get("ScorePerKill", 0) > 0: lines[i] = f"{key_strip}={base_data['global_properties']['ScorePerKill'] * score_ratio:.3f}\n"
        elif v_key_upper == "TIMESCALE" and not in_any_section:
            if key_lower in [p.lower() for p in config['properties']]:
                base_val = base_data['global_properties'].get(key_strip, 1.0)
                lines[i] = f"{key_strip}={base_val * multiplier:.3f}\n"
            elif key_lower == "timelimit":
                base_val = base_data['global_properties'].get("Timelimit", 0)
                if base_val > 0: lines[i] = f"{key_strip}={base_val * multiplier:.1f}\n"
            elif multiplier > 0:
                if key_lower == "scoreperhit" and base_data['global_properties'].get("ScorePerHit", 0) > 0:
                    lines[i] = f"{key_strip}={base_data['global_properties']['ScorePerHit'] / multiplier:.3f}\n"
                if key_lower == "scoreperdamage" and base_data['global_properties'].get("ScorePerDamage", 0) > 0:
                    lines[i] = f"{key_strip}={base_data['global_properties']['ScorePerDamage'] / multiplier:.3f}\n"
                if key_lower == "scoreperkill" and base_data['global_properties'].get("ScorePerKill", 0) > 0:
                    lines[i] = f"{key_strip}={base_data['global_properties']['ScorePerKill'] / multiplier:.3f}\n"
        elif config['scope'] == 'Character Profile' and in_char_profile_section:
            if key_lower == "name": current_profile_name = value_raw.strip()
            if current_profile_name and current_profile_name != player_name and current_profile_name in selected_bots:
                if key_lower in [p.lower() for p in config['properties']]:
                    if config['mod_type'] == 'Multiplier':
                        base_val = base_data["character_profiles"].get(current_profile_name, {}).get(key_strip, 0); should_modify = not (config['condition'] == "value > 0" and not base_val > 0)
                        if should_modify: lines[i] = f"{key_strip}={base_val * multiplier:.5f}\n"
                    elif config['mod_type'] == 'Calculated':
                        calc_base_prop = config['calculation_base']
                        base_val = base_data["character_profiles"].get(current_profile_name, {}).get(calc_base_prop, 0)
                        calculated_value = base_val * multiplier
                        lines[i] = f"{key_strip}={calculated_value:.5f}\n"
    if not found_name:
         return "name_not_found"
    try:
        with open(new_filename, 'w', encoding='utf-8') as f: f.writelines(lines)
        print(f"✅ Created: {new_scenario_name}.sce"); return "success"
    except Exception as e:
        print(f"❌ ERROR creating {new_filename}: {e}"); return "error"