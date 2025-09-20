# iyo_Variant_Generator0.5.py (Version 16.0 - Settings Profiles)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.simpledialog import askstring
import os
import re
import json
import sys
# Co-developed with Gemini, a large language model from Google.

# --- CORE LOGIC ---
SETTINGS_FILE = "settings.json"
DEFAULT_KOVAAKS_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Scenarios"

def get_variant_tag(tag_text, suffix, value):
    if suffix == "s": return f"{tag_text} {value}s"
    else: return f"{tag_text} {value}%"

def get_base_scenario_name(full_name, current_tags):
    base_name = full_name
    for tag in current_tags:
        if f" {tag} " in base_name: base_name = base_name.split(f" {tag} ")[0]
    return base_name.strip()

def get_default_profile():
    """Generates a clean, default settings profile."""
    default_percentages = [50, 60, 70, 80, 90, 110, 120, 130, 140, 150, 200]
    default_durations = [15, 30, 45, 60, 90, 120]
    profile = { 
        "folder_path": DEFAULT_KOVAAKS_PATH, "percentages_size": default_percentages.copy(), 
        "percentages_speed": default_percentages.copy(), "percentages_timescale": default_percentages.copy(), 
        "durations": default_durations.copy(), "checkboxes": {},
        "variant_tags": {"SIZE": "Size", "SPEED": "Speed", "TIMESCALE": "Timescale", "DURATION": "Dur"}
    }
    for i in range(len(default_percentages)): 
        profile["checkboxes"][f"SIZE_{i}"] = True; profile["checkboxes"][f"SPEED_{i}"] = True; profile["checkboxes"][f"TIMESCALE_{i}"] = True
    for i, duration_value in enumerate(default_durations):
        profile["checkboxes"][f"DURATION_{i}"] = (duration_value != 60)
    return profile

def save_settings(settings_data):
    """Saves the entire settings object (all profiles) to the file."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4)
        print("Settings saved.")
    except Exception as e: print(f"Error saving settings: {e}")

def load_settings():
    """Loads settings, creating a default structure or migrating old settings if necessary."""
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            # Check if it's the new profile structure
            if "profiles" in settings and "last_active_profile" in settings:
                return settings
            # If not, it's an old settings file that needs migration
            else:
                print("Old settings file detected. Migrating to new profile system.")
                return {
                    "last_active_profile": "Default",
                    "profiles": {"Default": settings}
                }
    except (FileNotFoundError, json.JSONDecodeError):
        # Create a fresh settings structure
        return {
            "last_active_profile": "Default",
            "profiles": {"Default": get_default_profile()}
        }

def parse_scenario_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f: lines = f.readlines()
    except Exception: return None
    extracted_data = { "all_lines": lines, "scenario_name": "N/A", "timelimit": 60.0, "timescale": 1.0, "score_per_hit": 0.0, "score_per_damage": 0.0, "score_per_kill": 0.0, "player_profile_name": None, "character_profiles": {} }
    in_any_section = False
    for line in lines:
        if line.strip().startswith('['): in_any_section = True
        if '=' not in line: continue
        key_part, value_part = line.split('=', 1); key = key_part.strip().lower(); value = value_part.strip()
        if key == "playercharacters": extracted_data["player_profile_name"] = value.split('.')[0]
        elif not in_any_section and key == "name": extracted_data["scenario_name"] = value
        elif key == "timelimit": extracted_data["timelimit"] = float(value)
        elif key == "timescale": extracted_data["timescale"] = float(value)
        elif key == "scoreperhit": extracted_data["score_per_hit"] = float(value)
        elif key == "scoreperdamage": extracted_data["score_per_damage"] = float(value)
        elif key == "scoreperkill": extracted_data["score_per_kill"] = float(value)
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
                if key.lower() == "mainbbradius": extracted_data["character_profiles"][current_profile_name]["radius"] = float(value)
                elif key.lower() == "maxspeed": extracted_data["character_profiles"][current_profile_name]["max_speed"] = float(value)
                elif key.lower() == "maxcrouchspeed": extracted_data["character_profiles"][current_profile_name]["max_crouch_speed"] = float(value)
    return extracted_data

def create_variant_file(base_data, folder_path, variant_type, new_value, variant_configs):
    user_provided_name = base_data['user_provided_name'].strip(); internal_name_to_replace = base_data['scenario_name'].strip()
    multiplier = new_value / 100.0
    current_tags = [cfg['tag_text'] for cfg in variant_configs.values()]; config = variant_configs[variant_type.upper()]
    clean_base_name = get_base_scenario_name(user_provided_name, current_tags)
    variant_tag = get_variant_tag(config['tag_text'], config['suffix'], new_value); new_scenario_name = f"{clean_base_name} {variant_tag}"
    if variant_type == "Duration":
        original_timelimit = base_data['timelimit']
        if original_timelimit <= 0: return "error_timelimit"
        score_ratio = original_timelimit / new_value if new_value > 0 else 1 
    new_filename = os.path.join(folder_path, new_scenario_name + ".sce")
    lines = base_data["all_lines"][:]; found_name = False
    current_profile_name = None; in_char_profile_section = False; in_any_section = False
    player_name = base_data.get("player_profile_name")
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
        if not in_any_section:
            if variant_type == "Timescale" and key_lower == "timescale": lines[i] = f"{key_strip}={base_data['timescale'] * multiplier:.3f}\n"; continue
            if variant_type == "Duration":
                if key_lower == "timelimit": lines[i] = f"{key_strip}={float(new_value):.1f}\n"; continue
                if key_lower == "scoreperhit" and base_data['score_per_hit'] > 0: lines[i] = f"{key_strip}={base_data['score_per_hit'] * score_ratio:.3f}\n"; continue
                if key_lower == "scoreperdamage" and base_data['score_per_damage'] > 0: lines[i] = f"{key_strip}={base_data['score_per_damage'] * score_ratio:.3f}\n"; continue
                if key_lower == "scoreperkill" and base_data['score_per_kill'] > 0: lines[i] = f"{key_strip}={base_data['score_per_kill'] * score_ratio:.3f}\n"; continue
        if in_char_profile_section:
            if key_lower == "name": current_profile_name = value_raw.strip()
            if current_profile_name and current_profile_name != player_name:
                profile_data = base_data["character_profiles"].get(current_profile_name, {})
                if variant_type == "Size" and key_lower == "mainbbradius": lines[i] = f"{key_strip}={profile_data.get('radius', 0) * multiplier:.5f}\n"
                elif variant_type == "Speed":
                    if key_lower == "maxspeed" and profile_data.get('max_speed', 0) > 0: lines[i] = f"{key_strip}={profile_data.get('max_speed', 0) * multiplier:.5f}\n"
                    elif key_lower == "maxcrouchspeed" and profile_data.get('max_crouch_speed', 0) > 0: lines[i] = f"{key_strip}={profile_data.get('max_crouch_speed', 0) * multiplier:.5f}\n"
    if not found_name:
        messagebox.showerror("Parsing Error", f"Could not find the name line in the file.\n\nThe app was looking for:\n'{internal_name_to_replace}'"); return "name_not_found"
    try:
        with open(new_filename, 'w', encoding='utf-8') as f: f.writelines(lines)
        print(f"✅ Created: {new_scenario_name}.sce"); return "success"
    except Exception as e:
        print(f"❌ ERROR creating {new_filename}: {e}"); return "error"

# --- UI Application Classes ---
class RedirectText:
    def __init__(self, text_widget): self.text_space = text_widget
    def write(self, string): self.text_space.config(state='normal'); self.text_space.insert('end', string); self.text_space.see('end'); self.text_space.config(state='disabled')
    def flush(self): pass

class OverwriteDialog(tk.Toplevel):
    def __init__(self, parent, filename):
        super().__init__(parent); self.title("Overwrite Confirmation"); self.result = "no"
        message = f'The file "{filename}" already exists.\n\nHow would you like to proceed for this and all future conflicts in this batch?'
        ttk.Label(self, text=message, wraplength=350, justify='center').pack(padx=20, pady=20)
        btn_frame = ttk.Frame(self); btn_frame.pack(padx=10, pady=10)
        ttk.Button(btn_frame, text="Yes", command=lambda: self.set_result_and_close("yes")).pack(side="left", padx=5); ttk.Button(btn_frame, text="No", command=lambda: self.set_result_and_close("no")).pack(side="left", padx=5); ttk.Button(btn_frame, text="Yes to All", command=lambda: self.set_result_and_close("yes_all")).pack(side="left", padx=5); ttk.Button(btn_frame, text="No to All", command=lambda: self.set_result_and_close("no_all")).pack(side="left", padx=5)
        self.transient(parent); self.grab_set(); self.wait_window(self)
    def set_result_and_close(self, result): self.result = result; self.destroy()

class VariantGeneratorApp:
    def __init__(self, root):
        self.root = root; self.root.title("iyo's Variant Generator"); self.root.resizable(False, False)
        self.settings = load_settings()
        self.active_profile_name = self.settings["last_active_profile"]
        if self.active_profile_name not in self.settings["profiles"]:
            self.active_profile_name = list(self.settings["profiles"].keys())[0]

        self.variant_configs = {}; self.loaded_scenario_data = None; self.is_edit_mode = False; self.checkbox_vars = {}
        self._create_widgets()
        self._load_profile(self.active_profile_name) # Load the initial profile
        sys.stdout = RedirectText(self.log_widget); sys.stderr = RedirectText(self.log_widget)
        print("Application started. Load a scenario to begin.")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10"); main_frame.grid(row=0, column=0, sticky="nsew")
        frame1 = ttk.LabelFrame(main_frame, text="1. Select Scenario", padding="10"); frame1.grid(row=0, column=0, sticky="ew", pady=5)
        self.folder_path_var = tk.StringVar(); ttk.Label(frame1, text="Folder Path:").grid(row=0, column=0, sticky="w", padx=5); ttk.Entry(frame1, textvariable=self.folder_path_var, width=80).grid(row=0, column=1, sticky="ew"); ttk.Button(frame1, text="Browse...", command=self._on_browse).grid(row=0, column=2, padx=5)
        self.scenario_name_var = tk.StringVar(); ttk.Label(frame1, text="Scenario Name:").grid(row=1, column=0, sticky="w", padx=5); ttk.Entry(frame1, textvariable=self.scenario_name_var, width=80).grid(row=1, column=1, sticky="ew"); ttk.Label(frame1, text=".sce").grid(row=1, column=2, sticky="w"); ttk.Button(frame1, text="Load Scenario", command=self._on_load).grid(row=2, column=1, pady=5)
        
        # --- NEW: Settings Profile Section ---
        frame_profiles = ttk.LabelFrame(main_frame, text="Settings Profile", padding="10"); frame_profiles.grid(row=1, column=0, sticky="ew", pady=5)
        ttk.Label(frame_profiles, text="Active Profile:").pack(side="left", padx=(0, 5))
        self.profile_combobox = ttk.Combobox(frame_profiles, state="readonly", width=30); self.profile_combobox.pack(side="left", padx=5)
        self.profile_combobox.bind("<<ComboboxSelected>>", self._on_profile_select)
        ttk.Button(frame_profiles, text="Save As...", command=self._on_save_profile_as).pack(side="left", padx=5)
        ttk.Button(frame_profiles, text="Rename", command=self._on_rename_profile).pack(side="left", padx=5)
        ttk.Button(frame_profiles, text="Delete", command=self._on_delete_profile).pack(side="left", padx=5)
        
        frame2 = ttk.LabelFrame(main_frame, text="2. Detected Base Stats", padding="10"); frame2.grid(row=2, column=0, sticky="ew", pady=5)
        self.stat_vars = { "Scenario Name:": tk.StringVar(value="N/A"), "Timescale:": tk.StringVar(value="N/A"), "Target(s):": tk.StringVar(value="N/A"), "Duration:": tk.StringVar(value="N/A"), "Target Radius:": tk.StringVar(value="N/A"), "Target Max Speed:": tk.StringVar(value="N/A") }
        items = list(self.stat_vars.items()); num_rows = (len(items) + 1) // 2 
        for i, (text, var) in enumerate(items):
            row = i % num_rows; col = (i // num_rows) * 2
            ttk.Label(frame2, text=text, width=15).grid(row=row, column=col, sticky="w", padx=5); ttk.Label(frame2, textvariable=var).grid(row=row, column=col + 1, sticky="w")
        
        self.frame3 = ttk.LabelFrame(main_frame, text="3. Choose Variants to Create", padding="10"); self.frame3.grid(row=3, column=0, sticky="ew", pady=5)
        self.generate_button = ttk.Button(main_frame, text="Generate Variants", command=self._on_generate, state="disabled"); self.generate_button.grid(row=4, column=0, sticky="w", pady=10)
        self.progress_bar = ttk.Progressbar(main_frame, orient='horizontal', length=500, mode='determinate'); self.progress_bar.grid(row=4, column=0, columnspan=2, sticky="ew", pady=10, padx=(150, 0))
        log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding="5"); log_frame.grid(row=5, column=0, sticky="ew")
        self.log_widget = tk.Text(log_frame, height=8, state='disabled', wrap='word', font=("Courier New", 9)); self.log_widget.pack(fill="both", expand=True)

    def _build_variant_columns(self):
        # Clear existing columns if they exist
        for widget in self.frame3.winfo_children(): widget.destroy()
        
        num_variants = len(self.variant_configs); edit_button_col = (num_variants * 2) - 1 
        self.edit_button = ttk.Button(self.frame3, text="Edit Values", command=self._toggle_edit_mode); self.edit_button.grid(row=0, column=edit_button_col, sticky="e", pady=(0, 5))
        col_index = 0
        for vtype_key, config in self.variant_configs.items():
            widgets = self._create_variant_column(self.frame3, vtype_key, config['values'], config['suffix'], config['display_name'])
            widgets['frame'].grid(row=1, column=col_index, padx=5, sticky="ns"); config['widgets'] = widgets; col_index += 1
            if col_index < edit_button_col: ttk.Separator(self.frame3, orient='vertical').grid(row=1, column=col_index, sticky="ns", padx=5); col_index += 1

    def _create_variant_column(self, parent, vtype_key, values, suffix, display_name):
        frame = ttk.Frame(parent)
        header_var = tk.StringVar(value=self.variant_configs[vtype_key]['tag_text'])
        header_label = ttk.Label(frame, text=f"{display_name} Variants")
        header_entry = ttk.Entry(frame, textvariable=header_var, width=12)
        header_label.pack(pady=(0, 5))
        btn_frame = ttk.Frame(frame); btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Select All", command=lambda v=vtype_key: self._select_all(v, True)).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Deselect All", command=lambda v=vtype_key: self._select_all(v, False)).pack(side='left', padx=2)
        widgets = {'labels': [], 'entries': [], 'header_label': header_label, 'header_entry': header_entry, 'header_var': header_var, 'btn_frame': btn_frame}
        for i, val in enumerate(values):
            row_frame = ttk.Frame(frame); row_frame.pack(anchor="w")
            key = f"{vtype_key}_{i}"
            self.checkbox_vars[key] = tk.BooleanVar(value=True); self.checkbox_vars[key].trace_add("write", self._on_settings_change)
            ttk.Checkbutton(row_frame, variable=self.checkbox_vars[key]).pack(side='left')
            label = ttk.Label(row_frame, text=f"{val}{suffix}"); label.pack(side='left'); widgets['labels'].append(label)
            entry_var = tk.StringVar(value=str(val)); entry = ttk.Entry(row_frame, textvariable=entry_var, width=4); widgets['entries'].append({'widget': entry, 'var': entry_var})
        widgets['frame'] = frame; return widgets

    def _load_profile(self, profile_name):
        print(f"Loading profile: {profile_name}")
        self.active_profile_name = profile_name
        self.settings['last_active_profile'] = profile_name
        
        profile_data = self.settings["profiles"][profile_name]
        
        self.variant_configs = {
            "SIZE":      {"values": profile_data["percentages_size"],      "suffix": "%", "tag_text": profile_data["variant_tags"]["SIZE"],      "display_name": profile_data["variant_tags"]["SIZE"]},
            "SPEED":     {"values": profile_data["percentages_speed"],     "suffix": "%", "tag_text": profile_data["variant_tags"]["SPEED"],     "display_name": profile_data["variant_tags"]["SPEED"]},
            "TIMESCALE": {"values": profile_data["percentages_timescale"], "suffix": "%", "tag_text": profile_data["variant_tags"]["TIMESCALE"], "display_name": profile_data["variant_tags"]["TIMESCALE"]},
            "DURATION":  {"values": profile_data["durations"],             "suffix": "s", "tag_text": profile_data["variant_tags"]["DURATION"],  "display_name": "Duration"}
        }

        self.folder_path_var.set(profile_data["folder_path"])
        
        self._build_variant_columns() # Rebuild UI from scratch
        
        # Load checkbox states from the profile
        for key, value in profile_data["checkboxes"].items():
            if key in self.checkbox_vars:
                self.checkbox_vars[key].set(value)
        
        self._update_profile_dropdown()
        self.is_edit_mode = False # Ensure we are not in edit mode
        
    def _update_profile_dropdown(self):
        profiles = list(self.settings["profiles"].keys())
        self.profile_combobox['values'] = profiles
        self.profile_combobox.set(self.active_profile_name)

    def _on_profile_select(self, event=None):
        new_profile_name = self.profile_combobox.get()
        if new_profile_name != self.active_profile_name:
            self._on_settings_change() # Save changes to the old profile first
            self._load_profile(new_profile_name)

    def _on_save_profile_as(self):
        new_name = askstring("Save Profile As", "Enter a name for the new profile:", parent=self.root)
        if new_name and not new_name.isspace():
            if new_name in self.settings["profiles"]:
                messagebox.showerror("Error", "A profile with this name already exists.")
                return
            self._on_settings_change() # Ensure current changes are captured
            self.settings["profiles"][new_name] = self.settings["profiles"][self.active_profile_name].copy()
            self._load_profile(new_name)
            print(f"Profile saved as: {new_name}")

    def _on_rename_profile(self):
        old_name = self.active_profile_name
        new_name = askstring("Rename Profile", f"Enter a new name for '{old_name}':", parent=self.root)
        if new_name and not new_name.isspace():
            if new_name in self.settings["profiles"]:
                messagebox.showerror("Error", "A profile with this name already exists."); return
            self.settings["profiles"][new_name] = self.settings["profiles"].pop(old_name)
            self._load_profile(new_name)
            print(f"Profile '{old_name}' renamed to '{new_name}'")

    def _on_delete_profile(self):
        if len(self.settings["profiles"]) <= 1:
            messagebox.showerror("Error", "Cannot delete the last profile."); return
        profile_to_delete = self.active_profile_name
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the profile '{profile_to_delete}'?"):
            del self.settings["profiles"][profile_to_delete]
            new_active_profile = list(self.settings["profiles"].keys())[0]
            self._load_profile(new_active_profile)
            print(f"Profile '{profile_to_delete}' deleted.")
    
    def _on_browse(self):
        folder = filedialog.askdirectory()
        if folder: self.folder_path_var.set(folder); self._on_settings_change()

    def _on_load(self):
        user_typed_name = self.scenario_name_var.get(); folder_path = self.folder_path_var.get()
        if not folder_path or not user_typed_name: messagebox.showerror("Error", "Folder path and scenario name cannot be empty."); return
        full_path = os.path.join(folder_path, user_typed_name + ".sce"); print(f"Attempting to load: {full_path}")
        self.loaded_scenario_data = parse_scenario_file(full_path)
        if self.loaded_scenario_data:
            self.loaded_scenario_data["user_provided_name"] = user_typed_name; self.stat_vars["Scenario Name:"].set(user_typed_name)
            self.stat_vars["Timescale:"].set(self.loaded_scenario_data.get("timescale", "N/A"))
            duration = self.loaded_scenario_data.get("timelimit", "N/A"); self.stat_vars["Duration:"].set(f"{duration:.1f}s" if isinstance(duration, (int, float)) else "N/A")
            player_name = self.loaded_scenario_data.get("player_profile_name"); all_profiles = self.loaded_scenario_data.get("character_profiles", {})
            target_names = [name for name in all_profiles.keys() if name != player_name]
            if target_names:
                self.stat_vars["Target(s):"].set(", ".join(target_names)); first_target_profile = all_profiles.get(target_names[0], {})
                self.stat_vars["Target Radius:"].set(first_target_profile.get("radius", "N/A")); self.stat_vars["Target Max Speed:"].set(first_target_profile.get("max_speed", "N/A"))
            else:
                self.stat_vars["Target(s):"].set("N/A"); self.stat_vars["Target Radius:"].set("N/A"); self.stat_vars["Target Max Speed:"].set("N/A")
            self.generate_button.config(state="normal"); print("✅ Success! Scenario file loaded.")
        else:
            messagebox.showerror("Error", "Could not find or read the scenario file."); self.generate_button.config(state="disabled")

    def _on_generate(self):
        if not self.loaded_scenario_data: messagebox.showerror("Error", "No scenario loaded."); return
        tasks = [];
        for vtype_key, config in self.variant_configs.items():
            vtype_logic = vtype_key.capitalize()
            for i, value in enumerate(config['values']):
                if self.checkbox_vars[f"{vtype_key}_{i}"].get(): tasks.append((vtype_logic, value))
        if not tasks: print("--- No variants were selected. ---"); return
        print(f"\n--- Starting Generation of {len(tasks)} variants ---")
        self.progress_bar['maximum'] = len(tasks); created_count = 0; overwrite_decision = 'ask'
        for i, (vtype, val) in enumerate(tasks):
            should_create = True
            if overwrite_decision != 'yes_all':
                user_provided_name = self.loaded_scenario_data['user_provided_name'].strip()
                current_tags = [cfg['tag_text'] for cfg in self.variant_configs.values()]
                clean_base_name = get_base_scenario_name(user_provided_name, current_tags)
                config = self.variant_configs[vtype.upper()]
                variant_tag = get_variant_tag(config['tag_text'], config['suffix'], val)
                new_scenario_name = f"{clean_base_name} {variant_tag}"; new_filename = new_scenario_name + ".sce"
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
        else: # Saving
            try:
                new_values_map = {key: [int(e['var'].get()) for e in cfg['widgets']['entries']] for key, cfg in self.variant_configs.items()}
                new_tags_map = {key: cfg['widgets']['header_var'].get().strip() for key, cfg in self.variant_configs.items()}
                if any(not tag for tag in new_tags_map.values()):
                    messagebox.showerror("Error", "Variant tags cannot be empty."); self.is_edit_mode = True; return
                for vtype_key, config in self.variant_configs.items():
                    config['values'] = new_values_map[vtype_key]; config['tag_text'] = new_tags_map[vtype_key]
                    if vtype_key != "DURATION": config['display_name'] = new_tags_map[vtype_key]
                self.edit_button.config(text="Edit Values")
                for config in self.variant_configs.values():
                    w = config['widgets']; w['header_label'].config(text=f"{config['display_name']} Variants"); w['header_entry'].pack_forget()
                    w['header_label'].pack(pady=(0, 5), before=w['btn_frame'])
                    for i, value in enumerate(config['values']):
                        w['labels'][i].config(text=f"{value}{config['suffix']}"); w['entries'][i]['widget'].pack_forget(); w['labels'][i].pack(side='left')
                self._on_settings_change() # Trigger save after edit
            except ValueError:
                messagebox.showerror("Error", "All numeric values must be whole numbers."); self.is_edit_mode = True

    def _select_all(self, vtype_key, state):
        if vtype_key in self.variant_configs:
            for i in range(len(self.variant_configs[vtype_key]['values'])): self.checkbox_vars[f"{vtype_key}_{i}"].set(state)
    
    def _on_settings_change(self, *args):
        """This function now gathers the current UI state and saves it to the active profile in memory."""
        active_profile = self.settings["profiles"][self.active_profile_name]
        active_profile["folder_path"] = self.folder_path_var.get()
        active_profile["checkboxes"] = {key: var.get() for key, var in self.checkbox_vars.items()}
        for key, config in self.variant_configs.items():
            if key == "SIZE": active_profile["percentages_size"] = config["values"]
            elif key == "SPEED": active_profile["percentages_speed"] = config["values"]
            elif key == "TIMESCALE": active_profile["percentages_timescale"] = config["values"]
            elif key == "DURATION": active_profile["durations"] = config["values"]
            active_profile["variant_tags"][key] = config["tag_text"]
        
    def _on_closing(self):
        """Gathers the final state into the active profile and saves everything to file."""
        self._on_settings_change() # Ensure final changes are captured
        save_settings(self.settings) # Save the entire structure
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VariantGeneratorApp(root)
    root.mainloop()