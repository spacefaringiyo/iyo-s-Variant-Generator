# iyo_Scenario_Variant_GeneratorV0.7.1.py (Version 19.12 - Smart Variant Stacking)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.simpledialog import askstring
from tkinter import font
import os
import re
import json
import sys
# Co-developed with Gemini, a large language model from Google.

# --- MASTER MODIFIER CONFIGURATION ---
MODIFIER_CONFIG = {
    "SIZE": { "display_name": "Size", "tag_text": "Size", "mod_type": "Multiplier", "scope": "Character Profile", "properties": ["MainBBRadius"], "condition": None, "suffix": "%", "value_key": "percentages" },
    "SPEED": { "display_name": "Speed", "tag_text": "Speed", "mod_type": "Multiplier", "scope": "Character Profile", "properties": ["MaxSpeed", "MaxCrouchSpeed"], "condition": "value > 0", "suffix": "%", "value_key": "percentages" },
    "TIMESCALE": { "display_name": "Timescale", "tag_text": "Timescale", "mod_type": "Multiplier", "scope": "Global", "properties": ["Timescale"], "condition": None, "suffix": "%", "value_key": "percentages" },
    "DURATION": { "display_name": "Duration", "tag_text": "Dur", "mod_type": "Direct", "scope": "Global", "properties": ["Timelimit"], "condition": None, "suffix": "s", "value_key": "durations" },
    "HP": { "display_name": "HP", "tag_text": "HP", "mod_type": "Multiplier", "scope": "Character Profile", "properties": ["MaxHealth"], "condition": None, "suffix": "%", "value_key": "hp_percentages" },
    "REGEN_RATE": { "display_name": "Regen", "tag_text": "Regen", "mod_type": "Calculated", "scope": "Character Profile", "properties": ["HealthRegenPerSec"], "calculation_base": "MaxHealth", "condition": None, "suffix": "%", "value_key": "regen_percentages" }
}

# --- CORE LOGIC ---
SETTINGS_FILE = "settings.json"
DEFAULT_KOVAAKS_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Scenarios"

def get_variant_tag(tag_text, suffix, value):
    if suffix == "s": return f"{tag_text} {value}s"
    else: return f"{tag_text} {value}%"
def get_base_scenario_name(full_name, current_tags):
    base_name = full_name
    for tag in current_tags:
        # Improved regex to avoid accidentally splitting words. Looks for " tag " or " tag" at the end.
        pattern = r' (\b' + re.escape(tag) + r'\b .*?)(?=( \b[A-Z][a-z]*\b|$))'
        base_name = re.split(pattern, base_name, 1)[0]
    return base_name.strip()
def get_default_profile():
    profile = {
        "folder_path": DEFAULT_KOVAAKS_PATH,
        "percentages": [50, 60, 70, 80, 90, 110, 120, 130, 140, 150, 200], "durations": [15, 30, 45, 60, 90, 120],
        "hp_percentages": [20, 50, 80, 90, 110, 130, 150, 200, 300], "regen_percentages": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "checkboxes": {}, "variant_tags": {key: config['tag_text'] for key, config in MODIFIER_CONFIG.items()}
    }
    for key, config in MODIFIER_CONFIG.items():
        value_list = profile[config['value_key']]
        for i, value in enumerate(value_list):
            is_checked = not (key in ["HP", "REGEN_RATE"] or (key == "DURATION" and value == 60))
            profile["checkboxes"][f"{key}_{i}"] = is_checked
    return profile
def save_settings(settings_data):
    try:
        for profile in settings_data.get("profiles", {}).values():
            if "legacy_timescale_mode" in profile:
                del profile["legacy_timescale_mode"]
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f: json.dump(settings_data, f, indent=4)
        print("Settings saved.")
    except Exception as e: print(f"Error saving settings: {e}")
def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            if "profiles" in settings and "last_active_profile" in settings: return settings
            else:
                print("Old or invalid settings file detected. Creating a fresh one.")
                migrated_profile = get_default_profile()
                if "folder_path" in settings: migrated_profile["folder_path"] = settings["folder_path"]
                return {"last_active_profile": "Default", "profiles": {"Default": migrated_profile}}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_active_profile": "Default", "profiles": {"Default": get_default_profile()}}
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

def create_variant_file(base_data, folder_path, variant_type_key, new_value, variant_configs):
    user_provided_name = base_data['user_provided_name'].strip(); internal_name_to_replace = base_data['scenario_name'].strip()
    multiplier = new_value / 100.0; config = MODIFIER_CONFIG[variant_type_key.upper()]; ui_config = variant_configs[variant_type_key.upper()]
    
    # --- NEW: Smart Stacking Logic ---
    variant_tag = get_variant_tag(ui_config['tag_text'], ui_config['suffix'], new_value)
    base_name_for_new_file = user_provided_name
    
    # Check if a tag of the same type already exists in the name
    current_tag_text = ui_config['tag_text']
    # Build a regex to find an existing tag, e.g., " Dur [0-9]+s"
    existing_tag_pattern = r' (\b' + re.escape(current_tag_text) + r'\b \d+s?)' # Handles "s" suffix for duration
    if ui_config['suffix'] == '%':
         existing_tag_pattern = r' (\b' + re.escape(current_tag_text) + r'\b \d+%)'
    
    match = re.search(existing_tag_pattern, base_name_for_new_file)
    if match:
        # If found, REPLACE the old tag with the new one
        new_scenario_name = base_name_for_new_file.replace(match.group(1), f" {variant_tag}")
    else:
        # If not found, STACK the new tag at the end
        # First, clean any potential old tags if the user loads an old-style variant to prevent double-stacking
        clean_base = get_base_scenario_name(base_name_for_new_file, [cfg['tag_text'] for cfg in variant_configs.values()])
        # Check if the cleaning actually changed the name, if so, use the cleaned name to avoid issues.
        if f" {current_tag_text} " in user_provided_name:
             base_name_for_new_file = clean_base
        new_scenario_name = f"{base_name_for_new_file} {variant_tag}"

    new_filename = os.path.join(folder_path, new_scenario_name + ".sce")
    lines = base_data["all_lines"][:]; found_name = False; current_profile_name = None; in_char_profile_section = False; in_any_section = False
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
                if base_val > 0:
                    lines[i] = f"{key_strip}={base_val * multiplier:.1f}\n"

        elif config['scope'] == 'Character Profile' and in_char_profile_section:
            if key_lower == "name": current_profile_name = value_raw.strip()
            if current_profile_name and current_profile_name != player_name:
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
        messagebox.showerror("Parsing Error", f"Could not find the name line in the file.\n\nLooking for: '{internal_name_to_replace}'"); return "name_not_found"
    try:
        with open(new_filename, 'w', encoding='utf-8') as f: f.writelines(lines)
        print(f"✅ Created: {new_scenario_name}.sce"); return "success"
    except Exception as e:
        print(f"❌ ERROR creating {new_filename}: {e}"); return "error"

# --- UI Application Classes (No changes below this line) ---
class RedirectText:
    def __init__(self, text_widget): self.text_space = text_widget
    def write(self, string): self.text_space.config(state='normal'); self.text_space.insert('end', string); self.text_space.see('end'); self.text_space.config(state='disabled')
    def flush(self): pass
class OverwriteDialog(tk.Toplevel):
    def __init__(self, parent, filename):
        super().__init__(parent); self.title("Overwrite Confirmation"); self.result = "no"
        message = f'The file "{filename}" already exists.\n\nHow would you like to proceed for this and all future conflicts in this batch?'
        ttk.Label(self, text=message, wraplength=350, justify='center').pack(padx=20, pady=20); btn_frame = ttk.Frame(self); btn_frame.pack(padx=10, pady=10); ttk.Button(btn_frame, text="Yes", command=lambda: self.set_result_and_close("yes")).pack(side="left", padx=5); ttk.Button(btn_frame, text="No", command=lambda: self.set_result_and_close("no")).pack(side="left", padx=5); ttk.Button(btn_frame, text="Yes to All", command=lambda: self.set_result_and_close("yes_all")).pack(side="left", padx=5); ttk.Button(btn_frame, text="No to All", command=lambda: self.set_result_and_close("no_all")).pack(side="left", padx=5)
        self.transient(parent); self.grab_set(); self.wait_window(self)
    def set_result_and_close(self, result): self.result = result; self.destroy()

class VariantGeneratorApp:
    def __init__(self, root):
        self.root = root; self.root.title("iyo's Scenario Variant Generator v0.7.1"); self.root.resizable(False, False)
        self.ui_ready = False
        self.settings = load_settings()
        self.active_profile_name = self.settings["last_active_profile"]
        if self.active_profile_name not in self.settings["profiles"]: self.active_profile_name = list(self.settings["profiles"].keys())[0]
        self.variant_configs = {}; self.loaded_scenario_data = None; self.is_edit_mode = False; self.checkbox_vars = {}
        self.all_scenarios = []; self._after_id = None
        default_font = font.nametofont("TkDefaultFont"); self.header_font = font.Font(family=default_font.cget("family"), size=default_font.cget("size")+2, weight="bold")
        self._create_widgets()
        self._load_profile(self.active_profile_name)
        self._populate_scenario_list()
        sys.stdout = RedirectText(self.log_widget); sys.stderr = RedirectText(self.log_widget)
        print("Application started. Load a scenario to begin.")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.ui_ready = True

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10"); main_frame.grid(row=0, column=0, sticky="nsew")
        frame1 = ttk.LabelFrame(main_frame, text="1. Select Scenario", padding="10"); frame1.grid(row=0, column=0, sticky="ew", pady=5)
        self.folder_path_var = tk.StringVar(); self.folder_path_var.trace_add("write", self._on_settings_change)
        ttk.Label(frame1, text="Folder Path:").grid(row=0, column=0, sticky="w", padx=5); ttk.Entry(frame1, textvariable=self.folder_path_var, width=80).grid(row=0, column=1, sticky="ew", padx=5); ttk.Button(frame1, text="Browse...", command=self._on_browse).grid(row=0, column=2, padx=5)
        self.scenario_name_var = tk.StringVar(); self.scenario_name_var.trace_add("write", self._schedule_load_from_entry); ttk.Label(frame1, text="Scenario Name:").grid(row=1, column=0, sticky="w", padx=5); ttk.Entry(frame1, textvariable=self.scenario_name_var, width=80).grid(row=1, column=1, sticky="ew", padx=5)
        list_frame = ttk.Frame(frame1); list_frame.grid(row=2, column=1, sticky="ew", padx=5, pady=(5,0)); self.scenario_listbox = tk.Listbox(list_frame, height=6, exportselection=False); self.scenario_listbox.pack(side="left", fill="both", expand=True); scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.scenario_listbox.yview); scrollbar.pack(side="right", fill="y"); self.scenario_listbox.config(yscrollcommand=scrollbar.set); self.scenario_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        frame_profiles = ttk.LabelFrame(main_frame, text="Settings Profile", padding="10"); frame_profiles.grid(row=1, column=0, sticky="ew", pady=5); ttk.Label(frame_profiles, text="Active Profile:").pack(side="left", padx=(0, 5)); self.profile_combobox = ttk.Combobox(frame_profiles, state="readonly", width=30); self.profile_combobox.pack(side="left", padx=5); self.profile_combobox.bind("<<ComboboxSelected>>", self._on_profile_select); ttk.Button(frame_profiles, text="Save As...", command=self._on_save_profile_as).pack(side="left", padx=5); ttk.Button(frame_profiles, text="Rename", command=self._on_rename_profile).pack(side="left", padx=5); ttk.Button(frame_profiles, text="Delete", command=self._on_delete_profile).pack(side="left", padx=5)
        frame2 = ttk.LabelFrame(main_frame, text="2. Detected Base Stats", padding="10"); frame2.grid(row=2, column=0, sticky="ew", pady=5); frame2.columnconfigure(1, weight=1); frame2.columnconfigure(3, weight=1)
        self.stat_vars = { "Scenario Name:": tk.StringVar(value="Scenario Name: N/A"), "Target(s):": tk.StringVar(value="N/A"), "Target HP:": tk.StringVar(value="N/A"), "Target Regen/s:": tk.StringVar(value="N/A"), "Target Radius:": tk.StringVar(value="N/A"), "Target Max Speed:": tk.StringVar(value="N/A"), "Timescale:": tk.StringVar(value="N/A"), "Duration:": tk.StringVar(value="N/A") }
        scen_name_var = self.stat_vars["Scenario Name:"]; scen_name_label = ttk.Label(frame2, textvariable=scen_name_var, font=self.header_font, anchor="center"); scen_name_label.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 5))
        items = list(self.stat_vars.items()); items.pop(0) 
        num_rows = (len(items) + 1) // 2
        for i, (text, var) in enumerate(items):
            row = (i % num_rows) + 1; col = (i // num_rows) * 2
            ttk.Label(frame2, text=text, width=15).grid(row=row, column=col, sticky="w", padx=5); ttk.Label(frame2, textvariable=var).grid(row=row, column=col + 1, sticky="w")
        self.frame3 = ttk.LabelFrame(main_frame, text="3. Choose Variants to Create", padding="10"); self.frame3.grid(row=3, column=0, sticky="ew", pady=5)
        generate_frame = ttk.Frame(main_frame); generate_frame.grid(row=4, column=0, sticky="ew")
        self.generate_button = ttk.Button(generate_frame, text="Generate Variants", command=self._on_generate, state="disabled"); self.generate_button.pack(side="left", pady=10)
        self.progress_bar = ttk.Progressbar(generate_frame, orient='horizontal', length=500, mode='determinate'); self.progress_bar.pack(side="left", fill="x", expand=True, pady=10, padx=(20,10))
        log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding="5"); log_frame.grid(row=5, column=0, sticky="ew"); self.log_widget = tk.Text(log_frame, height=8, state='disabled', wrap='word', font=("Courier New", 9)); self.log_widget.pack(fill="both", expand=True)

    def _populate_scenario_list(self):
        self.all_scenarios = []; folder = self.folder_path_var.get()
        if not os.path.isdir(folder): return
        try:
            for filename in os.listdir(folder):
                if filename.lower().endswith(".sce"): self.all_scenarios.append(filename[:-4])
            self.all_scenarios.sort(key=str.lower); self._update_filtered_list()
        except Exception as e: print(f"Error reading scenario folder: {e}")
    def _update_filtered_list(self, *args):
        search_term = self.scenario_name_var.get().lower(); self.scenario_listbox.delete(0, tk.END)
        for name in self.all_scenarios:
            if not search_term or search_term in name.lower(): self.scenario_listbox.insert(tk.END, name)
    def _schedule_load_from_entry(self, *args):
        self._update_filtered_list()
        if self._after_id: self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(500, self._on_load)
    def _on_listbox_select(self, event=None):
        selected_indices = self.scenario_listbox.curselection()
        if not selected_indices: return
        selected_name = self.scenario_listbox.get(selected_indices[0])
        if self._after_id: self.root.after_cancel(self._after_id); self._after_id = None
        self.scenario_name_var.set(selected_name); self._on_load()
    def _on_browse(self):
        folder = filedialog.askdirectory()
        if folder: self.folder_path_var.set(folder); self._populate_scenario_list()
    def _build_variant_columns(self):
        for widget in self.frame3.winfo_children(): widget.destroy()
        num_variants = len(self.variant_configs); edit_button_col = (num_variants * 2) - 1
        self.edit_button = ttk.Button(self.frame3, text="Edit Values", command=self._toggle_edit_mode); self.edit_button.grid(row=0, column=edit_button_col, sticky="e", pady=(0, 5))
        col_index = 0
        for vtype_key, config in self.variant_configs.items():
            widgets = self._create_variant_column(self.frame3, vtype_key, config['values'], config['suffix'], config['display_name'])
            widgets['frame'].grid(row=1, column=col_index, padx=5, sticky="ns"); config['widgets'] = widgets; col_index += 1
            if col_index < edit_button_col: ttk.Separator(self.frame3, orient='vertical').grid(row=1, column=col_index, sticky="ns", padx=5); col_index += 1
    def _create_variant_column(self, parent, vtype_key, values, suffix, display_name):
        frame = ttk.Frame(parent); header_var = tk.StringVar(value=self.variant_configs[vtype_key]['tag_text']); header_label = ttk.Label(frame, text=f"{display_name} Variants"); header_entry = ttk.Entry(frame, textvariable=header_var, width=12); header_label.pack(pady=(0, 5)); btn_frame = ttk.Frame(frame); btn_frame.pack(pady=5); ttk.Button(btn_frame, text="Select All", command=lambda v=vtype_key: self._select_all(v, True)).pack(side='left', padx=2); ttk.Button(btn_frame, text="Deselect All", command=lambda v=vtype_key: self._select_all(v, False)).pack(side='left', padx=2); widgets = {'labels': [], 'entries': [], 'header_label': header_label, 'header_entry': header_entry, 'header_var': header_var, 'btn_frame': btn_frame}
        for i, val in enumerate(values):
            row_frame = ttk.Frame(frame); row_frame.pack(anchor="w"); key = f"{vtype_key}_{i}"; self.checkbox_vars[key] = tk.BooleanVar(value=True); ttk.Checkbutton(row_frame, variable=self.checkbox_vars[key]).pack(side='left'); label = ttk.Label(row_frame, text=f"{val}{suffix}"); label.pack(side='left'); widgets['labels'].append(label); entry_var = tk.StringVar(value=str(val)); entry = ttk.Entry(row_frame, textvariable=entry_var, width=4); widgets['entries'].append({'widget': entry, 'var': entry_var})
            self.checkbox_vars[key].trace_add("write", self._on_settings_change)
            entry_var.trace_add("write", self._on_settings_change)
        header_var.trace_add("write", self._on_settings_change)
        widgets['frame'] = frame; return widgets
    def _load_profile(self, profile_name):
        self.ui_ready = False
        print(f"Loading profile: {profile_name}"); self.active_profile_name = profile_name; self.settings['last_active_profile'] = profile_name
        profile_data = self.settings["profiles"][profile_name]
        self.variant_configs = {}
        for key, config in MODIFIER_CONFIG.items():
            self.variant_configs[key] = {"values": profile_data[config['value_key']], "suffix": config['suffix'], "tag_text": profile_data["variant_tags"][key], "display_name": config['display_name'] if key == "DURATION" else profile_data["variant_tags"][key]}
        self.folder_path_var.set(profile_data["folder_path"])
        self._build_variant_columns()
        for key, value in profile_data["checkboxes"].items():
            if key in self.checkbox_vars: self.checkbox_vars[key].set(value)
        self._update_profile_dropdown()
        self.is_edit_mode = False
        self._toggle_edit_mode(); self._toggle_edit_mode()
        self.ui_ready = True
    def _update_profile_dropdown(self):
        self.profile_combobox['values'] = list(self.settings["profiles"].keys()); self.profile_combobox.set(self.active_profile_name)
    def _on_profile_select(self, event=None):
        new_profile_name = self.profile_combobox.get()
        if new_profile_name != self.active_profile_name:
            self._on_settings_change()
            self._load_profile(new_profile_name)
    def _on_save_profile_as(self):
        new_name = askstring("Save Profile As", "Enter a name for the new profile:", parent=self.root)
        if new_name and not new_name.isspace():
            if new_name in self.settings["profiles"]: messagebox.showerror("Error", "A profile with this name already exists."); return
            self._on_settings_change()
            self.settings["profiles"][new_name] = json.loads(json.dumps(self.settings["profiles"][self.active_profile_name]))
            self._load_profile(new_name); print(f"Profile saved as: {new_name}")
    def _on_rename_profile(self):
        old_name = self.active_profile_name; new_name = askstring("Rename Profile", f"Enter a new name for '{old_name}':", parent=self.root)
        if new_name and not new_name.isspace():
            if new_name in self.settings["profiles"]: messagebox.showerror("Error", "A profile with this name already exists."); return
            self._on_settings_change()
            self.settings["profiles"][new_name] = self.settings["profiles"].pop(old_name)
            self._load_profile(new_name); print(f"Profile '{old_name}' renamed to '{new_name}'")
    def _on_delete_profile(self):
        if len(self.settings["profiles"]) <= 1: messagebox.showerror("Error", "Cannot delete the last profile."); return
        profile_to_delete = self.active_profile_name
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the profile '{profile_to_delete}'?"):
            del self.settings["profiles"][profile_to_delete]
            new_active_profile = list(self.settings["profiles"].keys())[0]
            self._load_profile(new_active_profile); print(f"Profile '{profile_to_delete}' deleted.")
    def _on_load(self):
        user_typed_name = self.scenario_name_var.get().strip(); folder_path = self.folder_path_var.get()
        if not folder_path or not user_typed_name: self.stat_vars["Scenario Name:"].set("Scenario Name: N/A"); return
        full_path = os.path.join(folder_path, user_typed_name + ".sce")
        if not os.path.exists(full_path):
            self.generate_button.config(state="disabled"); self.stat_vars["Scenario Name:"].set("Scenario Name: N/A"); return
        print(f"Attempting to load: {full_path}")
        self.loaded_scenario_data = parse_scenario_file(full_path)
        if self.loaded_scenario_data:
            self.loaded_scenario_data["user_provided_name"] = user_typed_name; self.stat_vars["Scenario Name:"].set(f"Scenario Name: {user_typed_name}")
            self.stat_vars["Timescale:"].set(self.loaded_scenario_data.get('global_properties', {}).get('Timescale', 'N/A'))
            duration = self.loaded_scenario_data.get('global_properties', {}).get('Timelimit', 'N/A'); self.stat_vars["Duration:"].set(f"{duration:.1f}s" if isinstance(duration, (int, float)) else "N/A")
            player_name = self.loaded_scenario_data.get("player_profile_name"); all_profiles = self.loaded_scenario_data.get("character_profiles", {})
            target_names = [name for name in all_profiles.keys() if name != player_name]
            if target_names:
                self.stat_vars["Target(s):"].set(", ".join(target_names)); first_target_profile = all_profiles.get(target_names[0], {})
                self.stat_vars["Target Radius:"].set(first_target_profile.get("MainBBRadius", "N/A")); self.stat_vars["Target Max Speed:"].set(first_target_profile.get("MaxSpeed", "N/A")); self.stat_vars["Target HP:"].set(first_target_profile.get("MaxHealth", "N/A")); self.stat_vars["Target Regen/s:"].set(first_target_profile.get("HealthRegenPerSec", "N/A"))
            else:
                for key in self.stat_vars:
                    if key != "Scenario Name:": self.stat_vars[key].set("N/A")
            self.generate_button.config(state="normal"); print("✅ Success! Scenario file loaded.")
        else:
            messagebox.showerror("Error", f"Found '{user_typed_name}.sce' but could not read or parse it."); self.generate_button.config(state="disabled")
    def _on_generate(self):
        if not self.loaded_scenario_data: messagebox.showerror("Error", "No scenario loaded."); return
        self._on_settings_change()
        tasks = [];
        for vtype_key, config in self.variant_configs.items():
            for i, value in enumerate(config['values']):
                if self.checkbox_vars[f"{vtype_key}_{i}"].get(): tasks.append((vtype_key, value))
        if not tasks: print("--- No variants were selected. ---"); return
        print(f"\n--- Starting Generation of {len(tasks)} variants ---")
        self.progress_bar['maximum'] = len(tasks); created_count = 0; overwrite_decision = 'ask'
        for i, (vtype, val) in enumerate(tasks):
            should_create = True
            if overwrite_decision != 'yes_all':
                user_provided_name = self.loaded_scenario_data['user_provided_name'].strip(); current_tags = [cfg['tag_text'] for cfg in self.variant_configs.values()]; clean_base_name = get_base_scenario_name(user_provided_name, current_tags); config = self.variant_configs[vtype.upper()]; variant_tag = get_variant_tag(config['tag_text'], config['suffix'], val); new_scenario_name = f"{clean_base_name} {variant_tag}"; new_filename = new_scenario_name + ".sce"
                if os.path.exists(os.path.join(self.folder_path_var.get(), new_filename)):
                    if overwrite_decision == 'ask': dialog = OverwriteDialog(self.root, new_filename); overwrite_decision = dialog.result
                    if overwrite_decision == 'no_all': print("⏩ Skipping all remaining overwrites."); break
                    if overwrite_decision == 'no': print(f"⏩ Skipped: {new_filename}"); should_create = False
            if should_create:
                result = create_variant_file(self.loaded_scenario_data, self.folder_path_var.get(), vtype, val, self.variant_configs)
                if result == "success": created_count += 1
                elif result == "name_not_found": break
                elif result == "error_timelimit": messagebox.showerror("Error", f"Cannot create duration variant for a scenario with Timelimit=0."); break
            self.progress_bar['value'] = i + 1; self.root.update_idletasks()
        print(f"--- Finished! Created {created_count} new files. ---"); self.progress_bar['value'] = 0
    def _toggle_edit_mode(self):
        self.is_edit_mode = not self.is_edit_mode
        if self.is_edit_mode:
            self.edit_button.config(text="Save Values")
            for config in self.variant_configs.values():
                w = config['widgets']; w['header_label'].pack_forget(); w['header_entry'].pack(pady=(0, 5))
                for i in range(len(w['labels'])): w['labels'][i].pack_forget(); w['entries'][i]['widget'].pack(side='left')
        else:
            try:
                new_tags_map = {key: cfg['widgets']['header_var'].get().strip() for key, cfg in self.variant_configs.items()}
                if any(not tag for tag in new_tags_map.values()):
                    messagebox.showerror("Error", "Variant tags cannot be empty."); self.is_edit_mode = True; return
                {key: [int(e['var'].get()) for e in cfg['widgets']['entries']] for key, cfg in self.variant_configs.items()}
                self._on_settings_change()
                self.edit_button.config(text="Edit Values")
                for vtype_key, config in self.variant_configs.items():
                    if vtype_key != "DURATION": config['display_name'] = new_tags_map[vtype_key]
                    w = config['widgets']; w['header_label'].config(text=f"{config['display_name']} Variants"); w['header_entry'].pack_forget()
                    w['header_label'].pack(pady=(0, 5), before=w['btn_frame'])
                    for i, value in enumerate(config['values']):
                        w['labels'][i].config(text=f"{value}{config['suffix']}"); w['entries'][i]['widget'].pack_forget(); w['labels'][i].pack(side='left')
            except ValueError:
                messagebox.showerror("Error", "All numeric values must be whole numbers."); self.is_edit_mode = True
    def _select_all(self, vtype_key, state):
        if vtype_key in self.variant_configs:
            for i in range(len(self.variant_configs[vtype_key]['values'])): self.checkbox_vars[f"{vtype_key}_{i}"].set(state)
    def _on_settings_change(self, *args):
        if not self.ui_ready:
            return
        active_profile = self.settings["profiles"][self.active_profile_name]
        active_profile["folder_path"] = self.folder_path_var.get()
        active_profile["checkboxes"] = {key: var.get() for key, var in self.checkbox_vars.items()}
        try:
            for key, config in self.variant_configs.items():
                if 'widgets' not in config:
                    continue
                master_config = MODIFIER_CONFIG[key]
                current_values = [int(e['var'].get()) for e in config['widgets']['entries']]
                current_tag = config['widgets']['header_var'].get().strip()
                if not current_tag: current_tag = master_config['tag_text']
                active_profile[master_config['value_key']] = current_values
                active_profile["variant_tags"][key] = current_tag
                config["values"] = current_values
                config["tag_text"] = current_tag
        except (ValueError, tk.TclError):
            pass

    def _on_closing(self):
        if self.ui_ready:
            self._on_settings_change()
            save_settings(self.settings)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VariantGeneratorApp(root)
    root.mainloop()