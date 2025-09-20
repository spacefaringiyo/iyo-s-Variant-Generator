# iyo_Variant_Generator0.4.py (Version 15.2 - Final)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
import json
import sys
# Co-developed with Gemini, a large language model from Google.

# --- CORE LOGIC ---
SETTINGS_FILE = "settings.json"
DEFAULT_KOVAAKS_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Scenarios"

# --- HELPER FUNCTIONS FOR NAMING ---
def get_variant_tag(variant_type, value):
    if variant_type == "Duration":
        return f"Dur {value}s"
    else:
        return f"{variant_type} {value}%"

def get_base_scenario_name(full_name):
    variant_tags = ["Size", "Speed", "Timescale", "Dur"]
    base_name = full_name
    for tag in variant_tags:
        if f" {tag} " in base_name:
            base_name = base_name.split(f" {tag} ")[0]
    return base_name.strip()

def save_settings(folder_path, p_size, p_speed, p_scale, d_values, checkboxes):
    settings = { "folder_path": folder_path, "percentages_size": p_size, "percentages_speed": p_speed, "percentages_timescale": p_scale, "durations": d_values, "checkboxes": {key: var.get() for key, var in checkboxes.items()} }
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f: json.dump(settings, f, indent=4)
        print("Settings saved.")
    except Exception as e: print(f"Error saving settings: {e}")

def load_settings():
    default_percentages = [50, 60, 70, 80, 90, 110, 120, 130, 140, 150, 200]
    default_durations = [15, 30, 45, 60, 90, 120]
    
    default_settings = { "folder_path": DEFAULT_KOVAAKS_PATH, "percentages_size": default_percentages.copy(), "percentages_speed": default_percentages.copy(), "percentages_timescale": default_percentages.copy(), "durations": default_durations.copy(), "checkboxes": {} }
    
    for i in range(len(default_percentages)): 
        default_settings["checkboxes"][f"SIZE_{i}"] = True; default_settings["checkboxes"][f"SPEED_{i}"] = True; default_settings["checkboxes"][f"TIMESCALE_{i}"] = True
    
    for i, duration_value in enumerate(default_durations):
        default_settings["checkboxes"][f"DURATION_{i}"] = (duration_value != 60)

    try:
        with open(SETTINGS_FILE, 'r') as f: saved_settings = json.load(f)
        for key in default_settings:
            if key in saved_settings:
                if isinstance(default_settings[key], dict): default_settings[key].update(saved_settings[key])
                else: default_settings[key] = saved_settings[key]
        return default_settings
    except (FileNotFoundError, json.JSONDecodeError): return default_settings

def parse_scenario_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f: lines = f.readlines()
    except Exception: return None

    extracted_data = {
        "all_lines": lines, "scenario_name": "N/A", "timelimit": 60.0, "timescale": 1.0,
        "score_per_hit": 0.0, "score_per_damage": 0.0, "score_per_kill": 0.0,
        "player_profile_name": None, "character_profiles": {}
    }
    
    in_any_section = False
    for line in lines:
        if line.strip().startswith('['): in_any_section = True
        if '=' not in line: continue
        key_part, value_part = line.split('=', 1)
        key = key_part.strip().lower()
        value = value_part.strip()

        if key == "playercharacters": extracted_data["player_profile_name"] = value.split('.')[0]
        # Only read the main scenario name if we are NOT in a section
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
                if current_profile_name not in extracted_data["character_profiles"]:
                    extracted_data["character_profiles"][current_profile_name] = {}
            if current_profile_name:
                if key.lower() == "mainbbradius": extracted_data["character_profiles"][current_profile_name]["radius"] = float(value)
                elif key.lower() == "maxspeed": extracted_data["character_profiles"][current_profile_name]["max_speed"] = float(value)
                elif key.lower() == "maxcrouchspeed": extracted_data["character_profiles"][current_profile_name]["max_crouch_speed"] = float(value)
    return extracted_data

def create_variant_file(base_data, folder_path, variant_type, new_value):
    user_provided_name = base_data['user_provided_name'].strip()
    internal_name_to_replace = base_data['scenario_name'].strip()
    
    multiplier = new_value / 100.0

    clean_base_name = get_base_scenario_name(user_provided_name)
    variant_tag = get_variant_tag(variant_type, new_value)
    new_scenario_name = f"{clean_base_name} {variant_tag}"

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
        
        # --- MODIFIED: Section tracking logic ---
        if line_strip.startswith('['):
            in_any_section = True
            if line_strip.lower() == "[character profile]":
                in_char_profile_section = True
                current_profile_name = None
            else:
                in_char_profile_section = False
            continue
        # ---

        if '=' not in line: continue
        key_raw, value_raw = line.split('=', 1); key_strip = key_raw.strip(); key_lower = key_strip.lower()

        # --- MODIFIED: Only check for main scenario name if NOT in a section ---
        if not in_any_section and key_lower == "name" and value_raw.strip().lower() == internal_name_to_replace.lower():
            lines[i] = f"{key_strip}={new_scenario_name}\n"; found_name = True; continue
        # ---

        if not in_any_section: # Global properties
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
                if variant_type == "Size" and key_lower == "mainbbradius":
                    lines[i] = f"{key_strip}={profile_data.get('radius', 0) * multiplier:.5f}\n"
                elif variant_type == "Speed":
                    if key_lower == "maxspeed" and profile_data.get('max_speed', 0) > 0:
                        lines[i] = f"{key_strip}={profile_data.get('max_speed', 0) * multiplier:.5f}\n"
                    elif key_lower == "maxcrouchspeed" and profile_data.get('max_crouch_speed', 0) > 0:
                        lines[i] = f"{key_strip}={profile_data.get('max_crouch_speed', 0) * multiplier:.5f}\n"

    if not found_name:
        error_msg = f"Could not find the name line in the file.\n\nThe app was looking for:\n'{internal_name_to_replace}'"
        messagebox.showerror("Parsing Error", error_msg)
        return "name_not_found"

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
        ttk.Button(btn_frame, text="Yes", command=lambda: self.set_result_and_close("yes")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="No", command=lambda: self.set_result_and_close("no")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Yes to All", command=lambda: self.set_result_and_close("yes_all")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="No to All", command=lambda: self.set_result_and_close("no_all")).pack(side="left", padx=5)
        self.transient(parent); self.grab_set(); self.wait_window(self)
    def set_result_and_close(self, result): self.result = result; self.destroy()

class VariantGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("iyo's Variant Generator v0.4") 
        self.root.resizable(False, False)
        self.settings = load_settings()
        
        self.variant_configs = {
            "Size":      {"values": self.settings["percentages_size"],      "suffix": "%"},
            "Speed":     {"values": self.settings["percentages_speed"],     "suffix": "%"},
            "Timescale": {"values": self.settings["percentages_timescale"], "suffix": "%"},
            "Duration":  {"values": self.settings["durations"],             "suffix": "s"}
        }

        self.loaded_scenario_data = None; self.is_edit_mode = False; self.checkbox_vars = {}
        self._create_widgets()
        self._load_checkbox_states()
        sys.stdout = RedirectText(self.log_widget); sys.stderr = RedirectText(self.log_widget)
        print("Application started. Load a scenario to begin.")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10"); main_frame.grid(row=0, column=0, sticky="nsew")
        frame1 = ttk.LabelFrame(main_frame, text="1. Select Scenario", padding="10"); frame1.grid(row=0, column=0, columnspan=4, sticky="ew", pady=5)
        self.folder_path_var = tk.StringVar(value=self.settings["folder_path"])
        ttk.Label(frame1, text="Folder Path:").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Entry(frame1, textvariable=self.folder_path_var, width=80).grid(row=0, column=1, sticky="ew")
        ttk.Button(frame1, text="Browse...", command=self._on_browse).grid(row=0, column=2, padx=5)
        self.scenario_name_var = tk.StringVar()
        ttk.Label(frame1, text="Scenario Name:").grid(row=1, column=0, sticky="w", padx=5)
        ttk.Entry(frame1, textvariable=self.scenario_name_var, width=80).grid(row=1, column=1, sticky="ew")
        ttk.Label(frame1, text=".sce").grid(row=1, column=2, sticky="w")
        ttk.Button(frame1, text="Load Scenario", command=self._on_load).grid(row=2, column=1, pady=5)
        
        frame2 = ttk.LabelFrame(main_frame, text="2. Detected Base Stats", padding="10"); frame2.grid(row=1, column=0, columnspan=4, sticky="ew", pady=5)
        self.stat_vars = { "Scenario Name:": tk.StringVar(value="N/A"), "Target Profile(s):": tk.StringVar(value="N/A"), "Target Radius:": tk.StringVar(value="N/A"), "Target Max Speed:": tk.StringVar(value="N/A") }
        for i, (text, var) in enumerate(self.stat_vars.items()):
            ttk.Label(frame2, text=text, width=15).grid(row=i, column=0, sticky="w"); ttk.Label(frame2, textvariable=var).grid(row=i, column=1, sticky="w")
        
        frame3 = ttk.LabelFrame(main_frame, text="3. Choose Variants to Create", padding="10"); frame3.grid(row=2, column=0, columnspan=4, sticky="ew", pady=5)
        
        num_variants = len(self.variant_configs)
        edit_button_col = (num_variants * 2) - 1 
        self.edit_button = ttk.Button(frame3, text="Edit Values", command=self._toggle_edit_mode); self.edit_button.grid(row=0, column=edit_button_col, sticky="e", pady=(0, 5))

        col_index = 0
        for vtype, config in self.variant_configs.items():
            widgets = self._create_variant_column(frame3, vtype, config['values'], config['suffix'])
            widgets['frame'].grid(row=1, column=col_index, padx=5, sticky="ns"); config['widgets'] = widgets; col_index += 1
            if col_index < edit_button_col: ttk.Separator(frame3, orient='vertical').grid(row=1, column=col_index, sticky="ns", padx=5); col_index += 1
        
        self.generate_button = ttk.Button(main_frame, text="Generate Variants", command=self._on_generate, state="disabled"); self.generate_button.grid(row=3, column=0, sticky="w", pady=10)
        self.progress_bar = ttk.Progressbar(main_frame, orient='horizontal', length=500, mode='determinate'); self.progress_bar.grid(row=3, column=1, columnspan=3, sticky="ew", pady=10, padx=5)
        log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding="5"); log_frame.grid(row=4, column=0, columnspan=4, sticky="ew")
        self.log_widget = tk.Text(log_frame, height=8, state='disabled', wrap='word', font=("Courier New", 9)); self.log_widget.pack(fill="both", expand=True)

    def _create_variant_column(self, parent, vtype, values, suffix):
        frame = ttk.Frame(parent); ttk.Label(frame, text=f"{vtype} Variants").pack(pady=(0, 5))
        btn_frame = ttk.Frame(frame); btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Select All", command=lambda v=vtype: self._select_all(v, True)).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Deselect All", command=lambda v=vtype: self._select_all(v, False)).pack(side='left', padx=2)
        widgets = {'labels': [], 'entries': []}
        for i, val in enumerate(values):
            row_frame = ttk.Frame(frame); row_frame.pack(anchor="w")
            key = f"{vtype.upper()}_{i}"
            self.checkbox_vars[key] = tk.BooleanVar(value=True); self.checkbox_vars[key].trace_add("write", self._on_settings_change)
            ttk.Checkbutton(row_frame, variable=self.checkbox_vars[key]).pack(side='left')
            label = ttk.Label(row_frame, text=f"{val}{suffix}"); label.pack(side='left'); widgets['labels'].append(label)
            entry_var = tk.StringVar(value=str(val)); entry = ttk.Entry(row_frame, textvariable=entry_var, width=4); widgets['entries'].append({'widget': entry, 'var': entry_var})
        widgets['frame'] = frame; return widgets

    def _load_checkbox_states(self):
        for key, value in self.settings["checkboxes"].items():
            if key in self.checkbox_vars: self.checkbox_vars[key].set(value)
    
    def _on_browse(self):
        folder = filedialog.askdirectory();
        if folder: self.folder_path_var.set(folder); self._on_settings_change()

    def _on_load(self):
        user_typed_name = self.scenario_name_var.get()
        folder_path = self.folder_path_var.get()
        if not folder_path or not user_typed_name: messagebox.showerror("Error", "Folder path and scenario name cannot be empty."); return
        
        full_path = os.path.join(folder_path, user_typed_name + ".sce"); print(f"Attempting to load: {full_path}")
        
        self.loaded_scenario_data = parse_scenario_file(full_path)
        if self.loaded_scenario_data:
            self.loaded_scenario_data["user_provided_name"] = user_typed_name
            self.stat_vars["Scenario Name:"].set(user_typed_name)
            
            player_name = self.loaded_scenario_data.get("player_profile_name")
            all_profiles = self.loaded_scenario_data.get("character_profiles", {})
            target_names = [name for name in all_profiles.keys() if name != player_name]

            if target_names:
                self.stat_vars["Target Profile(s):"].set(", ".join(target_names))
                first_target_profile = all_profiles.get(target_names[0], {})
                self.stat_vars["Target Radius:"].set(first_target_profile.get("radius", "N/A"))
                self.stat_vars["Target Max Speed:"].set(first_target_profile.get("max_speed", "N/A"))
            else:
                self.stat_vars["Target Profile(s):"].set("N/A"); self.stat_vars["Target Radius:"].set("N/A"); self.stat_vars["Target Max Speed:"].set("N/A")

            self.generate_button.config(state="normal"); print("✅ Success! Scenario file loaded.")
        else:
            messagebox.showerror("Error", "Could not find or read the scenario file."); self.generate_button.config(state="disabled")

    def _on_generate(self):
        if not self.loaded_scenario_data: messagebox.showerror("Error", "No scenario loaded."); return
        
        tasks = [];
        for vtype, config in self.variant_configs.items():
            for i, value in enumerate(config['values']):
                if self.checkbox_vars[f"{vtype.upper()}_{i}"].get(): tasks.append((vtype, value))

        if not tasks: print("--- No variants were selected. ---"); return
        print(f"\n--- Starting Generation of {len(tasks)} variants ---")
        self.progress_bar['maximum'] = len(tasks); created_count = 0; overwrite_decision = 'ask'
        for i, (vtype, val) in enumerate(tasks):
            should_create = True
            if overwrite_decision != 'yes_all':
                user_provided_name = self.loaded_scenario_data['user_provided_name'].strip()
                clean_base_name = get_base_scenario_name(user_provided_name)
                variant_tag = get_variant_tag(vtype, val)
                new_scenario_name = f"{clean_base_name} {variant_tag}"
                new_filename = new_scenario_name + ".sce"

                if os.path.exists(os.path.join(self.folder_path_var.get(), new_filename)):
                    if overwrite_decision == 'ask': dialog = OverwriteDialog(self.root, new_filename); overwrite_decision = dialog.result
                    if overwrite_decision == 'no_all': print("⏩ Skipping all remaining overwrites."); break
                    if overwrite_decision == 'no': print(f"⏩ Skipped: {new_filename}"); should_create = False
            if should_create:
                result = create_variant_file(self.loaded_scenario_data, self.folder_path_var.get(), vtype, val)
                if result == "success": created_count += 1
                elif result == "name_not_found": break 
                elif result == "error_timelimit": messagebox.showerror("Error", f"Cannot create duration variant for a scenario with Timelimit=0."); break
            self.progress_bar['value'] = i + 1; self.root.update_idletasks()
        print(f"--- Finished! Created {created_count} new files. ---"); self.progress_bar['value'] = 0

    def _toggle_edit_mode(self):
        if not self.is_edit_mode:
            self.is_edit_mode = True; self.edit_button.config(text="Save Values")
            for config in self.variant_configs.values():
                for i in range(len(config['widgets']['labels'])):
                    config['widgets']['labels'][i].pack_forget(); config['widgets']['entries'][i]['widget'].pack(side='left')
        else:
            try:
                new_values_map = {vtype: [int(e['var'].get()) for e in cfg['widgets']['entries']] for vtype, cfg in self.variant_configs.items()}
                for vtype, new_vals in new_values_map.items(): self.variant_configs[vtype]['values'] = new_vals
                self.is_edit_mode = False; self.edit_button.config(text="Edit Values")
                for config in self.variant_configs.values():
                    for i, value in enumerate(config['values']):
                        config['widgets']['labels'][i].config(text=f"{value}{config['suffix']}")
                        config['widgets']['entries'][i]['widget'].pack_forget(); config['widgets']['labels'][i].pack(side='left')
                self._on_settings_change()
            except ValueError: messagebox.showerror("Error", "All values must be whole numbers.")

    def _select_all(self, vtype, state):
        if vtype in self.variant_configs:
            for i in range(len(self.variant_configs[vtype]['values'])): self.checkbox_vars[f"{vtype.upper()}_{i}"].set(state)
    
    def _on_settings_change(self, *args):
        save_settings(self.folder_path_var.get(), self.variant_configs["Size"]['values'], self.variant_configs["Speed"]['values'], self.variant_configs["Timescale"]['values'], self.variant_configs["Duration"]['values'], self.checkbox_vars)

    def _on_closing(self): self._on_settings_change(); self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VariantGeneratorApp(root)
    root.mainloop()