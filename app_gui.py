import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.simpledialog import askstring
from tkinter import font
import os
import sys
import subprocess
import json

from PIL import Image, ImageTk, ImageEnhance

# Import from our new modules
from config import MODIFIER_CONFIG
from language import LANGUAGES
from scenario_logic import (
    load_settings, save_settings, parse_scenario_file, 
    create_variant_file, get_default_profile, 
    get_base_scenario_name, calculate_target_filename
)

# --- VISUAL CONSTANTS ---
TRANSPARENT_KEY = "#000001" 
DEFAULT_BG_COLOR = "#2b2b2b" 

DARK_BG = TRANSPARENT_KEY       
LIGHT_TEXT = "#ffffff"    
ENTRY_BG = "#2e2e2e"      
ACCENT_COLOR = "#ff7eb6"  # Hot Pink
MATRIX_GREEN = "#00ff41"  # Matrix Green

class RedirectText:
    def __init__(self, text_widget): self.text_space = text_widget
    def write(self, string): 
        try:
            self.text_space.config(state='normal')
            self.text_space.insert('end', string)
            self.text_space.see('end')
            self.text_space.config(state='disabled')
        except tk.TclError: pass
    def flush(self): pass

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Grid configuration for 2D scrolling
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(self, bg=ENTRY_BG, highlightthickness=0)
        self.scrollbar_y = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        
        self.scrollable_frame = ttk.Frame(self.canvas, style="Opaque.TFrame")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.scrollbar_x.grid(row=1, column=0, sticky="ew")

class OverwriteDialog(tk.Toplevel):
    def __init__(self, parent, filename, current_lang):
        super().__init__(parent);
        lang = current_lang
        self.title(LANGUAGES[lang]['dialog_overwrite_title']); self.result = "no"
        self.configure(bg=ENTRY_BG)
        message = LANGUAGES[lang]['dialog_overwrite_text'].format(filename=filename)
        lbl = ttk.Label(self, text=message, wraplength=350, justify='center', background=ENTRY_BG)
        lbl.pack(padx=20, pady=20)
        btn_frame = ttk.Frame(self, style="Opaque.TFrame"); btn_frame.pack(padx=10, pady=10)
        ttk.Button(btn_frame, text="Yes", command=lambda: self.set_result_and_close("yes")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="No", command=lambda: self.set_result_and_close("no")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Yes to All", command=lambda: self.set_result_and_close("yes_all")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="No to All", command=lambda: self.set_result_and_close("no_all")).pack(side="left", padx=5)
        self.transient(parent); self.grab_set(); self.wait_window(self)
    def set_result_and_close(self, result): self.result = result; self.destroy()

class VariantGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.ui_ready = False
        self.settings = load_settings()
        
        # State
        self.bg_edit_mode = False
        self.raw_bg_image = None 
        self.bg_scale = 1.0
        self.bg_brightness = self.settings.get("bg_brightness", 0.3)
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.is_batch_mode = False
        self.batch_queue = {}
        self.batch_rows = {} 

        # Architecture
        self.root.config(bg=DEFAULT_BG_COLOR) 
        self.root.title("iyo's Variant Generator")
        self.bg_canvas = tk.Canvas(self.root, bg=DEFAULT_BG_COLOR, highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bg_canvas.bind("<ButtonPress-1>", self._start_pan)
        self.bg_canvas.bind("<B1-Motion>", self._on_pan)
        
        self.ui_window = tk.Toplevel(self.root)
        self.ui_window.overrideredirect(True) 
        self.ui_window.wm_attributes('-transparentcolor', TRANSPARENT_KEY) 
        self.ui_window.config(bg=TRANSPARENT_KEY)
        self.ui_window.transient(self.root) 
        self.root.bind('<Configure>', self._sync_windows)
        self.root.bind('<Map>', self._sync_map)
        self.root.bind('<Unmap>', self._sync_unmap)

        self.current_lang = self.settings.get("language", "EN")
        if self.current_lang not in LANGUAGES: self.current_lang = "EN"
        self.active_profile_name = self.settings["last_active_profile"]
        if self.active_profile_name not in self.settings["profiles"]: self.active_profile_name = list(self.settings["profiles"].keys())[0]
        
        self.variant_configs = {}; self.loaded_scenario_data = None; self.is_edit_mode = False; self.checkbox_vars = {}
        self.all_scenarios = []; self._after_id = None
        self.bot_selection_vars = {} 
        self.bg_image_ref = None
        self.bg_image_id = None 
        
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Consolas", size=10)
        self.header_font = font.Font(family="Consolas", size=11, weight="bold")
        
        self._configure_styles()
        self._create_widgets()
        
        if "background_path" in self.settings:
            self._apply_background_image(self.settings["background_path"], reset_view=False)
            
        self._load_profile(self.active_profile_name)
        self._populate_scenario_list()
        self._update_ui_text()
        
        sys.stdout = RedirectText(self.log_widget); sys.stderr = RedirectText(self.log_widget)
        print("Application started. Load a scenario to begin.")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self.ui_ready = True
        self._force_initial_geometry()

    def _toggle_bg_edit(self):
        self.bg_edit_mode = not self.bg_edit_mode
        if self.bg_edit_mode:
            self.btn_adjust_bg.config(text="✅ Done", style="Accent.TButton")
            self.bg_canvas.bind("<ButtonPress-1>", self._start_pan)
            self.bg_canvas.bind("<B1-Motion>", self._on_pan)
            self.root.bind("<MouseWheel>", self._on_zoom)
            self.root.bind("<Button-4>", self._on_zoom)
            self.root.bind("<Button-5>", self._on_zoom)
            print("--- Edit Mode: DRAG to Move, SCROLL to Zoom ---")
        else:
            self.btn_adjust_bg.config(text="✋ Adjust BG", style="TButton")
            self.bg_canvas.unbind("<ButtonPress-1>")
            self.bg_canvas.unbind("<B1-Motion>")
            self.root.unbind("<MouseWheel>")
            self.root.unbind("<Button-4>")
            self.root.unbind("<Button-5>")
            print("--- Edit Mode Locked ---")

    def _start_pan(self, event): self.pan_start_x = event.x; self.pan_start_y = event.y
    def _on_pan(self, event):
        if self.bg_image_id and self.bg_edit_mode:
            dx = event.x - self.pan_start_x; dy = event.y - self.pan_start_y
            self.bg_canvas.move(self.bg_image_id, dx, dy)
            self.pan_start_x = event.x; self.pan_start_y = event.y
    def _on_zoom(self, event):
        if not self.bg_edit_mode or not self.raw_bg_image: return
        scale_multiplier = 0.9 if (event.num == 5 or event.delta < 0) else 1.1
        new_scale = self.bg_scale * scale_multiplier
        if 0.1 < new_scale < 5.0:
            self.bg_scale = new_scale; self._render_bg_image()
    def _on_brightness_change(self, val):
        self.bg_brightness = float(val); self._render_bg_image()
    def _render_bg_image(self):
        if not self.raw_bg_image: return
        orig_w, orig_h = self.raw_bg_image.size
        new_w = int(orig_w * self.bg_scale); new_h = int(orig_h * self.bg_scale)
        try:
            resized = self.raw_bg_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            enhancer = ImageEnhance.Brightness(resized)
            final_img = enhancer.enhance(self.bg_brightness)
            self.bg_image_ref = ImageTk.PhotoImage(final_img)
            if self.bg_image_id: self.bg_canvas.itemconfig(self.bg_image_id, image=self.bg_image_ref)
            else:
                cx = self.root.winfo_width() // 2; cy = self.root.winfo_height() // 2
                self.bg_image_id = self.bg_canvas.create_image(cx, cy, image=self.bg_image_ref, anchor="center")
        except Exception: pass

    def _force_initial_geometry(self):
        self.ui_window.update_idletasks() 
        req_w = self.ui_window.winfo_reqwidth(); req_h = self.ui_window.winfo_reqheight()
        w = req_w + 20; h = req_h + 20
        ws = self.root.winfo_screenwidth(); hs = self.root.winfo_screenheight()
        x = int((ws/2) - (w/2)); y = int((hs/2) - (h/2))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _configure_styles(self):
        style = ttk.Style()

        style.configure("TButton", anchor="center")
        style.configure("TFrame", background=TRANSPARENT_KEY)
        style.configure("TLabelframe", background=TRANSPARENT_KEY)
        style.configure("TLabelframe.Label", background=TRANSPARENT_KEY, foreground=ACCENT_COLOR, font=self.header_font)
        style.configure("TLabel", background=TRANSPARENT_KEY, foreground=LIGHT_TEXT)
        style.configure("TCheckbutton", background=TRANSPARENT_KEY, foreground=LIGHT_TEXT)
        style.configure("Opaque.TFrame", background=ENTRY_BG)
        style.configure("Accent.TButton", foreground=MATRIX_GREEN, anchor="center")
        
        # New Style for Batch Mode Switch
        style.configure("Switch.TCheckbutton", background=TRANSPARENT_KEY, foreground=LIGHT_TEXT, font=("Consolas", 10, "bold"))
        style.map("Switch.TCheckbutton", foreground=[('selected', MATRIX_GREEN)])

        # --- UPDATE: Added anchor="center" here ---
        style.configure("CTA.TButton", font=("Consolas", 12, "bold"), foreground=ACCENT_COLOR, padding=5, anchor="center")


    def _sync_windows(self, event=None):
        if not self.ui_ready: return 
        try:
            x = self.root.winfo_rootx(); y = self.root.winfo_rooty()
            w = self.root.winfo_width(); h = self.root.winfo_height()
            self.ui_window.geometry(f"{w}x{h}+{x}+{y}"); self.ui_window.lift()
        except Exception: pass

    def _sync_map(self, event): self.ui_window.deiconify(); self._sync_windows()
    def _sync_unmap(self, event): self.ui_window.withdraw()

    def _update_ui_text(self):
        lang = LANGUAGES[self.current_lang]
        self.root.title(lang["window_title"])
        self.frame1.config(text=lang["frame_scenario"])
        self.label_folder_path.config(text=lang["label_folder_path"])
        self.button_browse.config(text=lang["button_browse"])
        self.label_scenario_name.config(text=lang["label_scenario_name"])
        self.frame_profiles.config(text=lang["frame_profiles"])
        self.label_active_profile.config(text=lang["label_active_profile"])
        self.button_new.config(text=lang["button_new"])
        self.button_rename.config(text=lang["button_rename"])
        self.button_delete.config(text=lang["button_delete"])
        
        if self.is_batch_mode:
            self.frame2.config(text=f"📊 Batch Queue ({len(self.batch_queue)})")
            self.generate_button.config(text=f"Generate Batch ({len(self.batch_queue)})")
        else:
            self.frame2.config(text=lang["frame_stats"])
            self.generate_button.config(text=lang["button_generate"])
            
        self.label_target.config(text=lang["stats_targets"])
        self.label_hp.config(text=lang["stats_hp"])
        self.label_regen.config(text=lang["stats_regen"])
        self.label_radius.config(text=lang["stats_radius"])
        self.label_head_radius.config(text=lang["stats_head_radius"]) 
        self.label_speed.config(text=lang["stats_speed"])
        self.label_timescale.config(text=lang["stats_timescale"])
        self.label_duration.config(text=lang["stats_duration"])
        self.frame3.config(text=lang["frame_variants"])
        self.edit_button.config(text=lang["button_edit_values"] if not self.is_edit_mode else lang["button_save_values"])
        self.log_frame.config(text=lang["frame_log"])
        if hasattr(self, 'bot_selection_frame'):
            self.bot_selection_frame.config(text=lang["frame_targets_modify"])
        if hasattr(self, 'bot_select_all_btn'):
            self.bot_select_all_btn.config(text=lang["button_select_all"])
        for vtype_key, config in self.variant_configs.items():
            if 'widgets' in config:
                widgets = config['widgets']
                display_name = config['display_name']
                widgets['header_label'].config(text=f"{display_name} Variants")
                widgets['btn_frame'].winfo_children()[0].config(text=lang["button_select_all"])
                widgets['btn_frame'].winfo_children()[1].config(text=lang["button_deselect_all"])

    def _style_checkbox_dynamic(self, cb, var):
        def update_color(*args):
            try:
                if var.get(): cb.config(selectcolor=ACCENT_COLOR)
                else: cb.config(selectcolor=ENTRY_BG)
            except tk.TclError: pass
        update_color()
        var.trace_add("write", update_color)

    def _run_with_hidden_ui(self, task_func):
        self.ui_window.withdraw()
        try: return task_func()
        finally: self.ui_window.deiconify(); self._sync_windows()
    
    def _open_folder(self):
        path = self.folder_path_var.get()
        if os.path.isdir(path):
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform.startswith('linux'):
                try:
                    subprocess.call(['xdg-open', path])
                except Exception as e:
                    print(f"Error opening folder: {e}")
    
    def _on_reload(self):
        self._populate_scenario_list()
        print("🔄 Scenario list reloaded from disk.")

    def _select_background(self):
        # 1. Check if we have a saved folder from last time
        initial_dir = self.settings.get("bg_last_folder", "")
        
        # 2. If not (or if that folder was deleted), default to Downloads
        if not initial_dir or not os.path.exists(initial_dir):
            initial_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            
        def task(): 
            return filedialog.askopenfilename(
                parent=self.root, 
                initialdir=initial_dir,
                filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")]
            )
            
        file_path = self._run_with_hidden_ui(task)
        
        if file_path:
            self.settings["background_path"] = file_path
            
            # 3. Save the folder for next time so we remember the user's choice
            self.settings["bg_last_folder"] = os.path.dirname(file_path)
            
            self._apply_background_image(file_path, reset_view=True)
            save_settings(self.settings)

    def _reset_background(self):
        # 1. Clear memory and canvas
        self.raw_bg_image = None
        self.bg_image_ref = None
        self.bg_image_id = None
        self.bg_canvas.delete("all")
        
        # 2. Reset variables to defaults
        self.bg_scale = 1.0
        self.bg_brightness = 0.3
        self.bright_scale.set(0.3)
        
        # 3. Clean up settings file
        keys_to_remove = ["background_path", "bg_scale", "bg_x", "bg_y", "bg_brightness"]
        changed = False
        for k in keys_to_remove:
            if k in self.settings:
                del self.settings[k]
                changed = True
        
        if changed:
            save_settings(self.settings)
            
        print("Restored default dark background.")

    def _apply_background_image(self, path, reset_view=False):
        try:
            img = Image.open(path)
            self.raw_bg_image = img 
            win_w = self.root.winfo_screenwidth(); win_h = self.root.winfo_screenheight()
            img_ratio = img.width / img.height; screen_ratio = win_w / win_h
            if screen_ratio > img_ratio: default_scale = win_w / img.width
            else: default_scale = win_h / img.height
            
            if reset_view or "bg_scale" not in self.settings:
                self.bg_scale = default_scale; center_x = win_w // 2; center_y = win_h // 2
            else:
                self.bg_scale = float(self.settings.get("bg_scale", default_scale))
                center_x = self.settings.get("bg_x", win_w // 2); center_y = self.settings.get("bg_y", win_h // 2)
            
            self.bg_canvas.delete("all"); self.bg_image_id = None
            self._render_bg_image()
            if self.bg_image_id: self.bg_canvas.coords(self.bg_image_id, center_x, center_y)
            print(f"Background set to: {path}")
        except Exception as e: print(f"Error loading background: {e}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self.ui_window, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # --- HEADER ---
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.lang_combobox = ttk.Combobox(header_frame, values=["English", "日本語"], state="readonly", width=10)
        self.lang_combobox.set("English" if self.current_lang == "EN" else "日本語")
        self.lang_combobox.pack(side="right")
        lang_label = ttk.Label(header_frame, text="Language / 言語 🌐:")
        lang_label.pack(side="right", padx=(0, 5))
        bright_frame = ttk.Frame(header_frame)
        bright_frame.pack(side="right", padx=10)
        
        # --- Frame 1: FILES ---
        self.frame1 = ttk.LabelFrame(self.ui_window, padding="10", text="📂 1. Select Scenario")
        self.frame1.grid(row=1, column=0, sticky="ew", pady=5, padx=15)
        self.frame1.columnconfigure(1, weight=1) 
        
        # ROW 0: Folder Path
        btn_box_row0 = ttk.Frame(self.frame1)
        btn_box_row0.grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.button_browse = ttk.Button(btn_box_row0, command=self._on_browse) 
        self.button_browse.pack(side="left")
        ttk.Button(btn_box_row0, text="Open Folder", width=12, command=self._open_folder).pack(side="left", padx=2)
        
        self.folder_path_var = tk.StringVar(); self.folder_path_var.trace_add("write", self._on_settings_change)
        ttk.Entry(self.frame1, textvariable=self.folder_path_var).grid(row=0, column=1, sticky="ew", pady=2)

        # ROW 1: Batch Mode + Search Toolbar
        self.batch_mode_var = tk.BooleanVar(value=False)
        self.batch_chk = ttk.Checkbutton(self.frame1, text="Batch Mode", variable=self.batch_mode_var, command=self._toggle_batch_mode, style="Switch.TCheckbutton")
        self.batch_chk.grid(row=1, column=0, padx=(0, 10), sticky="w")
        
        self.scenario_name_var = tk.StringVar(); self.scenario_name_var.trace_add("write", self._schedule_load_from_entry)
        
        search_container = ttk.Frame(self.frame1)
        search_container.grid(row=1, column=1, sticky="ew", pady=2)
        
        # --- NEW: Reload Button (Icon Style) ---
        # U+21BB is Clockwise Open Circle Arrow
        self.btn_reload = ttk.Button(search_container, text="↻", width=3, command=self._on_reload, style="Accent.TButton")
        self.btn_reload.pack(side="left", padx=(0, 2))
        # ---------------------------------------

        self.btn_clear_search = ttk.Button(search_container, text="X", width=3, command=self._clear_search, style="Accent.TButton")
        self.btn_clear_search.pack(side="left", padx=(0, 5))
        
        self.search_entry = ttk.Entry(search_container, textvariable=self.scenario_name_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        
        self.label_folder_path = ttk.Label(self.ui_window) 
        self.label_scenario_name = ttk.Label(self.ui_window)

        list_frame = ttk.Frame(self.frame1); list_frame.grid(row=2, column=1, sticky="ew", pady=(5,0))
        self.scenario_listbox = tk.Listbox(list_frame, height=6, exportselection=False, selectmode="extended", bg=ENTRY_BG, fg=LIGHT_TEXT, selectbackground=ACCENT_COLOR, selectforeground="black", borderwidth=0, highlightthickness=1, relief="flat", font=("Consolas", 9))
        self.scenario_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.scenario_listbox.yview)
        scrollbar.pack(side="right", fill="y"); self.scenario_listbox.config(yscrollcommand=scrollbar.set)
        self.scenario_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        
        # --- Frame Profiles ---
        self.frame_profiles = ttk.LabelFrame(self.ui_window, padding="10", text="💾 Settings Profile")
        self.frame_profiles.grid(row=2, column=0, sticky="ew", pady=5, padx=15)
        self.label_active_profile = ttk.Label(self.frame_profiles); self.label_active_profile.pack(side="left", padx=(0, 5))
        self.profile_combobox = ttk.Combobox(self.frame_profiles, state="readonly", width=20)
        self.profile_combobox.pack(side="left", padx=5); self.profile_combobox.bind("<<ComboboxSelected>>", self._on_profile_select)
        self.button_new = ttk.Button(self.frame_profiles, command=self._on_new_profile); self.button_new.pack(side="left", padx=5)
        self.button_rename = ttk.Button(self.frame_profiles, command=self._on_rename_profile); self.button_rename.pack(side="left", padx=5)
        self.button_delete = ttk.Button(self.frame_profiles, command=self._on_delete_profile); self.button_delete.pack(side="left", padx=5)
        self.lang_combobox.bind("<<ComboboxSelected>>", self._on_language_change)
        right_controls = ttk.Frame(self.frame_profiles); right_controls.pack(side="right")
        ttk.Button(right_controls, text="Reset BG", width=9, command=self._reset_background).pack(side="left", padx=(0, 5))
        ttk.Label(right_controls, text="Dimmer:").pack(side="left", padx=(10, 2))
        self.bright_scale = ttk.Scale(right_controls, from_=0.0, to=1.0, orient="horizontal", length=80, command=self._on_brightness_change)
        self.bright_scale.set(self.bg_brightness); self.bright_scale.pack(side="left", padx=5)
        self.btn_adjust_bg = ttk.Button(right_controls, text="✋ Adjust BG", command=self._toggle_bg_edit); self.btn_adjust_bg.pack(side="right", padx=5)
        self.btn_set_bg = ttk.Button(right_controls, text="🖼 Set BG", command=self._select_background); self.btn_set_bg.pack(side="right", padx=5)
    
        # --- MIDDLE SECTION ---
        middle_container = ttk.Frame(self.ui_window)
        middle_container.grid(row=3, column=0, sticky="ew", padx=15, pady=5)
        middle_container.columnconfigure(0, weight=1)
        middle_container.columnconfigure(1, weight=1)

        # --- Frame 2: STATS ---
        self.frame2 = ttk.LabelFrame(middle_container, padding="10", text="📊 2. Base Stats")
        self.frame2.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        self.single_mode_frame = ttk.Frame(self.frame2); self.single_mode_frame.pack(fill="both", expand=True)
        self.single_mode_frame.columnconfigure(1, weight=1); self.single_mode_frame.columnconfigure(3, weight=1)
        self.stat_vars = { "Scenario Name:": tk.StringVar(value=LANGUAGES[self.current_lang]['stats_scenario_name']), "Target(s):": tk.StringVar(value="N/A"), "Target HP:": tk.StringVar(value="N/A"), "Target Regen/s:": tk.StringVar(value="N/A"), "Target Radius:": tk.StringVar(value="N/A"), "Target Head Radius:": tk.StringVar(value="N/A"), "Target Max Speed:": tk.StringVar(value="N/A"), "Timescale:": tk.StringVar(value="N/A"), "Duration:": tk.StringVar(value="N/A") }
        scen_name_var = self.stat_vars["Scenario Name:"]
        scen_name_label = ttk.Label(self.single_mode_frame, textvariable=scen_name_var, font=("Consolas", 14, "bold"), anchor="center", foreground=ACCENT_COLOR)
        scen_name_label.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        def add_stat_row(r, label_key, val_key, col_offset=0):
            lbl = ttk.Label(self.single_mode_frame, text="temp"); lbl.grid(row=r, column=0+col_offset, sticky="w", padx=5, pady=2)
            val = ttk.Label(self.single_mode_frame, textvariable=self.stat_vars[val_key]); val.grid(row=r, column=1+col_offset, sticky="w", pady=2)
            return lbl

        lbl_target = ttk.Label(self.single_mode_frame, text="temp")
        lbl_target.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.label_target = lbl_target 
        
        val_target = ttk.Label(self.single_mode_frame, textvariable=self.stat_vars["Target(s):"])
        val_target.grid(row=1, column=1, columnspan=3, sticky="w", pady=2)

        self.label_hp = add_stat_row(2, "stats_hp", "Target HP:")
        self.label_radius = add_stat_row(2, "stats_radius", "Target Radius:", 2)
        self.label_regen = add_stat_row(3, "stats_regen", "Target Regen/s:")
        self.label_head_radius = add_stat_row(3, "stats_head_radius", "Target Head Radius:", 2)
        self.label_speed = add_stat_row(4, "stats_speed", "Target Max Speed:")
        self.label_duration = add_stat_row(4, "stats_duration", "Duration:", 2)
        self.label_timescale = add_stat_row(5, "stats_timescale", "Timescale:")
        
        self.bot_selection_frame = ttk.LabelFrame(self.single_mode_frame, padding="5")
        self.bot_selection_frame.grid(row=6, column=0, columnspan=4, sticky="w", padx=5, pady=(15, 5))
        
        self.bot_scroll_wrapper = ttk.Frame(self.bot_selection_frame, height=150, width=550) 
        self.bot_scroll_wrapper.pack(fill="x", expand=True)
        self.bot_scroll_wrapper.pack_propagate(False) 
        
        self.bot_scroll_area = ScrollableFrame(self.bot_scroll_wrapper)
        self.bot_scroll_area.pack(fill="both", expand=True)

        # BATCH MODE
        self.batch_container = ttk.Frame(self.frame2)
        batch_filter_frame = ttk.Frame(self.batch_container); batch_filter_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(batch_filter_frame, text="Filter (Exact Name):").pack(side="left", padx=5)
        self.batch_filter_var = tk.StringVar()
        ttk.Entry(batch_filter_frame, textvariable=self.batch_filter_var, width=15).pack(side="left", padx=5)
        ttk.Button(batch_filter_frame, text="Select All Bots", command=self._batch_select_all_bots).pack(side="left", padx=(10, 2))
        ttk.Button(batch_filter_frame, text="Check Match", command=lambda: self._apply_batch_check(True)).pack(side="left", padx=2)
        ttk.Button(batch_filter_frame, text="Uncheck Match", command=lambda: self._apply_batch_check(False)).pack(side="left", padx=2)
        ttk.Button(batch_filter_frame, text="Clear List", command=self._clear_batch_list).pack(side="left", padx=(30, 5))
        self.batch_scroll_frame = ScrollableFrame(self.batch_container); self.batch_scroll_frame.pack(fill="both", expand=True)

        # --- Frame 3: VARIANTS ---
        self.frame3 = ttk.LabelFrame(middle_container, padding="10", text="🚀 3. Create Variants")
        self.frame3.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # --- GENERATE & LOG ---
        generate_frame = ttk.Frame(self.ui_window); generate_frame.grid(row=4, column=0, sticky="ew", pady=10, padx=15)
        self.generate_button = ttk.Button(generate_frame, command=self._on_generate, state="disabled", style="CTA.TButton", width=30)
        self.generate_button.pack(anchor="center", pady=5)
        self.progress_bar = ttk.Progressbar(generate_frame, orient='horizontal', length=500, mode='determinate')
        self.progress_bar.pack(fill="x", expand=True, pady=5, padx=(20,20))
        
        self.disclaimer_label = ttk.Label(self.ui_window, text="⚠️ Note: Edge cases might exist. Please playtest before uploading generated scenarios.", font=("Consolas", 15, "bold"), foreground=ACCENT_COLOR)
        self.disclaimer_label.grid(row=5, column=0, pady=(0, 5))

        self.log_frame = ttk.LabelFrame(self.ui_window, padding="5", text="📝 Log")
        self.log_frame.grid(row=6, column=0, sticky="ew", pady=(0, 15), padx=15)
        self.log_widget = tk.Text(self.log_frame, height=8, state='disabled', wrap='word', font=("Consolas", 9), bg="black", fg=MATRIX_GREEN, borderwidth=0, highlightthickness=0)
        self.log_widget.pack(fill="both", expand=True)

    def _toggle_batch_mode(self):
        self.is_batch_mode = self.batch_mode_var.get()
        if self.is_batch_mode:
            self.single_mode_frame.pack_forget(); self.batch_container.pack(fill="both", expand=True)
            self.frame2.config(text=f"📊 Batch Queue ({len(self.batch_queue)})")
            self.generate_button.config(text=f"Generate Batch ({len(self.batch_queue)})", state="normal")
            print("--- Batch Mode Enabled: Click Scenarios to Add to Queue ---")
        else:
            self.batch_container.pack_forget(); self.single_mode_frame.pack(fill="both", expand=True)
            self.frame2.config(text=LANGUAGES[self.current_lang]["frame_stats"])
            self.generate_button.config(text=LANGUAGES[self.current_lang]["button_generate"])
            self._on_listbox_select()

    def _on_listbox_select(self, event=None):
        selected_indices = self.scenario_listbox.curselection()
        if not selected_indices: return
        selected_name = self.scenario_listbox.get(selected_indices[0])
        if self.is_batch_mode:
            self._add_to_batch(selected_name); self.scenario_listbox.selection_clear(0, tk.END)
        else:
            if self._after_id: self.root.after_cancel(self._after_id); self._after_id = None
            self.scenario_name_var.set(selected_name); self._on_load()

    def _add_to_batch(self, scenario_name):
        if scenario_name in self.batch_queue: return
        folder_path = self.folder_path_var.get(); full_path = os.path.join(folder_path, scenario_name + ".sce")
        data = parse_scenario_file(full_path)
        if not data: print(f"Error loading {scenario_name}"); return
        player_name = data.get("player_profile_name")
        bots = [name for name in data.get("character_profiles", {}).keys() if name != player_name]
        if not bots: print(f"No editable bots found in {scenario_name}"); return
        
        self.batch_queue[scenario_name] = {}
        row = ttk.Frame(self.batch_scroll_frame.scrollable_frame, style="Opaque.TFrame")
        row.pack(fill="x", pady=2, padx=5, anchor="w")
        self.batch_rows[scenario_name] = row
        del_btn = tk.Button(row, text="X", bg=DARK_BG, fg="red", bd=0, font=("Consolas", 10, "bold"), command=lambda s=scenario_name: self._remove_from_batch(s))
        del_btn.pack(side="left", padx=(0, 5))
        # Fill x so name pushes bots to right
        lbl = tk.Label(row, text=scenario_name, anchor="w", bg=ENTRY_BG, fg=ACCENT_COLOR, font=("Consolas", 9))
        lbl.pack(side="left", fill="x", expand=True, padx=2)
        bot_frame = ttk.Frame(row, style="Opaque.TFrame"); bot_frame.pack(side="right")

        for bot in bots:
            var = tk.BooleanVar(value=True); self.batch_queue[scenario_name][bot] = var
            cb = tk.Checkbutton(bot_frame, text=bot, variable=var, bg=ENTRY_BG, fg=LIGHT_TEXT, selectcolor=ENTRY_BG, activebackground=ENTRY_BG, activeforeground=ACCENT_COLOR, borderwidth=0, highlightthickness=0, padx=5)
            cb.pack(side="left", padx=2); self._style_checkbox_dynamic(cb, var)

        self.frame2.config(text=f"📊 Batch Queue ({len(self.batch_queue)})")
        self.generate_button.config(text=f"Generate Batch ({len(self.batch_queue)})")
        print(f"Added to batch: {scenario_name}")

    def _remove_from_batch(self, scenario_name):
        if scenario_name in self.batch_queue: del self.batch_queue[scenario_name]
        if scenario_name in self.batch_rows: self.batch_rows[scenario_name].destroy(); del self.batch_rows[scenario_name]
        self.frame2.config(text=f"📊 Batch Queue ({len(self.batch_queue)})")
        self.generate_button.config(text=f"Generate Batch ({len(self.batch_queue)})")

    def _clear_batch_list(self):
        for s_name in list(self.batch_queue.keys()): self._remove_from_batch(s_name)

    def _apply_batch_check(self, target_state):
        filter_text = self.batch_filter_var.get().lower()
        if not filter_text: return
        count = 0
        for s_name, bots_dict in self.batch_queue.items():
            for bot_name, var in bots_dict.items():
                if filter_text == bot_name.lower(): var.set(target_state); count += 1
        print(f"Updated {count} bots matching '{filter_text}'.")
    def _batch_select_all_bots(self):
        for s_name, bots_dict in self.batch_queue.items():
            for var in bots_dict.values(): var.set(True)
    
    # ------------------------

    def _on_language_change(self, event=None):
        selection = self.lang_combobox.get()
        new_lang_code = "JP" if selection == "日本語" else "EN"
        if new_lang_code != self.current_lang:
            self.current_lang = new_lang_code
            self.settings["language"] = self.current_lang
            self._update_ui_text()
    
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

    def _on_browse(self):
        def task(): return filedialog.askdirectory(parent=self.root)
        folder = self._run_with_hidden_ui(task)
        if folder: self.folder_path_var.set(folder); self._populate_scenario_list()

    def _clear_search(self):
        self.scenario_name_var.set("")
        self.search_entry.focus_set()

    def _build_variant_columns(self):
        for widget in self.frame3.winfo_children(): widget.destroy()
        
        num_variants = len(self.variant_configs)
        # Calculate total grid columns needed: (Variants) + (Separators)
        total_grid_cols = (num_variants * 2) - 1
        
        # Configure the Edit Button to span across the top and stick to the Right
        self.edit_button = ttk.Button(self.frame3, command=self._toggle_edit_mode)
        self.edit_button.grid(row=0, column=0, columnspan=total_grid_cols, sticky="e", pady=(0, 5))
        
        col_index = 0
        for vtype_key, config in self.variant_configs.items():
            # Create the column
            widgets = self._create_variant_column(self.frame3, vtype_key, config['values'], config['suffix'], config['display_name'])
            widgets['frame'].grid(row=1, column=col_index, padx=10, sticky="ns")
            config['widgets'] = widgets
            
            col_index += 1
            
            # Add Separator if it's not the last column
            if col_index < total_grid_cols:
                sep = ttk.Separator(self.frame3, orient='vertical')
                sep.grid(row=1, column=col_index, sticky="ns", padx=5)
                col_index += 1
                
        self._update_ui_text()
    
    def _create_variant_column(self, parent, vtype_key, values, suffix, display_name):
        frame = ttk.Frame(parent)
        header_var = tk.StringVar(value=self.variant_configs[vtype_key]['tag_text'])
        header_label = ttk.Label(frame, text=f"{display_name} Variants")
        header_entry = ttk.Entry(frame, textvariable=header_var, width=12)
        header_label.pack(pady=(0, 10))
        btn_frame = ttk.Frame(frame); btn_frame.pack(pady=5)
        ttk.Button(btn_frame, command=lambda v=vtype_key: self._select_all(v, True)).pack(side='left', padx=2)
        ttk.Button(btn_frame, command=lambda v=vtype_key: self._select_all(v, False)).pack(side='left', padx=2)
        widgets = {'labels': [], 'entries': [], 'header_label': header_label, 'header_entry': header_entry, 'header_var': header_var, 'btn_frame': btn_frame}
        for i, val in enumerate(values):
            row_frame = ttk.Frame(frame); row_frame.pack(anchor="w", pady=1)
            key = f"{vtype_key}_{i}"
            self.checkbox_vars[key] = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(row_frame, variable=self.checkbox_vars[key], bg=ENTRY_BG, fg=LIGHT_TEXT, selectcolor=ENTRY_BG, activebackground=ENTRY_BG, activeforeground=ACCENT_COLOR, borderwidth=0, highlightthickness=0, padx=2, pady=0)
            cb.pack(side='left'); self._style_checkbox_dynamic(cb, self.checkbox_vars[key]) 
            label = tk.Label(row_frame, text=f"{val}{suffix}", bg=ENTRY_BG, fg=LIGHT_TEXT, font=("Consolas", 10))
            label.pack(side='left'); label.bind("<Button-1>", lambda e, k=key: self.checkbox_vars[k].set(not self.checkbox_vars[k].get()))
            widgets['labels'].append(label)
            entry_var = tk.StringVar(value=str(val))
            entry = ttk.Entry(row_frame, textvariable=entry_var, width=4)
            widgets['entries'].append({'widget': entry, 'var': entry_var})
            self.checkbox_vars[key].trace_add("write", self._on_settings_change); entry_var.trace_add("write", self._on_settings_change)
        header_var.trace_add("write", self._on_settings_change); widgets['frame'] = frame; return widgets
    
    def _load_profile(self, profile_name):
        self.ui_ready = False
        print(f"Loading profile: {profile_name}"); self.active_profile_name = profile_name; self.settings['last_active_profile'] = profile_name
        profile_data = self.settings["profiles"][profile_name]
        self.variant_configs = {}
        for key, config in MODIFIER_CONFIG.items():
            self.variant_configs[key] = {"values": profile_data.get(config['value_key'], get_default_profile()[config['value_key']]), "suffix": config['suffix'], "tag_text": profile_data["variant_tags"][key], "display_name": config['display_name'] if key == "DURATION" else profile_data["variant_tags"][key]}
        self.folder_path_var.set(profile_data["folder_path"])
        self._build_variant_columns()
        for key, value in profile_data["checkboxes"].items():
            if key in self.checkbox_vars: self.checkbox_vars[key].set(value)
        self._update_profile_dropdown()
        self.is_edit_mode = False
        self._toggle_edit_mode(); self._toggle_edit_mode()
        self.ui_ready = True
    def _update_profile_dropdown(self): self.profile_combobox['values'] = list(self.settings["profiles"].keys()); self.profile_combobox.set(self.active_profile_name)
    def _on_profile_select(self, event=None):
        new_profile_name = self.profile_combobox.get()
        if new_profile_name != self.active_profile_name:
            self._on_settings_change(); self._load_profile(new_profile_name)

    def _get_unique_profile_name(self):
        base = "Profile"; count = 1
        while True:
            name = f"{base} {count}"
            if name not in self.settings["profiles"]: return name
            count += 1
    def _on_new_profile(self):
        self._on_settings_change()
        new_name = self._get_unique_profile_name()
        self.settings["profiles"][new_name] = json.loads(json.dumps(self.settings["profiles"][self.active_profile_name]))
        self._load_profile(new_name)
        print(f"Created and switched to new profile: {new_name}")
    def _on_rename_profile(self):
        lang = LANGUAGES[self.current_lang]; old_name = self.active_profile_name
        def task(): return askstring(lang["dialog_rename_profile_title"], lang["dialog_rename_profile_prompt"].format(old_name=old_name), parent=self.root)
        new_name = self._run_with_hidden_ui(task)
        if new_name and not new_name.isspace():
            if new_name in self.settings["profiles"]: messagebox.showerror("Error", lang["error_profile_exists"]); return
            self._on_settings_change()
            self.settings["profiles"][new_name] = self.settings["profiles"].pop(old_name)
            self._load_profile(new_name); print(f"Profile '{old_name}' renamed to '{new_name}'")
    def _on_delete_profile(self):
        lang = LANGUAGES[self.current_lang]
        if len(self.settings["profiles"]) <= 1: messagebox.showerror("Error", lang["error_delete_last_profile"]); return
        profile_to_delete = self.active_profile_name
        def task(): return messagebox.askyesno(lang["dialog_confirm_delete_title"], lang["dialog_confirm_delete_prompt"].format(profile_to_delete=profile_to_delete), parent=self.root)
        if self._run_with_hidden_ui(task):
            del self.settings["profiles"][profile_to_delete]
            new_active_profile = list(self.settings["profiles"].keys())[0]
            self._load_profile(new_active_profile); print(f"Profile '{profile_to_delete}' deleted.")
    
    def _on_load(self):
        if self.is_batch_mode: return
        
        for widget in self.bot_scroll_area.scrollable_frame.winfo_children(): widget.destroy()
        
        self.bot_selection_vars = {}
        user_typed_name = self.scenario_name_var.get().strip(); folder_path = self.folder_path_var.get()
        if not folder_path or not user_typed_name: self.stat_vars["Scenario Name:"].set(LANGUAGES[self.current_lang]['stats_scenario_name']); return
        full_path = os.path.join(folder_path, user_typed_name + ".sce")
        if not os.path.exists(full_path):
            self.generate_button.config(state="disabled"); self.stat_vars["Scenario Name:"].set(LANGUAGES[self.current_lang]['stats_scenario_name'])
            for key, var in self.stat_vars.items():
                if key != "Scenario Name:": var.set("N/A")
            return
        print(f"Attempting to load: {full_path}")
        self.loaded_scenario_data = parse_scenario_file(full_path)
        if self.loaded_scenario_data:
            self.loaded_scenario_data["user_provided_name"] = user_typed_name; self.stat_vars["Scenario Name:"].set(f"{LANGUAGES[self.current_lang]['label_scenario_name']} {user_typed_name}")
            self.stat_vars["Timescale:"].set(self.loaded_scenario_data.get('global_properties', {}).get('Timescale', 'N/A'))
            duration = self.loaded_scenario_data.get('global_properties', {}).get('Timelimit', 'N/A'); self.stat_vars["Duration:"].set(f"{duration:.1f}s" if isinstance(duration, (int, float)) else "N/A")
            player_name = self.loaded_scenario_data.get("player_profile_name"); all_profiles = self.loaded_scenario_data.get("character_profiles", {})
            target_names = [name for name in all_profiles.keys() if name != player_name]
            if target_names:
                
                # --- TRUNCATION (Safer Limit) ---
                full_target_str = ", ".join(target_names)
                if len(full_target_str) > 60:
                    display_str = full_target_str[:57] + "..."
                else:
                    display_str = full_target_str
                
                self.stat_vars["Target(s):"].set(display_str)
                # -----------------------------
                
                first_target_profile = all_profiles.get(target_names[0], {})
                self.stat_vars["Target Radius:"].set(first_target_profile.get("MainBBRadius", "N/A")); self.stat_vars["Target Head Radius:"].set(first_target_profile.get("MainBBHeadRadius", "N/A"))
                self.stat_vars["Target Max Speed:"].set(first_target_profile.get("MaxSpeed", "N/A")); self.stat_vars["Target HP:"].set(first_target_profile.get("MaxHealth", "N/A")); self.stat_vars["Target Regen/s:"].set(first_target_profile.get("HealthRegenPerSec", "N/A"))
                
                self.bot_selection_frame.config(text=LANGUAGES[self.current_lang]["frame_targets_modify"])
                
                inner_frame = self.bot_scroll_area.scrollable_frame
                
                btn_frame = ttk.Frame(inner_frame); btn_frame.pack(anchor='w', pady=(0,5))
                self.bot_select_all_btn = ttk.Button(btn_frame, text=LANGUAGES[self.current_lang]["button_select_all"], command=lambda: self._select_all_bots(True))
                self.bot_select_all_btn.pack(side='left', padx=2)
                
                checkbox_container = ttk.Frame(inner_frame); checkbox_container.pack(fill='x')
                for i, bot_name in enumerate(target_names):
                    var = tk.BooleanVar(value=True); self.bot_selection_vars[bot_name] = var
                    cb = tk.Checkbutton(checkbox_container, text=bot_name, variable=var, bg=ENTRY_BG, fg=LIGHT_TEXT, selectcolor=ENTRY_BG, activebackground=ENTRY_BG, activeforeground=ACCENT_COLOR, borderwidth=0, highlightthickness=0, padx=5, pady=2)
                    cb.grid(row=i // 4, column=i % 4, sticky='w', padx=5, pady=2); self._style_checkbox_dynamic(cb, var)
            else:
                for key in self.stat_vars:
                    if key not in ["Scenario Name:", "Timescale:", "Duration:"]: self.stat_vars[key].set("N/A")
            self.generate_button.config(state="normal"); print("✅ Success! Scenario file loaded.")
        else: messagebox.showerror("Error", f"Found '{user_typed_name}.sce' but could not read or parse it."); self.generate_button.config(state="disabled")

    def _on_generate(self):
        if self.is_batch_mode:
            scenarios_to_process = list(self.batch_queue.keys())
            if not scenarios_to_process: messagebox.showerror("Error", "Batch queue is empty!"); return
        else:
            if not self.loaded_scenario_data: messagebox.showerror("Error", "No scenario loaded."); return
            scenarios_to_process = [self.scenario_name_var.get()]
        self._on_settings_change()
        tasks = []
        for vtype_key, config in self.variant_configs.items():
            for i, value in enumerate(config['values']):
                if self.checkbox_vars[f"{vtype_key}_{i}"].get(): tasks.append((vtype_key, value))
        if not tasks: print("--- No variants were selected. ---"); return

        print(f"\n--- Starting Generation of {len(tasks) * len(scenarios_to_process)} files ---")
        self.generate_button.config(state="disabled") # Disable during processing
        self.progress_bar['maximum'] = len(tasks) * len(scenarios_to_process); self.progress_bar['value'] = 0
        self.ui_window.update() # Force UI update
        
        created_count = 0; overwrite_decision = 'ask'; folder_path = self.folder_path_var.get()
        
        for s_index, s_name in enumerate(scenarios_to_process):
            print(f"Processing: {s_name}...")
            full_path = os.path.join(folder_path, s_name + ".sce"); scenario_data = parse_scenario_file(full_path)
            if not scenario_data: print(f"❌ Could not load {s_name}, skipping."); continue
            scenario_data["user_provided_name"] = s_name
            
            if self.is_batch_mode:
                file_bots = self.batch_queue.get(s_name, {}); selected_bots = [b for b, v in file_bots.items() if v.get()]
            else:
                selected_bots = [bot_name for bot_name, var in self.bot_selection_vars.items() if var.get()]
            
            if not selected_bots and any(MODIFIER_CONFIG[t[0].upper()]['scope'] == 'Character Profile' for t in tasks):
                 print(f"   ⚠ No targets selected for {s_name}. Skipping character variants.")

            for t_index, (vtype, val) in enumerate(tasks):
                should_create = True
                new_scenario_name = calculate_target_filename(s_name, vtype, val, self.variant_configs)
                new_filename = new_scenario_name + ".sce"
                if overwrite_decision != 'yes_all':
                    if os.path.exists(os.path.join(folder_path, new_filename)):
                        if overwrite_decision == 'ask': 
                            dialog = OverwriteDialog(self.ui_window, new_filename, self.current_lang); overwrite_decision = dialog.result
                        if overwrite_decision == 'no_all': print("⏩ Skipping remaining overwrites."); break
                        if overwrite_decision == 'no': print(f"⏩ Skipped: {new_filename}"); should_create = False
                if should_create:
                    result = create_variant_file(scenario_data, folder_path, vtype, val, self.variant_configs, selected_bots)
                    if result == "success": created_count += 1
                current_step = (s_index * len(tasks)) + t_index + 1
                self.progress_bar['value'] = current_step; self.ui_window.update_idletasks()
        
        print(f"--- Finished! Created {created_count} new files. ---")
        self._populate_scenario_list(); self.progress_bar['value'] = 0
        
        self.generate_button.config(state="normal") # Re-enable
        
        # --- FIX: Stronger Focus Force ---
        if hasattr(self, 'search_entry'):
            def restore_focus():
                self.search_entry.focus_force()     # Force OS to give focus
                self.search_entry.icursor(tk.END)   # Move caret to end
                self.search_entry.select_range(0, tk.END) # Optional: Select all text to make it obvious
            
            self.root.after(100, restore_focus)

    def _toggle_edit_mode(self):
        self.is_edit_mode = not self.is_edit_mode
        lang = LANGUAGES[self.current_lang]
        if self.is_edit_mode:
            self.edit_button.config(text=lang["button_save_values"])
            for config in self.variant_configs.values():
                w = config['widgets']; w['header_label'].pack_forget(); w['header_entry'].pack(pady=(0, 5))
                for i in range(len(w['labels'])): w['labels'][i].pack_forget(); w['entries'][i]['widget'].pack(side='left')
        else:
            try:
                new_tags_map = {key: cfg['widgets']['header_var'].get().strip() for key, cfg in self.variant_configs.items()}
                if any(not tag for tag in new_tags_map.values()): messagebox.showerror("Error", lang["error_tags_empty"]); self.is_edit_mode = True; return
                {key: [int(e['var'].get()) for e in cfg['widgets']['entries']] for key, cfg in self.variant_configs.items()}
                self._on_settings_change(); self.edit_button.config(text=lang["button_edit_values"])
                for vtype_key, config in self.variant_configs.items():
                    if vtype_key != "DURATION": config['display_name'] = new_tags_map[vtype_key]
                    w = config['widgets']; w['header_label'].config(text=f"{config['display_name']} Variants"); w['header_entry'].pack_forget()
                    w['header_label'].pack(pady=(0, 5), before=w['btn_frame'])
                    for i, value in enumerate(config['values']):
                        w['labels'][i].config(text=f"{value}{config['suffix']}"); w['entries'][i]['widget'].pack_forget(); w['labels'][i].pack(side='left')
            except ValueError: messagebox.showerror("Error", lang["error_must_be_whole_numbers"]); self.is_edit_mode = True
    def _select_all(self, vtype_key, state):
        if vtype_key in self.variant_configs:
            for i in range(len(self.variant_configs[vtype_key]['values'])): self.checkbox_vars[f"{vtype_key}_{i}"].set(state)
    def _select_all_bots(self, state):
        for var in self.bot_selection_vars.values(): var.set(state)

    def _on_settings_change(self, *args):
        if not self.ui_ready: return
        active_profile = self.settings["profiles"][self.active_profile_name]
        active_profile["folder_path"] = self.folder_path_var.get()
        active_profile["checkboxes"] = {key: var.get() for key, var in self.checkbox_vars.items()}
        try:
            for key, config in self.variant_configs.items():
                if 'widgets' not in config: continue
                master_config = MODIFIER_CONFIG[key]
                current_values = [int(e['var'].get()) for e in config['widgets']['entries']]
                current_tag = config['widgets']['header_var'].get().strip()
                if not current_tag: current_tag = master_config['tag_text']
                active_profile[master_config['value_key']] = current_values
                active_profile["variant_tags"][key] = current_tag
                config["values"] = current_values
                config["tag_text"] = current_tag
        except (ValueError, tk.TclError): pass
    def _on_closing(self):
        if self.ui_ready:
            self._on_settings_change()
            if self.bg_image_id:
                coords = self.bg_canvas.coords(self.bg_image_id)
                if coords:
                    self.settings["bg_x"] = coords[0]; self.settings["bg_y"] = coords[1]
                    self.settings["bg_scale"] = self.bg_scale; self.settings["bg_brightness"] = self.bg_brightness
            save_settings(self.settings)
        self.root.destroy()