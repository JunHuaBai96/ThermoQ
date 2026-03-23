import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import time
import re
import warnings
import pandas as pd
import numpy as np
import subprocess
import webbrowser
import platform
from decimal import Decimal
from periodic_table import PERIODIC_TABLE


def _step_to_output_decimals(step):
    """Decimal places needed so batch file values reflect the chosen step (e.g. 0.005 -> 3)."""
    try:
        d = Decimal(str(float(step))).normalize()
        if d == 0:
            return 8
        e = d.as_tuple().exponent
        return max(0, -e) if e < 0 else 0
    except Exception:
        return 8


def _composition_range_float64(lo, hi, step):
    """Inclusive lo..hi in float64 steps (avoids float32 / arange endpoint bugs)."""
    lo, hi, step = float(lo), float(hi), float(step)
    if step <= 0:
        return np.array([lo], dtype=np.float64)
    out = []
    i = 0
    while True:
        x = lo + i * step
        if x > hi + 1e-12:
            break
        out.append(x)
        i += 1
        if i > 10_000_000:
            break
    return np.array(out, dtype=np.float64)

# Optional imports for plotting
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.animation as animation
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, Matern
    from scipy.interpolate import griddata
    from scipy.ndimage import gaussian_filter
    SKLEARN_AVAILABLE = True
    SCIPY_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    SCIPY_AVAILABLE = False

class ElementSelector:
    def __init__(self, parent, gui=None):
        self.parent = parent
        self._gui = gui  # ThermoQGUI for translations (tr)
        self.selected_elements = {}  # Dictionary to store selected elements and their compositions (always in wt%)
        self.main_element = None  # The first added element will be considered main element
        
        # Create main frame; text updated by refresh_from_language()
        self.frame = ttk.LabelFrame(parent, text="Element Selection", padding="10")
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=5)
        
        # Create element selection area
        self.create_element_selection()
        
        # Create selected elements display area
        self.create_selected_elements_display()
    
    def create_element_selection(self):
        # Create a frame for element selection
        selection_frame = ttk.Frame(self.frame)
        selection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=3, pady=3)
        
        # Create element dropdown
        self.label_element = ttk.Label(selection_frame, text="Element:")
        self.label_element.grid(row=0, column=0, padx=3, pady=3)
        self.element_var = tk.StringVar()
        self.element_dropdown = ttk.Combobox(selection_frame, textvariable=self.element_var, 
                                           values=sorted(PERIODIC_TABLE.keys()), width=10)
        self.element_dropdown.grid(row=0, column=1, padx=3, pady=3)
        
        # Create composition entry (always in wt%)
        self.label_composition = ttk.Label(selection_frame, text="Composition (wt%):")
        self.label_composition.grid(row=0, column=2, padx=3, pady=3)
        self.composition_var = tk.StringVar()
        self.composition_entry = ttk.Entry(selection_frame, textvariable=self.composition_var, width=10)
        self.composition_entry.grid(row=0, column=3, padx=3, pady=3)
        
        # Add button
        self.button_add = ttk.Button(selection_frame, text="Add Element", 
                                     command=self.add_element)
        self.button_add.grid(row=0, column=4, padx=3, pady=3)

        # Hint: first added element is the main element
        self.main_hint_label = ttk.Label(
            self.frame,
            text="Hint: The first added element will be the main element",
            foreground="gray",
            wraplength=400
        )
        self.main_hint_label.grid(row=2, column=0, sticky='w', padx=3, pady=(0,3))
        
    
    def create_selected_elements_display(self):
        # Create a frame for displaying selected elements
        self.display_frame = ttk.LabelFrame(self.frame, text="Selected Elements", padding="5")
        self.display_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=3, pady=3)
        
        # Create treeview for displaying elements
        self.tree = ttk.Treeview(self.display_frame, columns=("Element", "Name", "Composition"), 
                                show="headings", height=5)
        self.tree.heading("Element", text="Element")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Composition", text="Composition (wt%)")
        
        self.tree.column("Element", width=80)
        self.tree.column("Name", width=150)
        self.tree.column("Composition", width=120)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.display_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Add remove button
        self.button_remove = ttk.Button(self.display_frame, text="Remove Selected", 
                                        command=self.remove_element)
        self.button_remove.grid(row=1, column=0, pady=3)
    
    def tr(self, key, default):
        if self._gui is not None and hasattr(self._gui, 'tr'):
            return self._gui.tr(key, default)
        return default

    def refresh_from_language(self):
        """Refresh static labels after Help → Language change."""
        if not self._gui:
            return
        t = self.tr
        self.frame.config(text=t('el_frame_title', 'Element Selection'))
        self.label_element.config(text=t('el_label_element', 'Element:'))
        self.label_composition.config(text=t('el_label_composition', 'Composition (wt%):'))
        self.button_add.config(text=t('el_add_button', 'Add Element'))
        self.display_frame.config(text=t('el_selected_frame', 'Selected Elements'))
        self.tree.heading("Element", text=t('el_tree_col_element', 'Element'))
        self.tree.heading("Name", text=t('el_tree_col_name', 'Name'))
        self.tree.heading("Composition", text=t('el_tree_col_comp', 'Composition (wt%)'))
        self.button_remove.config(text=t('el_remove_button', 'Remove Selected'))
        if hasattr(self, 'main_hint_label'):
            try:
                if self.main_hint_label.winfo_exists():
                    self.main_hint_label.config(
                        text=t('el_hint_main', 'Hint: The first added element will be the main element')
                    )
            except tk.TclError:
                pass
        if hasattr(self, 'main_element_label') and self.main_element:
            try:
                if self.main_element_label.winfo_exists():
                    self.main_element_label.config(
                        text=t('el_main_lbl', 'Main element: {elem}').format(elem=self.main_element)
                    )
            except tk.TclError:
                pass
        if hasattr(self, 'sum_status_label'):
            try:
                if self.sum_status_label.winfo_exists():
                    total_wt, is_complete = self.check_composition_sum()
                    if is_complete:
                        txt = t('el_sum_ok', 'Total composition: {total:.2f} wt% ✓').format(total=total_wt)
                        color = 'green'
                    else:
                        txt = t(
                            'el_sum_need_100',
                            'Total composition: {total:.2f} wt% (should be 100.00 wt%)',
                        ).format(total=total_wt)
                        color = 'red'
                    self.sum_status_label.config(text=txt, foreground=color)
            except tk.TclError:
                pass

    def convert_at_to_wt(self, at_composition):
        """Convert atomic percent to weight percent"""
        # at_composition is a dict: {element: at%}
        if not at_composition:
            return {}
        
        # Calculate total atomic mass
        total_atomic_mass = sum(at_composition[el] * PERIODIC_TABLE[el]['mass'] 
                                for el in at_composition)
        
        if total_atomic_mass == 0:
            return {}
        
        # Convert to weight percent
        wt_composition = {}
        for element, at_pct in at_composition.items():
            wt_pct = (at_pct * PERIODIC_TABLE[element]['mass']) / total_atomic_mass * 100
            wt_composition[element] = wt_pct
        
        return wt_composition
    
    def convert_wt_to_at(self, wt_composition):
        """Convert weight percent to atomic percent"""
        # wt_composition is a dict: {element: wt%}
        if not wt_composition:
            return {}
        
        # Calculate total moles
        total_moles = sum(wt_composition[el] / PERIODIC_TABLE[el]['mass'] 
                         for el in wt_composition)
        
        if total_moles == 0:
            return {}
        
        # Convert to atomic percent
        at_composition = {}
        for element, wt_pct in wt_composition.items():
            at_pct = (wt_pct / PERIODIC_TABLE[element]['mass']) / total_moles * 100
            at_composition[element] = at_pct
        
        return at_composition
    
    def check_composition_sum(self):
        """Check if the total composition equals 100 wt%"""
        total_wt = sum(self.selected_elements.values())
        return total_wt, abs(total_wt - 100.0) <= 0.01  # Allow small floating point errors
    
    def add_element(self):
        element = self.element_var.get()
        try:
            composition = float(self.composition_var.get())
            if element in PERIODIC_TABLE and 0 <= composition <= 100:
                if element not in self.selected_elements:
                    # Store composition in wt%
                    self.selected_elements[element] = composition
                    
                    # Update display
                    self.update_display()
                    
                    # Check composition sum and show status
                    total_wt, is_complete = self.check_composition_sum()
                    if hasattr(self, 'sum_status_label'):
                        self.sum_status_label.destroy()
                    
                    if is_complete:
                        status_text = self.tr('el_sum_ok', 'Total composition: {total:.2f} wt% ✓').format(
                            total=total_wt
                        )
                        status_color = "green"
                    else:
                        status_text = self.tr(
                            'el_sum_need_100',
                            'Total composition: {total:.2f} wt% (should be 100.00 wt%)',
                        ).format(total=total_wt)
                        status_color = "red"
                    
                    # Create status label with wraplength to prevent text cutoff
                    self.sum_status_label = ttk.Label(self.frame, text=status_text, foreground=status_color, wraplength=500)
                    self.sum_status_label.grid(row=3, column=0, sticky='w', padx=3, pady=(0,3))
                    
                    # Set main element if not set yet
                    if self.main_element is None:
                        self.main_element = element
                        # Hide hint label and show current main element label
                        if hasattr(self, 'main_hint_label'):
                            self.main_hint_label.destroy()
                        if hasattr(self, 'main_element_label'):
                            self.main_element_label.destroy()
                        self.main_element_label = ttk.Label(
                            self.frame,
                            text=self.tr('el_main_lbl', 'Main element: {elem}').format(elem=self.main_element),
                            foreground="blue",
                            wraplength=400,
                        )
                        self.main_element_label.grid(row=2, column=0, sticky='w', padx=3, pady=(0,3))
                    self.element_var.set("")
                    self.composition_var.set("")
                else:
                    tk.messagebox.showwarning(
                        self.tr('dlg_warning', 'Warning'),
                        self.tr('el_warn_duplicate', 'Element already added!'),
                    )
            else:
                tk.messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('el_err_invalid_comp', 'Invalid element or composition!'),
                )
        except ValueError:
            tk.messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr('el_err_comp_number', 'Please enter a valid number for composition!'),
            )
    
    def remove_element(self):
        selected_item = self.tree.selection()
        if selected_item:
            element = self.tree.item(selected_item[0])['values'][0]
            del self.selected_elements[element]
            self.tree.delete(selected_item[0])
            # Update display after removal
            self.update_display()
            
            # Update composition sum status
            if self.selected_elements:
                total_wt, is_complete = self.check_composition_sum()
                if hasattr(self, 'sum_status_label'):
                    self.sum_status_label.destroy()
                
                if is_complete:
                    status_text = self.tr('el_sum_ok', 'Total composition: {total:.2f} wt% ✓').format(
                        total=total_wt
                    )
                    status_color = "green"
                else:
                    status_text = self.tr(
                        'el_sum_need_100',
                        'Total composition: {total:.2f} wt% (should be 100.00 wt%)',
                    ).format(total=total_wt)
                    status_color = "red"
                
                # Create status label with wraplength to prevent text cutoff
                self.sum_status_label = ttk.Label(self.frame, text=status_text, foreground=status_color, wraplength=500)
                self.sum_status_label.grid(row=3, column=0, sticky='w', padx=5, pady=(0,5))
            else:
                # No elements left, remove status label
                if hasattr(self, 'sum_status_label'):
                    self.sum_status_label.destroy()
            
            # If main element removed, reset to next available or None
            if self.main_element == element:
                self.main_element = next(iter(self.selected_elements.keys()), None)
                if hasattr(self, 'main_element_label'):
                    self.main_element_label.destroy()
                if self.main_element:
                    self.main_element_label = ttk.Label(self.frame, text=f"Main element: {self.main_element}", foreground="blue", wraplength=400)
                    self.main_element_label.grid(row=2, column=0, sticky='w', padx=5, pady=(0,5))
                else:
                    # No main element left, show hint again
                    if hasattr(self, 'main_hint_label'):
                        self.main_hint_label.destroy()
                    self.main_hint_label = ttk.Label(self.frame, text="Hint: The first added element will be the main element", foreground="gray", wraplength=400)
                    self.main_hint_label.grid(row=2, column=0, sticky='w', padx=3, pady=(0,3))
    
    def update_display(self):
        """Update the display with current elements"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Display in wt%
        for element, comp in self.selected_elements.items():
            self.tree.insert("", "end", values=(
                element,
                PERIODIC_TABLE[element]['name'],
                f"{comp:.2f} wt%"
            ))
    
    def get_composition(self):
        # Return composition in wt% as numeric values
        return {element: float(comp) for element, comp in self.selected_elements.items()}

class SplashScreen:
    def __init__(self, root):
        # Create the splash window
        self.splash_root = tk.Toplevel(root)
        self.splash_root.overrideredirect(True)  # Remove window decorations
        
        try:
            # Load and resize splash image
            splash_img = Image.open("images/logo.png")
            # Set splash size
            splash_size = (600, 600)  # Set to 600x600 pixels
            splash_img = splash_img.resize(splash_size, Image.Resampling.LANCZOS)
            self.splash_photo = ImageTk.PhotoImage(splash_img)
            
            # Calculate position for center of screen
            screen_width = self.splash_root.winfo_screenwidth()
            screen_height = self.splash_root.winfo_screenheight()
            x = (screen_width - splash_size[0]) // 2
            y = (screen_height - splash_size[1]) // 2
            
            # Set splash window size and position
            self.splash_root.geometry(f"{splash_size[0]}x{splash_size[1]}+{x}+{y}")
            
            # Create and pack splash image label with yellow background
            splash_label = tk.Label(self.splash_root, image=self.splash_photo, bg='yellow')
            splash_label.pack(fill='both', expand=True)
            
            # Lift splash window to top
            self.splash_root.lift()
            self.splash_root.update()
            
        except Exception as e:
            print(f"Error loading splash screen: {e}")
            self.splash_root.destroy()
    
    def destroy(self):
        self.splash_root.destroy()

class ThermoQGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ThermoQ")
        # Set compact default window size
        self.root.geometry("920x680")
        # Set a sensible minimum to prevent cramped UI
        self.root.minsize(820, 560)
        self.root.withdraw()  # Hide main window initially
        
        # Set yellow background for main window
        self.root.configure(bg='yellow')
        
        # Initialize Pandat data storage
        self.pandat_p_data = None  # P.xls data (Equilibrium/Lever solidification)
        self.pandat_ts_data = None  # Ts.xlsx data (Equilibrium/Lever solidification)
        self.pandat_p_s_data = None  # P-S.xlsx data (Scheil solidification)
        self.pandat_ts_s_data = None  # Ts-S.xlsx data (Scheil solidification)
        self.available_elements = []  # Elements available from Pandat data
        self.pandat_solid_phase = None   # Detected solid phase from w(*@*) / -T//fw(@*), e.g. FCC_A1, BCC_A2
        self.pandat_q_col = None         # Detected Q column, e.g. -T//fw(@FCC_A1)
        self.last_batch_results_df = None  # Batch composition-space table (pandas DataFrame)
        self.last_batch_n_limit = None  # Total rows in last batch (P + P-S when mode All)
        self.last_batch_n_p = 0  # Rows taken from P file in last batch
        self.last_batch_n_ps = 0  # Rows taken from P-S file in last batch
        self.last_batch_mode = None  # "Lever" | "Scheil" | "All" — last compute source mode
        self._tool_lang_refresh_callbacks = []  # Callables to refresh tool window labels when Help → Language changes

        # Create menu bar
        self.menu_bar = tk.Menu(root)
        self.root.config(menu=self.menu_bar)

        # Language resources
        self.language = 'en'
        self.texts = {
            'en': {
                'menu_file': 'File',
                'menu_import': 'Import',
                'menu_plot': 'Plot',
                'menu_tools': 'Tools',
                'menu_help': 'Help',
                'file_exit': 'Exit',
                'import_pandat': 'Pandat to ThermoQ',
                'plot_phase': 'Plot Phase Surfaces',
                'plot_qtrue': 'Plot Qtrue Values',
                'plot_liqvec': 'Plot Liquidus Vectors',
                'plot_kvec': 'Plot Solid-Liquid Partition Coefficients',
                'plot_t0surf': 'Plot T-zero Surface',
                'tools_converter': 'Composition Converter (wt% ↔ at%)',
                'tools_generate': 'Generate Thermo-calc Batch File',
                'tools_extract_exp': 'Extract Thermo-calc Results',
                'tools_extract_pandat': 'Extract Pandat Results',
                'help_language': 'Language',
                'help_english': 'English',
                'help_chinese': '中文',
                'help_example': 'Example',
                # Shared tool window UI
                'ui_close': 'Close',
                'ui_plot': 'Plot',
                'ui_export': 'Export',
                'plot_ready': 'Ready to plot',
                'plot_vis_label': 'Visualization:',
                'plot_elev_range': '(0–90)',
                'plot_azim_range': '(-180–180)',
                'plot_phase_win_title': 'Plot Phase Surfaces (Liquidus/Solidus)',
                'plot_phase_heading': 'Phase Surface Plotter',
                'plot_phase_intro': (
                    'Pandat: plot solidus/liquidus surfaces using imported Pandat data.\n'
                    'Thermo-calc: plot surfaces using Excel exported from Extract Thermo-calc Results → Melting Range.\n'
                    'Thermo-calc columns: use Liquidus_Temperature (liquidus) / Solidus_Temperature (solidus).'
                ),
                'plot_phase_tab_pandat': 'Pandat',
                'plot_phase_tab_tc': 'Thermo-calc',
                'plot_phase_settings_shared': 'Settings (Shared)',
                'plot_phase_dataset': 'Dataset:',
                'plot_phase_ds_equilibrium': 'Equilibrium/Lever',
                'plot_phase_ds_scheil': 'Scheil',
                'plot_phase_type': 'Type:',
                'plot_phase_liquidus': 'Liquidus',
                'plot_phase_solidus': 'Solidus',
                'plot_phase_ready_pandat': 'Ready to plot (Pandat)',
                'plot_phase_ready_tc': 'Ready to plot (Thermo-calc)',
                'plot_phase_note_pandat': 'Use Import → Pandat to ThermoQ first. Then select Dataset + Elements and click Plot.',
                'plot_phase_plot_pandat': 'Plot (Pandat)',
                'plot_phase_plot_tc': 'Plot (Thermo-calc)',
                'plot_phase_output_settings': 'Output Settings',
                'plot_phase_tc_excel_frame': 'Input Excel (from Melting Range output.xlsx)',
                'plot_phase_fd_mr': 'Select Melting Range Excel',
                'plot_tc_loaded_rows': 'Loaded {n} rows from Excel.',
                'qtrue_win_title': 'Plot Qtrue Values',
                'qtrue_heading': 'Qtrue Value Plotter',
                'qtrue_intro': (
                    'Plot Qtrue values (-T//fw(@phase)) using imported Pandat data.\n'
                    'Phase and Q column are detected from w(*@*) and -T//fw(@*) in the data.\n'
                    'Select X and Y elements. Equilibrium/Lever: P.xlsx; Scheil: P-S.xlsx.'
                ),
                'qtrue_settings': 'Settings',
                'qtrue_dataset': 'Dataset:',
                'qtrue_ds_equilibrium': 'Equilibrium/Lever',
                'qtrue_ds_scheil': 'Scheil',
                'qtrue_ready': 'Ready to plot',
                'liqvec_win_title': 'Plot Liquidus Vectors',
                'liqvec_heading': 'Liquidus Vector Plotter',
                'liqvec_intro': (
                    'Plot quiver plots showing liquidus vectors from Pandat data. '
                    'Data is read from P file (Equilibrium/Lever) or P-S file (Scheil) imported via Pandat to ThermoQ.'
                ),
                'liqvec_solid_mode': 'Solidification Mode',
                'liqvec_elem_sel': 'Element Selection',
                'liqvec_options': 'Options',
                'liqvec_clean_fill': 'Clean and fill data before plotting',
                'liqvec_export_proc': 'Export Processed Data (T, w(*), 1/dwdT_L(*@LIQUID))',
                'liqvec_export_clean_frame': 'Export Cleaned Data (Excel)',
                'liqvec_viz_frame': 'Visualization (Z Vectors on Liquidus Surface)',
                'liqvec_arrow_3d': 'Arrow Settings (3D)',
                'liqvec_mpl_arrow': '3D Static / 3D Rotation GIF (Matplotlib)',
                'liqvec_arrow_len': 'Arrow Length Scale:',
                'liqvec_arrow_head': 'Arrow Head Size:',
                'liqvec_plotly_arrow': 'Plotly 3D (Interactive)',
                'liqvec_plotly_len': 'Arrow Length Scale (relative):',
                'liqvec_plotly_head': 'Arrow Head Fraction:',
                'liqvec_no_pandat': 'No Pandat data imported. Please import data via Import → Pandat to ThermoQ first.',
                'liqvec_fd_clean': 'Save Cleaned Excel File',
                'liqvec_proc_export_title': 'Export processed data',
                'tzero_win_title': 'Plot T-zero Surface',
                'tzero_heading': 'T-zero Surface Plotter',
                'tzero_intro': (
                    'Load Excel exported from Extract Thermo-calc Results → T-zero.\n'
                    'Z uses column: T0 (K). Choose X/Y from w(...) columns.'
                ),
                'tzero_input_excel': 'Input Excel',
                'tzero_settings': 'Settings',
                'tzero_fd_excel': 'Select T-zero Excel',
                'tzero_ready': 'Ready to plot',
                'conv_win_title': 'Composition Converter (wt% ↔ at%)',
                'conv_heading': 'Composition Converter',
                'conv_intro': 'Enter element compositions and convert between weight percent (wt%) and atomic percent (at%)',
                'conv_input': 'Input',
                'conv_input_unit': 'Input Unit:',
                'conv_wt': 'wt%',
                'conv_at': 'at%',
                'conv_example_text': (
                    'Example input format (one element per line):\n'
                    'Al 90.0\nMg 8.0\nSi 2.0\nOr:\nAl: 90.0\nMg: 8.0\nSi: 2.0'
                ),
                'conv_convert': 'Convert',
                'conv_clear': 'Clear',
                'conv_result': 'Result',
                'tbatch_win_title': 'Thermo-calc Batch File Generator',
                'tbatch_subtitle': 'Generate Thermo-calc batch file (.tcm) by combining template files with element combinations',
                'tbatch_tpl0': 'Template0 File (Complete TCM for single point calculation)',
                'tbatch_tpl': 'Template File (Loop body)',
                'tbatch_tpl1': 'Template1 File (Optional - TCM for abnormal point calculation)',
                'tbatch_elem_cfg': 'Element Configuration',
                'tbatch_tbl_element': 'Element',
                'tbatch_tbl_min': 'Min',
                'tbatch_tbl_max': 'Max',
                'tbatch_tbl_step': 'Step',
                'tbatch_lbl_element': 'Element:',
                'tbatch_lbl_min': 'Min:',
                'tbatch_lbl_max': 'Max:',
                'tbatch_lbl_step': 'Step:',
                'tbatch_add': 'Add Element',
                'tbatch_remove': 'Remove Selected',
                'tbatch_constraints': 'Constraints (Optional)',
                'tbatch_sum_leq': 'Sum of all elements <= 1',
                'tbatch_exclude_zeros': 'Exclude all zeros (0, 0, ...)',
                'tbatch_output_file': 'Output File',
                'tbatch_ready': 'Ready to generate',
                'tbatch_generate': 'Generate Batch File',
                'tbatch_fd_out': 'Save batch file',
                'extp_win_title': 'Extract Pandat Results',
                'extp_heading': 'Extract Pandat Results',
                'extp_intro': 'Extract data from CSV/DAT files to generate P.xlsx, Ts.xlsx, P-S.xlsx, and Ts-S.xlsx',
                'extp_lever_folder': 'Lever/Equilibrium Folder (All table_Lever)',
                'extp_scheil_folder': 'Scheil Folder (All table_Scheil)',
                'extp_output_dir': 'Output Directory',
                'extp_status': 'Status',
                'extp_ready': 'Ready to extract',
                'extp_extract_btn': 'Extract Results',
                'extp_fd_lever': 'Select Lever folder',
                'extp_fd_scheil': 'Select Scheil folder',
                'extp_fd_output': 'Select output directory',
                'extp_processing': 'Processing files...',
                'extp_close': 'Close',
                'tbatch_fd_tpl0': 'Select Template0 File',
                'tbatch_fd_tpl': 'Select Template File',
                'tbatch_fd_tpl1': 'Select Template1 File',
                'tbatch_fd_save_out': 'Save Output File',
                'filetype_text': 'Text files',
                'filetype_tcm': 'TCM files',
                'filetype_all': 'All files',
                'liqvec_proc_export_status': 'Processing data for export...',
                'liqvec_clean_prep_status': 'Processing and cleaning data for export...',
                'liqvec_status_clean_fill': 'Cleaning and filling data...',
                'liqvec_plot_proc_status': 'Processing data...',
                'conv_result_input': 'Input ({unit}):',
                'conv_result_conv': 'Converted ({unit}):',
                'conv_result_total': 'Total {unit}:',
                'conv_example_prefix_en': 'Example input format',
                'conv_example_prefix_zh': '输入示例',
                'btn_calculate': 'Calculate',
                'btn_show_results': 'Show Results',
                'calc_tab_single': 'Single composition',
                'calc_tab_batch': 'Composition space (batch)',
                'batch_intro': (
                    'Compute P, Q, Qtrue, ΔT, ΔTs, β, etc. for each row of the P and/or P-S liquidus table '
                    '(same physics as Calculate). Source: Lever only, Scheil only, or both. CSV / interpolated Excel '
                    'apply Newton fill to missing Q/P/Beta at w≈0 (ternary) and drop columns by source. '
                    'Quantity (Z): choose All to write every visualization type for each numeric column (w_*, Q/P/Beta, Qtrue, ΔT/ΔTs) to the output folder.'
                ),
                'batch_frame_source': 'Batch source',
                'batch_mode_lever': 'Equilibrium/Lever (rows from P file)',
                'batch_mode_scheil': 'Scheil (rows from P-S file)',
                'batch_mode_all': 'All (rows from P file and P-S file)',
                'batch_save_excel_filled': 'Save Excel (interpolated batch)…',
                'batch_need_all_pandat': '“All” requires P, Ts, P-S, and Ts-S data. Import via Pandat to ThermoQ.',
                'batch_need_three_el_fill': 'Q/P/Beta Newton fill needs exactly three elements (three w_* columns).',
                'batch_max_rows_invalid': 'Invalid integer for max rows.',
                'batch_z_all': 'All',
                'batch_plot_all_done': 'Generated {n} plot file(s) in the output folder.',
                'batch_plot_all_errors': 'Some plots failed:\n{detail}',
                'batch_max_rows': 'Max rows (blank = all):',
                'batch_compute': 'Compute batch',
                'batch_save_csv': 'Save CSV…',
                'batch_plot_group': 'Plot (2D / 3D)',
                'batch_plot_intro': 'Uses the last computed batch table. Choose composition axes and Z quantity.',
                'batch_z_quantity': 'Quantity (Z):',
                'batch_viz': 'Visualization:',
                'batch_viz_2d': '2D Heatmap',
                'batch_viz_3d': '3D Static',
                'batch_viz_gif': '3D Rotation GIF',
                'batch_viz_plotly': 'Plotly 3D',
                'batch_smooth': 'Smoothness:',
                'batch_view_3d': '3D Static View (Rotation Angles)',
                'batch_elev': 'Elevation (deg):',
                'batch_azim': 'Azimuth (deg):',
                'batch_output_dir': 'Output Directory:',
                'batch_browse': 'Browse',
                'batch_prefix': 'Output Prefix:',
                'batch_image_fmt': 'Image Format (2D/3D Static):',
                'batch_gif_params': '3D Rotation GIF Parameters',
                'batch_gif_speed': 'Rotation Speed (degrees/frame):',
                'batch_gif_interval': 'Frame Interval (ms):',
                'batch_gif_fps': 'FPS:',
                'batch_plot_btn': 'Generate plot',
                'batch_status_ready': 'Run “Compute batch” first.',
                'batch_need_compute': 'Please run “Compute batch” first.',
                'batch_done': 'Batch done: {n} rows ({skipped} skipped).',
                'batch_saved': 'Saved: {path}',
                'batch_no_numeric_z': 'No numeric Z column selected.',
                'batch_missing_wxy': 'Missing composition columns in batch table (expected "{wx}" and "{wy}").',
                'batch_no_rows': 'No valid rows computed. Check that compositions sum to ~100 wt% and lie within tabulated ranges.',
                'batch_plot_x_el': 'X element:',
                'batch_plot_y_el': 'Y element:',
                'batch_output_block': 'Output files',
                # Main window / element selector
                'el_frame_title': 'Element Selection',
                'el_label_element': 'Element:',
                'el_label_composition': 'Composition (wt%):',
                'el_add_button': 'Add Element',
                'el_selected_frame': 'Selected Elements',
                'el_tree_col_element': 'Element',
                'el_tree_col_name': 'Name',
                'el_tree_col_comp': 'Composition (wt%)',
                'el_remove_button': 'Remove Selected',
                'el_hint_main': 'Hint: The first added element will be the main element',
                # Calculate / results / save
                'calc_msg_title': 'Calculation Result',
                'calc_err_title': 'Calculation Error',
                'calc_err_total_comp': 'Total composition must equal 100%! Current total: {total:.2f}%',
                'calc_pandat_col_title': 'Pandat columns',
                'calc_range_title': 'Composition outside tabulated range',
                'calc_range_body': 'Each element must lie within the min–max of w(element) in each loaded file:\n\n',
                'calc_interp_note': 'No nearly exact row match; Qtrue, Q/P/Beta per element, and ΔT/ΔTs use quadratic Newton divided-difference interpolation from nearby compositions (linear if fewer than 3 distinct projections along the projection axis).\n\n',
                'calc_results_header': 'Calculation Results',
                'calc_composition_label': 'Composition:',
                'calc_errors_header': 'Errors:',
                'res_win_title': 'Calculation Results',
                'res_frame_title': 'Results',
                'res_component_block': 'Component Results',
                'res_not_avail': 'Not available',
                'res_no_data_msg': 'No results available. Please run calculation first.',
                'res_close': 'Close',
                'res_save': 'Save results…',
                'res_save_title': 'Save calculation results',
                'res_save_ok': 'Results saved successfully.',
                'res_save_fail': 'Failed to save results.',
                'res_interp_note': 'Quadratic Newton divided-difference interpolation from nearby compositions (linear if <3 distinct projections).\n\n',
                'res_warn_no_results_title': 'No Results',
                'res_warn_no_results_msg': 'Please calculate first before showing results!',
                'calc_no_results_body': 'No results calculated. Please check your composition and data files.',
                # Dialog titles / common
                'dlg_error': 'Error',
                'dlg_warning': 'Warning',
                'dlg_success': 'Success',
                'dlg_partial': 'Partial Success',
                'dlg_info': 'Information',
                # Example / main calculate
                'example_not_found': 'Example folder not found!',
                'example_open_fail': 'Failed to open Example folder:\n{e}',
                'calc_need_element': 'Please select at least one element!',
                'calc_need_pandat': "Please import Pandat data first using 'Import > Pandat to ThermoQ'!",
                'calc_failed_detail': 'Failed to calculate: {e}\n\nDetails:\n{details}',
                # Element selector (messages + dynamic labels)
                'el_warn_duplicate': 'Element already added!',
                'el_err_invalid_comp': 'Invalid element or composition!',
                'el_err_comp_number': 'Please enter a valid number for composition!',
                'el_sum_ok': 'Total composition: {total:.2f} wt% ✓',
                'el_sum_need_100': 'Total composition: {total:.2f} wt% (should be 100.00 wt%)',
                'el_main_lbl': 'Main element: {elem}',
                'el_avail_pandat': 'Available elements from Pandat data: {els}',
                # Pandat import window
                'pandat_win_title': 'Pandat to ThermoQ',
                'pandat_note': 'Note: P/Ts files are for Equilibrium (Lever) solidification.\nP-S/Ts-S files are for Scheil solidification.',
                'pandat_frame_p': 'P File (Equilibrium/Lever Solidification - Liquidus Data)',
                'pandat_frame_ts': 'Ts File (Equilibrium/Lever Solidification - Solidus Temperature)',
                'pandat_frame_ps': 'P-S File (Scheil Solidification - Liquidus Data)',
                'pandat_frame_tss': 'Ts-S File (Scheil Solidification - Solidus Temperature)',
                'pandat_browse': 'Browse',
                'pandat_fd_p': 'Select P File',
                'pandat_fd_ts': 'Select Ts File',
                'pandat_fd_ps': 'Select P-S File',
                'pandat_fd_tss': 'Select Ts-S File',
                'pandat_fd_excel': 'Excel files',
                'pandat_status_prompt': 'Please select at least P and Ts files to proceed',
                'pandat_err_need_pt_ts': 'Please select at least P and Ts files (Equilibrium/Lever solidification)!',
                'pandat_clear_title': 'Clear Imported Data',
                'pandat_clear_msg': 'This will clear all imported Pandat datasets (P, Ts, P-S, Ts-S) and reset available elements.\n\nContinue?',
                'pandat_cleared_status': 'Imported data cleared. You can import new files now.',
                'pandat_load_intro': 'Pandat data loaded successfully!\n',
                'pandat_load_row_p': 'P file (Equilibrium): {n} rows\n',
                'pandat_load_row_ts': 'Ts file (Equilibrium): {n} rows\n',
                'pandat_load_row_ps': 'P-S file (Scheil): {n} rows\n',
                'pandat_load_row_tss': 'Ts-S file (Scheil): {n} rows\n',
                'pandat_load_elements': 'Recognized elements: {els}',
                'pandat_status_ok': 'Successfully loaded Pandat data! Recognized elements: {els}',
                'pandat_load_fail': 'Failed to load Pandat data: {e}',
                'imp_btn_import': 'Import Data',
                'imp_btn_clear': 'Clear Imported Data',
                'imp_btn_cancel': 'Cancel',
                # Plot / data (shared)
                'plot_data_missing': 'Data Missing',
                'plot_msg_import_pandat_all': 'No data found. Please import P/Ts or P-S/Ts-S files via Import → Pandat to ThermoQ first.',
                'plot_msg_import_pandat_p': 'No data found. Please import P.xlsx (Equilibrium) or P-S.xlsx (Scheil) via Import → Pandat to ThermoQ first.',
                'plot_elem_title': 'Element Selection',
                'plot_select_xy': 'Please select X and Y elements first.',
                'plot_col_not_found': 'Column Not Found',
                'plot_cols_pandat': 'Required columns not found in dataset.\nNeed: w({ex}), w({ey}), and T or temperature-related columns.\n',
                'plot_cols_phase_surface': 'Required columns not found in dataset.\nLooking for: {cx}, {cy}\nAvailable w(*) columns (first 10): {avail}',
                'plot_cols_q_dataset': 'Required columns not found in dataset.\nNeed: w({ex}), w({ey}), and a -T//fw(@phase) column.\nAvailable columns (first 20): {avail}',
                'plot_t_missing': 'Temperature column T not found in dataset.',
                'plot_no_valid': 'No valid data points after filtering.',
                'plot_no_data_title': 'No Data',
                'plot_failed': 'Plotting Failed',
                'plot_err_detail': 'An error occurred: {e}\n\nDetails:\n{details}',
                'plot_err_simple': 'An error occurred: {e}',
                'plot_load_fail': 'Load Failed',
                'plot_read_excel': 'Failed to read Excel:\n{e}',
                'plot_dep_title': 'Dependency Missing',
                'plot_dep_2d': 'Matplotlib is not installed. Cannot generate 2D heatmap.',
                'plot_dep_3d': 'Matplotlib is not installed. Cannot generate 3D image.',
                'plot_dep_gif': 'Matplotlib is not installed. Cannot generate GIF.',
                'plot_smooth_title': 'Smoothing Failed',
                'plot_smooth_msg': 'Could not create smooth surface. Using scatter/triangulated surface instead. Please install scikit-learn and scipy for smooth surfaces.',
                'plot_status_smooth': 'Creating smooth surface...',
                'plot_mr_need': 'Please load Melting Range output.xlsx first.',
                'plot_mr_cols': 'Required composition columns not found in Excel.\nLooking for: w({ex}), w({ey})\n',
                'plot_mr_z_col': "Required column '{z}' not found in Excel.",
                'plot_t0_need': 'Please load T-zero output.xlsx first.',
                'plot_t0_cols': 'Required columns not found.\nLooking for: w({ex}), w({ey})\n',
                'plot_t0_z': "T0 column not found. Expected 'T0 (K)'.",
                # File helper
                'file_open_fail': 'Failed to open file: {e}',
                'file_save_ok': 'File saved to:\n{path}',
                'file_save_fail': 'Failed to save file: {e}',
                # Composition converter
                'conv_need_comp': 'Please enter element compositions!',
                'conv_no_valid': 'No valid elements found! Please check your input format.',
                'conv_failed': 'Conversion failed: {e}',
                # Batch generator (Thermo-calc)
                'gen_no_placeholders': 'No element placeholders (like %Al%) found in template.',
                'gen_tpl_loaded': 'Template loaded.\nFound elements: {els}\n\nYou can now set ranges and generate the batch file.',
                'gen_tpl_parse_fail': 'Failed to parse template: {e}',
                'gen_invalid_el': 'Invalid element: {el}',
                'gen_el_not_in_tpl': 'Element {el} is not in the template!\nAllowed: {allowed}',
                'gen_invalid_range': 'Invalid range! Min should be >= 0, Max should be <= 1, and Min < Max',
                'gen_step_pos': 'Step must be > 0',
                'gen_invalid_nums': 'Please enter valid numbers for Min, Max, and Step!',
                'gen_locked': 'Cannot remove elements when locked by template.\nYou can only modify their ranges.',
                'gen_need_tpl0': 'Please select a valid Template0 file!',
                'gen_need_tpl': 'Please select a valid Template file!',
                'gen_need_out': 'Please specify an output file!',
                'gen_need_cfg': 'Please add at least one element configuration!',
                'gen_ok': 'Batch file generated successfully!\n\nTotal combinations: {n}\nOutput file: {path}',
                'gen_fail': 'Failed to generate batch file:\n{e}',
                'gen_tpl_loaded_body': 'Found elements: {els}\n\nElement selection has been locked to these elements.\nPlease configure Min/Max/Step for each.',
                'gen_locked_title': 'Locked',
                # Extract Thermo-calc (melting / T0)
                'exp_need_folder': 'Please select a valid folder!',
                'exp_need_out': 'Please specify an output file!',
                'exp_no_exp': 'No .exp files found in the selected folder!',
                'exp_regex_bad': 'Invalid regex pattern: {e}',
                'exp_no_results': 'No valid results extracted from files!',
                'exp_save_fail': 'Failed to save Excel file:\n{e}',
                'exp_process_fail': 'Processing failed:\n{e}',
                'exp_t0_no_match': 'No matching .exp files found in the selected folder!',
                'exp_t0_no_data': 'No valid data extracted from files!',
                # Extract Thermo-calc Results (GUI)
                'exptc_win_title': 'Extract Thermo-calc Results',
                'exptc_heading': 'Extract Thermo-calc Results',
                'exptc_intro': (
                    'Melting Range: extract liquidus/solidus and melting range.\n'
                    'T-zero: extract w(*) and the corresponding T0 from *_T0.exp files.'
                ),
                'exptc_tab_mr': 'Melting Range',
                'exptc_tab_t0': 'T-zero',
                'exptc_mr_folder': 'Select Folder Containing .exp Files',
                'exptc_mr_pattern': 'Filename Pattern (Optional)',
                'exptc_mr_pattern_lbl': 'Pattern:',
                'exptc_mr_pattern_hint': 'Empty = all .exp\nRegex groups -> w(...) columns',
                'exptc_output_xlsx': 'Output Excel File',
                'exptc_status': 'Status',
                'exptc_process': 'Process Files',
                'exptc_fd_mr_folder': 'Select Folder with .exp Files',
                'exptc_t0_folder': 'Select Folder Containing *_T0.exp Files',
                'exptc_fd_t0_folder': 'Select Folder with *_T0.exp Files',
                'exptc_t0_filter': 'Filename Filter (Optional)',
                'exptc_t0_regex_lbl': 'Regex:',
                'exptc_t0_filter_hint': 'Only matching filenames will be processed.',
                'exptc_mr_done': (
                    'Results extracted successfully!\n\n'
                    'Processed: {ok} files\n'
                    'Errors: {bad} files\n'
                    'Results saved to: {path}'
                ),
                'exptc_t0_done': (
                    'T-zero extracted successfully!\n\n'
                    'Processed: {ok} files\n'
                    'Errors: {bad} files\n'
                    'Rows: {rows}\n'
                    'Saved to: {path}'
                ),
                # Extract Pandat Results
                'extp_need_lever': 'Please select a valid Lever folder!',
                'extp_need_scheil': 'Please select a valid Scheil folder!',
                'extp_no_csv': 'No CSV or DAT files found in Lever folder!',
                'extp_permission': 'Cannot write {path}\n\nClose the file if it is open in Excel or another program, or choose a different output folder.',
                'dlg_permission': 'Permission Denied',
                'gen_template_info': 'Template Info',
                'extp_extract_fail': 'Failed to extract results:\n{e}',
                'plot_k_no_p': 'No P file data found. Please import P file via Import → Pandat to ThermoQ first.',
                'plot_k_no_ps': 'No P-S file data found. Please import P-S file via Import → Pandat to ThermoQ first.',
                'plot_k_select_xy': 'Please select X and Y elements!',
                'plot_k_no_points': 'Not enough valid data points to plot partition coefficient vectors.',
                'plot_k_fail': 'Failed to plot partition coefficient vectors:\n{e}',
                'plot_k_dep_vec': 'Matplotlib is not installed. Cannot generate partition coefficient vectors.',
                # Solid-Liquid partition coefficient (k-vectors): Liquidus (P/P-S) tab
                'plot_k_liq_intro': 'Plot k-vectors defined by k = w(*@solid)/w(*@LIQUID) from imported Pandat P or P-S data.\nThe solid phase is chosen automatically from -T//fw(@*) columns and matching w(*@PHASE) columns.',
                'plot_k_mode_eq': 'Equilibrium/Lever (P file)',
                'plot_k_mode_scheil': 'Scheil (P-S file)',
                'plot_k_vis_frame': 'Visualization (|k-1| Field)',
                'plot_k_vis_heatmap': '2D Heatmap',
                'plot_k_vis_3d': '3D Static',
                'plot_k_vis_gif': '3D Rotation GIF',
                'plot_k_vis_plotly': 'Plotly 3D',
                'plot_k_gif_fps': 'GIF FPS:',
                'plot_k_rot_step': 'Rotation step (deg):',
                'plot_k_img_fmt_2d3d': 'Image Format (2D/3D static):',
                'plot_k_status_ready': 'Ready',
                'plot_k_processing': 'Processing data...',
                'plot_k_done_all_viz': 'Done. Generated 2D quiver, heatmap, 3D static, GIF and Plotly 3D for k-vectors.',
                'dlg_select_output_dir': 'Select Output Directory',
                'dlg_select_all_table_lever_folder': 'Select All table_Lever folder',
                'dlg_select_all_table_scheil_folder': 'Select All table_Scheil folder',
                # Solid-Liquid partition coefficient (k-vectors): pages
                'partition_tab_liquid_points': 'Liquidus',
                'partition_tab_same_temp': 'isotherm',
                'partition_tab_isocomposition': 'isocomposition',
                'iso_tab_title': 'isocomposition',
                'iso_info': 'Compute tie-line projection and 3D plot for a user-defined alloy composition O using All table_Lever / All table_Scheil csv/dat files.\nFor each temperature, f is from w(X@LIQUID), and S is from w(X@solid) inferred from -T//fw(@*).',
                'iso_o_frame_title': 'Alloy composition O',
                'iso_t_frame_title': 'Temperature range',
                'iso_o_wx': 'O: w(X) (wt%):',
                'iso_o_wy': 'O: w(Y) (wt%):',
                'iso_tmin': 'T min (auto, K):',
                'iso_tmax': 'T max (auto, K):',
                'iso_npts': 'Number of temperature points:',
                'iso_plot_button': 'Plot isocomposition',
                'iso_need_o': 'Please enter O composition values (w(X), w(Y)).',
                'iso_o_out_of_range': 'Selected alloy composition is outside the available data composition range.',
                'iso_done': 'Done. Generated 2D projection and 3D plots for isocomposition.',
                'iso_2d_title': '2D Projection (isocomposition)',
                'iso_3d_title': '3D Isocomposition (T as Z)',
                'iso_dyn_title': '3D Dynamic (high -> low)',
                'iso_plotly_3d_title': '3D Isocomposition Interactive (Plotly)',
                # Solid-Liquid partition coefficient (k-vectors): same temperature page
                'stp_target_temp': 'Target Temperature (K):',
                'stp_all_table_lever': 'All table_Lever folder:',
                'stp_all_table_scheil': 'All table_Scheil folder:',
                'stp_need_folder': 'Please select a valid All table folder!',
                'stp_dataset_lever': 'All table_Lever (Equilibrium/Lever)',
                'stp_dataset_scheil': 'All table_Scheil (Scheil)',
                'stp_temp_out_of_range': 'Target temperature {t} K is outside data range [{tmin}, {tmax}] K.',
                'stp_no_valid_points': 'No valid data points at/near the selected temperature!',
                'stp_plot_button': 'Plot U/V/Z at T',
                'stp_solidification_mode': 'Solidification Mode',
                'stp_output': 'Output',
                'stp_filename_prefix': 'Filename prefix:',
                'stp_output_settings': 'Output Settings',
                'stp_output_directory': 'Output directory:',
                'stp_image_format': 'Image Format:',
                'stp_invalid_temp': 'Invalid target temperature.',
                'stp_solid_phase_infer_fail': 'Cannot infer solid phase from -T//fw(@*) columns.',
                'stp_all_table_folders': 'All table Folders',
                'stp_elem_selection': 'Element Selection',
                'stp_x_element': 'X Element:',
                'stp_y_element': 'Y Element:',
                'stp_temperature': 'Temperature',
                'stp_tab2_info': 'Compute U/V/Z vectors at a user-defined temperature T using All table_Lever / All table_Scheil csv/dat files.\nIf T does not exist in a file, values are estimated by quadratic Newton divided-difference interpolation.',
                'stp_loading': 'Loading All table files...',
                'stp_done': 'Done. Generated U/V/Z at T={t} from All table files.',
                'stp_detected_elements': 'Detected elements: {els}',
                'btn_plot_vectors': 'Plot Vectors',
                'plot_liq_dep_vec': 'Matplotlib is not installed. Cannot generate vector plots.',
                'plot_liq_t_missing': 'Temperature column T not found in data!',
                'export_need_path': 'Please specify export path!',
                'export_ok_proc': 'Processed data exported successfully to:\n{path}',
                'export_ok_clean': 'Cleaned data exported successfully to:\n{path}',
                'export_fail_proc_xlsx': 'Failed to export processed Excel file:\n{e}',
                'export_fail_proc': 'Failed to export processed data:\n{e}',
                'export_fail_clean_xlsx': 'Failed to export cleaned Excel file:\n{e}',
                'export_fail_clean': 'Failed to export cleaned data:\n{e}',
                'export_err_title': 'Export Error',
                'plot_liq_invalid_els': 'Invalid elements: {ex} or {ey}',
                'plot_liq_el_missing': 'Element {el} not found in data. Available elements: {avail}',
                'plot_liq_dwdT_missing': 'Column dwdT_L({el}@LIQUID) not found in data!',
                'plot_liq_no_points_filter': 'No valid data points found after filtering!',
                'plot_liq_gen_fail': 'Failed to generate vector plots:\n{e}',
                'plot_tc_cols_missing': 'Required composition columns not found in Excel.\nLooking for: w({ex}), w({ey})\nAvailable w(*) columns (first 10): {avail}',
                'extp_success': 'Results extracted successfully!\n\nOutput directory: {dir}\n\nP.xlsx: {np} rows\nTs.xlsx: {nts} rows\nP-S.xlsx: {nps} rows\nTs-S.xlsx: {ntss} rows',
                'liqvec_ok_4': 'Vector plots generated successfully!\n\nU horizontal: {u}\nV vertical: {v}\nZ resultant: {z}\nZ on liquidus ({viz}): {zliq}',
                'liqvec_ok_3': 'Vector plots generated successfully!\n\nU horizontal: {u}\nV vertical: {v}\nZ resultant: {z}',
                'liqvec_partial': 'Vector plots generated, but visualization plot failed:\n{err}\n\nU horizontal: {u}\nV vertical: {v}\nZ resultant: {z}',
                'liqvec_ok_no_t': 'Vector plots generated successfully!\n\nU horizontal: {u}\nV vertical: {v}\nZ resultant: {z}\n\nNote: Z vectors on liquidus surface plot skipped (no temperature data)',
            },
            'zh': {
                'menu_file': '文件',
                'menu_import': '导入',
                'menu_plot': '绘图',
                'menu_tools': '工具',
                'menu_help': '帮助',
                'file_exit': '退出',
                'import_pandat': 'Pandat到ThermoQ',
                'plot_phase': '绘制相面',
                'plot_qtrue': '绘制Qtrue值',
                'plot_liqvec': '绘制液相线向量',
                'plot_kvec': '绘制固-液分配系数向量',
                'plot_t0surf': '绘制T-zero曲面',
                'tools_converter': '成分换算（wt% ↔ at%）',
                'tools_generate': '生成Thermo-calc批处理文件',
                'tools_extract_exp': '提取Thermo-calc结果',
                'tools_extract_pandat': '提取Pandat结果',
                'help_language': '界面语言',
                'help_english': 'English',
                'help_chinese': '中文',
                'help_example': '示例',
                'ui_close': '关闭',
                'ui_plot': '绘图',
                'ui_export': '导出',
                'plot_ready': '就绪，可绘图',
                'plot_vis_label': '可视化：',
                'plot_elev_range': '（0–90）',
                'plot_azim_range': '（-180–180）',
                'plot_phase_win_title': '绘制相表面（液相线/固相线）',
                'plot_phase_heading': '相表面绘图',
                'plot_phase_intro': (
                    'Pandat：使用已导入的 Pandat 数据绘制固相线/液相线表面。\n'
                    'Thermo-calc：使用「提取 Thermo-calc 结果 → 熔程」导出的 Excel 绘图。\n'
                    'Thermo-calc 列：液相线用 Liquidus_Temperature，固相线用 Solidus_Temperature。'
                ),
                'plot_phase_tab_pandat': 'Pandat',
                'plot_phase_tab_tc': 'Thermo-calc',
                'plot_phase_settings_shared': '设置（共用）',
                'plot_phase_dataset': '数据集：',
                'plot_phase_ds_equilibrium': '平衡/Lever',
                'plot_phase_ds_scheil': 'Scheil',
                'plot_phase_type': '类型：',
                'plot_phase_liquidus': '液相线',
                'plot_phase_solidus': '固相线',
                'plot_phase_ready_pandat': '就绪（Pandat）',
                'plot_phase_ready_tc': '就绪（Thermo-calc）',
                'plot_phase_note_pandat': '请先使用「导入 → Pandat到ThermoQ」。再选择数据集与组元并点击绘图。',
                'plot_phase_plot_pandat': '绘图（Pandat）',
                'plot_phase_plot_tc': '绘图（Thermo-calc）',
                'plot_phase_output_settings': '输出设置',
                'plot_phase_tc_excel_frame': '输入 Excel（熔程输出 output.xlsx）',
                'plot_phase_fd_mr': '选择熔程 Excel',
                'plot_tc_loaded_rows': '已从 Excel 加载 {n} 行。',
                'qtrue_win_title': '绘制 Qtrue 值',
                'qtrue_heading': 'Qtrue 值绘图',
                'qtrue_intro': (
                    '使用已导入的 Pandat 数据绘制 Qtrue（-T//fw(@相)）。\n'
                    '相与 Q 列由数据中的 w(*@*) 与 -T//fw(@*) 自动识别。\n'
                    '选择 X、Y 组元。平衡/Lever：P.xlsx；Scheil：P-S.xlsx。'
                ),
                'qtrue_settings': '设置',
                'qtrue_dataset': '数据集：',
                'qtrue_ds_equilibrium': '平衡/Lever',
                'qtrue_ds_scheil': 'Scheil',
                'qtrue_ready': '就绪，可绘图',
                'liqvec_win_title': '绘制液相线矢量',
                'liqvec_heading': '液相线矢量绘图',
                'liqvec_intro': (
                    '根据 Pandat 数据绘制液相线矢量（quiver）。'
                    '数据来自已导入的 P 文件（平衡/Lever）或 P-S 文件（Scheil）。'
                ),
                'liqvec_solid_mode': '凝固模式',
                'liqvec_elem_sel': '组元选择',
                'liqvec_options': '选项',
                'liqvec_clean_fill': '绘图前清洗并填充数据',
                'liqvec_export_proc': '导出处理后数据（T、w(*)、1/dwdT_L(*@LIQUID)）',
                'liqvec_export_clean_frame': '导出清洗后数据（Excel）',
                'liqvec_viz_frame': '可视化（液相面上的 Z 矢量）',
                'liqvec_arrow_3d': '箭头设置（3D）',
                'liqvec_mpl_arrow': '3D 静态 / 3D 旋转 GIF（Matplotlib）',
                'liqvec_arrow_len': '箭头长度比例：',
                'liqvec_arrow_head': '箭头头部大小：',
                'liqvec_plotly_arrow': 'Plotly 3D（交互）',
                'liqvec_plotly_len': '箭头长度比例（相对）：',
                'liqvec_plotly_head': '箭头头部占比：',
                'liqvec_no_pandat': '尚未导入 Pandat 数据。请先使用「导入 → Pandat到ThermoQ」。',
                'liqvec_fd_clean': '保存清洗后的 Excel',
                'liqvec_proc_export_title': '导出处理后数据',
                'tzero_win_title': '绘制 T-zero 曲面',
                'tzero_heading': 'T-zero 曲面绘图',
                'tzero_intro': (
                    '加载「提取 Thermo-calc 结果 → T-zero」导出的 Excel。\n'
                    'Z 使用列 T0 (K)。X/Y 从 w(...) 列选择。'
                ),
                'tzero_input_excel': '输入 Excel',
                'tzero_settings': '设置',
                'tzero_fd_excel': '选择 T-zero Excel',
                'tzero_ready': '就绪，可绘图',
                'conv_win_title': '成分换算（wt% ↔ at%）',
                'conv_heading': '成分换算',
                'conv_intro': '输入各组元成分，在质量分数（wt%）与原子分数（at%）之间换算',
                'conv_input': '输入',
                'conv_input_unit': '输入单位：',
                'conv_wt': 'wt%',
                'conv_at': 'at%',
                'conv_example_text': (
                    '输入示例（每行一个元素）：\n'
                    'Al 90.0\nMg 8.0\nSi 2.0\n或：\nAl: 90.0\nMg: 8.0\nSi: 2.0'
                ),
                'conv_convert': '换算',
                'conv_clear': '清空',
                'conv_result': '结果',
                'tbatch_win_title': 'Thermo-calc 批处理文件生成器',
                'tbatch_subtitle': '将模板文件与成分组合生成 Thermo-calc 批处理文件（.tcm）',
                'tbatch_tpl0': 'Template0 文件（单点计算的完整 TCM）',
                'tbatch_tpl': 'Template 文件（循环体）',
                'tbatch_tpl1': 'Template1 文件（可选：异常点计算用 TCM）',
                'tbatch_elem_cfg': '组元配置',
                'tbatch_tbl_element': '元素',
                'tbatch_tbl_min': '最小',
                'tbatch_tbl_max': '最大',
                'tbatch_tbl_step': '步长',
                'tbatch_lbl_element': '元素：',
                'tbatch_lbl_min': '最小：',
                'tbatch_lbl_max': '最大：',
                'tbatch_lbl_step': '步长：',
                'tbatch_add': '添加元素',
                'tbatch_remove': '删除选中',
                'tbatch_constraints': '约束（可选）',
                'tbatch_sum_leq': '所有元素之和 ≤ 1',
                'tbatch_exclude_zeros': '排除全零组合 (0, 0, …)',
                'tbatch_output_file': '输出文件',
                'tbatch_ready': '就绪，可生成',
                'tbatch_generate': '生成批处理文件',
                'tbatch_fd_out': '保存批处理文件',
                'extp_win_title': '提取 Pandat 结果',
                'extp_heading': '提取 Pandat 结果',
                'extp_intro': '从 CSV/DAT 提取并生成 P.xlsx、Ts.xlsx、P-S.xlsx、Ts-S.xlsx',
                'extp_lever_folder': 'Lever/平衡 文件夹（All table_Lever）',
                'extp_scheil_folder': 'Scheil 文件夹（All table_Scheil）',
                'extp_output_dir': '输出目录',
                'extp_status': '状态',
                'extp_ready': '就绪，可提取',
                'extp_extract_btn': '提取结果',
                'extp_fd_lever': '选择 Lever 文件夹',
                'extp_fd_scheil': '选择 Scheil 文件夹',
                'extp_fd_output': '选择输出目录',
                'extp_processing': '正在处理文件…',
                'extp_close': '关闭',
                'tbatch_fd_tpl0': '选择 Template0 文件',
                'tbatch_fd_tpl': '选择 Template 文件',
                'tbatch_fd_tpl1': '选择 Template1 文件',
                'tbatch_fd_save_out': '保存输出文件',
                'filetype_text': '文本文件',
                'filetype_tcm': 'TCM 文件',
                'filetype_all': '所有文件',
                'liqvec_proc_export_status': '正在处理待导出数据…',
                'liqvec_clean_prep_status': '正在处理并清洗待导出数据…',
                'liqvec_status_clean_fill': '正在清洗并填充数据…',
                'liqvec_plot_proc_status': '正在处理数据…',
                'conv_result_input': '输入（{unit}）：',
                'conv_result_conv': '换算结果（{unit}）：',
                'conv_result_total': '{unit} 合计：',
                'conv_example_prefix_en': 'Example input format',
                'conv_example_prefix_zh': '输入示例',
                'btn_calculate': '计算',
                'btn_show_results': '显示结果',
                'calc_tab_single': '单点计算',
                'calc_tab_batch': '成分空间（批量）',
                'batch_intro': (
                    '对 P 和/或 P-S 液相线表中每一行成分计算 P、Q、Qtrue、ΔT、ΔTs、β 等（与「计算」相同）。'
                    '数据来源可选仅 Lever、仅 Scheil 或两者。CSV 与插值 Excel 对三元体系在 w≈0 处填充缺失 Q/P/Beta，并按来源筛列。'
                    '物理量 (Z) 选「全部」时，会对每个数值列（w_*、Q/P/Beta、Qtrue、ΔT/ΔTs）生成全部可视化类型并保存到输出目录。'
                ),
                'batch_frame_source': '批量数据来源',
                'batch_mode_lever': '平衡/Lever（P 文件各行）',
                'batch_mode_scheil': 'Scheil（P-S 文件各行）',
                'batch_mode_all': '全部（P 与 P-S 文件各行）',
                'batch_save_excel_filled': '保存 Excel（插值填充后）…',
                'batch_need_all_pandat': '「全部」需要已导入 P、Ts、P-S、Ts-S。请通过「导入 → Pandat to ThermoQ」加载。',
                'batch_need_three_el_fill': '对 Q/P/Beta 进行角点 Newton 填充需要恰好三个组元（三个 w_* 列）。',
                'batch_z_all': '全部',
                'batch_plot_all_done': '已在输出目录生成 {n} 个图文件。',
                'batch_plot_all_errors': '部分图形生成失败：\n{detail}',
                'batch_max_rows': '最大行数（留空=全部）：',
                'batch_compute': '计算批量',
                'batch_save_csv': '保存 CSV…',
                'batch_plot_group': '绘图（2D / 3D）',
                'batch_plot_intro': '使用最近一次批量计算结果。选择成分坐标轴与 Z 向物理量。',
                'batch_z_quantity': '物理量（Z）：',
                'batch_viz': '可视化：',
                'batch_viz_2d': '2D 热图',
                'batch_viz_3d': '3D 静态',
                'batch_viz_gif': '3D 旋转 GIF',
                'batch_viz_plotly': 'Plotly 3D',
                'batch_smooth': '平滑度：',
                'batch_view_3d': '3D 静态视角（旋转角）',
                'batch_elev': '仰角 (°)：',
                'batch_azim': '方位角 (°)：',
                'batch_output_dir': '输出目录：',
                'batch_browse': '浏览',
                'batch_prefix': '输出文件名前缀：',
                'batch_image_fmt': '图像格式（2D/3D 静态）：',
                'batch_gif_params': '3D 旋转 GIF 参数',
                'batch_gif_speed': '转速（度/帧）：',
                'batch_gif_interval': '帧间隔 (ms)：',
                'batch_gif_fps': '帧率：',
                'batch_plot_btn': '生成图像',
                'batch_status_ready': '请先点击「计算批量」。',
                'batch_need_compute': '请先执行「计算批量」。',
                'batch_done': '批量完成：{n} 行（跳过 {skipped} 行）。',
                'batch_saved': '已保存：{path}',
                'batch_no_numeric_z': '所选 Z 列不是有效数值列。',
                'batch_missing_wxy': '批量结果表中缺少成分列（需要 "{wx}" 与 "{wy}"）。',
                'batch_no_rows': '没有有效行。请确认各行成分总和约 100 wt% 且在表格范围内。',
                'batch_plot_x_el': 'X 组元：',
                'batch_plot_y_el': 'Y 组元：',
                'batch_output_block': '输出文件',
                'batch_max_rows_invalid': '最大行数不是有效整数。',
                # Main window / element selector
                'el_frame_title': '元素选择',
                'el_label_element': '元素：',
                'el_label_composition': '成分 (wt%)：',
                'el_add_button': '添加元素',
                'el_selected_frame': '已选元素',
                'el_tree_col_element': '元素',
                'el_tree_col_name': '名称',
                'el_tree_col_comp': '成分 (wt%)',
                'el_remove_button': '删除选中',
                'el_hint_main': '提示：第一个添加的元素将作为主元素',
                # Calculate / results / save
                'calc_msg_title': '计算结果',
                'calc_err_title': '计算错误',
                'calc_err_total_comp': '成分总和须为 100%！当前总和：{total:.2f}%',
                'calc_pandat_col_title': 'Pandat 列错误',
                'calc_range_title': '成分超出数据范围',
                'calc_range_body': '所选 wt% 必须在各已导入表格中对应 w(元素) 列的最小值与最大值之间。\n\n',
                'calc_interp_note': '【插值】表中无几乎完全匹配行：Qtrue、各组元 Q/P/Beta、ΔT/ΔTs 等由附近成分经 Newton 二次差分插值（投影方向独立点不足 3 个时为线性）。\n\n',
                'calc_results_header': '计算结果',
                'calc_composition_label': '成分：',
                'calc_errors_header': '错误：',
                'res_win_title': '计算结果',
                'res_frame_title': '结果',
                'res_component_block': '分量结果',
                'res_not_avail': '无数据',
                'res_no_data_msg': '暂无计算结果，请先点击「计算」。',
                'res_close': '关闭',
                'res_save': '保存结果…',
                'res_save_title': '保存计算结果',
                'res_save_ok': '结果已成功保存。',
                'res_save_fail': '保存失败。',
                'res_interp_note': '【插值】附近成分 Newton 二次差分插值（独立投影点不足 3 个时为线性）。\n\n',
                'res_warn_no_results_title': '无结果',
                'res_warn_no_results_msg': '请先进行计算再显示结果！',
                'calc_no_results_body': '未得到计算结果，请检查成分与数据文件。',
                'dlg_error': '错误',
                'dlg_warning': '警告',
                'dlg_success': '成功',
                'dlg_partial': '部分成功',
                'dlg_info': '提示',
                'example_not_found': '未找到示例文件夹！',
                'example_open_fail': '无法打开示例文件夹：\n{e}',
                'calc_need_element': '请至少选择一个元素！',
                'calc_need_pandat': '请先使用「导入 → Pandat到ThermoQ」导入 Pandat 数据！',
                'calc_failed_detail': '计算失败：{e}\n\n详情：\n{details}',
                'el_warn_duplicate': '该元素已添加！',
                'el_err_invalid_comp': '无效的元素或成分！',
                'el_err_comp_number': '请输入有效的成分数值！',
                'el_sum_ok': '成分总和：{total:.2f} wt% ✓',
                'el_sum_need_100': '成分总和：{total:.2f} wt%（应为 100.00 wt%）',
                'el_main_lbl': '主元素：{elem}',
                'el_avail_pandat': 'Pandat 数据中可用元素：{els}',
                'pandat_win_title': 'Pandat 到 ThermoQ',
                'pandat_note': '说明：P/Ts 用于平衡（Lever）凝固；P-S/Ts-S 用于 Scheil 凝固。',
                'pandat_frame_p': 'P 文件（平衡/Lever 凝固 — 液相线数据）',
                'pandat_frame_ts': 'Ts 文件（平衡/Lever 凝固 — 固相线温度）',
                'pandat_frame_ps': 'P-S 文件（Scheil 凝固 — 液相线数据）',
                'pandat_frame_tss': 'Ts-S 文件（Scheil 凝固 — 固相线温度）',
                'pandat_browse': '浏览…',
                'pandat_fd_p': '选择 P 文件',
                'pandat_fd_ts': '选择 Ts 文件',
                'pandat_fd_ps': '选择 P-S 文件',
                'pandat_fd_tss': '选择 Ts-S 文件',
                'pandat_fd_excel': 'Excel 文件',
                'pandat_status_prompt': '请至少选择 P 与 Ts 文件后继续',
                'pandat_err_need_pt_ts': '请至少选择 P 与 Ts 文件（平衡/Lever 凝固）！',
                'pandat_clear_title': '清除已导入数据',
                'pandat_clear_msg': '将清除所有已导入的 Pandat 数据集（P、Ts、P-S、Ts-S）并重置可用元素。\n\n是否继续？',
                'pandat_cleared_status': '已清除导入数据。可重新选择文件导入。',
                'pandat_load_intro': 'Pandat 数据加载成功！\n',
                'pandat_load_row_p': 'P 文件（平衡）：{n} 行\n',
                'pandat_load_row_ts': 'Ts 文件（平衡）：{n} 行\n',
                'pandat_load_row_ps': 'P-S 文件（Scheil）：{n} 行\n',
                'pandat_load_row_tss': 'Ts-S 文件（Scheil）：{n} 行\n',
                'pandat_load_elements': '识别元素：{els}',
                'pandat_status_ok': '已成功加载 Pandat 数据！识别元素：{els}',
                'pandat_load_fail': '加载 Pandat 数据失败：{e}',
                'imp_btn_import': '导入数据',
                'imp_btn_clear': '清除已导入数据',
                'imp_btn_cancel': '取消',
                'plot_data_missing': '缺少数据',
                'plot_msg_import_pandat_all': '未找到数据。请先通过「导入 → Pandat到ThermoQ」导入 P/Ts 或 P-S/Ts-S 文件。',
                'plot_msg_import_pandat_p': '未找到数据。请先通过「导入 → Pandat到ThermoQ」导入 P.xlsx（平衡）或 P-S.xlsx（Scheil）。',
                'plot_elem_title': '元素选择',
                'plot_select_xy': '请先选择 X 与 Y 元素。',
                'plot_col_not_found': '未找到列',
                'plot_cols_pandat': '数据集中缺少所需列。\n需要：w({ex})、w({ey})，以及 T 或与温度相关的列。\n',
                'plot_cols_phase_surface': '数据集中缺少所需列。\n查找：{cx}、{cy}\n可用 w(*) 列（前 10 个）：{avail}',
                'plot_cols_q_dataset': '数据集中缺少所需列。\n需要：w({ex})、w({ey})，以及 -T//fw(@相) 列。\n可用列（前 20 个）：{avail}',
                'plot_t_missing': '数据集中未找到温度列 T。',
                'plot_no_valid': '过滤后无有效数据点。',
                'plot_no_data_title': '无数据',
                'plot_failed': '绘图失败',
                'plot_err_detail': '发生错误：{e}\n\n详情：\n{details}',
                'plot_err_simple': '发生错误：{e}',
                'plot_load_fail': '读取失败',
                'plot_read_excel': '读取 Excel 失败：\n{e}',
                'plot_dep_title': '缺少依赖',
                'plot_dep_2d': '未安装 Matplotlib，无法生成 2D 热图。',
                'plot_dep_3d': '未安装 Matplotlib，无法生成 3D 图。',
                'plot_dep_gif': '未安装 Matplotlib，无法生成 GIF。',
                'plot_smooth_title': '平滑失败',
                'plot_smooth_msg': '无法生成平滑曲面，将改用散点/三角剖分曲面。请安装 scikit-learn 与 scipy 以获得平滑曲面。',
                'plot_status_smooth': '正在生成平滑曲面…',
                'plot_mr_need': '请先加载熔程（Melting Range）导出的 output.xlsx。',
                'plot_mr_cols': 'Excel 中缺少所需成分列。\n查找：w({ex})、w({ey})\n',
                'plot_mr_z_col': "未找到所需列「{z}」。",
                'plot_t0_need': '请先加载 T-zero 导出的 xlsx。',
                'plot_t0_cols': '缺少所需列。\n查找：w({ex})、w({ey})\n',
                'plot_t0_z': "未找到 T0 列，应为「T0 (K)」。",
                'file_open_fail': '打开文件失败：{e}',
                'file_save_ok': '文件已保存至：\n{path}',
                'file_save_fail': '保存文件失败：{e}',
                'conv_need_comp': '请输入元素成分！',
                'conv_no_valid': '未找到有效元素！请检查输入格式。',
                'conv_failed': '换算失败：{e}',
                'gen_no_placeholders': '模板中未找到元素占位符（如 %Al%）。',
                'gen_tpl_loaded': '模板已加载。\n识别元素：{els}\n\n可设置范围并生成批处理文件。',
                'gen_tpl_parse_fail': '解析模板失败：{e}',
                'gen_invalid_el': '无效元素：{el}',
                'gen_el_not_in_tpl': '元素 {el} 不在模板中！\n允许：{allowed}',
                'gen_invalid_range': '范围无效！Min≥0，Max≤1，且 Min<Max',
                'gen_step_pos': '步长必须 > 0',
                'gen_invalid_nums': '请输入 Min、Max、Step 的有效数值！',
                'gen_locked': '模板锁定状态下无法删除元素，仅可修改范围。',
                'gen_need_tpl0': '请选择有效的 Template0 文件！',
                'gen_need_tpl': '请选择有效的 Template 文件！',
                'gen_need_out': '请指定输出文件！',
                'gen_need_cfg': '请至少添加一组元素配置！',
                'gen_ok': '批处理文件已生成！\n\n组合总数：{n}\n输出：{path}',
                'gen_fail': '生成批处理文件失败：\n{e}',
                'gen_tpl_loaded_body': '识别元素：{els}\n\n元素选择已锁定为上述元素。\n请为每个元素配置 Min/Max/Step。',
                'gen_locked_title': '已锁定',
                'exp_need_folder': '请选择有效文件夹！',
                'exp_need_out': '请指定输出文件！',
                'exp_no_exp': '所选文件夹中未找到 .exp 文件！',
                'exp_regex_bad': '正则表达式无效：{e}',
                'exp_no_results': '未能从文件中提取有效结果！',
                'exp_save_fail': '保存 Excel 失败：\n{e}',
                'exp_process_fail': '处理失败：\n{e}',
                'exp_t0_no_match': '所选文件夹中未找到匹配的 .exp 文件！',
                'exp_t0_no_data': '未能从文件中提取有效数据！',
                'exptc_win_title': '提取 Thermo-calc 结果',
                'exptc_heading': '提取 Thermo-calc 结果',
                'exptc_intro': (
                    '熔程：从 .exp 提取液相线/固相线温度与熔程。\n'
                    'T-zero：从 *_T0.exp 提取 w(*) 及对应 T0。'
                ),
                'exptc_tab_mr': '熔程',
                'exptc_tab_t0': 'T-zero',
                'exptc_mr_folder': '选择包含 .exp 文件的文件夹',
                'exptc_mr_pattern': '文件名模式（可选）',
                'exptc_mr_pattern_lbl': '模式：',
                'exptc_mr_pattern_hint': '留空 = 处理全部 .exp\n正则捕获组 → w(...) 列',
                'exptc_output_xlsx': '输出 Excel 文件',
                'exptc_status': '状态',
                'exptc_process': '处理文件',
                'exptc_fd_mr_folder': '选择包含 .exp 文件的文件夹',
                'exptc_t0_folder': '选择包含 *_T0.exp 的文件夹',
                'exptc_fd_t0_folder': '选择包含 *_T0.exp 的文件夹',
                'exptc_t0_filter': '文件名过滤（可选）',
                'exptc_t0_regex_lbl': '正则：',
                'exptc_t0_filter_hint': '仅处理匹配的文件名。',
                'exptc_mr_done': (
                    '提取完成！\n\n'
                    '成功：{ok} 个文件\n'
                    '失败：{bad} 个文件\n'
                    '已保存至：{path}'
                ),
                'exptc_t0_done': (
                    'T-zero 提取完成！\n\n'
                    '成功：{ok} 个文件\n'
                    '失败：{bad} 个文件\n'
                    '行数：{rows}\n'
                    '已保存至：{path}'
                ),
                'extp_need_lever': '请选择有效的 Lever 文件夹！',
                'extp_need_scheil': '请选择有效的 Scheil 文件夹！',
                'extp_no_csv': 'Lever 文件夹中未找到 CSV 或 DAT 文件！',
                'extp_permission': '无法写入 {path}\n\n若文件在 Excel 等程序中打开，请关闭后重试或更换输出目录。',
                'dlg_permission': '无法写入（权限）',
                'gen_template_info': '模板信息',
                'extp_extract_fail': '提取结果失败：\n{e}',
                'plot_k_no_p': '未找到 P 文件数据。请先通过「导入 → Pandat到ThermoQ」导入 P 文件。',
                'plot_k_no_ps': '未找到 P-S 文件数据。请先通过「导入 → Pandat到ThermoQ」导入 P-S 文件。',
                'plot_k_select_xy': '请选择 X 与 Y 元素！',
                'plot_k_no_points': '有效数据点不足，无法绘制固-液分配系数向量。',
                'plot_k_fail': '绘制分配系数向量失败：\n{e}',
                'plot_k_dep_vec': '未安装 Matplotlib，无法生成分配系数向量图。',
                # Solid-Liquid partition coefficient (k-vectors): Liquidus (P/P-S) tab
                'plot_k_liq_intro': '根据已导入的 Pandat P 或 P-S 数据绘制定义为 k = w(*@固相)/w(*@LIQUID) 的 k 向量。\n固相由 -T//fw(@*) 列及匹配的 w(*@相名) 列自动识别。',
                'plot_k_mode_eq': '平衡/Lever（P 文件）',
                'plot_k_mode_scheil': 'Scheil（P-S 文件）',
                'plot_k_vis_frame': '可视化（|k-1| 场）',
                'plot_k_vis_heatmap': '2D 热力图',
                'plot_k_vis_3d': '3D 静态图',
                'plot_k_vis_gif': '3D 旋转 GIF',
                'plot_k_vis_plotly': 'Plotly 3D',
                'plot_k_gif_fps': 'GIF 帧率：',
                'plot_k_rot_step': '旋转步长（度）：',
                'plot_k_img_fmt_2d3d': '图像格式（2D/3D 静态）：',
                'plot_k_status_ready': '就绪',
                'plot_k_processing': '正在处理数据...',
                'plot_k_done_all_viz': '完成：已生成 k 向量的 2D 矢量、热力图、3D 静态、GIF 与 Plotly 3D。',
                'dlg_select_output_dir': '选择输出目录',
                'dlg_select_all_table_lever_folder': '选择 All table_Lever 文件夹',
                'dlg_select_all_table_scheil_folder': '选择 All table_Scheil 文件夹',
                # Solid-Liquid partition coefficient (k-vectors): pages
                'partition_tab_liquid_points': '液相线',
                'partition_tab_same_temp': '等温线',
                'partition_tab_isocomposition': '等成分',
                'iso_tab_title': '等成分',
                'iso_info': '使用 All table_Lever / All table_Scheil 的 csv/dat 文件，为用户定义的合金成分 O 绘制固-液配分投影与 3D 图。\n对每个温度，f 由 w(X@LIQUID) 给出，S 由 -T//fw(@*) 推断的固相 w(X@solid) 给出。',
                'iso_o_frame_title': '合金成分 O',
                'iso_t_frame_title': '温度范围',
                'iso_o_wx': 'O：w(X)（wt%）：',
                'iso_o_wy': 'O：w(Y)（wt%）：',
                'iso_tmin': 'T 最小值 (K)：',
                'iso_tmax': 'T 最大值 (K)：',
                'iso_npts': '温度点数量：',
                'iso_plot_button': '绘制等成分曲线',
                'iso_need_o': '请输入 O 合金成分（w(X)、w(Y)）！',
                'iso_o_out_of_range': '请检查：所选合金成分超出数据可用的成分范围！',
                'iso_done': '完成：已生成等成分的2D投影与3D图。',
                'iso_2d_title': '2D投影（等成分）',
                'iso_3d_title': '3D等成分（T作Z轴）',
                'iso_dyn_title': '3D动态（高温到低温）',
                'iso_plotly_3d_title': '等成分3D交互图（Plotly）',
                # Solid-Liquid partition coefficient (k-vectors): same temperature page
                'stp_target_temp': '目标温度 (K)：',
                'stp_all_table_lever': 'All table_Lever 文件夹：',
                'stp_all_table_scheil': 'All table_Scheil 文件夹：',
                'stp_need_folder': '请选择有效的 All table 文件夹！',
                'stp_dataset_lever': 'All table_Lever（平衡凝固）',
                'stp_dataset_scheil': 'All table_Scheil（Scheil 凝固）',
                'stp_temp_out_of_range': '目标温度 {t} K 超出数据范围 [{tmin}, {tmax}] K。',
                'stp_no_valid_points': '在所选温度附近没有有效数据点！',
                'stp_plot_button': '在 T 下绘制 U/V/Z',
                'stp_solidification_mode': '凝固模式',
                'stp_output': '输出',
                'stp_filename_prefix': '文件名前缀：',
                'stp_output_settings': '输出设置',
                'stp_output_directory': '输出目录：',
                'stp_image_format': '图像格式：',
                'stp_invalid_temp': '目标温度无效！',
                'stp_solid_phase_infer_fail': '无法从 -T//fw(@*) 列推断固相！',
                'stp_all_table_folders': 'All table 文件夹',
                'stp_elem_selection': '元素选择',
                'stp_x_element': 'X 元素：',
                'stp_y_element': 'Y 元素：',
                'stp_temperature': '温度',
                'stp_tab2_info': '使用 All table_Lever / All table_Scheil 的 csv/dat 文件，在用户指定温度 T 下计算 U/V/Z。\n若文件中不存在该温度，则用二次 Newton 差分插值（选择附近温度点）估算。',
                'stp_loading': '正在读取 All table 文件...',
                'stp_done': '完成：已在 T={t} 下由 All table 文件生成 U/V/Z。',
                'stp_detected_elements': '已检测到元素：{els}',
                'btn_plot_vectors': '绘制向量',
                'plot_liq_dep_vec': '未安装 Matplotlib，无法生成向量图。',
                'plot_liq_t_missing': '数据中未找到温度列 T！',
                'export_need_path': '请指定导出路径！',
                'export_ok_proc': '已导出处理后的数据至：\n{path}',
                'export_ok_clean': '已导出清理后的数据至：\n{path}',
                'export_fail_proc_xlsx': '导出处理后 Excel 失败：\n{e}',
                'export_fail_proc': '导出处理后数据失败：\n{e}',
                'export_fail_clean_xlsx': '导出清理后 Excel 失败：\n{e}',
                'export_fail_clean': '导出清理后数据失败：\n{e}',
                'export_err_title': '导出错误',
                'plot_liq_invalid_els': '无效元素：{ex} 或 {ey}',
                'plot_liq_el_missing': '数据中未找到元素 {el}。可用元素：{avail}',
                'plot_liq_dwdT_missing': '未找到列 dwdT_L({el}@LIQUID)！',
                'plot_liq_no_points_filter': '过滤后无有效数据点！',
                'plot_liq_gen_fail': '生成向量图失败：\n{e}',
                'plot_tc_cols_missing': 'Excel 中缺少所需成分列。\n查找：w({ex})、w({ey})\n可用 w(*) 列（前 10 个）：{avail}',
                'extp_success': '结果提取成功！\n\n输出目录：{dir}\n\nP.xlsx：{np} 行\nTs.xlsx：{nts} 行\nP-S.xlsx：{nps} 行\nTs-S.xlsx：{ntss} 行',
                'liqvec_ok_4': '向量图已生成！\n\nU（水平）：{u}\nV（垂直）：{v}\nZ（合成）：{z}\n液相面上 Z（{viz}）：{zliq}',
                'liqvec_ok_3': '向量图已生成！\n\nU（水平）：{u}\nV（垂直）：{v}\nZ（合成）：{z}',
                'liqvec_partial': '向量图已生成，但可视化图失败：\n{err}\n\nU（水平）：{u}\nV（垂直）：{v}\nZ（合成）：{z}',
                'liqvec_ok_no_t': '向量图已生成！\n\nU（水平）：{u}\nV（垂直）：{v}\nZ（合成）：{z}\n\n说明：无温度数据，已跳过液相面 Z 向量图。',
            }
        }
        
        # Create File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Exit", command=root.quit)
        
        # Create Import menu
        self.import_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Import", menu=self.import_menu)
        self.import_menu.add_command(label="Pandat to ThermoQ", command=self.open_pandat_import)
        
        # Create Tools menu
        self.plot_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Plot", menu=self.plot_menu)
        self.plot_menu.add_command(label="Plot Phase Surfaces", command=self.open_phase_surface_plotter)
        self.plot_menu.add_command(label="Plot Qtrue Values", command=self.open_q_value_plotter)
        self.plot_menu.add_command(label="Plot Liquidus Vectors", command=self.open_liquidus_vector_plotter)
        self.plot_menu.add_command(label="Plot Solid-Liquid Partition Coefficients", command=self.open_partition_vector_plotter)
        self.plot_menu.add_command(label="Plot T-zero Surface", command=self.open_t_zero_surface_plotter)
        
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(label="Composition Converter (wt% ↔ at%)", command=self.open_composition_converter)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="Generate Thermo-calc Batch File", command=self.open_therocalc_generator)
        self.tools_menu.add_command(label="Extract Thermo-calc Results", command=self.open_exp_data_processor)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="Extract Pandat Results", command=self.open_extract_pandat_results)

        # Create Help menu
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.lang_menu = tk.Menu(self.help_menu, tearoff=0)
        self.help_menu.add_cascade(label="Language", menu=self.lang_menu)
        self.lang_menu.add_command(label="English", command=lambda: self.set_language('en'))
        self.lang_menu.add_command(label="中文", command=lambda: self.set_language('zh'))
        self.help_menu.add_separator()
        self.help_menu.add_command(label="Example", command=self.open_example_folder)
        
        # Set window icon
        try:
            icon_path = "images/Simplified logo.png"
            icon_image = Image.open(icon_path)
            icon_photo = ImageTk.PhotoImage(icon_image)
            self.root.iconphoto(True, icon_photo)
            self.icon_photo = icon_photo
        except Exception as e:
            print(f"Error loading window icon: {e}")
        
        # Configure grid weights for better layout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create main frame with yellow background
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame grid weights
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Logo section
        try:
            logo_img = Image.open("images/Simplified logo.png")
            logo_size = (80, 80)  # Reduced logo size
            logo_img = logo_img.resize(logo_size, Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            
            logo_label = ttk.Label(main_frame, image=self.logo_photo)
            logo_label.grid(row=0, column=0, sticky=(tk.N), padx=(0, 10), pady=5)
        except Exception as e:
            print(f"Error loading logo: {e}")
        
        # Calculate workspace: tab "Single composition" + tab "Composition space (batch)"
        self.calc_notebook = ttk.Notebook(main_frame)
        self.calc_notebook.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        tab_single = ttk.Frame(self.calc_notebook, padding=(4, 6))
        self.calc_notebook.add(tab_single, text="Single composition")
        tab_single.grid_columnconfigure(0, weight=1)
        tab_single.grid_rowconfigure(0, weight=1)

        self.element_selector = ElementSelector(tab_single, self)
        self.element_selector.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        buttons_frame = ttk.Frame(tab_single)
        buttons_frame.grid(row=1, column=0, pady=10)
        self.calculate_button = ttk.Button(buttons_frame, text="Calculate", command=self.calculate)
        self.calculate_button.grid(row=0, column=0, padx=10)
        self.show_results_button = ttk.Button(buttons_frame, text="Show Results", command=self.show_results)
        self.show_results_button.grid(row=0, column=1, padx=10)

        tab_batch = ttk.Frame(self.calc_notebook, padding=6)
        self.calc_notebook.add(tab_batch, text="Composition space (batch)")
        self._setup_calculate_batch_tab(tab_batch)

        # Apply initial language (updates tab titles + batch labels)
        self.set_language(self.language)

    def show(self):
        # Center window on screen after splash
        self.center_window()
        self.root.deiconify()

    def _refresh_calculate_main_language(self):
        """Update Calculate notebook tab titles and batch-tab static strings (Help → Language)."""
        if not hasattr(self, 'calc_notebook'):
            return
        t = self.texts.get(self.language, self.texts['en'])
        try:
            self.calc_notebook.tab(0, text=t.get('calc_tab_single', 'Single composition'))
            self.calc_notebook.tab(1, text=t.get('calc_tab_batch', 'Composition space (batch)'))
        except tk.TclError:
            pass
        pairs = getattr(self, '_batch_lang_widgets', None)
        if pairs:
            for w, key in pairs:
                try:
                    if w.winfo_exists():
                        w.config(text=self.tr(key, ''))
                except tk.TclError:
                    pass
        if hasattr(self, 'batch_intro_label'):
            try:
                if self.batch_intro_label.winfo_exists():
                    self.batch_intro_label.config(text=self.tr('batch_intro', ''))
            except tk.TclError:
                pass
        # Visualization radiobuttons share tr keys
        vmeta = getattr(self, '_batch_viz_lang', None)
        if vmeta:
            for rb, key, _val in vmeta:
                try:
                    if rb.winfo_exists():
                        rb.config(text=self.tr(key, ''))
                except tk.TclError:
                    pass
        try:
            self._refresh_batch_z_combo_values()
        except Exception:
            pass

    def _setup_calculate_batch_tab(self, tab_batch):
        """Build the batch export / plot sub-UI on the Calculate notebook."""
        self._batch_lang_widgets = []
        outer = ttk.Frame(tab_batch)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        canvas = tk.Canvas(outer, highlightthickness=0, takefocus=1)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        scrollable_frame = ttk.Frame(canvas)
        self._batch_scroll_canvas = canvas
        _batch_cw = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)

        def _batch_on_inner_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _batch_on_canvas_configure(event):
            try:
                canvas.itemconfigure(_batch_cw, width=max(1, int(event.width)))
            except tk.TclError:
                pass

        scrollable_frame.bind("<Configure>", _batch_on_inner_configure)
        canvas.bind("<Configure>", _batch_on_canvas_configure)

        def _batch_mousewheel(event):
            delta = 0
            d = getattr(event, "delta", 0) or 0
            if d:
                if platform.system() == "Darwin":
                    delta = -1 if d > 0 else 1
                else:
                    delta = int(-1 * (d / 120))
                    if delta == 0:
                        delta = -1 if d > 0 else 1
            elif getattr(event, "num", None) == 4:
                delta = -1
            elif getattr(event, "num", None) == 5:
                delta = 1
            if delta:
                canvas.yview_scroll(delta, "units")
            return "break"

        def _batch_bind_wheel(_e=None):
            canvas.bind_all("<MouseWheel>", _batch_mousewheel)
            if platform.system() == "Linux":
                canvas.bind_all("<Button-4>", _batch_mousewheel)
                canvas.bind_all("<Button-5>", _batch_mousewheel)

        def _batch_unbind_wheel(_e=None):
            try:
                canvas.unbind_all("<MouseWheel>")
                if platform.system() == "Linux":
                    canvas.unbind_all("<Button-4>")
                    canvas.unbind_all("<Button-5>")
            except tk.TclError:
                pass

        outer.bind("<Enter>", _batch_bind_wheel)
        outer.bind("<Leave>", _batch_unbind_wheel)

        self.batch_intro_label = ttk.Label(
            scrollable_frame,
            text=self.tr(
                'batch_intro',
                'Compute P, Q, Qtrue, ΔT, ΔTs, β, etc. for every composition row in the selected liquidus table.',
            ),
            wraplength=700,
            justify='left',
        )
        self.batch_intro_label.pack(anchor='w', pady=(0, 8))

        src_fr = ttk.LabelFrame(scrollable_frame, text=self.tr('batch_frame_source', 'Batch source'), padding=8)
        src_fr.pack(fill=tk.X, pady=4)
        self._batch_lang_widgets.append((src_fr, 'batch_frame_source'))

        self.batch_source_var = tk.StringVar(value="Lever")
        rb_lev = ttk.Radiobutton(
            src_fr,
            text=self.tr('batch_mode_lever', 'Equilibrium/Lever (rows from P file)'),
            variable=self.batch_source_var,
            value="Lever",
        )
        rb_lev.pack(anchor='w', padx=4, pady=2)
        self._batch_lang_widgets.append((rb_lev, 'batch_mode_lever'))
        rb_sch = ttk.Radiobutton(
            src_fr,
            text=self.tr('batch_mode_scheil', 'Scheil (rows from P-S file)'),
            variable=self.batch_source_var,
            value="Scheil",
        )
        rb_sch.pack(anchor='w', padx=4, pady=2)
        self._batch_lang_widgets.append((rb_sch, 'batch_mode_scheil'))
        rb_all = ttk.Radiobutton(
            src_fr,
            text=self.tr('batch_mode_all', 'All (rows from P file and P-S file)'),
            variable=self.batch_source_var,
            value="All",
        )
        rb_all.pack(anchor='w', padx=4, pady=2)
        self._batch_lang_widgets.append((rb_all, 'batch_mode_all'))

        mr_fr = ttk.Frame(src_fr)
        mr_fr.pack(fill=tk.X, pady=4)
        mr_lbl = ttk.Label(mr_fr, text=self.tr('batch_max_rows', 'Max rows (blank = all):'))
        mr_lbl.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((mr_lbl, 'batch_max_rows'))
        self.batch_max_rows_var = tk.StringVar(value="")
        ttk.Entry(mr_fr, textvariable=self.batch_max_rows_var, width=10).pack(side=tk.LEFT, padx=4)

        btn_fr = ttk.Frame(scrollable_frame)
        btn_fr.pack(fill=tk.X, pady=6)
        self.batch_compute_btn = ttk.Button(btn_fr, text=self.tr('batch_compute', 'Compute batch'), command=self.run_batch_compute_for_space)
        self.batch_compute_btn.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((self.batch_compute_btn, 'batch_compute'))
        self.batch_save_btn = ttk.Button(btn_fr, text=self.tr('batch_save_csv', 'Save CSV…'), command=self.run_batch_save_csv)
        self.batch_save_btn.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((self.batch_save_btn, 'batch_save_csv'))
        self.batch_save_excel_filled_btn = ttk.Button(
            btn_fr,
            text=self.tr('batch_save_excel_filled', 'Save Excel (interpolated batch)…'),
            command=self.run_batch_save_excel_interpolated,
        )
        self.batch_save_excel_filled_btn.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((self.batch_save_excel_filled_btn, 'batch_save_excel_filled'))

        self.batch_compute_status_label = ttk.Label(
            scrollable_frame,
            text=self.tr('batch_status_ready', 'Run “Compute batch” first.'),
            foreground="blue",
        )
        self.batch_compute_status_label.pack(anchor='w', pady=4)

        plot_fr = ttk.LabelFrame(scrollable_frame, text=self.tr('batch_plot_group', 'Plot (2D / 3D)'), padding=8)
        plot_fr.pack(fill=tk.X, pady=6)
        self._batch_lang_widgets.append((plot_fr, 'batch_plot_group'))

        pi = ttk.Label(
            plot_fr,
            text=self.tr('batch_plot_intro', 'Uses the last computed batch table. Choose composition axes and Z quantity.'),
            wraplength=680,
            justify='left',
        )
        pi.pack(anchor='w', pady=(0, 6))
        self._batch_lang_widgets.append((pi, 'batch_plot_intro'))

        elem_vals = self.available_elements if self.available_elements else sorted(PERIODIC_TABLE.keys())
        xy_fr = ttk.Frame(plot_fr)
        xy_fr.pack(fill=tk.X, pady=4)
        lx = ttk.Label(xy_fr, text=self.tr('batch_plot_x_el', 'X element:'))
        lx.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lx, 'batch_plot_x_el'))
        self.batch_plot_x_var = tk.StringVar()
        self.batch_plot_x_combo = ttk.Combobox(xy_fr, textvariable=self.batch_plot_x_var, values=elem_vals, width=8)
        self.batch_plot_x_combo.pack(side=tk.LEFT, padx=4)
        ly = ttk.Label(xy_fr, text=self.tr('batch_plot_y_el', 'Y element:'))
        ly.pack(side=tk.LEFT, padx=12)
        self._batch_lang_widgets.append((ly, 'batch_plot_y_el'))
        self.batch_plot_y_var = tk.StringVar()
        self.batch_plot_y_combo = ttk.Combobox(xy_fr, textvariable=self.batch_plot_y_var, values=elem_vals, width=8)
        self.batch_plot_y_combo.pack(side=tk.LEFT, padx=4)

        z_fr = ttk.Frame(plot_fr)
        z_fr.pack(fill=tk.X, pady=4)
        lz = ttk.Label(z_fr, text=self.tr('batch_z_quantity', 'Quantity (Z):'))
        lz.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lz, 'batch_z_quantity'))
        self.batch_z_var = tk.StringVar(value=self.tr('batch_z_all', 'All'))
        self.batch_z_combo = ttk.Combobox(z_fr, textvariable=self.batch_z_var, width=42, state="readonly")
        self.batch_z_combo.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        self.batch_z_combo['values'] = (self.tr('batch_z_all', 'All'),)

        vz_fr = ttk.Frame(plot_fr)
        vz_fr.pack(fill=tk.X, pady=4)
        lvz = ttk.Label(vz_fr, text=self.tr('batch_viz', 'Visualization:'))
        lvz.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lvz, 'batch_viz'))
        self.batch_viz_var = tk.StringVar(value="2D Heatmap")
        self._batch_viz_lang = []
        viz_specs = [
            ('batch_viz_2d', '2D Heatmap'),
            ('batch_viz_3d', '3D Static'),
            ('batch_viz_gif', '3D Rotation GIF'),
            ('batch_viz_plotly', 'Plotly 3D'),
        ]
        for trk, val in viz_specs:
            rb = ttk.Radiobutton(vz_fr, text=self.tr(trk, val), variable=self.batch_viz_var, value=val)
            rb.pack(side=tk.LEFT, padx=4)
            self._batch_viz_lang.append((rb, trk, val))

        sm_fr = ttk.Frame(plot_fr)
        sm_fr.pack(fill=tk.X, pady=4)
        lsm = ttk.Label(sm_fr, text=self.tr('batch_smooth', 'Smoothness:'))
        lsm.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lsm, 'batch_smooth'))
        self.batch_smoothness_var = tk.DoubleVar(value=100.0)
        self.batch_smooth_val_lbl = ttk.Label(sm_fr, text="100")
        self.batch_smooth_val_lbl.pack(side=tk.RIGHT, padx=6)

        def _on_batch_smooth(val):
            try:
                self.batch_smooth_val_lbl.config(text=str(int(float(val))))
            except Exception:
                self.batch_smooth_val_lbl.config(text="100")

        ttk.Scale(
            sm_fr,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.batch_smoothness_var,
            command=_on_batch_smooth,
        ).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        view_fr = ttk.LabelFrame(plot_fr, text=self.tr('batch_view_3d', '3D Static View (Rotation Angles)'), padding=6)
        view_fr.pack(fill=tk.X, pady=4)
        self._batch_lang_widgets.append((view_fr, 'batch_view_3d'))
        self.batch_elev_var = tk.DoubleVar(value=30.0)
        self.batch_azim_var = tk.DoubleVar(value=-60.0)
        er = ttk.Frame(view_fr)
        er.pack(fill=tk.X, pady=2)
        le = ttk.Label(er, text=self.tr('batch_elev', 'Elevation (deg):'))
        le.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((le, 'batch_elev'))
        ttk.Entry(er, textvariable=self.batch_elev_var, width=8).pack(side=tk.LEFT, padx=4)
        ar = ttk.Frame(view_fr)
        ar.pack(fill=tk.X, pady=2)
        la = ttk.Label(ar, text=self.tr('batch_azim', 'Azimuth (deg):'))
        la.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((la, 'batch_azim'))
        ttk.Entry(ar, textvariable=self.batch_azim_var, width=8).pack(side=tk.LEFT, padx=4)

        out_fr = ttk.LabelFrame(plot_fr, text=self.tr('batch_output_block', 'Output files'), padding=6)
        out_fr.pack(fill=tk.X, pady=4)
        self._batch_lang_widgets.append((out_fr, 'batch_output_block'))
        out_row = ttk.Frame(out_fr)
        out_row.pack(fill=tk.X, pady=2)
        lod = ttk.Label(out_row, text=self.tr('batch_output_dir', 'Output Directory:'))
        lod.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lod, 'batch_output_dir'))
        self.batch_output_dir_var = tk.StringVar()
        ttk.Entry(out_row, textvariable=self.batch_output_dir_var, width=36).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        def _browse_batch_out():
            d = filedialog.askdirectory(title=self.tr('batch_output_dir', 'Output Directory:'))
            if d:
                self.batch_output_dir_var.set(d)

        bb = ttk.Button(out_row, text=self.tr('batch_browse', 'Browse'), command=_browse_batch_out)
        bb.pack(side=tk.RIGHT, padx=4)
        self._batch_lang_widgets.append((bb, 'batch_browse'))

        pfx_fr = ttk.Frame(plot_fr)
        pfx_fr.pack(fill=tk.X, pady=2)
        lpfx = ttk.Label(pfx_fr, text=self.tr('batch_prefix', 'Output Prefix:'))
        lpfx.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lpfx, 'batch_prefix'))
        self.batch_output_prefix_var = tk.StringVar(value="batch_calc")
        ttk.Entry(pfx_fr, textvariable=self.batch_output_prefix_var, width=30).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        fmt_fr = ttk.Frame(plot_fr)
        fmt_fr.pack(fill=tk.X, pady=2)
        lfmt = ttk.Label(fmt_fr, text=self.tr('batch_image_fmt', 'Image Format (2D/3D Static):'))
        lfmt.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lfmt, 'batch_image_fmt'))
        self.batch_image_format_var = tk.StringVar(value="PNG")
        fmt_opts = ["PNG", "JPEG", "GIF", "BMP", "TIFF", "WebP", "SVG", "PDF"]
        ttk.Combobox(fmt_fr, textvariable=self.batch_image_format_var, values=fmt_opts, state="readonly", width=12).pack(
            side=tk.LEFT, padx=4
        )

        gif_fr = ttk.LabelFrame(plot_fr, text=self.tr('batch_gif_params', '3D Rotation GIF Parameters'), padding=6)
        gif_fr.pack(fill=tk.X, pady=4)
        self._batch_lang_widgets.append((gif_fr, 'batch_gif_params'))
        self.batch_gif_speed_var = tk.StringVar(value="5")
        self.batch_gif_interval_var = tk.StringVar(value="50")
        self.batch_gif_fps_var = tk.StringVar(value="20")
        g1 = ttk.Frame(gif_fr)
        g1.pack(fill=tk.X, pady=2)
        lg1 = ttk.Label(g1, text=self.tr('batch_gif_speed', 'Rotation Speed (degrees/frame):'))
        lg1.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lg1, 'batch_gif_speed'))
        ttk.Entry(g1, textvariable=self.batch_gif_speed_var, width=8).pack(side=tk.LEFT, padx=4)
        g2 = ttk.Frame(gif_fr)
        g2.pack(fill=tk.X, pady=2)
        lg2 = ttk.Label(g2, text=self.tr('batch_gif_interval', 'Frame Interval (ms):'))
        lg2.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lg2, 'batch_gif_interval'))
        ttk.Entry(g2, textvariable=self.batch_gif_interval_var, width=8).pack(side=tk.LEFT, padx=4)
        g3 = ttk.Frame(gif_fr)
        g3.pack(fill=tk.X, pady=2)
        lg3 = ttk.Label(g3, text=self.tr('batch_gif_fps', 'FPS:'))
        lg3.pack(side=tk.LEFT, padx=4)
        self._batch_lang_widgets.append((lg3, 'batch_gif_fps'))
        ttk.Entry(g3, textvariable=self.batch_gif_fps_var, width=8).pack(side=tk.LEFT, padx=4)

        self.batch_plot_btn = ttk.Button(plot_fr, text=self.tr('batch_plot_btn', 'Generate plot'), command=self.run_batch_plot_for_space)
        self.batch_plot_btn.pack(pady=10)
        self._batch_lang_widgets.append((self.batch_plot_btn, 'batch_plot_btn'))

    @staticmethod
    def _infer_batch_xyz_elements(df):
        """
        X, Y, Z = three elements by mean bulk composition: X lowest, Y middle, Z highest (major element).
        Returns (x, y, z) or None if not exactly three w_* columns.
        """
        els = []
        for c in df.columns:
            cs = str(c)
            if cs.startswith('w_'):
                els.append(cs[2:])
        if len(els) != 3:
            return None
        means = {}
        for e in els:
            col = f"w_{e}"
            means[e] = float(pd.to_numeric(df[col], errors='coerce').mean())
        ordered = sorted(els, key=lambda k: means[k])
        return ordered[0], ordered[1], ordered[2]

    @staticmethod
    def _batch_export_column_names(cols, mode):
        """Columns to keep for CSV/Excel export by batch source mode."""
        out = []
        for c in cols:
            s = str(c)
            if s.startswith('__'):
                continue
            if mode == "Scheil":
                if s.startswith('w_') or s == 'ΔTs' or '(Scheil)' in s or s.startswith('Qtrue (Scheil)'):
                    out.append(c)
            elif mode == "Lever":
                if s.startswith('w_') or s == 'ΔT' or '(Lever)' in s or s.startswith('Qtrue (Lever)'):
                    out.append(c)
            else:
                out.append(c)
        return out

    def _batch_fill_qpb_newton(self, df, x_el, y_el, z_el, do_lever, do_scheil):
        """
        Newton forward extrapolation to w=0 for missing Q/P/Beta (Lever and/or Scheil) using samples at w=1,2,3
        as specified for composition-space batch export (ternary X,Y,Z).
        """
        out = df.copy()
        col_wx = f"w_{x_el}"
        col_wy = f"w_{y_el}"
        atol = 1e-4
        atol_w123 = 2e-3
        suffixes = []
        if do_lever:
            suffixes.append('Lever')
        if do_scheil:
            suffixes.append('Scheil')
        metrics = ('Q', 'P', 'Beta')

        def _triplet_at_w_axis(sub_df, axis_col, w_targets, col_target):
            vals = []
            for t in w_targets:
                wv = pd.to_numeric(sub_df[axis_col], errors='coerce')
                rows = sub_df[np.isclose(wv, float(t), atol=atol_w123)]
                if rows.empty:
                    return None
                v = pd.to_numeric(rows.iloc[0][col_target], errors='coerce')
                if pd.isna(v):
                    return None
                vals.append(float(v))
            return self._liquidus_newton_forward_interpolation(vals[0], vals[1], vals[2])

        for suf in suffixes:
            cols_x = [f"{m} ({x_el} {suf})" for m in metrics]
            cols_y = [f"{m} ({y_el} {suf})" for m in metrics]
            cols_z = [f"{m} ({z_el} {suf})" for m in metrics]

            # Step 1: w(X)≈0, w(Y) not ≈0 → X columns
            for col_tgt in cols_x:
                if col_tgt not in out.columns:
                    continue
                wx = pd.to_numeric(out[col_wx], errors='coerce')
                wy = pd.to_numeric(out[col_wy], errors='coerce')
                for idx in out.index:
                    if not (np.isclose(wx.loc[idx], 0.0, atol=atol) and not np.isclose(wy.loc[idx], 0.0, atol=atol)):
                        continue
                    if pd.notna(pd.to_numeric(out.loc[idx, col_tgt], errors='coerce')):
                        continue
                    cur_wy = wy.loc[idx]
                    sub = out[np.isclose(wy, cur_wy, atol=atol)]
                    nv = _triplet_at_w_axis(sub, col_wx, (1, 2, 3), col_tgt)
                    if pd.notna(nv):
                        out.loc[idx, col_tgt] = nv

            # Step 2: w(Y)≈0, w(X) not ≈0 → Y columns
            for col_tgt in cols_y:
                if col_tgt not in out.columns:
                    continue
                wx = pd.to_numeric(out[col_wx], errors='coerce')
                wy = pd.to_numeric(out[col_wy], errors='coerce')
                for idx in out.index:
                    if not (np.isclose(wy.loc[idx], 0.0, atol=atol) and not np.isclose(wx.loc[idx], 0.0, atol=atol)):
                        continue
                    if pd.notna(pd.to_numeric(out.loc[idx, col_tgt], errors='coerce')):
                        continue
                    cur_wx = wx.loc[idx]
                    sub = out[np.isclose(wx, cur_wx, atol=atol)]
                    nv = _triplet_at_w_axis(sub, col_wy, (1, 2, 3), col_tgt)
                    if pd.notna(nv):
                        out.loc[idx, col_tgt] = nv

            # Step 3: corner w(X)≈0, w(Y)≈0
            for col_tgt in cols_x:
                if col_tgt not in out.columns:
                    continue
                wx = pd.to_numeric(out[col_wx], errors='coerce')
                wy = pd.to_numeric(out[col_wy], errors='coerce')
                for idx in out.index:
                    if not (np.isclose(wx.loc[idx], 0.0, atol=atol) and np.isclose(wy.loc[idx], 0.0, atol=atol)):
                        continue
                    if pd.notna(pd.to_numeric(out.loc[idx, col_tgt], errors='coerce')):
                        continue
                    sub = out[np.isclose(wy, 0.0, atol=atol)]
                    nv = _triplet_at_w_axis(sub, col_wx, (1, 2, 3), col_tgt)
                    if pd.notna(nv):
                        out.loc[idx, col_tgt] = nv

            for col_tgt in cols_y:
                if col_tgt not in out.columns:
                    continue
                wx = pd.to_numeric(out[col_wx], errors='coerce')
                wy = pd.to_numeric(out[col_wy], errors='coerce')
                for idx in out.index:
                    if not (np.isclose(wx.loc[idx], 0.0, atol=atol) and np.isclose(wy.loc[idx], 0.0, atol=atol)):
                        continue
                    if pd.notna(pd.to_numeric(out.loc[idx, col_tgt], errors='coerce')):
                        continue
                    sub = out[np.isclose(wx, 0.0, atol=atol)]
                    nv = _triplet_at_w_axis(sub, col_wy, (1, 2, 3), col_tgt)
                    if pd.notna(nv):
                        out.loc[idx, col_tgt] = nv

            # Z at corner: average of two Newton paths when both available
            for col_tgt in cols_z:
                if col_tgt not in out.columns:
                    continue
                wx = pd.to_numeric(out[col_wx], errors='coerce')
                wy = pd.to_numeric(out[col_wy], errors='coerce')
                for idx in out.index:
                    if not (np.isclose(wx.loc[idx], 0.0, atol=atol) and np.isclose(wy.loc[idx], 0.0, atol=atol)):
                        continue
                    if pd.notna(pd.to_numeric(out.loc[idx, col_tgt], errors='coerce')):
                        continue
                    sub_a = out[np.isclose(wx, 0.0, atol=atol)]
                    v_a = _triplet_at_w_axis(sub_a, col_wy, (1, 2, 3), col_tgt)
                    sub_b = out[np.isclose(wy, 0.0, atol=atol)]
                    v_b = _triplet_at_w_axis(sub_b, col_wx, (1, 2, 3), col_tgt)
                    if pd.notna(v_a) and pd.notna(v_b):
                        out.loc[idx, col_tgt] = 0.5 * (float(v_a) + float(v_b))
                    elif pd.notna(v_a):
                        out.loc[idx, col_tgt] = float(v_a)
                    elif pd.notna(v_b):
                        out.loc[idx, col_tgt] = float(v_b)

        return out

    def _batch_dataframe_for_export(self, apply_newton_fill=True):
        """
        Copy last batch results, optional Q/P/Beta Newton fill, filter columns by last_batch_mode, drop __ columns.
        """
        if self.last_batch_results_df is None or len(self.last_batch_results_df) == 0:
            return None
        mode = self.last_batch_mode or self.batch_source_var.get()
        df = self.last_batch_results_df.copy()
        if apply_newton_fill:
            xyz = self._infer_batch_xyz_elements(df)
            if xyz is None:
                # Ternary Newton fill only; still export filtered columns without fill
                pass
            else:
                x_el, y_el, z_el = xyz
                do_lev = mode in ("Lever", "All")
                do_sch = mode in ("Scheil", "All")
                df = self._batch_fill_qpb_newton(df, x_el, y_el, z_el, do_lev, do_sch)
        keep = self._batch_export_column_names(df.columns, mode)
        df = df[[c for c in keep if c in df.columns]]
        return df

    def _batch_is_z_all(self, z):
        z = (z or '').strip()
        for lang in ('en', 'zh'):
            lab = self.texts[lang].get('batch_z_all', 'All' if lang == 'en' else '全部')
            if z == lab:
                return True
        return False

    def _batch_numeric_z_columns(self, df):
        cols = []
        if df is None or len(df) == 0:
            return cols
        for c in df.columns:
            if str(c).startswith('__'):
                continue
            if pd.api.types.is_numeric_dtype(df[c]):
                cols.append(c)
        return cols

    def _refresh_batch_z_combo_values(self):
        """Rebuild Quantity (Z) list with localized 'All' + numeric columns; call after compute or language change."""
        if not hasattr(self, 'batch_z_combo'):
            return
        all_lbl = self.tr('batch_z_all', 'All')
        df = getattr(self, 'last_batch_results_df', None)
        if df is None or len(df) == 0:
            self.batch_z_combo['values'] = (all_lbl,)
            self.batch_z_var.set(all_lbl)
            return
        num_cols = self._batch_numeric_z_columns(df)
        self.batch_z_combo['values'] = (all_lbl,) + tuple(num_cols)
        cur = (self.batch_z_var.get() or '').strip()
        if self._batch_is_z_all(cur):
            self.batch_z_var.set(all_lbl)
        elif cur in num_cols:
            pass
        else:
            pick = None
            mode = getattr(self, 'last_batch_mode', None) or self.batch_source_var.get()
            if mode == "Scheil":
                for prefer in ("Qtrue (Scheil)", "ΔTs"):
                    if prefer in num_cols:
                        pick = prefer
                        break
            elif mode == "Lever":
                for prefer in ("Qtrue (Lever)", "ΔT"):
                    if prefer in num_cols:
                        pick = prefer
                        break
            else:
                for prefer in ("Qtrue (Lever)", "Qtrue (Scheil)", "ΔT", "ΔTs"):
                    if prefer in num_cols:
                        pick = prefer
                        break
            self.batch_z_var.set(pick if pick else (num_cols[0] if num_cols else all_lbl))

    def run_batch_compute_for_space(self):
        """Fill last_batch_results_df from each row of P, P-S, or both (same formulas as Calculate)."""
        if self.pandat_p_data is None or self.pandat_ts_data is None:
            messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr('calc_need_pandat', "Please import Pandat data first using 'Import > Pandat to ThermoQ'!"),
            )
            return
        mode = self.batch_source_var.get()
        if mode in ("Scheil", "All") and self.pandat_p_s_data is None:
            messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr('plot_msg_import_pandat_p', 'No P-S data. Please import Scheil files.'),
            )
            return
        if mode == "All" and (self.pandat_ts_s_data is None or self.pandat_p_s_data is None):
            messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr('batch_need_all_pandat', '“All” requires P, Ts, P-S, and Ts-S data. Import via Pandat to ThermoQ.'),
            )
            return

        def _cap_rows(s_raw, n_total):
            s_raw = (s_raw or "").strip()
            if not s_raw:
                return n_total
            try:
                return min(max(1, int(s_raw)), n_total)
            except ValueError:
                return None

        s = self.batch_max_rows_var.get()
        rows_out = []
        skipped = 0
        row_id = 0
        n_p_used = 0
        n_ps_used = 0
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:

            def _one_source(df_source, n_cap, tag):
                nonlocal row_id, skipped
                local_skipped = 0
                for idx in range(n_cap):
                    wt = self._bulk_composition_from_pandat_row(df_source, idx)
                    if len(wt) < 1:
                        local_skipped += 1
                        continue
                    tot = sum(wt.values())
                    if abs(tot - 100.0) > 0.6:
                        local_skipped += 1
                        continue
                    element_order = sorted(wt.keys())
                    try:
                        etc_p = self._pandat_element_to_col(wt, self.pandat_p_data)
                        etc_ts = self._pandat_element_to_col(wt, self.pandat_ts_data)
                        range_errs = []
                        range_errs.extend(
                            self._pandat_composition_range_errors(wt, self.pandat_p_data, etc_p, 'P.xlsx (Lever)')
                        )
                        range_errs.extend(
                            self._pandat_composition_range_errors(wt, self.pandat_ts_data, etc_ts, 'Ts.xlsx (Lever)')
                        )
                        etc_ps = None
                        etc_tss = None
                        if self.pandat_p_s_data is not None:
                            etc_ps = self._pandat_element_to_col(wt, self.pandat_p_s_data)
                            range_errs.extend(
                                self._pandat_composition_range_errors(wt, self.pandat_p_s_data, etc_ps, 'P-S.xlsx (Scheil)')
                            )
                        if self.pandat_ts_s_data is not None:
                            etc_tss = self._pandat_element_to_col(wt, self.pandat_ts_s_data)
                            range_errs.extend(
                                self._pandat_composition_range_errors(wt, self.pandat_ts_s_data, etc_tss, 'Ts-S.xlsx (Scheil)')
                            )
                    except ValueError:
                        local_skipped += 1
                        continue
                    if range_errs:
                        local_skipped += 1
                        continue
                    results, _errors, _interp = self._compute_thermoq_results(
                        wt, element_order, etc_p, etc_ts, etc_ps, etc_tss
                    )
                    rec = {f"w_{k}": float(v) for k, v in wt.items()}
                    for k, v in results.items():
                        try:
                            rec[k] = float(v) if v is not None else np.nan
                        except (TypeError, ValueError):
                            rec[k] = np.nan
                    rec['__batch_src_idx__'] = int(idx)
                    rec['__batch_source_table__'] = tag
                    rec['__batch_row__'] = int(row_id)
                    row_id += 1
                    rows_out.append(rec)
                skipped += local_skipped

            if mode in ("Lever", "All"):
                n_cap = _cap_rows(s, len(self.pandat_p_data))
                if n_cap is None:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('batch_max_rows_invalid', 'Invalid integer for max rows.'),
                    )
                    return
                before = len(rows_out)
                _one_source(self.pandat_p_data, n_cap, 'P')
                n_p_used = len(rows_out) - before

            if mode in ("Scheil", "All"):
                n_cap = _cap_rows(s, len(self.pandat_p_s_data))
                if n_cap is None:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('batch_max_rows_invalid', 'Invalid integer for max rows.'),
                    )
                    return
                before = len(rows_out)
                _one_source(self.pandat_p_s_data, n_cap, 'PS')
                n_ps_used = len(rows_out) - before

        finally:
            self.root.config(cursor="")

        if not rows_out:
            self.last_batch_results_df = None
            self.last_batch_n_limit = None
            self.last_batch_n_p = 0
            self.last_batch_n_ps = 0
            self.last_batch_mode = None
            messagebox.showwarning(
                self.tr('dlg_warning', 'Warning'),
                self.tr(
                    'batch_no_rows',
                    'No valid rows computed. Check that compositions sum to ~100 wt% and lie within tabulated ranges.',
                ),
            )
            self.batch_compute_status_label.config(
                text=self.tr('batch_status_ready', 'Run “Compute batch” first.'),
                foreground="orange",
            )
            return

        self.last_batch_mode = mode
        self.last_batch_n_p = int(n_p_used)
        self.last_batch_n_ps = int(n_ps_used)
        self.last_batch_n_limit = int(len(rows_out))
        self.last_batch_results_df = pd.DataFrame(rows_out)
        self._refresh_batch_z_combo_values()

        msg = self.tr('batch_done', 'Batch done: {n} rows ({skipped} skipped).').format(
            n=len(rows_out), skipped=skipped
        )
        self.batch_compute_status_label.config(text=msg, foreground="green")

    def run_batch_save_csv(self):
        if self.last_batch_results_df is None or len(self.last_batch_results_df) == 0:
            messagebox.showwarning(self.tr('dlg_warning', 'Warning'), self.tr('batch_need_compute', 'Please run “Compute batch” first.'))
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=self.tr('batch_save_csv', 'Save CSV…'),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
            initialfile="thermoq_batch_calc.csv",
        )
        if not path:
            return
        try:
            df_out = self._batch_dataframe_for_export(apply_newton_fill=True)
            if df_out is None:
                return
            df_out.to_csv(path, index=False, encoding="utf-8-sig")
            messagebox.showinfo(
                self.tr('dlg_success', 'Success'),
                self.tr('batch_saved', 'Saved: {path}').format(path=path),
            )
        except Exception as e:
            messagebox.showerror(self.tr('dlg_error', 'Error'), str(e))

    def run_batch_save_excel_interpolated(self):
        """Export batch table after Q/P/Beta Newton fill, columns filtered by batch source mode."""
        if self.last_batch_results_df is None or len(self.last_batch_results_df) == 0:
            messagebox.showwarning(self.tr('dlg_warning', 'Warning'), self.tr('batch_need_compute', 'Please run “Compute batch” first.'))
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=self.tr('batch_save_excel_filled', 'Save Excel (interpolated batch)…'),
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="thermoq_batch_filled.xlsx",
        )
        if not path:
            return
        try:
            df_out = self._batch_dataframe_for_export(apply_newton_fill=True)
            if df_out is None:
                return
            df_out.to_excel(path, index=False)
            messagebox.showinfo(
                self.tr('dlg_success', 'Success'),
                self.tr('batch_saved', 'Saved: {path}').format(path=path),
            )
            self.batch_compute_status_label.config(
                text=self.tr('batch_saved', 'Saved: {path}').format(path=path),
                foreground="green",
            )
        except Exception as e:
            messagebox.showerror(
                self.tr('export_err_title', 'Export Error'),
                self.tr('export_fail_clean_xlsx', 'Failed to export Excel:\n{e}').format(e=str(e)),
            )

    @staticmethod
    def _liquidus_newton_forward_interpolation(f1, f2, f3):
        """Newton forward difference at x=0 from samples at x=1,2,3 (Liquidus Vector Plotter)."""
        if pd.isna(f1) or pd.isna(f2) or pd.isna(f3):
            return np.nan
        return 2.5 * f1 - 2.0 * f2 + 0.5 * f3

    @staticmethod
    def _liquidus_newton_from_axis_samples(w_samples, f_samples, w1_max=12.0, ap_rtol=0.025):
        """
        Extrapolate f(0) from the first three samples along a composition axis that lie on a uniform grid
        (same spacing), with the smallest w <= w1_max (wt% near a pure corner). Returns NaN if not found.
        """
        w_samples = np.asarray(w_samples, dtype=float)
        f_samples = np.asarray(f_samples, dtype=float)
        mask = np.isfinite(w_samples) & np.isfinite(f_samples) & (w_samples > 1e-9)
        w_samples = w_samples[mask]
        f_samples = f_samples[mask]
        if w_samples.size < 3:
            return np.nan
        order = np.argsort(w_samples)
        w_samples = w_samples[order]
        f_samples = f_samples[order]
        uw, uf = [], []
        i = 0
        while i < len(w_samples):
            w0 = w_samples[i]
            uw.append(w0)
            uf.append(f_samples[i])
            i += 1
            while i < len(w_samples) and abs(w_samples[i] - w0) < 1e-6:
                i += 1
        if len(uw) < 3:
            return np.nan
        uw = np.array(uw, dtype=float)
        uf = np.array(uf, dtype=float)
        for j in range(len(uw) - 2):
            w1, w2, w3 = uw[j], uw[j + 1], uw[j + 2]
            f1, f2, f3 = uf[j], uf[j + 1], uf[j + 2]
            if w1 > float(w1_max):
                break
            d1, d2 = w2 - w1, w3 - w2
            if d1 <= 0 or d2 <= 0:
                continue
            if abs(d1 - d2) > ap_rtol * max(abs(w2), 1.0):
                continue
            return ThermoQGUI._liquidus_newton_forward_interpolation(f1, f2, f3)
        return np.nan

    @staticmethod
    def _liquidus_rows_match_composition(df, idx, cols, atol=1e-4):
        """Boolean mask: rows whose composition columns match df.loc[idx] within atol."""
        m = pd.Series(True, index=df.index)
        for c in cols:
            v = pd.to_numeric(df.loc[idx, c], errors='coerce')
            vc = pd.to_numeric(df[c], errors='coerce')
            m &= np.isclose(vc, v, rtol=0.0, atol=atol, equal_nan=True)
        return m

    def _liquidus_clean_fill_dataframe(self, source_df, ex, ey):
        """
        Replicate 'Clean and fill data before plotting' from Liquidus Vector Plotter export path:
        T, all w(EL), 1/dwdT_L(EL@LIQUID) from dwdT_L (or use existing 1/dwdT columns);
        Newton steps at w≈0 edges using uniform triplets near zero; then fill each 1/dwdT_L column
        by linear interpolation along its own w(element) axis (fixed other compositions), with bfill/ffill
        inside each group so row order in P/batch tables does not matter.
        Returns cleaned DataFrame. Raises ValueError on missing columns.
        """
        ex = (ex or "").strip()
        ey = (ey or "").strip()
        if not ex or not ey:
            raise ValueError("need_xy")

        df = source_df.copy()
        df = df.rename(columns={c: c.strip() for c in df.columns})

        col_t = None
        for col in df.columns:
            if isinstance(col, str) and col.strip().upper() == 'T':
                col_t = col
                break
        if col_t is None:
            raise ValueError("no_T")

        w_cols = {}
        for col in df.columns:
            if isinstance(col, str):
                col_upper = col.strip().upper()
                match = re.match(r'^W\(([A-Z]+)\)$', col_upper)
                if match:
                    element = match.group(1).capitalize()
                    if element in PERIODIC_TABLE:
                        w_cols[element] = col

        inv_dwdt_cols = {}
        dwdt_cols = {}
        for col in df.columns:
            if not isinstance(col, str):
                continue
            col_upper = col.strip().upper()
            m_inv = re.match(r'^1/DWDT_L\(([A-Z]+)@LIQUID\)$', col_upper)
            if m_inv:
                element = m_inv.group(1).capitalize()
                if element in PERIODIC_TABLE:
                    inv_dwdt_cols[element] = col
            m_dw = re.match(r'^DWDT_L\(([A-Z]+)@LIQUID\)$', col_upper)
            if m_dw:
                element = m_dw.group(1).capitalize()
                if element in PERIODIC_TABLE:
                    dwdt_cols[element] = col

        for element, col in dwdt_cols.items():
            if element not in inv_dwdt_cols:
                inv_col_name = f"1/dwdT_L({element}@LIQUID)"
                dwdt_values = pd.to_numeric(df[col], errors='coerce')
                df[inv_col_name] = np.where(dwdt_values != 0, 1.0 / dwdt_values, np.nan)
                inv_dwdt_cols[element] = inv_col_name

        if ex not in w_cols or ey not in w_cols:
            avail = ', '.join(sorted(w_cols.keys()))
            raise ValueError(f"MISSING_W:{ex}:{ey}:{avail}")
        if ex not in inv_dwdt_cols or ey not in inv_dwdt_cols:
            miss = ex if ex not in inv_dwdt_cols else ey
            raise ValueError(f"MISSING_DWDT:{miss}")

        selected_cols = [col_t] + list(w_cols.values()) + list(inv_dwdt_cols.values())
        seen = set()
        selected_cols = [c for c in selected_cols if c not in seen and not seen.add(c)]
        df = df[selected_cols].copy()
        df = df.replace(r"^\s*$", np.nan, regex=True).dropna(how="all")

        col_wx = w_cols[ex]
        col_wy = w_cols[ey]
        col_inv_x = inv_dwdt_cols[ex]
        col_inv_y = inv_dwdt_cols[ey]
        other_w_cols = [w_cols[e] for e in sorted(w_cols.keys()) if e not in (ex, ey)]
        w_atol = 1e-4

        wx_vals = pd.to_numeric(df[col_wx], errors='coerce')
        wy_vals = pd.to_numeric(df[col_wy], errors='coerce')
        inv_x_vals = pd.to_numeric(df[col_inv_x], errors='coerce')
        inv_y_vals = pd.to_numeric(df[col_inv_y], errors='coerce')

        w1_max_x = 12.0
        pos_wx = wx_vals[np.isfinite(wx_vals) & (wx_vals > w_atol)]
        if len(pos_wx) > 0:
            w1_max_x = float(min(12.0, max(5.0, 0.35 * float(np.percentile(pos_wx, 15)))))
        w1_max_y = 12.0
        pos_wy = wy_vals[np.isfinite(wy_vals) & (wy_vals > w_atol)]
        if len(pos_wy) > 0:
            w1_max_y = float(min(12.0, max(5.0, 0.35 * float(np.percentile(pos_wy, 15)))))

        mask_step1 = (
            np.isclose(wx_vals, 0.0, atol=w_atol, rtol=0.0)
            & ~np.isclose(wy_vals, 0.0, atol=w_atol, rtol=0.0)
            & pd.isna(inv_x_vals)
        )
        for idx in df[mask_step1].index:
            fix_cols = [col_wy] + other_w_cols
            mfix = self._liquidus_rows_match_composition(df, idx, fix_cols, atol=w_atol)
            sub = df.loc[mfix & (wx_vals > w_atol)]
            if len(sub) < 3:
                continue
            w_s = pd.to_numeric(sub[col_wx], errors='coerce').values
            f_s = pd.to_numeric(sub[col_inv_x], errors='coerce').values
            interpolated = self._liquidus_newton_from_axis_samples(w_s, f_s, w1_max=w1_max_x)
            if not pd.isna(interpolated):
                df.loc[idx, col_inv_x] = interpolated

        inv_x_vals = pd.to_numeric(df[col_inv_x], errors='coerce')

        mask_step2 = (
            np.isclose(wy_vals, 0.0, atol=w_atol, rtol=0.0)
            & ~np.isclose(wx_vals, 0.0, atol=w_atol, rtol=0.0)
            & pd.isna(inv_y_vals)
        )
        for idx in df[mask_step2].index:
            fix_cols = [col_wx] + other_w_cols
            mfix = self._liquidus_rows_match_composition(df, idx, fix_cols, atol=w_atol)
            sub = df.loc[mfix & (wy_vals > w_atol)]
            if len(sub) < 3:
                continue
            w_s = pd.to_numeric(sub[col_wy], errors='coerce').values
            f_s = pd.to_numeric(sub[col_inv_y], errors='coerce').values
            interpolated = self._liquidus_newton_from_axis_samples(w_s, f_s, w1_max=w1_max_y)
            if not pd.isna(interpolated):
                df.loc[idx, col_inv_y] = interpolated

        inv_y_vals = pd.to_numeric(df[col_inv_y], errors='coerce')

        mask_step3a = (
            np.isclose(wx_vals, 0.0, atol=w_atol, rtol=0.0)
            & np.isclose(wy_vals, 0.0, atol=w_atol, rtol=0.0)
            & pd.isna(inv_x_vals)
        )
        for idx in df[mask_step3a].index:
            mfix = self._liquidus_rows_match_composition(df, idx, other_w_cols, atol=w_atol) if other_w_cols else pd.Series(True, index=df.index)
            sub = df.loc[mfix & np.isclose(wy_vals, 0.0, atol=w_atol, rtol=0.0) & (wx_vals > w_atol)]
            if len(sub) < 3:
                continue
            w_s = pd.to_numeric(sub[col_wx], errors='coerce').values
            f_s = pd.to_numeric(sub[col_inv_x], errors='coerce').values
            interpolated = self._liquidus_newton_from_axis_samples(w_s, f_s, w1_max=w1_max_x)
            if not pd.isna(interpolated):
                df.loc[idx, col_inv_x] = interpolated

        inv_x_vals = pd.to_numeric(df[col_inv_x], errors='coerce')

        mask_step3b = (
            np.isclose(wx_vals, 0.0, atol=w_atol, rtol=0.0)
            & np.isclose(wy_vals, 0.0, atol=w_atol, rtol=0.0)
            & pd.isna(inv_y_vals)
        )
        for idx in df[mask_step3b].index:
            mfix = self._liquidus_rows_match_composition(df, idx, other_w_cols, atol=w_atol) if other_w_cols else pd.Series(True, index=df.index)
            sub = df.loc[mfix & np.isclose(wx_vals, 0.0, atol=w_atol, rtol=0.0) & (wy_vals > w_atol)]
            if len(sub) < 3:
                continue
            w_s = pd.to_numeric(sub[col_wy], errors='coerce').values
            f_s = pd.to_numeric(sub[col_inv_y], errors='coerce').values
            interpolated = self._liquidus_newton_from_axis_samples(w_s, f_s, w1_max=w1_max_y)
            if not pd.isna(interpolated):
                df.loc[idx, col_inv_y] = interpolated

        def _fill_inv_along_element_axis(frame, elem, inv_col):
            col_w = w_cols[elem]
            gcols = [w_cols[ot] for ot in sorted(w_cols.keys()) if ot != elem]
            sort_order = gcols + [col_w]
            work = frame.sort_values(by=sort_order).reset_index(drop=True)
            if not gcols:
                s = pd.to_numeric(work[inv_col], errors='coerce')
                work[inv_col] = s.interpolate(method='linear', limit_direction='both').bfill().ffill()
                return work
            work[inv_col] = (
                work.groupby(gcols, sort=False, dropna=False)[inv_col]
                .transform(
                    lambda s: pd.to_numeric(s, errors='coerce')
                    .interpolate(method='linear', limit_direction='both')
                    .bfill()
                    .ffill()
                )
            )
            return work

        out = df
        for elem in sorted(inv_dwdt_cols.keys()):
            out = _fill_inv_along_element_axis(out, elem, inv_dwdt_cols[elem])

        return out

    def _batch_safe_fname_part(self, s, max_len=72):
        t = str(s).replace("/", "_").replace("\\", "_").replace(":", "_")
        return "".join(c if (c.isalnum() or c in " ._-+()[]%") else "_" for c in t)[:max_len]

    def _batch_plot_export_surface_file(self, df, ex, ey, zcol, viz, open_after=True, suppress_smooth_warn=False):
        """
        Write one batch surface/scatter plot for quantity zcol and visualization viz.
        Returns (out_path_or_None, err_code_or_None) where err_code is 'few_points', 'missing_xy', 'no_mpl', 'no_plotly', or exception text.
        """
        cx, cy = f"w_{ex}", f"w_{ey}"
        if cx not in df.columns or cy not in df.columns:
            return None, 'missing_xy'
        x = pd.to_numeric(df[cx], errors="coerce")
        y = pd.to_numeric(df[cy], errors="coerce")
        z = pd.to_numeric(df[zcol], errors="coerce")
        mask = x.notna() & y.notna() & z.notna()
        x = x.loc[mask].to_numpy(dtype=float)
        y = y.loc[mask].to_numpy(dtype=float)
        z = z.loc[mask].to_numpy(dtype=float)
        if len(x) < 2:
            return None, 'few_points'

        out_dir = self.batch_output_dir_var.get().strip()
        base_path = out_dir if out_dir and os.path.isdir(out_dir) else "."
        prefix = self.batch_output_prefix_var.get().strip() or "batch_calc"
        mode = self.batch_source_var.get()
        sz = self._batch_safe_fname_part(zcol)
        base = os.path.join(base_path, f"{prefix}_{mode}_{sz}")
        label_z = zcol
        smooth = float(self.batch_smoothness_var.get())

        self.batch_compute_status_label.config(text=self.tr('plot_status_smooth', 'Creating smooth surface...'), foreground="orange")
        self.root.update_idletasks()
        xi_grid, yi_grid, zi_grid = self.create_smooth_surface(x, y, z, grid_resolution=100, smoothness=smooth)
        if xi_grid is None and not suppress_smooth_warn:
            messagebox.showwarning(
                self.tr('plot_smooth_title', 'Smoothing Failed'),
                self.tr(
                    'plot_smooth_msg',
                    'Could not create smooth surface. Using triangulated surface instead.',
                ),
            )

        fmt = (self.batch_image_format_var.get() or "PNG").upper()
        ext_map = {"PNG": "png", "JPEG": "jpg", "JPG": "jpg", "GIF": "gif", "BMP": "bmp", "TIFF": "tif", "WEBP": "webp", "SVG": "svg", "PDF": "pdf"}
        ext = ext_map.get(fmt, "png")

        try:
            if viz == "2D Heatmap":
                if not MATPLOTLIB_AVAILABLE:
                    return None, 'no_mpl'
                plt.figure(figsize=(10, 8))
                plt.xlabel(f"w({ex}) (%)")
                plt.ylabel(f"w({ey}) (%)")
                if xi_grid is not None:
                    cf = plt.contourf(xi_grid, yi_grid, zi_grid, levels=50, cmap="coolwarm", alpha=1.0)
                    plt.colorbar(cf, label=label_z)
                else:
                    sc = plt.scatter(x, y, c=z, cmap="coolwarm", s=40, alpha=0.9)
                    plt.colorbar(sc, label=label_z)
                plt.grid(False)
                out_path = f"{base}_Heatmap.{ext}"
                plt.savefig(out_path, dpi=300, bbox_inches="tight")
                plt.close()
                if open_after:
                    self.batch_compute_status_label.config(text=self.tr('batch_saved', 'Saved: {path}').format(path=out_path), foreground="green")
                    self.open_file_and_offer_save_as(out_path, self.root)
                return out_path, None
            if viz == "3D Static":
                if not MATPLOTLIB_AVAILABLE:
                    return None, 'no_mpl'
                fig = plt.figure(figsize=(12, 10))
                ax = fig.add_subplot(111, projection="3d")
                if xi_grid is not None:
                    surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap="coolwarm", alpha=0.98, linewidth=0, antialiased=True, shade=True)
                    fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                else:
                    trisurf = ax.plot_trisurf(x, y, z, cmap="coolwarm", linewidth=0.0, antialiased=True, alpha=0.98)
                    fig.colorbar(trisurf, shrink=0.5, aspect=5, label=label_z)
                ax.set_xlabel(f"w({ex}) (%)")
                ax.set_ylabel(f"w({ey}) (%)")
                ax.set_zlabel(label_z)
                try:
                    ax.view_init(elev=float(self.batch_elev_var.get()), azim=float(self.batch_azim_var.get()))
                except Exception:
                    pass
                out_path = f"{base}_3d.{ext}"
                plt.savefig(out_path, dpi=300, bbox_inches="tight")
                plt.close()
                if open_after:
                    self.batch_compute_status_label.config(text=self.tr('batch_saved', 'Saved: {path}').format(path=out_path), foreground="green")
                    self.open_file_and_offer_save_as(out_path, self.root)
                return out_path, None
            if viz == "3D Rotation GIF":
                if not MATPLOTLIB_AVAILABLE:
                    return None, 'no_mpl'
                fig = plt.figure(figsize=(12, 10))
                ax = fig.add_subplot(111, projection="3d")
                if xi_grid is not None:
                    surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap="coolwarm", alpha=0.98, linewidth=0, antialiased=True, shade=True)
                    fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                else:
                    trisurf = ax.plot_trisurf(x, y, z, cmap="coolwarm", linewidth=0.0, antialiased=True, alpha=0.98)
                    fig.colorbar(trisurf, shrink=0.5, aspect=5, label=label_z)
                ax.set_xlabel(f"w({ex}) (%)")
                ax.set_ylabel(f"w({ey}) (%)")
                ax.set_zlabel(label_z)

                def _rotate(angle):
                    ax.view_init(azim=angle)
                    return [ax]

                try:
                    rotation_step = int(float(self.batch_gif_speed_var.get()))
                except Exception:
                    rotation_step = 5
                try:
                    interval_ms = int(float(self.batch_gif_interval_var.get()))
                except Exception:
                    interval_ms = 50
                try:
                    fps_val = int(float(self.batch_gif_fps_var.get()))
                except Exception:
                    fps_val = 20
                ani = animation.FuncAnimation(fig, _rotate, frames=range(0, 360, rotation_step), interval=interval_ms)
                out_path = f"{base}_3d_rotation.gif"
                ani.save(out_path, writer="pillow", fps=fps_val, dpi=100)
                plt.close()
                if open_after:
                    self.batch_compute_status_label.config(text=self.tr('batch_saved', 'Saved: {path}').format(path=out_path), foreground="green")
                    self.open_file_and_offer_save_as(out_path, self.root)
                return out_path, None
            # Plotly 3D
            out_path = f"{base}_3d_interactive.html"
            if not PLOTLY_AVAILABLE:
                return None, 'no_plotly'
            if xi_grid is not None:
                fig_plotly = go.Figure(
                    data=[
                        go.Surface(
                            x=xi_grid,
                            y=yi_grid,
                            z=zi_grid,
                            colorscale="RdBu",
                            reversescale=True,
                            opacity=0.98,
                            colorbar=dict(title=label_z),
                        )
                    ]
                )
            else:
                fig_plotly = go.Figure(
                    data=[
                        go.Scatter3d(
                            x=x,
                            y=y,
                            z=z,
                            mode="markers",
                            marker=dict(
                                size=3,
                                color=z,
                                colorscale="RdBu",
                                reversescale=True,
                                opacity=0.85,
                                colorbar=dict(title=label_z),
                            ),
                        )
                    ]
                )
            fig_plotly.update_layout(
                scene=dict(
                    xaxis_title=f"w({ex})",
                    yaxis_title=f"w({ey})",
                    zaxis_title=label_z,
                ),
                width=900,
                height=700,
            )
            fig_plotly.write_html(out_path)
            if open_after:
                self.batch_compute_status_label.config(text=self.tr('batch_saved', 'Saved: {path}').format(path=out_path), foreground="green")
                self.open_file_and_offer_save_as(out_path, self.root)
            return out_path, None
        except Exception as e:
            return None, str(e)

    def run_batch_plot_for_space(self):
        """2D/3D output from last_batch_results_df; Quantity (Z) = All runs every visualization for every numeric column."""
        df = self.last_batch_results_df
        if df is None or len(df) == 0:
            messagebox.showwarning(self.tr('dlg_warning', 'Warning'), self.tr('batch_need_compute', 'Please run “Compute batch” first.'))
            return

        ex = (self.batch_plot_x_var.get() or "").strip()
        ey = (self.batch_plot_y_var.get() or "").strip()
        zraw = (self.batch_z_var.get() or "").strip()
        if not ex or not ey:
            messagebox.showerror(self.tr('plot_elem_title', 'Element Selection'), self.tr('plot_select_xy', 'Please select X and Y elements first.'))
            return

        cx, cy = f"w_{ex}", f"w_{ey}"
        if cx not in df.columns or cy not in df.columns:
            messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr(
                    'batch_missing_wxy',
                    'Missing composition columns in batch table (expected "{wx}" and "{wy}").',
                ).format(wx=cx, wy=cy),
            )
            return

        if self._batch_is_z_all(zraw):
            zcols = self._batch_numeric_z_columns(df)
            if not zcols:
                messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('batch_no_numeric_z', 'No numeric Z column selected.'))
                return
            all_viz = ["2D Heatmap", "3D Static", "3D Rotation GIF", "Plotly 3D"]
            n_ok = 0
            errs = []
            first_combo = True
            for zc in zcols:
                for viz in all_viz:
                    path, err = self._batch_plot_export_surface_file(
                        df, ex, ey, zc, viz, open_after=False, suppress_smooth_warn=not first_combo,
                    )
                    first_combo = False
                    if path:
                        n_ok += 1
                    elif err and err not in ('few_points',):
                        errs.append(f"{zc} | {viz}: {err}")
            self.batch_compute_status_label.config(
                text=self.tr('batch_plot_all_done', 'Generated {n} plot file(s) in the output folder.').format(n=n_ok),
                foreground="green",
            )
            body = self.tr('batch_plot_all_done', 'Generated {n} plot file(s) in the output folder.').format(n=n_ok)
            if errs:
                detail = "\n".join(errs[:12])
                if len(errs) > 12:
                    detail += "\n…"
                body += "\n\n" + self.tr('batch_plot_all_errors', 'Some plots failed:\n{detail}').format(detail=detail)
                messagebox.showwarning(self.tr('dlg_success', 'Success'), body)
            else:
                messagebox.showinfo(self.tr('dlg_success', 'Success'), body)
            return

        zcol = zraw
        if not zcol or zcol not in df.columns:
            messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('batch_no_numeric_z', 'No numeric Z column selected.'))
            return

        viz = self.batch_viz_var.get()
        try:
            path, err = self._batch_plot_export_surface_file(df, ex, ey, zcol, viz, open_after=True, suppress_smooth_warn=False)
            if err == 'few_points':
                messagebox.showerror(self.tr('plot_no_data_title', 'No Data'), self.tr('plot_no_valid', 'No valid data points after filtering.'))
                return
            if err == 'missing_xy':
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr(
                        'batch_missing_wxy',
                        'Missing composition columns in batch table (expected "{wx}" and "{wy}").',
                    ).format(wx=cx, wy=cy),
                )
                return
            if err == 'no_mpl':
                msg = self.tr('plot_dep_3d', 'Matplotlib required.') if viz != "2D Heatmap" else self.tr('plot_dep_2d', 'Matplotlib required.')
                messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), msg)
                return
            if err == 'no_plotly':
                messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), "Plotly not installed.")
                return
            if err:
                messagebox.showerror(
                    self.tr('plot_failed', 'Plotting Failed'),
                    self.tr('plot_err_simple', 'An error occurred: {e}').format(e=str(err)),
                )
                return
            if not path:
                messagebox.showerror(
                    self.tr('plot_failed', 'Plotting Failed'),
                    self.tr('plot_err_simple', 'An error occurred: {e}').format(e='unknown'),
                )
        except Exception as e:
            import traceback
            messagebox.showerror(
                self.tr('plot_failed', 'Plotting Failed'),
                self.tr('plot_err_simple', 'An error occurred: {e}').format(e=str(e)) + "\n" + traceback.format_exc(),
            )

    def _register_tool_lang_refresh(self, callback):
        if callback not in self._tool_lang_refresh_callbacks:
            self._tool_lang_refresh_callbacks.append(callback)

    def _unregister_tool_lang_refresh(self, callback):
        try:
            self._tool_lang_refresh_callbacks.remove(callback)
        except (ValueError, AttributeError):
            pass

    def set_language(self, lang):
        try:
            if lang not in self.texts:
                return
            self.language = lang
            t = self.texts[lang]

            # Rebuild menubar cascades to avoid platform-specific label issues
            try:
                end_index = self.menu_bar.index('end')
                if end_index is not None:
                    for i in reversed(range(end_index + 1)):
                        self.menu_bar.delete(i)
            except Exception:
                pass
            # Re-add cascades with new labels
            self.menu_bar.add_cascade(label=t['menu_file'], menu=self.file_menu)
            self.menu_bar.add_cascade(label=t['menu_import'], menu=self.import_menu)
            self.menu_bar.add_cascade(label=t['menu_plot'], menu=self.plot_menu)
            self.menu_bar.add_cascade(label=t['menu_tools'], menu=self.tools_menu)
            self.menu_bar.add_cascade(label=t['menu_help'], menu=self.help_menu)

            # Rebuild File menu
            try:
                end_index = self.file_menu.index('end')
                if end_index is not None:
                    for i in reversed(range(end_index + 1)):
                        self.file_menu.delete(i)
            except Exception:
                pass
            self.file_menu.add_command(label=t['file_exit'], command=self.root.quit)

            # Rebuild Import menu
            try:
                end_index = self.import_menu.index('end')
                if end_index is not None:
                    for i in reversed(range(end_index + 1)):
                        self.import_menu.delete(i)
            except Exception:
                pass
            self.import_menu.add_command(label=t['import_pandat'], command=self.open_pandat_import)

            # Rebuild Plot menu
            try:
                end_index = self.plot_menu.index('end')
                if end_index is not None:
                    for i in reversed(range(end_index + 1)):
                        self.plot_menu.delete(i)
            except Exception:
                pass
            self.plot_menu.add_command(label=t['plot_phase'], command=self.open_phase_surface_plotter)
            self.plot_menu.add_command(label=t['plot_qtrue'], command=self.open_q_value_plotter)
            self.plot_menu.add_command(label=t['plot_liqvec'], command=self.open_liquidus_vector_plotter)
            self.plot_menu.add_command(label=t['plot_kvec'], command=self.open_partition_vector_plotter)
            self.plot_menu.add_command(label=t['plot_t0surf'], command=self.open_t_zero_surface_plotter)

            # Rebuild Tools menu
            try:
                end_index = self.tools_menu.index('end')
                if end_index is not None:
                    for i in reversed(range(end_index + 1)):
                        self.tools_menu.delete(i)
            except Exception:
                pass
            self.tools_menu.add_command(label=t['tools_converter'], command=self.open_composition_converter)
            self.tools_menu.add_separator()
            self.tools_menu.add_command(label=t['tools_generate'], command=self.open_therocalc_generator)
            self.tools_menu.add_command(label=t['tools_extract_exp'], command=self.open_exp_data_processor)
            self.tools_menu.add_separator()
            self.tools_menu.add_command(label=t['tools_extract_pandat'], command=self.open_extract_pandat_results)

            # Rebuild Help menu and Language submenu
            try:
                end_index = self.help_menu.index('end')
                if end_index is not None:
                    for i in reversed(range(end_index + 1)):
                        self.help_menu.delete(i)
            except Exception:
                pass
            # Rebuild Language submenu
            try:
                end_index = self.lang_menu.index('end')
                if end_index is not None:
                    for i in reversed(range(end_index + 1)):
                        self.lang_menu.delete(i)
            except Exception:
                pass
            self.lang_menu.add_command(label=t['help_english'], command=lambda: self.set_language('en'))
            self.lang_menu.add_command(label=t['help_chinese'], command=lambda: self.set_language('zh'))
            self.help_menu.add_cascade(label=t['help_language'], menu=self.lang_menu)
            self.help_menu.add_separator()
            self.help_menu.add_command(label=t['help_example'], command=self.open_example_folder)

            # Main window buttons
            self.calculate_button.config(text=t['btn_calculate'])
            self.show_results_button.config(text=t['btn_show_results'])
            if hasattr(self, 'element_selector'):
                self.element_selector.refresh_from_language()
            if hasattr(self, '_refresh_calculate_main_language'):
                try:
                    self._refresh_calculate_main_language()
                except Exception:
                    pass
            refresh_k = getattr(self, '_partition_plotter_lang_refresh', None)
            if callable(refresh_k):
                try:
                    refresh_k()
                except Exception:
                    pass
            for cb in list(getattr(self, '_tool_lang_refresh_callbacks', []) or []):
                try:
                    cb()
                except tk.TclError:
                    pass
                except Exception:
                    pass
        except Exception as e:
            print(f"Language switch error: {e}")

    def tr(self, key, default):
        """Translate a UI string based on current language, fallback to default."""
        try:
            lang_dict = self.texts.get(self.language, {})
            return lang_dict.get(key, default)
        except Exception:
            return default

    def _build_calc_result_report(
        self,
        composition,
        results,
        errors,
        used_interp,
        float_fmt,
        *,
        show_missing_na=False,
        include_component_section_title=False,
        use_short_interp_note=False,
    ):
        """Build multiline text for Calculate dialog, Show Results, and Save (txt/dat).

        use_short_interp_note: in results window, use res_interp_note (one line) instead of calc_interp_note.
        """
        fs = float_fmt if isinstance(float_fmt, str) and float_fmt.startswith('.') else '.6f'
        na = self.tr('res_not_avail', 'Not available')
        lines = []
        lines.append(self.tr('calc_results_header', 'Calculation Results'))
        lines.append('')
        comp_label = self.tr('calc_composition_label', 'Composition:')
        lines.append(
            f"{comp_label} "
            + ', '.join([f'{elem}: {comp:.2f}wt%' for elem, comp in composition.items()])
        )
        lines.append('')
        if used_interp:
            if use_short_interp_note:
                lines.append(self.tr('res_interp_note', '').rstrip())
            else:
                lines.append(self.tr('calc_interp_note', '').rstrip())
            lines.append('')

        def _qtrue_lines():
            if show_missing_na:
                if 'Qtrue (Lever)' in results:
                    lines.append(f"Qtrue (Lever): {results['Qtrue (Lever)']:{fs}}")
                else:
                    lines.append(f"Qtrue (Lever): {na}")
                if 'Qtrue (Scheil)' in results:
                    lines.append(f"Qtrue (Scheil): {results['Qtrue (Scheil)']:{fs}}")
                else:
                    lines.append(f"Qtrue (Scheil): {na}")
            else:
                if 'Qtrue (Lever)' in results:
                    lines.append(f"Qtrue (Lever): {results['Qtrue (Lever)']:{fs}}")
                if 'Qtrue (Scheil)' in results:
                    lines.append(f"Qtrue (Scheil): {results['Qtrue (Scheil)']:{fs}}")

        _qtrue_lines()

        elems_comp = self._component_result_elements(results)
        if include_component_section_title and elems_comp:
            lines.append('')
            lines.append(self.tr('res_component_block', 'Component Results'))

        for elem in elems_comp:
            if f'Q ({elem} Lever)' in results:
                lines.append(f"Q ({elem} Lever): {results[f'Q ({elem} Lever)']:{fs}}")
            if f'P ({elem} Lever)' in results:
                lines.append(f"P ({elem} Lever): {results[f'P ({elem} Lever)']:{fs}}")
            if f'Beta ({elem} Lever)' in results:
                lines.append(f"Beta ({elem} Lever): {results[f'Beta ({elem} Lever)']:{fs}}")
            if f'Q ({elem} Scheil)' in results:
                lines.append(f"Q ({elem} Scheil): {results[f'Q ({elem} Scheil)']:{fs}}")
            if f'P ({elem} Scheil)' in results:
                lines.append(f"P ({elem} Scheil): {results[f'P ({elem} Scheil)']:{fs}}")
            if f'Beta ({elem} Scheil)' in results:
                lines.append(f"Beta ({elem} Scheil): {results[f'Beta ({elem} Scheil)']:{fs}}")

        if show_missing_na:
            lines.append('')
            if 'ΔT' in results:
                lines.append(f"ΔT: {results['ΔT']:{fs}}")
            else:
                lines.append(f"ΔT: {na}")
            if 'ΔTs' in results:
                lines.append(f"ΔTs: {results['ΔTs']:{fs}}")
            else:
                lines.append(f"ΔTs: {na}")
        else:
            if 'ΔT' in results:
                lines.append(f"ΔT: {results['ΔT']:{fs}}")
            if 'ΔTs' in results:
                lines.append(f"ΔTs: {results['ΔTs']:{fs}}")

        if errors:
            lines.append('')
            lines.append(self.tr('calc_errors_header', 'Errors:'))
            lines.extend(errors)
        return '\n'.join(lines)

    def _save_calculation_results_to_file(self, path, composition, results, errors, used_interp):
        """Save results to .xlsx, .csv, .txt, or .dat (UTF-8 with BOM for csv/excel-friendly)."""
        ext = os.path.splitext(path)[1].lower()
        rows_kv = []
        for elem in sorted(composition.keys()):
            comp = composition[elem]
            rows_kv.append({'Quantity': f'w({elem})', 'Value': comp, 'Unit': 'wt%'})
        if used_interp:
            rows_kv.append({'Quantity': 'Note', 'Value': self.tr('calc_interp_note', '').strip(), 'Unit': ''})
        for key in sorted(results.keys()):
            val = results[key]
            try:
                fv = float(val)
                rows_kv.append({'Quantity': key, 'Value': fv, 'Unit': ''})
            except (TypeError, ValueError):
                rows_kv.append({'Quantity': key, 'Value': val, 'Unit': ''})
        if errors:
            for i, err in enumerate(errors):
                rows_kv.append({'Quantity': f"Error_{i+1}", 'Value': err, 'Unit': ''})
        df = pd.DataFrame(rows_kv)
        if ext in ('.xlsx',):
            df.to_excel(path, index=False, engine='openpyxl')
        elif ext in ('.csv',):
            df.to_csv(path, index=False, encoding='utf-8-sig')
        elif ext in ('.txt', '.dat'):
            text = self._build_calc_result_report(composition, results, errors, used_interp, '.8f')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text)
                if not text.endswith('\n'):
                    fh.write('\n')
        else:
            raise ValueError(f"Unsupported extension: {ext}")

    @staticmethod
    def _present_tool_window(win, master):
        """Show a tool Toplevel on top without grab_set().
        On Windows, grab_set() modal grab often blocks minimizing the window."""
        win.lift(master)
        def _focus():
            try:
                if win.winfo_exists():
                    win.focus_set()
            except tk.TclError:
                pass
        win.after(80, _focus)

    def open_example_folder(self):
        try:
            path = r"c:\Users\17868\OneDrive\文档\GitHub\ThermoQ\Example"
            if not os.path.exists(path):
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('example_not_found', 'Example folder not found!'),
                )
                return
            if platform.system() == 'Windows':
                os.startfile(path)
            else:
                webbrowser.open(path)
        except Exception as e:
            messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr('example_open_fail', 'Failed to open Example folder:\n{e}').format(e=str(e)),
            )

    def _bulk_composition_from_pandat_row(self, df, row_index):
        """Build wt% composition dict from a Pandat row using plain w(EL) columns (no @phase)."""
        comp = {}
        if df is None or row_index < 0 or row_index >= len(df):
            return comp
        row = df.iloc[row_index]
        for col in df.columns:
            if not isinstance(col, str):
                continue
            col_st = col.strip()
            if '@' in col_st:
                continue
            m = re.match(r"^w\(\s*([A-Za-z]{1,3})\s*\)$", col_st, re.I)
            if not m:
                continue
            raw = m.group(1)
            symbol = raw[:1].upper() + raw[1:].lower()
            if symbol not in PERIODIC_TABLE:
                continue
            val = self._pandat_wt_from_cell(row[col])
            try:
                val = float(val)
            except (TypeError, ValueError):
                continue
            if not np.isfinite(val):
                continue
            comp[symbol] = val
        return comp

    def _compute_thermoq_results(self, wt_composition, element_order, etc_p, etc_ts, etc_ps, etc_tss):
        """Core Calculate physics: Qtrue, Q/P/Beta per element, ΔT, ΔTs. Returns (results, errors, used_interp)."""
        results = {}
        errors = []
        interp_used = [False]

        def _mark_interp(mode):
            if mode != 'exact':
                interp_used[0] = True

        # 1. ΔT = T(P) - T(Ts)
        delta_t = None
        try:
            if self.pandat_p_data is not None and self.pandat_ts_data is not None:
                t_col_p = self._resolve_pandat_column(self.pandat_p_data.columns, 'T')
                t_col_ts = self._resolve_pandat_column(self.pandat_ts_data.columns, 'T')
                if t_col_p and t_col_ts:
                    t_p, m1 = self._pandat_interp_scalar_column(
                        wt_composition, self.pandat_p_data, t_col_p, etc_p, element_order
                    )
                    t_ts, m2 = self._pandat_interp_scalar_column(
                        wt_composition, self.pandat_ts_data, t_col_ts, etc_ts, element_order
                    )
                    _mark_interp(m1)
                    _mark_interp(m2)
                    if t_p is not None and t_ts is not None:
                        delta_t = float(t_p) - float(t_ts)
                        results['ΔT'] = delta_t
        except Exception as e:
            errors.append(f"ΔT calculation failed: {str(e)}")

        # 2. ΔTs = T(P-S) - T(Ts-S)
        delta_ts = None
        try:
            if self.pandat_p_s_data is not None and self.pandat_ts_s_data is not None and etc_ps and etc_tss:
                t_col_p_s = self._resolve_pandat_column(self.pandat_p_s_data.columns, 'T')
                t_col_ts_s = self._resolve_pandat_column(self.pandat_ts_s_data.columns, 'T')
                if t_col_p_s and t_col_ts_s:
                    t_p_s, m1 = self._pandat_interp_scalar_column(
                        wt_composition, self.pandat_p_s_data, t_col_p_s, etc_ps, element_order
                    )
                    t_ts_s, m2 = self._pandat_interp_scalar_column(
                        wt_composition, self.pandat_ts_s_data, t_col_ts_s, etc_tss, element_order
                    )
                    _mark_interp(m1)
                    _mark_interp(m2)
                    if t_p_s is not None and t_ts_s is not None:
                        delta_ts = float(t_p_s) - float(t_ts_s)
                        results['ΔTs'] = delta_ts
        except Exception as e:
            errors.append(f"ΔTs calculation failed: {str(e)}")

        # 3. Lever / P file
        try:
            cols = self.pandat_p_data.columns
            q_col = self.pandat_q_col
            solid_phase = self.pandat_solid_phase
            if solid_phase is None:
                parsed = self._parse_pandat_phases_from_df(self.pandat_p_data)
                solid_phase = parsed['solid_phase']
                q_col = parsed['q_col']

            q_col_res = self._resolve_pandat_column(cols, q_col) if q_col else None
            if q_col_res:
                q_lever, mq = self._pandat_interp_scalar_column(
                    wt_composition, self.pandat_p_data, q_col_res, etc_p, element_order
                )
                _mark_interp(mq)
                if q_lever is not None:
                    results['Qtrue (Lever)'] = float(q_lever)

            elem_list = self.available_elements if self.available_elements else []
            for elem in elem_list:
                elem_upper = elem.upper()
                col_w = self._resolve_pandat_column(cols, f'w({elem_upper})')
                col_solid = self._resolve_pandat_column(cols, f'w({elem_upper}@{solid_phase})') if solid_phase else None
                col_liq = self._resolve_pandat_column(cols, f'w({elem_upper}@LIQUID)')
                col_slope, slope_is_inverse = self._resolve_pandat_slope_column(cols, elem_upper)
                if not col_solid:
                    continue
                if not all([col_w, col_solid, col_liq, col_slope]):
                    continue
                w, mw = self._pandat_interp_scalar_column(
                    wt_composition, self.pandat_p_data, col_w, etc_p, element_order
                )
                w_solid, ms = self._pandat_interp_scalar_column(
                    wt_composition, self.pandat_p_data, col_solid, etc_p, element_order
                )
                w_liq, ml = self._pandat_interp_scalar_column(
                    wt_composition, self.pandat_p_data, col_liq, etc_p, element_order
                )
                raw_slope, mr = self._pandat_interp_scalar_column(
                    wt_composition, self.pandat_p_data, col_slope, etc_p, element_order
                )
                for _m in (mw, ms, ml, mr):
                    _mark_interp(_m)
                if w is None or w_solid is None or w_liq is None or raw_slope is None:
                    continue
                w = float(w)
                w_solid = float(w_solid)
                w_liq = float(w_liq)
                raw_slope = float(raw_slope)
                if slope_is_inverse:
                    slope = 1.0 / (100.0 * raw_slope) if raw_slope and raw_slope != 0 else 0.0
                else:
                    slope = raw_slope
                if w_liq != 0 and slope != 0 and not np.isnan(slope):
                    ratio = w_solid / w_liq
                    q_comp = (ratio - 1) * (1 / slope) * 0.01 * w
                    results[f'Q ({elem} Lever)'] = q_comp
                    if ratio != 0:
                        p_comp = q_comp / ratio
                        results[f'P ({elem} Lever)'] = p_comp
                    if delta_t is not None and delta_t != 0:
                        beta_comp = (q_comp / delta_t) - ratio
                        results[f'Beta ({elem} Lever)'] = beta_comp
        except Exception as e:
            errors.append(f"Lever calculation failed: {str(e)}")

        # 4. Scheil / P-S file
        if self.pandat_p_s_data is not None and etc_ps is not None:
            try:
                cols_s = self.pandat_p_s_data.columns
                q_col_s = self.pandat_q_col
                solid_phase_s = self.pandat_solid_phase
                if solid_phase_s is None:
                    parsed_s = self._parse_pandat_phases_from_df(self.pandat_p_s_data)
                    solid_phase_s = parsed_s['solid_phase']
                    q_col_s = parsed_s['q_col']

                q_col_s_res = self._resolve_pandat_column(cols_s, q_col_s) if q_col_s else None
                if q_col_s_res:
                    q_scheil, mq = self._pandat_interp_scalar_column(
                        wt_composition, self.pandat_p_s_data, q_col_s_res, etc_ps, element_order
                    )
                    _mark_interp(mq)
                    if q_scheil is not None:
                        results['Qtrue (Scheil)'] = float(q_scheil)

                elem_list_s = self.available_elements if self.available_elements else []
                for elem in elem_list_s:
                    elem_upper = elem.upper()
                    col_w = self._resolve_pandat_column(cols_s, f'w({elem_upper})')
                    col_solid = self._resolve_pandat_column(cols_s, f'w({elem_upper}@{solid_phase_s})') if solid_phase_s else None
                    col_liq = self._resolve_pandat_column(cols_s, f'w({elem_upper}@LIQUID)')
                    col_slope, slope_is_inverse = self._resolve_pandat_slope_column(cols_s, elem_upper)
                    if not col_solid:
                        continue
                    if not all([col_w, col_solid, col_liq, col_slope]):
                        continue
                    w, mw = self._pandat_interp_scalar_column(
                        wt_composition, self.pandat_p_s_data, col_w, etc_ps, element_order
                    )
                    w_solid, ms = self._pandat_interp_scalar_column(
                        wt_composition, self.pandat_p_s_data, col_solid, etc_ps, element_order
                    )
                    w_liq, ml = self._pandat_interp_scalar_column(
                        wt_composition, self.pandat_p_s_data, col_liq, etc_ps, element_order
                    )
                    raw_slope, mr = self._pandat_interp_scalar_column(
                        wt_composition, self.pandat_p_s_data, col_slope, etc_ps, element_order
                    )
                    for _m in (mw, ms, ml, mr):
                        _mark_interp(_m)
                    if w is None or w_solid is None or w_liq is None or raw_slope is None:
                        continue
                    w = float(w)
                    w_solid = float(w_solid)
                    w_liq = float(w_liq)
                    raw_slope = float(raw_slope)
                    if slope_is_inverse:
                        slope = 1.0 / (100.0 * raw_slope) if raw_slope and raw_slope != 0 else 0.0
                    else:
                        slope = raw_slope
                    if w_liq != 0 and slope != 0 and not np.isnan(slope):
                        ratio = w_solid / w_liq
                        q_comp = (ratio - 1) * (1 / slope) * 0.01 * w
                        results[f'Q ({elem} Scheil)'] = q_comp
                        if ratio != 0:
                            p_comp = q_comp / ratio
                            results[f'P ({elem} Scheil)'] = p_comp
                        if delta_ts is not None and delta_ts != 0:
                            beta_comp = (q_comp / delta_ts) - ratio
                            results[f'Beta ({elem} Scheil)'] = beta_comp
            except Exception as e:
                errors.append(f"Scheil calculation failed: {str(e)}")

        return results, list(errors), bool(interp_used[0])

    def calculate(self):
        # Get the selected elements and their compositions
        composition = self.element_selector.get_composition()
        
        # Validate composition
        if not composition:
            messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr('calc_need_element', 'Please select at least one element!'),
            )
            return
        
        # Check if Pandat data is loaded
        if self.pandat_p_data is None or self.pandat_ts_data is None:
            messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr('calc_need_pandat', "Please import Pandat data first using 'Import > Pandat to ThermoQ'!"),
            )
            return
        
        # Composition is already in weight percent (wt%)
        wt_composition = composition
        
        # Validate composition sum equals 100%
        total_composition = sum(wt_composition.values())
        if abs(total_composition - 100.0) > 0.01:  # Allow small floating point errors
            messagebox.showerror(
                self.tr('calc_err_title', 'Calculation Error'),
                self.tr(
                    'calc_err_total_comp',
                    'Total composition must equal 100%! Current total: {total:.2f}%',
                ).format(total=total_composition),
            )
            return
        
        # Perform calculations: Q, ΔT, ΔTs, Beta (with composition range check + Newton DD interpolation)
        element_order = sorted(wt_composition.keys())
        try:
            etc_p = self._pandat_element_to_col(wt_composition, self.pandat_p_data)
            etc_ts = self._pandat_element_to_col(wt_composition, self.pandat_ts_data)
            range_errs = []
            range_errs.extend(
                self._pandat_composition_range_errors(wt_composition, self.pandat_p_data, etc_p, 'P.xlsx (Lever)')
            )
            range_errs.extend(
                self._pandat_composition_range_errors(wt_composition, self.pandat_ts_data, etc_ts, 'Ts.xlsx (Lever)')
            )
            etc_ps = None
            etc_tss = None
            if self.pandat_p_s_data is not None:
                etc_ps = self._pandat_element_to_col(wt_composition, self.pandat_p_s_data)
                range_errs.extend(
                    self._pandat_composition_range_errors(wt_composition, self.pandat_p_s_data, etc_ps, 'P-S.xlsx (Scheil)')
                )
            if self.pandat_ts_s_data is not None:
                etc_tss = self._pandat_element_to_col(wt_composition, self.pandat_ts_s_data)
                range_errs.extend(
                    self._pandat_composition_range_errors(wt_composition, self.pandat_ts_s_data, etc_tss, 'Ts-S.xlsx (Scheil)')
                )
        except ValueError as e:
            messagebox.showerror(self.tr('calc_pandat_col_title', 'Pandat columns'), str(e))
            return

        if range_errs:
            messagebox.showerror(
                self.tr('calc_range_title', 'Composition outside tabulated range'),
                self.tr(
                    'calc_range_body',
                    'Each element must lie within the min–max of w(element) in each loaded file:\n\n',
                )
                + "\n".join(range_errs),
            )
            return

        try:
            results, errors, interp_used = self._compute_thermoq_results(
                wt_composition, element_order, etc_p, etc_ts, etc_ps, etc_tss
            )

            # Store result for display / save
            self.last_result = {
                'type': 'q_delta_t_delta_ts',
                'composition': wt_composition,
                'results': results,
                'used_interpolation': bool(interp_used),
                'errors': list(errors),
            }
            
            result_msg = self._build_calc_result_report(
                wt_composition, results, errors, interp_used, '.4f'
            )
            
            # Show result
            if results:
                messagebox.showinfo(self.tr('calc_msg_title', 'Calculation Result'), result_msg)
            else:
                error_msg = self.tr('calc_no_results_body', 'No results calculated.')
                if errors:
                    error_msg += '\n\n' + self.tr('calc_errors_header', 'Errors:') + '\n' + '\n'.join(errors)
                messagebox.showerror(self.tr('calc_err_title', 'Calculation Error'), error_msg)
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror(
                self.tr('calc_err_title', 'Calculation Error'),
                self.tr('calc_failed_detail', 'Failed to calculate: {e}\n\nDetails:\n{details}').format(
                    e=str(e), details=error_details
                ),
            )

    def show_results(self):
        """Display calculation results in a window (language-aware; optional save to xlsx/csv/txt/dat)."""
        if not hasattr(self, 'last_result') or self.last_result is None:
            messagebox.showwarning(
                self.tr('res_warn_no_results_title', 'No Results'),
                self.tr('res_warn_no_results_msg', 'Please calculate first before showing results!'),
            )
            return
        
        results_window = tk.Toplevel(self.root)
        results_window.title(self.tr('res_win_title', 'Calculation Results'))
        results_window.geometry("640x520")
        self._present_tool_window(results_window, self.root)
        
        main_frame = ttk.Frame(results_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(
            main_frame,
            text=self.tr('res_win_title', 'Calculation Results'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 10))
        
        results_frame = ttk.LabelFrame(
            main_frame,
            text=self.tr('res_frame_title', 'Results'),
            padding="15",
        )
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        text_frame = ttk.Frame(results_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        results_text = tk.Text(text_frame, height=16, width=64, wrap=tk.WORD, font=('Courier', 10))
        results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=results_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        results_text.configure(yscrollcommand=scrollbar.set)
        
        composition = self.last_result.get('composition', {})
        results = self.last_result.get('results', {})
        errors = self.last_result.get('errors', [])
        used_interp = self.last_result.get('used_interpolation', False)
        
        if results or errors:
            body = self._build_calc_result_report(
                composition,
                results,
                errors,
                used_interp,
                '.6f',
                show_missing_na=True,
                include_component_section_title=True,
                use_short_interp_note=True,
            )
            results_text.insert("1.0", body)
        else:
            results_text.insert("1.0", self.tr('res_no_data_msg', 'No results available.'))
        
        results_text.config(state=tk.DISABLED)
        
        btn_frame = ttk.Frame(main_frame)
        
        def save_results():
            path = filedialog.asksaveasfilename(
                parent=results_window,
                title=self.tr('res_save_title', 'Save calculation results'),
                defaultextension='.xlsx',
                filetypes=[
                    ('Excel workbook', '*.xlsx'),
                    ('CSV', '*.csv'),
                    ('Text file', '*.txt'),
                    ('DAT file', '*.dat'),
                    ('All files', '*.*'),
                ],
            )
            if not path:
                return
            try:
                self._save_calculation_results_to_file(
                    path, composition, results, errors, used_interp
                )
                messagebox.showinfo(
                    self.tr('calc_msg_title', 'Calculation Result'),
                    self.tr('res_save_ok', 'Results saved successfully.'),
                    parent=results_window,
                )
            except Exception as ex:
                messagebox.showerror(
                    self.tr('calc_err_title', 'Calculation Error'),
                    f"{self.tr('res_save_fail', 'Failed to save results.')}\n{ex}",
                    parent=results_window,
                )
        
        ttk.Button(btn_frame, text=self.tr('res_save', 'Save results…'), command=save_results).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Button(btn_frame, text=self.tr('res_close', 'Close'), command=results_window.destroy).pack(
            side=tk.LEFT, padx=8
        )
        btn_frame.pack(pady=10)
        
    def open_pandat_import(self):
        # Create a new window for Pandat import
        import_window = tk.Toplevel(self.root)
        import_window.title(self.tr('pandat_win_title', 'Pandat to ThermoQ'))
        import_window.geometry("600x500")
        self._present_tool_window(import_window, self.root)

        # Create main frame with scrollable area
        canvas = tk.Canvas(import_window)
        scrollbar = ttk.Scrollbar(import_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        main_frame = scrollable_frame
        
        # Information label
        info_label = ttk.Label(
            main_frame,
            text=self.tr(
                'pandat_note',
                'Note: P/Ts files are for Equilibrium (Lever) solidification.\nP-S/Ts-S files are for Scheil solidification.',
            ),
            foreground="blue",
            font=('Arial', 9),
        )
        info_label.pack(pady=5)
        
        # P file selection (Equilibrium/Lever solidification)
        p_frame = ttk.LabelFrame(
            main_frame,
            text=self.tr('pandat_frame_p', 'P File (Equilibrium/Lever Solidification - Liquidus Data)'),
            padding="10",
        )
        p_frame.pack(fill=tk.X, pady=5)
        
        p_file_var = tk.StringVar()
        p_entry = ttk.Entry(p_frame, textvariable=p_file_var, width=60)
        p_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_p_file():
            file_path = filedialog.askopenfilename(
                title=self.tr('pandat_fd_p', 'Select P File'),
                filetypes=[
                    (self.tr('pandat_fd_excel', 'Excel files'), "*.xls *.xlsx"),
                    ("XLS", "*.xls"),
                    ("XLSX", "*.xlsx"),
                ],
            )
            if file_path:
                p_file_var.set(file_path)
        
        ttk.Button(p_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_p_file).pack(side=tk.RIGHT, padx=5)
        
        # Ts file selection (Equilibrium/Lever solidification)
        ts_frame = ttk.LabelFrame(
            main_frame,
            text=self.tr('pandat_frame_ts', 'Ts File (Equilibrium/Lever Solidification - Solidus Temperature)'),
            padding="10",
        )
        ts_frame.pack(fill=tk.X, pady=5)
        
        ts_file_var = tk.StringVar()
        ts_entry = ttk.Entry(ts_frame, textvariable=ts_file_var, width=60)
        ts_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_ts_file():
            file_path = filedialog.askopenfilename(
                title=self.tr('pandat_fd_ts', 'Select Ts File'),
                filetypes=[
                    (self.tr('pandat_fd_excel', 'Excel files'), "*.xls *.xlsx"),
                    ("XLS", "*.xls"),
                    ("XLSX", "*.xlsx"),
                ],
            )
            if file_path:
                ts_file_var.set(file_path)
        
        ttk.Button(ts_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_ts_file).pack(side=tk.RIGHT, padx=5)
        
        # P-S file selection (Scheil solidification)
        p_s_frame = ttk.LabelFrame(
            main_frame,
            text=self.tr('pandat_frame_ps', 'P-S File (Scheil Solidification - Liquidus Data)'),
            padding="10",
        )
        p_s_frame.pack(fill=tk.X, pady=5)
        
        p_s_file_var = tk.StringVar()
        p_s_entry = ttk.Entry(p_s_frame, textvariable=p_s_file_var, width=60)
        p_s_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_p_s_file():
            file_path = filedialog.askopenfilename(
                title=self.tr('pandat_fd_ps', 'Select P-S File'),
                filetypes=[
                    (self.tr('pandat_fd_excel', 'Excel files'), "*.xls *.xlsx"),
                    ("XLS", "*.xls"),
                    ("XLSX", "*.xlsx"),
                ],
            )
            if file_path:
                p_s_file_var.set(file_path)
        
        ttk.Button(p_s_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_p_s_file).pack(side=tk.RIGHT, padx=5)
        
        # Ts-S file selection (Scheil solidification)
        ts_s_frame = ttk.LabelFrame(
            main_frame,
            text=self.tr('pandat_frame_tss', 'Ts-S File (Scheil Solidification - Solidus Temperature)'),
            padding="10",
        )
        ts_s_frame.pack(fill=tk.X, pady=5)
        
        ts_s_file_var = tk.StringVar()
        ts_s_entry = ttk.Entry(ts_s_frame, textvariable=ts_s_file_var, width=60)
        ts_s_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_ts_s_file():
            file_path = filedialog.askopenfilename(
                title=self.tr('pandat_fd_tss', 'Select Ts-S File'),
                filetypes=[
                    (self.tr('pandat_fd_excel', 'Excel files'), "*.xls *.xlsx"),
                    ("XLS", "*.xls"),
                    ("XLSX", "*.xlsx"),
                ],
            )
            if file_path:
                ts_s_file_var.set(file_path)
        
        ttk.Button(ts_s_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_ts_s_file).pack(side=tk.RIGHT, padx=5)
        
        # Status label
        status_label = ttk.Label(
            main_frame,
            text=self.tr('pandat_status_prompt', 'Please select at least P and Ts files to proceed'),
            foreground="red",
        )
        status_label.pack(pady=10)

        def clear_imported_data():
            """Clear currently imported Pandat data without closing the app."""
            if not messagebox.askyesno(
                self.tr('pandat_clear_title', 'Clear Imported Data'),
                self.tr(
                    'pandat_clear_msg',
                    'This will clear all imported Pandat datasets (P, Ts, P-S, Ts-S) and reset available elements.\n\nContinue?',
                ),
                parent=import_window,
            ):
                return

            # Clear in-memory datasets
            self.pandat_p_data = None
            self.pandat_ts_data = None
            self.pandat_p_s_data = None
            self.pandat_ts_s_data = None
            self.available_elements = []
            self.pandat_solid_phase = None
            self.pandat_q_col = None
            if hasattr(self, "last_result"):
                self.last_result = None

            # Reset file selectors in the import window
            p_file_var.set("")
            ts_file_var.set("")
            p_s_file_var.set("")
            ts_s_file_var.set("")

            # Reset element selection UI + any previously selected composition
            try:
                self.update_element_availability()
                if hasattr(self, "element_selector"):
                    self.element_selector.selected_elements = {}
                    self.element_selector.main_element = None
                    self.element_selector.update_display()
                    # Remove status labels if present
                    for attr in ["sum_status_label", "main_element_label", "main_hint_label", "availability_label"]:
                        if hasattr(self.element_selector, attr):
                            try:
                                getattr(self.element_selector, attr).destroy()
                            except Exception:
                                pass
                            try:
                                delattr(self.element_selector, attr)
                            except Exception:
                                pass
                    # Recreate main hint
                    self.element_selector.main_hint_label = ttk.Label(
                        self.element_selector.frame,
                        text=self.tr('el_hint_main', 'Hint: The first added element will be the main element'),
                        foreground="gray",
                        wraplength=400,
                    )
                    self.element_selector.main_hint_label.grid(row=2, column=0, sticky='w', padx=3, pady=(0, 3))
            except Exception:
                pass

            status_label.config(
                text=self.tr('pandat_cleared_status', 'Imported data cleared. You can import new files now.'),
                foreground="blue",
            )
        
        # Import button
        def import_pandat_data():
            p_file = p_file_var.get()
            ts_file = ts_file_var.get()
            p_s_file = p_s_file_var.get()
            ts_s_file = ts_s_file_var.get()
            
            if not p_file or not ts_file:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr(
                        'pandat_err_need_pt_ts',
                        'Please select at least P and Ts files (Equilibrium/Lever solidification)!',
                    ),
                )
                return
            
            try:
                # Helper to read Pandat export with robust fallbacks (Excel or TSV/CSV disguised as .xls/.xlsx)
                def _read_excel_auto(path):
                    ext = os.path.splitext(path)[1].lower()
                    excel_err = None
                    df = None

                    # Try Excel engines by extension
                    if ext in ['.xls', '.xlsx']:
                        if ext == '.xls':
                            try:
                                df = pd.read_excel(path, engine='xlrd')
                            except Exception as e1:
                                excel_err = e1
                                # Some "xls" are actually xlsx or text; try openpyxl
                                try:
                                    df = pd.read_excel(path, engine='openpyxl')
                                except Exception as e2:
                                    excel_err = e2
                        else:  # .xlsx
                            try:
                                df = pd.read_excel(path, engine='openpyxl')
                            except Exception as e1:
                                excel_err = e1
                                try:
                                    df = pd.read_excel(path, engine='xlrd')
                                except Exception as e2:
                                    excel_err = e2
                    else:
                        # Non-Excel extension provided
                        excel_err = ValueError(f"Unsupported Excel extension: {ext}")

                    # If Excel parse failed or returned None, attempt TSV/CSV fallback
                    if df is None:
                        try:
                            # Detect delimiter from first line
                            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                                first_line = fh.readline()
                            sep = '\t' if ('\t' in first_line) else ','
                            df = pd.read_csv(path, sep=sep, engine='python')
                        except Exception as text_err:
                            raise ValueError(
                                f"Failed to read {path} as Excel or delimited text: {str(text_err)}"
                            )

                    return df

                # Helper to clean numeric data without losing rows unnecessarily
                def _clean_numeric(df):
                    original_len = len(df)
                    # Remove completely blank rows first
                    df = df.dropna(how='all')
                    
                    # Process 'T' column more carefully - only filter if it exists
                    if 'T' in df.columns:
                        # Convert T column to numeric, keeping NaN for non-numeric values
                        t_num = pd.to_numeric(df['T'], errors='coerce')
                        # Only keep rows where T is numeric (not NaN)
                        valid_t_mask = t_num.notna()
                        df = df.loc[valid_t_mask].copy()
                        df['T'] = t_num.loc[valid_t_mask]
                    
                    # Coerce common numeric columns - use try-except instead of errors='ignore'
                    for col in df.columns:
                        try:
                            # Ensure col_str is always a string
                            if isinstance(col, (int, float)):
                                col_str = str(col)
                            else:
                                col_str = str(col) if col is not None else ''
                            
                            # Check if column name matches patterns we want to convert
                            if col_str and any(s in col_str for s in ['w(', '-T//fs', 'w_S', 'w_L', '1/dwdT_L(', 'dwdT_L(']):
                                try:
                                    # Try to convert to numeric, keeping original if conversion fails
                                    numeric_vals = pd.to_numeric(df[col], errors='coerce')
                                    # Only update if we got valid numeric values
                                    if numeric_vals.notna().any():
                                        df[col] = numeric_vals
                                except Exception:
                                    # If conversion fails completely, keep original column
                                    pass
                        except (TypeError, AttributeError):
                            # Skip columns that can't be converted to string or checked
                            continue
                    
                    return df

                # Load Equilibrium/Lever solidification data
                self.pandat_p_data = _read_excel_auto(p_file)
                self.pandat_ts_data = _read_excel_auto(ts_file)
                
                # Load Scheil solidification data if provided
                if p_s_file:
                    self.pandat_p_s_data = _read_excel_auto(p_s_file)
                else:
                    self.pandat_p_s_data = None
                    
                if ts_s_file:
                    self.pandat_ts_s_data = _read_excel_auto(ts_s_file)
                else:
                    self.pandat_ts_s_data = None
                
                # Clean numeric data
                self.pandat_p_data = _clean_numeric(self.pandat_p_data)
                self.pandat_ts_data = _clean_numeric(self.pandat_ts_data)
                
                if self.pandat_p_s_data is not None:
                    self.pandat_p_s_data = _clean_numeric(self.pandat_p_s_data)
                if self.pandat_ts_s_data is not None:
                    self.pandat_ts_s_data = _clean_numeric(self.pandat_ts_s_data)
                
                # Process 1/dwdT_L columns - divide by 100 (for all P files)
                for df in [self.pandat_p_data, self.pandat_p_s_data]:
                    if df is not None:
                        for col in df.columns:
                            try:
                                # Ensure col is converted to string safely
                                col_str = str(col) if col is not None else ''
                                if col_str and '1/dwdT_L(' in col_str and '@LIQUID)' in col_str:
                                    df[col] = df[col] / 100
                            except (TypeError, AttributeError):
                                # Skip columns that can't be converted to string
                                continue
                
                # Extract available elements from w(*) columns with robust parsing
                # Check both P and P-S files for elements
                self.available_elements = []
                for df in [self.pandat_p_data, self.pandat_p_s_data]:
                    if df is not None:
                        for col in df.columns:
                            try:
                                # Ensure col is converted to string safely
                                col_str = str(col) if col is not None else ''
                                if col_str:
                                    m = re.match(r"^w\(\s*([A-Za-z]{1,3})\s*\)$", col_str)
                                    if m:
                                        raw = m.group(1)
                                        symbol = raw[:1].upper() + raw[1:].lower()
                                        if symbol in PERIODIC_TABLE:
                                            self.available_elements.append(symbol)
                            except (TypeError, AttributeError):
                                # Skip columns that can't be converted to string
                                continue
                # Deduplicate and sort
                self.available_elements = sorted(set(self.available_elements))
                
                # Detect solid phase and Q column from P (or P-S) so program works with any phase, not only FCC
                self.pandat_solid_phase = None
                self.pandat_q_col = None
                for d in [self.pandat_p_data, self.pandat_p_s_data]:
                    if d is not None:
                        parsed = self._parse_pandat_phases_from_df(d)
                        if parsed['solid_phase'] and parsed['q_col']:
                            self.pandat_solid_phase = parsed['solid_phase']
                            self.pandat_q_col = parsed['q_col']
                            break
                    if self.pandat_q_col:
                        break
                
                # Update element selector to activate only available elements
                self.update_element_availability()
                
                # Build success message
                els = ', '.join(self.available_elements) if self.available_elements else 'None'
                success_msg = self.tr('pandat_load_intro', 'Pandat data loaded successfully!\n')
                success_msg += self.tr('pandat_load_row_p', 'P file (Equilibrium): {n} rows\n').format(
                    n=len(self.pandat_p_data)
                )
                success_msg += self.tr('pandat_load_row_ts', 'Ts file (Equilibrium): {n} rows\n').format(
                    n=len(self.pandat_ts_data)
                )
                if self.pandat_p_s_data is not None:
                    success_msg += self.tr('pandat_load_row_ps', 'P-S file (Scheil): {n} rows\n').format(
                        n=len(self.pandat_p_s_data)
                    )
                if self.pandat_ts_s_data is not None:
                    success_msg += self.tr('pandat_load_row_tss', 'Ts-S file (Scheil): {n} rows\n').format(
                        n=len(self.pandat_ts_s_data)
                    )
                success_msg += self.tr('pandat_load_elements', 'Recognized elements: {els}').format(els=els)
                
                status_label.config(
                    text=self.tr('pandat_status_ok', 'Successfully loaded Pandat data! Recognized elements: {els}').format(
                        els=els
                    ),
                    foreground="green",
                )
                
                messagebox.showinfo(self.tr('dlg_success', 'Success'), success_msg)
                
                import_window.destroy()
                
            except Exception as e:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('pandat_load_fail', 'Failed to load Pandat data: {e}').format(e=str(e)),
                )
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text=self.tr('imp_btn_import', 'Import Data'), command=import_pandat_data).pack(
            side=tk.LEFT, padx=10
        )
        ttk.Button(button_frame, text=self.tr('imp_btn_clear', 'Clear Imported Data'), command=clear_imported_data).pack(
            side=tk.LEFT, padx=10
        )
        ttk.Button(button_frame, text=self.tr('imp_btn_cancel', 'Cancel'), command=import_window.destroy).pack(
            side=tk.LEFT, padx=10
        )
    
    def update_element_availability(self):
        """Update element selector to show only available elements from Pandat data"""
        if not hasattr(self, 'element_selector'):
            return
            
        # Update dropdown to show only available elements
        if self.available_elements:
            # Force reset the dropdown values to only show available elements
            self.element_selector.element_dropdown['values'] = sorted(self.available_elements)
            
            # Reset current selection if not in available elements
            current = self.element_selector.element_var.get()
            if current and current not in self.available_elements:
                self.element_selector.element_var.set("")
                
            # Remove existing availability label if it exists
            if hasattr(self.element_selector, 'availability_label'):
                self.element_selector.availability_label.destroy()
            
            # Add a note about available elements
            self.element_selector.availability_label = ttk.Label(
                self.element_selector.frame,
                text=self.tr('el_avail_pandat', 'Available elements from Pandat data: {els}').format(
                    els=', '.join(sorted(self.available_elements))
                ),
                foreground="blue",
                font=('Arial', 8),
            )
            self.element_selector.availability_label.grid(row=4, column=0, pady=5, sticky='w')
        else:
            # If no Pandat data loaded, show all elements
            self.element_selector.element_dropdown['values'] = sorted(PERIODIC_TABLE.keys())

        elem_vals = self.available_elements if self.available_elements else sorted(PERIODIC_TABLE.keys())
        if hasattr(self, 'batch_plot_x_combo'):
            try:
                self.batch_plot_x_combo['values'] = elem_vals
            except tk.TclError:
                pass
        if hasattr(self, 'batch_plot_y_combo'):
            try:
                self.batch_plot_y_combo['values'] = elem_vals
            except tk.TclError:
                pass
            
    def open_phase_surface_plotter(self):
        """Open phase surface plotter window (Pandat + Thermo-calc)."""
        plot_window = tk.Toplevel(self.root)
        plot_window.geometry("850x900")
        plot_window.minsize(720, 480)
        self._present_tool_window(plot_window, self.root)

        # Scrollable body: content can exceed window height (settings below tabs).
        ps_canvas = tk.Canvas(plot_window, highlightthickness=0)
        ps_scroll = ttk.Scrollbar(plot_window, orient="vertical", command=ps_canvas.yview)
        ps_canvas.configure(yscrollcommand=ps_scroll.set)

        ps_scrollable = ttk.Frame(ps_canvas)
        ps_cwin = ps_canvas.create_window((0, 0), window=ps_scrollable, anchor="nw")

        def _ps_on_canvas_configure(event):
            w = event.width
            if w > 1:
                ps_canvas.itemconfigure(ps_cwin, width=w)

        def _ps_on_scrollable_configure(_event=None):
            ps_canvas.configure(scrollregion=ps_canvas.bbox("all"))

        ps_canvas.bind("<Configure>", _ps_on_canvas_configure)
        ps_scrollable.bind("<Configure>", _ps_on_scrollable_configure)

        ps_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ps_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def _unbind_phase_surface_scroll():
            try:
                if platform.system() == "Linux":
                    plot_window.unbind_all("<Button-4>")
                    plot_window.unbind_all("<Button-5>")
                else:
                    plot_window.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass

        def _on_phase_surface_destroy(event):
            if event.widget is plot_window:
                _unbind_phase_surface_scroll()

        plot_window.bind("<Destroy>", _on_phase_surface_destroy)

        def _on_ps_mousewheel(event):
            try:
                if not plot_window.winfo_exists() or not ps_canvas.winfo_exists():
                    return
            except tk.TclError:
                return
            if platform.system() == "Windows":
                ps_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif platform.system() == "Darwin":
                ps_canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                if event.num == 4:
                    ps_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    ps_canvas.yview_scroll(1, "units")

        if platform.system() == "Linux":
            ps_canvas.bind_all("<Button-4>", _on_ps_mousewheel)
            ps_canvas.bind_all("<Button-5>", _on_ps_mousewheel)
        else:
            ps_canvas.bind_all("<MouseWheel>", _on_ps_mousewheel)

        main_frame = ttk.Frame(ps_scrollable, padding="20")
        main_frame.pack(fill=tk.X, expand=False)

        title_label = ttk.Label(
            main_frame,
            text=self.tr('plot_phase_heading', 'Phase Surface Plotter'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 15))

        info_label = ttk.Label(
            main_frame,
            text=self.tr('plot_phase_intro', ''),
            wraplength=700,
            justify='left',
        )
        info_label.pack(pady=(0, 10))

        notebook = ttk.Notebook(main_frame)
        # Natural height from tab content; shared settings stay below and reachable via scrollbar.
        notebook.pack(fill=tk.X, expand=False, pady=10)

        tab_pandat = ttk.Frame(notebook, padding="10")
        tab_tc = ttk.Frame(notebook, padding="10")
        notebook.add(tab_pandat, text=self.tr('plot_phase_tab_pandat', 'Pandat'))
        notebook.add(tab_tc, text=self.tr('plot_phase_tab_tc', 'Thermo-calc'))

        # ------------------------------------------------------------------
        # Common plotting helper (reuses existing surface creation + outputs)
        # ------------------------------------------------------------------
        def _plot_xyz_surface(x, y, z, ex, ey, base, label_z, status_widget):
            viz = viz_var.get()
            status_widget.config(text=self.tr('plot_status_smooth', 'Creating smooth surface...'), foreground="orange")
            plot_window.update()

            xi_grid, yi_grid, zi_grid = self.create_smooth_surface(
                x, y, z,
                grid_resolution=100,
                smoothness=smoothness_var.get()
            )
            if xi_grid is None:
                messagebox.showwarning(
                    self.tr('plot_smooth_title', 'Smoothing Failed'),
                    self.tr(
                        'plot_smooth_msg',
                        'Could not create smooth surface. Using scatter/triangulated surface instead. Please install scikit-learn and scipy for smooth surfaces.',
                    ),
                )
                xi_grid, yi_grid, zi_grid = None, None, None

            if viz == "2D Heatmap":
                if not MATPLOTLIB_AVAILABLE:
                    messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_2d', 'Matplotlib is not installed. Cannot generate 2D heatmap.'))
                    return
                plt.figure(figsize=(10, 8))
                plt.xlabel(f"w({ex})")
                plt.ylabel(f"w({ey})")
                if xi_grid is not None:
                    contour = plt.contourf(xi_grid, yi_grid, zi_grid, levels=50, cmap='coolwarm', alpha=1.0)
                    plt.colorbar(contour, label=label_z)
                else:
                    scatter = plt.scatter(x, y, c=z, cmap='coolwarm', s=40, alpha=0.9)
                    plt.colorbar(scatter, label=label_z)
                plt.grid(False)
                out_path = f"{base}_Heatmap.png"
                plt.savefig(out_path, dpi=300, bbox_inches='tight')
                plt.close()
                status_widget.config(text=f"Heatmap saved: {out_path}", foreground="green")
                self.open_file_and_offer_save_as(out_path, plot_window)
            elif viz == "3D Static":
                if not MATPLOTLIB_AVAILABLE:
                    messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_3d', 'Matplotlib is not installed. Cannot generate 3D image.'))
                    return
                fig = plt.figure(figsize=(12, 10))
                ax = fig.add_subplot(111, projection='3d')
                if xi_grid is not None:
                    surf = ax.plot_surface(
                        xi_grid, yi_grid, zi_grid,
                        cmap='coolwarm', alpha=0.98, linewidth=0, antialiased=True, shade=True
                    )
                    fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                else:
                    trisurf = ax.plot_trisurf(x, y, z, cmap='coolwarm', linewidth=0.0, antialiased=True, alpha=0.98)
                    fig.colorbar(trisurf, shrink=0.5, aspect=5, label=label_z)
                ax.set_xlabel(f"w({ex})")
                ax.set_ylabel(f"w({ey})")
                ax.set_zlabel(label_z)
                try:
                    ax.view_init(elev=float(elev_var.get()), azim=float(azim_var.get()))
                except Exception:
                    pass

                img_format = image_format_var.get().upper()
                format_ext_map = {
                    "PNG": "png", "JPEG": "jpg", "GIF": "gif", "BMP": "bmp",
                    "TIFF": "tiff", "WEBP": "webp", "SVG": "svg", "AI": "ai",
                    "EPS": "eps", "PDF": "pdf"
                }
                ext = format_ext_map.get(img_format, "png")
                save_kwargs = {"dpi": 300, "bbox_inches": "tight"}
                if img_format == "PDF":
                    save_kwargs["format"] = "pdf"
                elif img_format == "EPS":
                    save_kwargs["format"] = "eps"
                elif img_format == "SVG":
                    save_kwargs["format"] = "svg"
                elif img_format == "AI":
                    save_kwargs["format"] = "pdf"
                elif img_format in ["JPEG", "JPG"]:
                    save_kwargs["format"] = "jpeg"
                elif img_format == "TIFF":
                    save_kwargs["format"] = "tiff"
                elif img_format == "WEBP":
                    save_kwargs["format"] = "webp"
                elif img_format == "BMP":
                    save_kwargs["format"] = "bmp"
                elif img_format == "GIF":
                    save_kwargs["format"] = "gif"
                else:
                    save_kwargs["format"] = "png"

                out_path = f"{base}_3d.{ext}"
                plt.savefig(out_path, **save_kwargs)
                plt.close()
                status_widget.config(text=f"3D plot saved: {out_path}", foreground="green")
                self.open_file_and_offer_save_as(out_path, plot_window)
            elif viz == "3D Rotation GIF":
                if not MATPLOTLIB_AVAILABLE:
                    messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_gif', 'Matplotlib is not installed. Cannot generate GIF.'))
                    return
                fig = plt.figure(figsize=(12, 10))
                ax = fig.add_subplot(111, projection='3d')
                if xi_grid is not None:
                    surf = ax.plot_surface(
                        xi_grid, yi_grid, zi_grid,
                        cmap='coolwarm', alpha=0.98, linewidth=0, antialiased=True, shade=True
                    )
                    fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                else:
                    trisurf = ax.plot_trisurf(x, y, z, cmap='coolwarm', linewidth=0.0, antialiased=True, alpha=0.98)
                    fig.colorbar(trisurf, shrink=0.5, aspect=5, label=label_z)
                ax.set_xlabel(f"w({ex})")
                ax.set_ylabel(f"w({ey})")
                ax.set_zlabel(label_z)

                def _rotate(angle):
                    ax.view_init(azim=angle)
                    return [ax]

                try:
                    rotation_step = int(float(gif_speed_var.get()))
                except Exception:
                    rotation_step = 5
                try:
                    interval_ms = int(float(gif_interval_var.get()))
                except Exception:
                    interval_ms = 50
                try:
                    fps_val = int(float(gif_fps_var.get()))
                except Exception:
                    fps_val = 20

                ani = animation.FuncAnimation(fig, _rotate, frames=range(0, 360, rotation_step), interval=interval_ms)
                out_path = f"{base}_3d_rotation.gif"
                ani.save(out_path, writer='pillow', fps=fps_val, dpi=100)
                plt.close()
                status_widget.config(text=f"GIF saved: {out_path}", foreground="green")
                self.open_file_and_offer_save_as(out_path, plot_window)
            else:
                if PLOTLY_AVAILABLE:
                    if xi_grid is not None:
                        fig_plotly = go.Figure(
                            data=[
                                go.Surface(
                                    x=xi_grid, y=yi_grid, z=zi_grid,
                                    colorscale='RdBu', reversescale=True, opacity=0.98,
                                    colorbar=dict(title=label_z)
                                )
                            ]
                        )
                    else:
                        fig_plotly = go.Figure(
                            data=[
                                go.Scatter3d(
                                    x=x, y=y, z=z,
                                    mode='markers',
                                    marker=dict(
                                        size=3, color=z, colorscale='RdBu', reversescale=True, opacity=0.85,
                                        colorbar=dict(title=label_z)
                                    )
                                )
                            ]
                        )
                    fig_plotly.update_layout(
                        scene=dict(
                            xaxis_title=f"w({ex})",
                            yaxis_title=f"w({ey})",
                            zaxis_title=label_z,
                        ),
                        width=900,
                        height=700,
                    )
                    out_path = f"{base}_3d_interactive.html"
                    fig_plotly.write_html(out_path)
                    status_widget.config(text=f"Interactive 3D plot saved: {out_path}", foreground="green")
                    self.open_file_and_offer_save_as(out_path, plot_window)
                else:
                    out_path = f"{base}_3d_interactive.html"
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write('<html><head><title>3D Interactive Plot</title></head><body>\n')
                        f.write('<h2>3D Interactive Plot - Rotate and zoom with mouse</h2>\n')
                        f.write('<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist@2.24.1/plotly.min.js"></script>\n')
                        f.write('<div id="plot" style="width:900px;height:700px;"></div>\n')
                        f.write('<script>\n')
                        f.write('var data = [{\n')
                        f.write('  type: "scatter3d",\n')
                        f.write('  mode: "markers",\n')
                        f.write('  x: ' + str(x.tolist()) + ',\n')
                        f.write('  y: ' + str(y.tolist()) + ',\n')
                        f.write('  z: ' + str(z.tolist()) + ',\n')
                        f.write('  marker: { size: 3, color: ' + str(z.tolist()) + ', colorscale: "RdBu", reversescale: true, opacity: 0.85, colorbar: {title: "' + label_z + '"} }\n')
                        f.write('}];\n')
                        f.write('var layout = {\n')
                        f.write('  scene: {\n')
                        f.write('    xaxis: {title: "w(' + ex + ') (%)"},\n')
                        f.write('    yaxis: {title: "w(' + ey + ') (%)"},\n')
                        f.write('    zaxis: {title: "' + label_z + '"}\n')
                        f.write('  }\n')
                        f.write('};\n')
                        f.write('Plotly.newPlot("plot", data, layout);\n')
                        f.write('</script>\n')
                        f.write('</body></html>')
                    status_widget.config(text=f"Interactive 3D plot saved: {out_path}", foreground="green")
                    self.open_file_and_offer_save_as(out_path, plot_window)

        # ------------------------------------------------------------------
        # Controls (shared across both tabs to keep behavior consistent)
        # ------------------------------------------------------------------
        controls = ttk.LabelFrame(
            main_frame,
            text=self.tr('plot_phase_settings_shared', 'Settings (Shared)'),
            padding="10",
        )
        controls.pack(fill=tk.X, pady=10)

        dataset_var = tk.StringVar(value="Equilibrium")
        dataset_frame = ttk.Frame(controls)
        dataset_frame.pack(fill=tk.X, pady=5)
        lbl_ps_dataset = ttk.Label(dataset_frame, text=self.tr('plot_phase_dataset', 'Dataset:'))
        lbl_ps_dataset.pack(side=tk.LEFT, padx=5)
        rb_ps_eq = ttk.Radiobutton(
            dataset_frame,
            text=self.tr('plot_phase_ds_equilibrium', 'Equilibrium/Lever'),
            variable=dataset_var,
            value="Equilibrium",
        )
        rb_ps_eq.pack(side=tk.LEFT, padx=5)
        rb_ps_sch = ttk.Radiobutton(
            dataset_frame,
            text=self.tr('plot_phase_ds_scheil', 'Scheil'),
            variable=dataset_var,
            value="Scheil",
        )
        rb_ps_sch.pack(side=tk.LEFT, padx=5)

        surface_var = tk.StringVar(value="Liquidus")
        surface_frame = ttk.Frame(controls)
        surface_frame.pack(fill=tk.X, pady=5)
        lbl_ps_type = ttk.Label(surface_frame, text=self.tr('plot_phase_type', 'Type:'))
        lbl_ps_type.pack(side=tk.LEFT, padx=5)
        rb_ps_liq = ttk.Radiobutton(
            surface_frame,
            text=self.tr('plot_phase_liquidus', 'Liquidus'),
            variable=surface_var,
            value="Liquidus",
        )
        rb_ps_liq.pack(side=tk.LEFT, padx=5)
        rb_ps_sol = ttk.Radiobutton(
            surface_frame,
            text=self.tr('plot_phase_solidus', 'Solidus'),
            variable=surface_var,
            value="Solidus",
        )
        rb_ps_sol.pack(side=tk.LEFT, padx=5)

        elements_frame = ttk.Frame(controls)
        elements_frame.pack(fill=tk.X, pady=5)
        lbl_ps_x = ttk.Label(elements_frame, text=self.tr('batch_plot_x_el', 'X element:'))
        lbl_ps_x.pack(side=tk.LEFT, padx=5)
        elem_x_var = tk.StringVar()
        elem_y_var = tk.StringVar()
        elem_values = self.available_elements if self.available_elements else sorted(PERIODIC_TABLE.keys())
        elem_x_combo = ttk.Combobox(elements_frame, textvariable=elem_x_var, values=elem_values, width=10)
        elem_x_combo.pack(side=tk.LEFT, padx=5)
        lbl_ps_y = ttk.Label(elements_frame, text=self.tr('batch_plot_y_el', 'Y element:'))
        lbl_ps_y.pack(side=tk.LEFT, padx=15)
        elem_y_combo = ttk.Combobox(elements_frame, textvariable=elem_y_var, values=elem_values, width=10)
        elem_y_combo.pack(side=tk.LEFT, padx=5)

        viz_frame = ttk.Frame(controls)
        viz_frame.pack(fill=tk.X, pady=5)
        lbl_ps_viz = ttk.Label(viz_frame, text=self.tr('plot_vis_label', 'Visualization:'))
        lbl_ps_viz.pack(side=tk.LEFT, padx=5)
        viz_var = tk.StringVar(value="2D Heatmap")
        rb_ps_v2 = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_2d', '2D Heatmap'), variable=viz_var, value="2D Heatmap")
        rb_ps_v2.pack(side=tk.LEFT, padx=5)
        rb_ps_v3 = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_3d', '3D Static'), variable=viz_var, value="3D Static")
        rb_ps_v3.pack(side=tk.LEFT, padx=5)
        rb_ps_vg = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_gif', '3D Rotation GIF'), variable=viz_var, value="3D Rotation GIF")
        rb_ps_vg.pack(side=tk.LEFT, padx=5)
        rb_ps_vp = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_plotly', 'Plotly 3D'), variable=viz_var, value="Plotly 3D")
        rb_ps_vp.pack(side=tk.LEFT, padx=5)

        smooth_frame = ttk.Frame(controls)
        smooth_frame.pack(fill=tk.X, pady=5)
        lbl_ps_smooth = ttk.Label(smooth_frame, text=self.tr('batch_smooth', 'Smoothness:'))
        lbl_ps_smooth.pack(side=tk.LEFT, padx=5)
        smoothness_var = tk.DoubleVar(value=100.0)
        smoothness_value_label = ttk.Label(smooth_frame, text="100")
        smoothness_value_label.pack(side=tk.RIGHT, padx=5)

        def _on_smoothness_change(val):
            try:
                smoothness_value_label.config(text=str(int(float(val))))
            except Exception:
                smoothness_value_label.config(text="100")

        smooth_scale = ttk.Scale(
            smooth_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=smoothness_var,
            command=_on_smoothness_change,
        )
        smooth_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        view_frame = ttk.LabelFrame(
            controls,
            text=self.tr('batch_view_3d', '3D Static View (Rotation Angles)'),
            padding="10",
        )
        view_frame.pack(fill=tk.X, pady=5)
        elev_var = tk.DoubleVar(value=30.0)
        azim_var = tk.DoubleVar(value=-60.0)

        elev_row = ttk.Frame(view_frame)
        elev_row.pack(fill=tk.X, pady=2)
        lbl_ps_elev = ttk.Label(elev_row, text=self.tr('batch_elev', 'Elevation (deg):'))
        lbl_ps_elev.pack(side=tk.LEFT, padx=5)
        ttk.Entry(elev_row, textvariable=elev_var, width=8).pack(side=tk.LEFT, padx=5)
        lbl_ps_elev_rng = ttk.Label(elev_row, text=self.tr('plot_elev_range', '(0–90)'))
        lbl_ps_elev_rng.pack(side=tk.LEFT, padx=5)

        azim_row = ttk.Frame(view_frame)
        azim_row.pack(fill=tk.X, pady=2)
        lbl_ps_azim = ttk.Label(azim_row, text=self.tr('batch_azim', 'Azimuth (deg):'))
        lbl_ps_azim.pack(side=tk.LEFT, padx=5)
        ttk.Entry(azim_row, textvariable=azim_var, width=8).pack(side=tk.LEFT, padx=5)
        lbl_ps_azim_rng = ttk.Label(azim_row, text=self.tr('plot_azim_range', '(-180–180)'))
        lbl_ps_azim_rng.pack(side=tk.LEFT, padx=5)

        output_settings_frame = ttk.LabelFrame(
            controls,
            text=self.tr('plot_phase_output_settings', 'Output Settings'),
            padding="10",
        )
        output_settings_frame.pack(fill=tk.X, pady=5)

        output_dir_frame = ttk.Frame(output_settings_frame)
        output_dir_frame.pack(fill=tk.X, pady=3)
        lbl_ps_outdir = ttk.Label(output_dir_frame, text=self.tr('batch_output_dir', 'Output Directory:'))
        lbl_ps_outdir.pack(side=tk.LEFT, padx=5)
        output_dir_var = tk.StringVar()
        ttk.Entry(output_dir_frame, textvariable=output_dir_var, width=35).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_output_dir():
            dir_path = filedialog.askdirectory(
                title=self.tr('batch_output_dir', 'Output Directory:'),
            )
            if dir_path:
                output_dir_var.set(dir_path)

        btn_ps_browse_out = ttk.Button(
            output_dir_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=browse_output_dir,
        )
        btn_ps_browse_out.pack(side=tk.RIGHT, padx=5)

        output_prefix_frame = ttk.Frame(output_settings_frame)
        output_prefix_frame.pack(fill=tk.X, pady=3)
        lbl_ps_prefix = ttk.Label(output_prefix_frame, text=self.tr('batch_prefix', 'Output Prefix:'))
        lbl_ps_prefix.pack(side=tk.LEFT, padx=5)
        output_var = tk.StringVar(value="phase_surface")
        ttk.Entry(output_prefix_frame, textvariable=output_var, width=35).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        format_frame = ttk.Frame(output_settings_frame)
        format_frame.pack(fill=tk.X, pady=3)
        lbl_ps_fmt = ttk.Label(format_frame, text=self.tr('batch_image_fmt', 'Image Format (2D/3D Static):'))
        lbl_ps_fmt.pack(side=tk.LEFT, padx=5)
        image_format_var = tk.StringVar(value="PNG")
        format_options = ["PNG", "JPEG", "GIF", "BMP", "TIFF", "WebP", "SVG", "AI", "EPS", "PDF"]
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=image_format_var,
            values=format_options,
            state="readonly",
            width=15,
        )
        format_combo.pack(side=tk.LEFT, padx=5)

        gif_params_frame = ttk.LabelFrame(
            controls,
            text=self.tr('batch_gif_params', '3D Rotation GIF Parameters'),
            padding="10",
        )
        gif_params_frame.pack(fill=tk.X, pady=5)

        gif_speed_frame = ttk.Frame(gif_params_frame)
        gif_speed_frame.pack(fill=tk.X, pady=3)
        lbl_ps_gspd = ttk.Label(gif_speed_frame, text=self.tr('batch_gif_speed', 'Rotation Speed (degrees/frame):'))
        lbl_ps_gspd.pack(side=tk.LEFT, padx=5)
        gif_speed_var = tk.StringVar(value="5")
        ttk.Entry(gif_speed_frame, textvariable=gif_speed_var, width=10).pack(side=tk.LEFT, padx=5)

        gif_interval_frame = ttk.Frame(gif_params_frame)
        gif_interval_frame.pack(fill=tk.X, pady=3)
        lbl_ps_gint = ttk.Label(gif_interval_frame, text=self.tr('batch_gif_interval', 'Frame Interval (ms):'))
        lbl_ps_gint.pack(side=tk.LEFT, padx=5)
        gif_interval_var = tk.StringVar(value="50")
        ttk.Entry(gif_interval_frame, textvariable=gif_interval_var, width=10).pack(side=tk.LEFT, padx=5)

        gif_fps_frame = ttk.Frame(gif_params_frame)
        gif_fps_frame.pack(fill=tk.X, pady=3)
        lbl_ps_gfps = ttk.Label(gif_fps_frame, text=self.tr('batch_gif_fps', 'FPS:'))
        lbl_ps_gfps.pack(side=tk.LEFT, padx=5)
        gif_fps_var = tk.StringVar(value="20")
        ttk.Entry(gif_fps_frame, textvariable=gif_fps_var, width=10).pack(side=tk.LEFT, padx=5)

        pandat_status_label = ttk.Label(
            tab_pandat,
            text=self.tr('plot_phase_ready_pandat', 'Ready to plot (Pandat)'),
            foreground="blue",
        )
        pandat_status_label.pack(pady=5)
        tc_status_label = ttk.Label(
            tab_tc,
            text=self.tr('plot_phase_ready_tc', 'Ready to plot (Thermo-calc)'),
            foreground="blue",
        )
        tc_status_label.pack(pady=5)

        pandat_note = ttk.Label(
            tab_pandat,
            text=self.tr('plot_phase_note_pandat', ''),
            foreground="gray",
            wraplength=740,
            justify="left",
        )
        pandat_note.pack(pady=(5, 10))

        def get_df():
            ds = dataset_var.get()
            sf = surface_var.get()
            if ds == "Equilibrium":
                if sf == "Liquidus":
                    return self.pandat_p_data
                else:
                    return self.pandat_ts_data
            else:
                if sf == "Liquidus":
                    return self.pandat_p_s_data
                else:
                    return self.pandat_ts_s_data

        def run_plot_pandat():
            try:
                df = get_df()
                if df is None or len(df) == 0:
                    messagebox.showerror(self.tr('plot_data_missing', 'Data Missing'), self.tr('plot_msg_import_pandat_all', 'No data found. Please import P/Ts or P-S/Ts-S files via Import → Pandat to ThermoQ first.'))
                    return

                ex = elem_x_var.get().strip()
                ey = elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror(self.tr('plot_elem_title', 'Element Selection'), self.tr('plot_select_xy', 'Please select X and Y elements first.'))
                    return
                
                # Try case-insensitive column matching
                col_x_pattern = f"w({ex})"
                col_y_pattern = f"w({ey})"
                col_x_found = None
                col_y_found = None
                col_t_found = None
                
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.upper()
                        # Match w(ELEMENT) columns
                        if col_upper == col_x_pattern.upper():
                            col_x_found = col
                        elif col_upper == col_y_pattern.upper():
                            col_y_found = col
                        # Match T column
                        elif col_upper == 'T':
                            col_t_found = col
                
                if col_x_found is None or col_y_found is None:
                    available_cols = [str(c) for c in df.columns if isinstance(c, str) and c.upper().startswith('W(')][:10]
                    messagebox.showerror(
                        self.tr('plot_col_not_found', 'Column Not Found'),
                        self.tr(
                            'plot_cols_phase_surface',
                            'Required columns not found in dataset.\nLooking for: {cx}, {cy}\nAvailable w(*) columns (first 10): {avail}',
                        ).format(
                            cx=col_x_pattern,
                            cy=col_y_pattern,
                            avail=', '.join(available_cols) if available_cols else 'None',
                        ),
                    )
                    return
                
                if col_t_found is None:
                    messagebox.showerror(self.tr('plot_col_not_found', 'Column Not Found'), self.tr('plot_t_missing', 'Temperature column T not found in dataset.'))
                    return

                x_vals = pd.to_numeric(df[col_x_found], errors='coerce')
                y_vals = pd.to_numeric(df[col_y_found], errors='coerce')
                t_vals = pd.to_numeric(df[col_t_found], errors='coerce')
                mask = x_vals.notna() & y_vals.notna() & t_vals.notna()
                x = x_vals.loc[mask].to_numpy()
                y = y_vals.loc[mask].to_numpy()
                z = t_vals.loc[mask].to_numpy()
                if len(x) == 0:
                    messagebox.showerror(self.tr('plot_no_data_title', 'No Data'), self.tr('plot_no_valid', 'No valid data points after filtering.'))
                    return

                prefix = output_var.get().strip() or "phase_surface"
                ds = dataset_var.get()
                sf = surface_var.get()
                
                # Get output directory
                output_dir = output_dir_var.get().strip()
                if output_dir and os.path.exists(output_dir):
                    base_path = output_dir
                else:
                    base_path = "."
                
                base = os.path.join(base_path, f"{prefix}_{sf}_{ds}_{ex}_{ey}")
                label_z = f"{sf.lower()} line (K)" if sf in ("Liquidus", "Solidus") else "Temperature (K)"

                _plot_xyz_surface(x, y, z, ex, ey, base, label_z, pandat_status_label)

            except Exception as e:
                messagebox.showerror(
                    self.tr('plot_failed', 'Plotting Failed'),
                    self.tr('plot_err_simple', 'An error occurred: {e}').format(e=str(e)),
                )

        # ------------------------------------------------------------------
        # Thermo-calc tab: load Melting Range output.xlsx and plot surfaces
        # ------------------------------------------------------------------
        tc_file_frame = ttk.LabelFrame(
            tab_tc,
            text=self.tr('plot_phase_tc_excel_frame', 'Input Excel (from Melting Range output.xlsx)'),
            padding="10",
        )
        tc_file_frame.pack(fill=tk.X, pady=(5, 8))
        tc_file_var = tk.StringVar()
        ttk.Entry(tc_file_frame, textvariable=tc_file_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        tc_df_state = {"df": None, "w_cols": []}

        def _tc_refresh_elements():
            df_tc = tc_df_state["df"]
            if df_tc is None or len(df_tc) == 0:
                tc_df_state["w_cols"] = []
                elem_x_combo.config(values=[])
                elem_y_combo.config(values=[])
                return
            w_cols = [c for c in df_tc.columns if isinstance(c, str) and c.upper().startswith("W(")]
            elements = []
            for c in w_cols:
                m = re.match(r"w\(([^)]+)\)", c, flags=re.IGNORECASE)
                if m:
                    elements.append(m.group(1).strip().title())
            elements = sorted(list(dict.fromkeys(elements)))
            tc_df_state["w_cols"] = w_cols
            elem_x_combo.config(values=elements)
            elem_y_combo.config(values=elements)
            if elements and not elem_x_var.get():
                elem_x_var.set(elements[0])
            if len(elements) > 1 and not elem_y_var.get():
                elem_y_var.set(elements[1])

        def browse_tc_excel():
            p = filedialog.askopenfilename(
                title=self.tr('plot_phase_fd_mr', 'Select Melting Range Excel'),
                filetypes=[("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")],
            )
            if not p:
                return
            tc_file_var.set(p)
            try:
                df_tc = pd.read_excel(p)
            except Exception as e:
                messagebox.showerror(self.tr('plot_load_fail', 'Load Failed'), self.tr('plot_read_excel', 'Failed to read Excel:\n{e}').format(e=str(e)))
                tc_df_state["df"] = None
                _tc_refresh_elements()
                return
            tc_df_state["df"] = df_tc
            _tc_refresh_elements()
            tc_status_label.config(
                text=self.tr('plot_tc_loaded_rows', 'Loaded {n} rows from Excel.').format(n=len(df_tc)),
                foreground="green",
            )

        btn_ps_browse_tc = ttk.Button(
            tc_file_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=browse_tc_excel,
        )
        btn_ps_browse_tc.pack(side=tk.RIGHT, padx=5)

        def run_plot_thermocalc():
            try:
                df_tc = tc_df_state["df"]
                if df_tc is None or len(df_tc) == 0:
                    messagebox.showerror(self.tr('plot_data_missing', 'Data Missing'), self.tr('plot_mr_need', 'Please load Melting Range output.xlsx first.'))
                    return

                ex = elem_x_var.get().strip()
                ey = elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror(self.tr('plot_elem_title', 'Element Selection'), self.tr('plot_select_xy', 'Please select X and Y elements first.'))
                    return

                # Determine columns
                col_x_found = None
                col_y_found = None
                for col in df_tc.columns:
                    if isinstance(col, str):
                        if col.upper() == f"w({ex})".upper():
                            col_x_found = col
                        elif col.upper() == f"w({ey})".upper():
                            col_y_found = col
                if col_x_found is None or col_y_found is None:
                    available_cols = [str(c) for c in df_tc.columns if isinstance(c, str) and c.upper().startswith("W(")][:10]
                    messagebox.showerror(
                        self.tr('plot_col_not_found', 'Column Not Found'),
                        self.tr(
                            'plot_tc_cols_missing',
                            'Required composition columns not found in Excel.\nLooking for: w({ex}), w({ey})\nAvailable w(*) columns (first 10): {avail}',
                        ).format(
                            ex=ex,
                            ey=ey,
                            avail=', '.join(available_cols) if available_cols else 'None',
                        ),
                    )
                    return

                sf = surface_var.get()
                z_col = "Liquidus_Temperature" if sf == "Liquidus" else "Solidus_Temperature"
                if z_col not in df_tc.columns:
                    messagebox.showerror(
                        self.tr('plot_col_not_found', 'Column Not Found'),
                        self.tr('plot_mr_z_col', "Required column '{z}' not found in Excel.").format(z=z_col),
                    )
                    return

                x_vals = pd.to_numeric(df_tc[col_x_found], errors='coerce')
                y_vals = pd.to_numeric(df_tc[col_y_found], errors='coerce')
                z_vals = pd.to_numeric(df_tc[z_col], errors='coerce')
                mask = x_vals.notna() & y_vals.notna() & z_vals.notna()
                x = x_vals.loc[mask].to_numpy()
                y = y_vals.loc[mask].to_numpy()
                z = z_vals.loc[mask].to_numpy()
                if len(x) == 0:
                    messagebox.showerror(self.tr('plot_no_data_title', 'No Data'), self.tr('plot_no_valid', 'No valid data points after filtering.'))
                    return

                prefix = output_var.get().strip() or "phase_surface"
                output_dir = output_dir_var.get().strip()
                base_path = output_dir if output_dir and os.path.exists(output_dir) else "."
                base = os.path.join(base_path, f"{prefix}_{sf}_ThermoCalc_{ex}_{ey}")
                label_z = f"{sf} Temperature (K)"

                _plot_xyz_surface(x, y, z, ex, ey, base, label_z, tc_status_label)

            except Exception as e:
                messagebox.showerror(
                    self.tr('plot_failed', 'Plotting Failed'),
                    self.tr('plot_err_simple', 'An error occurred: {e}').format(e=str(e)),
                )

        pandat_btns = ttk.Frame(tab_pandat)
        pandat_btns.pack(pady=10)
        btn_ps_plot_pd = ttk.Button(
            pandat_btns,
            text=self.tr('plot_phase_plot_pandat', 'Plot (Pandat)'),
            command=run_plot_pandat,
        )
        btn_ps_plot_pd.pack(side=tk.LEFT, padx=10)

        tc_btns = ttk.Frame(tab_tc)
        tc_btns.pack(pady=10)
        btn_ps_plot_tc = ttk.Button(
            tc_btns,
            text=self.tr('plot_phase_plot_tc', 'Plot (Thermo-calc)'),
            command=run_plot_thermocalc,
        )
        btn_ps_plot_tc.pack(side=tk.LEFT, padx=10)

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=10)

        def _close_phase_surface():
            self._unregister_tool_lang_refresh(_refresh_phase_surface_lang)
            _unbind_phase_surface_scroll()
            plot_window.destroy()

        btn_ps_close = ttk.Button(
            buttons_frame,
            text=self.tr('ui_close', 'Close'),
            command=_close_phase_surface,
        )
        btn_ps_close.pack(side=tk.LEFT, padx=10)

        def _refresh_phase_surface_lang():
            try:
                if not plot_window.winfo_exists():
                    return
            except tk.TclError:
                return
            plot_window.title(self.tr('plot_phase_win_title', 'Plot Phase Surfaces'))
            title_label.config(text=self.tr('plot_phase_heading', 'Phase Surface Plotter'))
            info_label.config(text=self.tr('plot_phase_intro', ''))
            try:
                notebook.tab(0, text=self.tr('plot_phase_tab_pandat', 'Pandat'))
                notebook.tab(1, text=self.tr('plot_phase_tab_tc', 'Thermo-calc'))
            except tk.TclError:
                pass
            controls.config(text=self.tr('plot_phase_settings_shared', 'Settings (Shared)'))
            lbl_ps_dataset.config(text=self.tr('plot_phase_dataset', 'Dataset:'))
            rb_ps_eq.config(text=self.tr('plot_phase_ds_equilibrium', 'Equilibrium/Lever'))
            rb_ps_sch.config(text=self.tr('plot_phase_ds_scheil', 'Scheil'))
            lbl_ps_type.config(text=self.tr('plot_phase_type', 'Type:'))
            rb_ps_liq.config(text=self.tr('plot_phase_liquidus', 'Liquidus'))
            rb_ps_sol.config(text=self.tr('plot_phase_solidus', 'Solidus'))
            lbl_ps_x.config(text=self.tr('batch_plot_x_el', 'X element:'))
            lbl_ps_y.config(text=self.tr('batch_plot_y_el', 'Y element:'))
            lbl_ps_viz.config(text=self.tr('plot_vis_label', 'Visualization:'))
            rb_ps_v2.config(text=self.tr('batch_viz_2d', '2D Heatmap'))
            rb_ps_v3.config(text=self.tr('batch_viz_3d', '3D Static'))
            rb_ps_vg.config(text=self.tr('batch_viz_gif', '3D Rotation GIF'))
            rb_ps_vp.config(text=self.tr('batch_viz_plotly', 'Plotly 3D'))
            lbl_ps_smooth.config(text=self.tr('batch_smooth', 'Smoothness:'))
            view_frame.config(text=self.tr('batch_view_3d', '3D Static View'))
            lbl_ps_elev.config(text=self.tr('batch_elev', 'Elevation (deg):'))
            lbl_ps_elev_rng.config(text=self.tr('plot_elev_range', '(0–90)'))
            lbl_ps_azim.config(text=self.tr('batch_azim', 'Azimuth (deg):'))
            lbl_ps_azim_rng.config(text=self.tr('plot_azim_range', '(-180–180)'))
            output_settings_frame.config(text=self.tr('plot_phase_output_settings', 'Output Settings'))
            lbl_ps_outdir.config(text=self.tr('batch_output_dir', 'Output Directory:'))
            btn_ps_browse_out.config(text=self.tr('pandat_browse', 'Browse'))
            lbl_ps_prefix.config(text=self.tr('batch_prefix', 'Output Prefix:'))
            lbl_ps_fmt.config(text=self.tr('batch_image_fmt', 'Image Format:'))
            gif_params_frame.config(text=self.tr('batch_gif_params', '3D Rotation GIF Parameters'))
            lbl_ps_gspd.config(text=self.tr('batch_gif_speed', 'Rotation Speed'))
            lbl_ps_gint.config(text=self.tr('batch_gif_interval', 'Frame Interval'))
            lbl_ps_gfps.config(text=self.tr('batch_gif_fps', 'FPS:'))
            tc_file_frame.config(text=self.tr('plot_phase_tc_excel_frame', 'Input Excel'))
            btn_ps_browse_tc.config(text=self.tr('pandat_browse', 'Browse'))
            btn_ps_plot_pd.config(text=self.tr('plot_phase_plot_pandat', 'Plot (Pandat)'))
            btn_ps_plot_tc.config(text=self.tr('plot_phase_plot_tc', 'Plot (Thermo-calc)'))
            btn_ps_close.config(text=self.tr('ui_close', 'Close'))
            pandat_note.config(text=self.tr('plot_phase_note_pandat', ''))
            cur_pd = pandat_status_label.cget('text')
            if 'Ready' in cur_pd or '就绪' in cur_pd or 'Pandat' in cur_pd:
                pandat_status_label.config(text=self.tr('plot_phase_ready_pandat', ''))
            cur_tc = tc_status_label.cget('text')
            if 'Ready' in cur_tc or '就绪' in cur_tc or 'Thermo' in cur_tc or 'Excel' in cur_tc:
                if 'Loaded' not in cur_tc and '加载' not in cur_tc:
                    tc_status_label.config(text=self.tr('plot_phase_ready_tc', ''))
            plot_window.update_idletasks()
            ps_canvas.configure(scrollregion=ps_canvas.bbox("all"))

        plot_window.protocol('WM_DELETE_WINDOW', _close_phase_surface)
        self._register_tool_lang_refresh(_refresh_phase_surface_lang)
        _refresh_phase_surface_lang()

    def create_smooth_surface(self, x, y, z, grid_resolution=100, smoothness=100):
        """Create smooth surface using Gaussian Process Regression or interpolation"""
        if SKLEARN_AVAILABLE and len(x) >= 3:
            try:
                # Prepare training data
                X_train = np.column_stack([x, y])
                z_train = z
                
                # Normalize input data to improve convergence
                x_mean, x_std = x.mean(), x.std()
                y_mean, y_std = y.mean(), y.std()
                z_mean, z_std = z.mean(), z.std()
                
                if x_std > 0:
                    x_norm = (x - x_mean) / x_std
                else:
                    x_norm = x
                if y_std > 0:
                    y_norm = (y - y_mean) / y_std
                else:
                    y_norm = y
                if z_std > 0:
                    z_norm = (z - z_mean) / z_std
                else:
                    z_norm = z
                
                X_train_norm = np.column_stack([x_norm, y_norm])
                
                # Smoothness: 0..100 (higher = smoother / less detail)
                try:
                    smoothness = float(smoothness)
                except Exception:
                    smoothness = 70.0
                smoothness = max(0.0, min(100.0, smoothness))
                s = smoothness / 100.0

                # Calculate appropriate length scale based on data range
                x_range_norm = x_norm.max() - x_norm.min()
                y_range_norm = y_norm.max() - y_norm.min()
                # Base length scales (as fraction of range), then scale by smoothness.
                base_frac = 0.20 + 0.60 * s  # 0.20..0.80 of range
                length_scale_x = max(base_frac * x_range_norm, 0.5 + 1.5 * s)
                length_scale_y = max(base_frac * y_range_norm, 0.5 + 1.5 * s)
                
                # Create Gaussian Process Regressor with smoother kernel
                # Matern(nu=2.5) tends to be less "wavy" than aggressive RBF fits on scattered data.
                kernel = C(1.0, (1e-3, 1e6)) * Matern(
                    length_scale=[length_scale_x, length_scale_y],
                    length_scale_bounds=(
                        max(0.5 * min(length_scale_x, length_scale_y), 0.5),
                        min(5.0 * max(length_scale_x, length_scale_y), 1e5),
                    ),
                    nu=2.5
                )
                
                # Regularization (alpha): increase strongly with smoothness to suppress wrinkles.
                alpha = 1e-6 + (3e-2 - 1e-6) * (s ** 2)  # ~1e-6 .. 3e-2

                gp = GaussianProcessRegressor(
                    kernel=kernel, 
                    n_restarts_optimizer=10,
                    alpha=alpha,
                    normalize_y=True,  # Enable y normalization for better convergence
                    optimizer='fmin_l_bfgs_b',  # Explicitly set optimizer
                    n_jobs=-1  # Use all available cores
                )
                
                # Suppress convergence warnings during fitting
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning)
                    gp.fit(X_train_norm, z_norm)
                
                # Create grid for prediction (in normalized space) with higher resolution
                x_min_norm, x_max_norm = x_norm.min(), x_norm.max()
                y_min_norm, y_max_norm = y_norm.min(), y_norm.max()
                x_range_norm = x_max_norm - x_min_norm
                y_range_norm = y_max_norm - y_min_norm
                
                # Add some padding
                x_pad_norm = x_range_norm * 0.05
                y_pad_norm = y_range_norm * 0.05
                
                xi_norm = np.linspace(x_min_norm - x_pad_norm, x_max_norm + x_pad_norm, grid_resolution)
                yi_norm = np.linspace(y_min_norm - y_pad_norm, y_max_norm + y_pad_norm, grid_resolution)
                xi_grid_norm, yi_grid_norm = np.meshgrid(xi_norm, yi_norm)
                
                # Predict on grid (in normalized space)
                X_grid_norm = np.column_stack([xi_grid_norm.ravel(), yi_grid_norm.ravel()])
                zi_grid_norm = gp.predict(X_grid_norm).reshape(xi_grid_norm.shape)
                
                # Apply Gaussian smoothing filter to remove small-scale noise and wrinkles
                if SCIPY_AVAILABLE:
                    # Post-smoothing in grid space (higher smoothness -> larger sigma)
                    sigma = 0.8 + 3.5 * s  # ~0.8..4.3 grid points
                    zi_grid_norm = gaussian_filter(zi_grid_norm, sigma=sigma)
                
                # Denormalize back to original space
                xi_grid = xi_grid_norm * x_std + x_mean if x_std > 0 else xi_grid_norm + x_mean
                yi_grid = yi_grid_norm * y_std + y_mean if y_std > 0 else yi_grid_norm + y_mean
                zi_grid = zi_grid_norm * z_std + z_mean if z_std > 0 else zi_grid_norm + z_mean
                
                return xi_grid, yi_grid, zi_grid
            except Exception as e:
                # Fallback to interpolation if GP fails
                pass
        
        # Fallback: Use scipy interpolation
        if SCIPY_AVAILABLE:
            try:
                x_min, x_max = x.min(), x.max()
                y_min, y_max = y.min(), y.max()
                x_range = x_max - x_min
                y_range = y_max - y_min
                
                # Add some padding
                x_pad = x_range * 0.05
                y_pad = y_range * 0.05
                
                xi = np.linspace(x_min - x_pad, x_max + x_pad, grid_resolution)
                yi = np.linspace(y_min - y_pad, y_max + y_pad, grid_resolution)
                xi_grid, yi_grid = np.meshgrid(xi, yi)
                
                # Interpolate using cubic method for smoother surfaces
                zi_grid = griddata((x, y), z, (xi_grid, yi_grid), method='cubic', fill_value=np.nan)
                
                # Fill NaN values with nearest neighbor interpolation
                if np.isnan(zi_grid).any():
                    zi_grid_filled = griddata((x, y), z, (xi_grid, yi_grid), method='nearest')
                    zi_grid = np.where(np.isnan(zi_grid), zi_grid_filled, zi_grid)
                
                # Apply Gaussian smoothing filter to remove wrinkles
                try:
                    try:
                        smoothness = float(smoothness)
                    except Exception:
                        smoothness = 70.0
                    smoothness = max(0.0, min(100.0, smoothness))
                    s = smoothness / 100.0
                    sigma = 0.8 + 3.5 * s
                    zi_grid = gaussian_filter(zi_grid, sigma=sigma)
                except:
                    pass  # If gaussian_filter fails, return unsmoothed result
                
                return xi_grid, yi_grid, zi_grid
            except Exception:
                pass
        
        # Final fallback: return original data
        return None, None, None

    def open_file_and_offer_save_as(self, file_path, parent_window):
        """Open a file with the system default application (no Save As prompt)."""
        try:
            # Open the file based on its extension
            if file_path.lower().endswith('.html'):
                # Open HTML file in browser
                webbrowser.open(f'file://{os.path.abspath(file_path)}')
            else:
                # Open image files with system default application
                if platform.system() == 'Windows':
                    os.startfile(os.path.abspath(file_path))
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', os.path.abspath(file_path)])
                else:  # Linux
                    subprocess.call(['xdg-open', os.path.abspath(file_path)])
        except Exception as e:
            messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr('file_open_fail', 'Failed to open file: {e}').format(e=str(e)),
                parent=parent_window,
            )

    def save_file_as(self, source_path, parent_window):
        """Save file to a different location"""
        try:
            # Determine file type and extension
            ext = os.path.splitext(source_path)[1]
            file_types = {
                '.png': [('PNG Image', '*.png'), ('All Files', '*.*')],
                '.gif': [('GIF Image', '*.gif'), ('All Files', '*.*')],
                '.html': [('HTML File', '*.html'), ('All Files', '*.*')],
            }
            
            file_type = file_types.get(ext.lower(), [('All Files', '*.*')])
            default_name = os.path.basename(source_path)
            
            # Ask user for save location
            save_path = filedialog.asksaveasfilename(
                parent=parent_window,
                title="Save As",
                defaultextension=ext,
                filetypes=file_type,
                initialfile=default_name
            )
            
            if save_path:
                # Copy file to new location
                import shutil
                shutil.copy2(source_path, save_path)
                messagebox.showinfo(
                    self.tr('dlg_success', 'Success'),
                    self.tr('file_save_ok', 'File saved to:\n{path}').format(path=save_path),
                    parent=parent_window,
                )
                
        except Exception as e:
            messagebox.showerror(
                self.tr('dlg_error', 'Error'),
                self.tr('file_save_fail', 'Failed to save file: {e}').format(e=str(e)),
                parent=parent_window,
            )

    def open_q_value_plotter(self):
        """Open Q value plotter window"""
        plot_window = tk.Toplevel(self.root)
        plot_window.geometry("850x900")
        self._present_tool_window(plot_window, self.root)

        main_frame = ttk.Frame(plot_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            main_frame,
            text=self.tr('qtrue_heading', 'Qtrue Value Plotter'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 15))

        info_label = ttk.Label(
            main_frame,
            text=self.tr('qtrue_intro', ''),
            wraplength=700,
            justify='left',
        )
        info_label.pack(pady=(0, 10))

        controls = ttk.LabelFrame(main_frame, text=self.tr('qtrue_settings', 'Settings'), padding="10")
        controls.pack(fill=tk.X, pady=10)

        dataset_var = tk.StringVar(value="Equilibrium")
        dataset_frame = ttk.Frame(controls)
        dataset_frame.pack(fill=tk.X, pady=5)
        lbl_q_ds = ttk.Label(dataset_frame, text=self.tr('qtrue_dataset', 'Dataset:'))
        lbl_q_ds.pack(side=tk.LEFT, padx=5)
        rb_q_eq = ttk.Radiobutton(
            dataset_frame,
            text=self.tr('qtrue_ds_equilibrium', 'Equilibrium/Lever'),
            variable=dataset_var,
            value="Equilibrium",
        )
        rb_q_eq.pack(side=tk.LEFT, padx=5)
        rb_q_sch = ttk.Radiobutton(
            dataset_frame,
            text=self.tr('qtrue_ds_scheil', 'Scheil'),
            variable=dataset_var,
            value="Scheil",
        )
        rb_q_sch.pack(side=tk.LEFT, padx=5)

        elements_frame = ttk.Frame(controls)
        elements_frame.pack(fill=tk.X, pady=5)
        lbl_q_x = ttk.Label(elements_frame, text=self.tr('batch_plot_x_el', 'X element:'))
        lbl_q_x.pack(side=tk.LEFT, padx=5)
        elem_x_var = tk.StringVar()
        elem_y_var = tk.StringVar()
        elem_values = self.available_elements if self.available_elements else sorted(PERIODIC_TABLE.keys())
        elem_x_combo = ttk.Combobox(elements_frame, textvariable=elem_x_var, values=elem_values, width=10)
        elem_x_combo.pack(side=tk.LEFT, padx=5)
        lbl_q_y = ttk.Label(elements_frame, text=self.tr('batch_plot_y_el', 'Y element:'))
        lbl_q_y.pack(side=tk.LEFT, padx=15)
        elem_y_combo = ttk.Combobox(elements_frame, textvariable=elem_y_var, values=elem_values, width=10)
        elem_y_combo.pack(side=tk.LEFT, padx=5)

        viz_frame = ttk.Frame(controls)
        viz_frame.pack(fill=tk.X, pady=5)
        lbl_q_viz = ttk.Label(viz_frame, text=self.tr('plot_vis_label', 'Visualization:'))
        lbl_q_viz.pack(side=tk.LEFT, padx=5)
        viz_var = tk.StringVar(value="2D Heatmap")
        rb_q_v2 = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_2d', '2D Heatmap'), variable=viz_var, value="2D Heatmap")
        rb_q_v2.pack(side=tk.LEFT, padx=5)
        rb_q_v3 = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_3d', '3D Static'), variable=viz_var, value="3D Static")
        rb_q_v3.pack(side=tk.LEFT, padx=5)
        rb_q_vg = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_gif', '3D Rotation GIF'), variable=viz_var, value="3D Rotation GIF")
        rb_q_vg.pack(side=tk.LEFT, padx=5)
        rb_q_vp = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_plotly', 'Plotly 3D'), variable=viz_var, value="Plotly 3D")
        rb_q_vp.pack(side=tk.LEFT, padx=5)

        smooth_frame = ttk.Frame(controls)
        smooth_frame.pack(fill=tk.X, pady=5)
        lbl_q_sm = ttk.Label(smooth_frame, text=self.tr('batch_smooth', 'Smoothness:'))
        lbl_q_sm.pack(side=tk.LEFT, padx=5)
        smoothness_var = tk.DoubleVar(value=100.0)
        smoothness_value_label = ttk.Label(smooth_frame, text="100")
        smoothness_value_label.pack(side=tk.RIGHT, padx=5)

        def _on_smoothness_change(val):
            try:
                smoothness_value_label.config(text=str(int(float(val))))
            except Exception:
                smoothness_value_label.config(text="100")

        smooth_scale = ttk.Scale(
            smooth_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=smoothness_var,
            command=_on_smoothness_change,
        )
        smooth_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        view_frame = ttk.LabelFrame(
            controls,
            text=self.tr('batch_view_3d', '3D Static View (Rotation Angles)'),
            padding="10",
        )
        view_frame.pack(fill=tk.X, pady=5)
        elev_var = tk.DoubleVar(value=30.0)
        azim_var = tk.DoubleVar(value=-60.0)

        elev_row = ttk.Frame(view_frame)
        elev_row.pack(fill=tk.X, pady=2)
        lbl_q_el = ttk.Label(elev_row, text=self.tr('batch_elev', 'Elevation (deg):'))
        lbl_q_el.pack(side=tk.LEFT, padx=5)
        ttk.Entry(elev_row, textvariable=elev_var, width=8).pack(side=tk.LEFT, padx=5)
        lbl_q_elr = ttk.Label(elev_row, text=self.tr('plot_elev_range', '(0–90)'))
        lbl_q_elr.pack(side=tk.LEFT, padx=5)

        azim_row = ttk.Frame(view_frame)
        azim_row.pack(fill=tk.X, pady=2)
        lbl_q_az = ttk.Label(azim_row, text=self.tr('batch_azim', 'Azimuth (deg):'))
        lbl_q_az.pack(side=tk.LEFT, padx=5)
        ttk.Entry(azim_row, textvariable=azim_var, width=8).pack(side=tk.LEFT, padx=5)
        lbl_q_azr = ttk.Label(azim_row, text=self.tr('plot_azim_range', '(-180–180)'))
        lbl_q_azr.pack(side=tk.LEFT, padx=5)

        output_settings_frame = ttk.LabelFrame(
            controls,
            text=self.tr('plot_phase_output_settings', 'Output Settings'),
            padding="10",
        )
        output_settings_frame.pack(fill=tk.X, pady=5)

        output_dir_frame = ttk.Frame(output_settings_frame)
        output_dir_frame.pack(fill=tk.X, pady=3)
        lbl_q_od = ttk.Label(output_dir_frame, text=self.tr('batch_output_dir', 'Output Directory:'))
        lbl_q_od.pack(side=tk.LEFT, padx=5)
        output_dir_var = tk.StringVar()
        ttk.Entry(output_dir_frame, textvariable=output_dir_var, width=35).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_output_dir():
            dir_path = filedialog.askdirectory(title=self.tr('batch_output_dir', 'Output Directory:'))
            if dir_path:
                output_dir_var.set(dir_path)

        btn_q_browse = ttk.Button(
            output_dir_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=browse_output_dir,
        )
        btn_q_browse.pack(side=tk.RIGHT, padx=5)

        output_prefix_frame = ttk.Frame(output_settings_frame)
        output_prefix_frame.pack(fill=tk.X, pady=3)
        lbl_q_pfx = ttk.Label(output_prefix_frame, text=self.tr('batch_prefix', 'Output Prefix:'))
        lbl_q_pfx.pack(side=tk.LEFT, padx=5)
        output_var = tk.StringVar(value="q_value")
        ttk.Entry(output_prefix_frame, textvariable=output_var, width=35).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        format_frame = ttk.Frame(output_settings_frame)
        format_frame.pack(fill=tk.X, pady=3)
        lbl_q_fmt = ttk.Label(format_frame, text=self.tr('batch_image_fmt', 'Image Format (2D/3D Static):'))
        lbl_q_fmt.pack(side=tk.LEFT, padx=5)
        image_format_var = tk.StringVar(value="PNG")
        format_options = ["PNG", "JPEG", "GIF", "BMP", "TIFF", "WebP", "SVG", "AI", "EPS", "PDF"]
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=image_format_var,
            values=format_options,
            state="readonly",
            width=15,
        )
        format_combo.pack(side=tk.LEFT, padx=5)

        gif_params_frame = ttk.LabelFrame(
            controls,
            text=self.tr('batch_gif_params', '3D Rotation GIF Parameters'),
            padding="10",
        )
        gif_params_frame.pack(fill=tk.X, pady=5)

        gif_speed_frame = ttk.Frame(gif_params_frame)
        gif_speed_frame.pack(fill=tk.X, pady=3)
        lbl_q_gspd = ttk.Label(gif_speed_frame, text=self.tr('batch_gif_speed', 'Rotation Speed (degrees/frame):'))
        lbl_q_gspd.pack(side=tk.LEFT, padx=5)
        gif_speed_var = tk.StringVar(value="5")
        ttk.Entry(gif_speed_frame, textvariable=gif_speed_var, width=10).pack(side=tk.LEFT, padx=5)

        gif_interval_frame = ttk.Frame(gif_params_frame)
        gif_interval_frame.pack(fill=tk.X, pady=3)
        lbl_q_gint = ttk.Label(gif_interval_frame, text=self.tr('batch_gif_interval', 'Frame Interval (ms):'))
        lbl_q_gint.pack(side=tk.LEFT, padx=5)
        gif_interval_var = tk.StringVar(value="50")
        ttk.Entry(gif_interval_frame, textvariable=gif_interval_var, width=10).pack(side=tk.LEFT, padx=5)

        gif_fps_frame = ttk.Frame(gif_params_frame)
        gif_fps_frame.pack(fill=tk.X, pady=3)
        lbl_q_gfps = ttk.Label(gif_fps_frame, text=self.tr('batch_gif_fps', 'FPS:'))
        lbl_q_gfps.pack(side=tk.LEFT, padx=5)
        gif_fps_var = tk.StringVar(value="20")
        ttk.Entry(gif_fps_frame, textvariable=gif_fps_var, width=10).pack(side=tk.LEFT, padx=5)

        status_label = ttk.Label(
            main_frame,
            text=self.tr('qtrue_ready', 'Ready to plot'),
            foreground="blue",
        )
        status_label.pack(pady=5)

        def get_df():
            ds = dataset_var.get()
            if ds == "Equilibrium":
                return self.pandat_p_data
            else:
                return self.pandat_p_s_data

        def run_plot():
            try:
                df = get_df()
                if df is None or len(df) == 0:
                    messagebox.showerror(self.tr('plot_data_missing', 'Data Missing'), self.tr('plot_msg_import_pandat_p', 'No data found. Please import P.xlsx (Equilibrium) or P-S.xlsx (Scheil) via Import → Pandat to ThermoQ first.'))
                    return

                ex = elem_x_var.get().strip()
                ey = elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror(self.tr('plot_elem_title', 'Element Selection'), self.tr('plot_select_xy', 'Please select X and Y elements first.'))
                    return
                
                # Dynamic columns: X = w(X element), Y = w(Y element), Z = -T//fw(@phase) (detected from data)
                col_x_pattern = f"w({ex})"
                col_y_pattern = f"w({ey})"
                col_q_found = None
                # Prefer instance Q column, else detect from current dataframe
                if self.pandat_q_col and self.pandat_q_col in df.columns:
                    col_q_found = self.pandat_q_col
                else:
                    parsed = self._parse_pandat_phases_from_df(df)
                    col_q_found = parsed['q_col']
                if col_q_found is None:
                    for col in df.columns:
                        if isinstance(col, str) and re.match(r'^-T//fw\s*\(\s*@\s*[A-Za-z0-9_]+\s*\)$', col, re.IGNORECASE):
                            col_q_found = col
                            break
                
                col_x_found = None
                col_y_found = None
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.upper()
                        if col_upper == col_x_pattern.upper():
                            col_x_found = col
                        elif col_upper == col_y_pattern.upper():
                            col_y_found = col
                
                if col_x_found is None or col_y_found is None or col_q_found is None:
                    available_cols = [str(c) for c in df.columns[:20]]
                    messagebox.showerror(
                        self.tr('plot_col_not_found', 'Column Not Found'),
                        self.tr(
                            'plot_cols_q_dataset',
                            'Required columns not found in dataset.\nNeed: w({ex}), w({ey}), and a -T//fw(@phase) column.\nAvailable columns (first 20): {avail}',
                        ).format(ex=ex, ey=ey, avail=', '.join(available_cols)),
                    )
                    return

                x_vals = pd.to_numeric(df[col_x_found], errors='coerce')
                y_vals = pd.to_numeric(df[col_y_found], errors='coerce')
                q_vals = pd.to_numeric(df[col_q_found], errors='coerce')
                mask = x_vals.notna() & y_vals.notna() & q_vals.notna()
                x = x_vals.loc[mask].to_numpy()
                y = y_vals.loc[mask].to_numpy()
                z = q_vals.loc[mask].to_numpy()
                
                if len(x) == 0:
                    messagebox.showerror(self.tr('plot_no_data_title', 'No Data'), self.tr('plot_no_valid', 'No valid data points after filtering.'))
                    return

                prefix = output_var.get().strip() or "q_value"
                ds = dataset_var.get()
                
                # Get output directory
                output_dir = output_dir_var.get().strip()
                if output_dir and os.path.exists(output_dir):
                    base_path = output_dir
                else:
                    base_path = "."
                
                base = os.path.join(base_path, f"{prefix}_{ds}")
                label_z = f"Q Value ({col_q_found})"

                # Create smooth surface using Gaussian Process
                status_label.config(text=self.tr('plot_status_smooth', 'Creating smooth surface...'), foreground="orange")
                plot_window.update()
                xi_grid, yi_grid, zi_grid = self.create_smooth_surface(
                    x, y, z,
                    grid_resolution=100,
                    smoothness=smoothness_var.get()
                )
                
                if xi_grid is None:
                    messagebox.showwarning(
                        self.tr('plot_smooth_title', 'Smoothing Failed'),
                        self.tr(
                            'plot_smooth_msg',
                            'Could not create smooth surface. Using scatter/triangulated surface instead. Please install scikit-learn and scipy for smooth surfaces.',
                        ),
                    )
                    xi_grid, yi_grid, zi_grid = None, None, None

                viz = viz_var.get()
                if viz == "2D Heatmap":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_2d', 'Matplotlib is not installed. Cannot generate 2D heatmap.'))
                        return
                    plt.figure(figsize=(10, 8))
                    plt.xlabel(f"w({ex}) (%)")
                    plt.ylabel(f"w({ey}) (%)")
                    if xi_grid is not None:
                        # Use smooth surface
                        contour = plt.contourf(xi_grid, yi_grid, zi_grid, levels=50, cmap='coolwarm', alpha=1.0)
                        plt.colorbar(contour, label=label_z)
                    else:
                        # Fallback to scatter
                        scatter = plt.scatter(x, y, c=z, cmap='coolwarm', s=40, alpha=0.9)
                        plt.colorbar(scatter, label=label_z)
                    plt.grid(False)
                    out_path = f"{base}_Heatmap.png"
                    plt.savefig(out_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    status_label.config(text=f"Heatmap saved: {out_path}", foreground="green")
                    # Open the file
                    self.open_file_and_offer_save_as(out_path, plot_window)
                elif viz == "3D Static":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_3d', 'Matplotlib is not installed. Cannot generate 3D image.'))
                        return
                    fig = plt.figure(figsize=(12, 10))
                    ax = fig.add_subplot(111, projection='3d')
                    if xi_grid is not None:
                        # Use smooth surface
                        surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap='coolwarm', alpha=0.98, 
                                              linewidth=0, antialiased=True, shade=True)
                        fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                    else:
                        # Fallback (avoid dot markers): use triangulated surface
                        trisurf = ax.plot_trisurf(x, y, z, cmap='coolwarm', linewidth=0.0, antialiased=True, alpha=0.98)
                        fig.colorbar(trisurf, shrink=0.5, aspect=5, label=label_z)
                    ax.set_xlabel(f"w({ex}) (%)")
                    ax.set_ylabel(f"w({ey}) (%)")
                    ax.set_zlabel(label_z)
                    # Apply user-selected view angles for 3D Static
                    try:
                        ax.view_init(elev=float(elev_var.get()), azim=float(azim_var.get()))
                    except Exception:
                        pass
                    out_path = f"{base}_3d.png"
                    plt.savefig(out_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    status_label.config(text=f"3D plot saved: {out_path}", foreground="green")
                    # Open the file
                    self.open_file_and_offer_save_as(out_path, plot_window)
                elif viz == "3D Rotation GIF":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_gif', 'Matplotlib is not installed. Cannot generate GIF.'))
                        return
                    fig = plt.figure(figsize=(12, 10))
                    ax = fig.add_subplot(111, projection='3d')
                    if xi_grid is not None:
                        # Use smooth surface
                        surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap='coolwarm', alpha=0.98, 
                                              linewidth=0, antialiased=True, shade=True)
                        fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                    else:
                        # Fallback (avoid dot markers): use triangulated surface
                        trisurf = ax.plot_trisurf(x, y, z, cmap='coolwarm', linewidth=0.0, antialiased=True, alpha=0.98)
                        fig.colorbar(trisurf, shrink=0.5, aspect=5, label=label_z)
                    ax.set_xlabel(f"w({ex}) (%)")
                    ax.set_ylabel(f"w({ey}) (%)")
                    ax.set_zlabel(label_z)

                    def _rotate(angle):
                        ax.view_init(azim=angle)
                        return [ax]

                    # Get GIF parameters
                    try:
                        rotation_step = int(float(gif_speed_var.get()))
                    except:
                        rotation_step = 5
                    try:
                        interval_ms = int(float(gif_interval_var.get()))
                    except:
                        interval_ms = 50
                    try:
                        fps_val = int(float(gif_fps_var.get()))
                    except:
                        fps_val = 20
                    
                    ani = animation.FuncAnimation(fig, _rotate, frames=range(0, 360, rotation_step), interval=interval_ms)
                    out_path = f"{base}_3d_rotation.gif"
                    ani.save(out_path, writer='pillow', fps=fps_val, dpi=100)
                    plt.close()
                    status_label.config(text=f"GIF saved: {out_path}", foreground="green")
                    # Open the file
                    self.open_file_and_offer_save_as(out_path, plot_window)
                else:
                    if PLOTLY_AVAILABLE:
                        if xi_grid is not None:
                            # Use smooth surface
                            fig_plotly = go.Figure(data=[
                                go.Surface(x=xi_grid, y=yi_grid, z=zi_grid, 
                                          colorscale='RdBu', reversescale=True, opacity=0.98,
                                          colorbar=dict(title=label_z))
                            ])
                        else:
                            # Fallback to scatter
                            fig_plotly = go.Figure(data=[go.Scatter3d(
                                x=x, y=y, z=z,
                                mode='markers',
                                marker=dict(size=3, color=z, colorscale='RdBu', reversescale=True, opacity=0.85,
                                            colorbar=dict(title=label_z))
                            )])
                        fig_plotly.update_layout(
                            scene=dict(
                            xaxis_title=f"w({ex})",
                            yaxis_title=f"w({ey})",
                                zaxis_title=label_z,
                            ),
                            width=900, height=700,
                        )
                        out_path = f"{base}_3d_interactive.html"
                        fig_plotly.write_html(out_path)
                        status_label.config(text=f"Interactive 3D plot saved: {out_path}", foreground="green")
                        # Open the file
                        self.open_file_and_offer_save_as(out_path, plot_window)
                    else:
                        out_path = f"{base}_3d_interactive.html"
                        with open(out_path, 'w', encoding='utf-8') as f:
                            f.write('<html><head><title>Q Value 3D Interactive Plot</title></head><body>\n')
                            f.write('<h2>Q Value 3D Interactive Plot - Rotate and zoom with mouse</h2>\n')
                            f.write('<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist@2.24.1/plotly.min.js"></script>\n')
                            f.write('<div id="plot" style="width:900px;height:700px;"></div>\n')
                            f.write('<script>\n')
                            if xi_grid is not None:
                                # Use smooth surface
                                f.write('var data = [{\n')
                                f.write('  type: "surface",\n')
                                f.write('  x: ' + str(xi_grid.tolist()) + ',\n')
                                f.write('  y: ' + str(yi_grid.tolist()) + ',\n')
                                f.write('  z: ' + str(zi_grid.tolist()) + ',\n')
                                f.write('  colorscale: "Jet",\n')
                                f.write('  opacity: 0.9,\n')
                                f.write('  colorbar: {title: "' + label_z + '"}\n')
                                f.write('}, {\n')
                                f.write('  type: "scatter3d",\n')
                                f.write('  mode: "markers",\n')
                                f.write('  x: ' + str(x.tolist()) + ',\n')
                                f.write('  y: ' + str(y.tolist()) + ',\n')
                                f.write('  z: ' + str(z.tolist()) + ',\n')
                                f.write('  marker: { size: 3, color: "black", opacity: 0.5 }\n')
                                f.write('}];\n')
                            else:
                                # Fallback to scatter
                                f.write('var data = [{\n')
                                f.write('  type: "scatter3d",\n')
                                f.write('  mode: "markers",\n')
                                f.write('  x: ' + str(x.tolist()) + ',\n')
                                f.write('  y: ' + str(y.tolist()) + ',\n')
                                f.write('  z: ' + str(z.tolist()) + ',\n')
                                f.write('  marker: { size: 3, color: ' + str(z.tolist()) + ', colorscale: "Jet", opacity: 0.8, colorbar: {title: "' + label_z + '"} }\n')
                                f.write('}];\n')
                            f.write('var layout = {\n')
                            f.write('  scene: {\n')
                            f.write(f'    xaxis: {{title: "w({ex})"}},\n')
                            f.write(f'    yaxis: {{title: "w({ey})"}},\n')
                            f.write('    zaxis: {title: "' + label_z + '"}\n')
                            f.write('  }\n')
                            f.write('};\n')
                            f.write('Plotly.newPlot("plot", data, layout);\n')
                            f.write('</script>\n')
                            f.write('</body></html>')
                        status_label.config(text=f"Interactive 3D plot saved: {out_path}", foreground="green")
                        # Open the file
                        self.open_file_and_offer_save_as(out_path, plot_window)

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                messagebox.showerror(
                    self.tr('plot_failed', 'Plotting Failed'),
                    self.tr('plot_err_detail', 'An error occurred: {e}\n\nDetails:\n{details}').format(
                        e=str(e), details=error_details
                    ),
                )

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=15)

        def _close_q_plotter():
            self._unregister_tool_lang_refresh(_refresh_q_plotter_lang)
            plot_window.destroy()

        btn_q_plot = ttk.Button(buttons_frame, text=self.tr('ui_plot', 'Plot'), command=run_plot)
        btn_q_plot.pack(side=tk.LEFT, padx=10)
        btn_q_close = ttk.Button(buttons_frame, text=self.tr('ui_close', 'Close'), command=_close_q_plotter)
        btn_q_close.pack(side=tk.LEFT, padx=10)

        def _refresh_q_plotter_lang():
            try:
                if not plot_window.winfo_exists():
                    return
            except tk.TclError:
                return
            plot_window.title(self.tr('qtrue_win_title', 'Plot Qtrue Values'))
            title_label.config(text=self.tr('qtrue_heading', 'Qtrue Value Plotter'))
            info_label.config(text=self.tr('qtrue_intro', ''))
            controls.config(text=self.tr('qtrue_settings', 'Settings'))
            lbl_q_ds.config(text=self.tr('qtrue_dataset', 'Dataset:'))
            rb_q_eq.config(text=self.tr('qtrue_ds_equilibrium', 'Equilibrium/Lever'))
            rb_q_sch.config(text=self.tr('qtrue_ds_scheil', 'Scheil'))
            lbl_q_x.config(text=self.tr('batch_plot_x_el', 'X element:'))
            lbl_q_y.config(text=self.tr('batch_plot_y_el', 'Y element:'))
            lbl_q_viz.config(text=self.tr('plot_vis_label', 'Visualization:'))
            rb_q_v2.config(text=self.tr('batch_viz_2d', '2D Heatmap'))
            rb_q_v3.config(text=self.tr('batch_viz_3d', '3D Static'))
            rb_q_vg.config(text=self.tr('batch_viz_gif', '3D Rotation GIF'))
            rb_q_vp.config(text=self.tr('batch_viz_plotly', 'Plotly 3D'))
            lbl_q_sm.config(text=self.tr('batch_smooth', 'Smoothness:'))
            view_frame.config(text=self.tr('batch_view_3d', '3D Static View'))
            lbl_q_el.config(text=self.tr('batch_elev', 'Elevation (deg):'))
            lbl_q_elr.config(text=self.tr('plot_elev_range', '(0–90)'))
            lbl_q_az.config(text=self.tr('batch_azim', 'Azimuth (deg):'))
            lbl_q_azr.config(text=self.tr('plot_azim_range', '(-180–180)'))
            output_settings_frame.config(text=self.tr('plot_phase_output_settings', 'Output Settings'))
            lbl_q_od.config(text=self.tr('batch_output_dir', 'Output Directory:'))
            btn_q_browse.config(text=self.tr('pandat_browse', 'Browse'))
            lbl_q_pfx.config(text=self.tr('batch_prefix', 'Output Prefix:'))
            lbl_q_fmt.config(text=self.tr('batch_image_fmt', 'Image Format:'))
            gif_params_frame.config(text=self.tr('batch_gif_params', '3D Rotation GIF Parameters'))
            lbl_q_gspd.config(text=self.tr('batch_gif_speed', 'Rotation Speed'))
            lbl_q_gint.config(text=self.tr('batch_gif_interval', 'Frame Interval'))
            lbl_q_gfps.config(text=self.tr('batch_gif_fps', 'FPS:'))
            btn_q_plot.config(text=self.tr('ui_plot', 'Plot'))
            btn_q_close.config(text=self.tr('ui_close', 'Close'))
            cur = status_label.cget('text')
            if 'Ready' in cur or '就绪' in cur:
                status_label.config(text=self.tr('qtrue_ready', 'Ready to plot'))

        plot_window.protocol('WM_DELETE_WINDOW', _close_q_plotter)
        self._register_tool_lang_refresh(_refresh_q_plotter_lang)
        _refresh_q_plotter_lang()

    def open_t_zero_surface_plotter(self):
        """Open T-zero surface plotter window (from Extract Thermo-calc Results → T-zero output.xlsx)."""
        plot_window = tk.Toplevel(self.root)
        plot_window.geometry("850x900")
        self._present_tool_window(plot_window, self.root)

        main_frame = ttk.Frame(plot_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            main_frame,
            text=self.tr('tzero_heading', 'T-zero Surface Plotter'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 10))

        info_label = ttk.Label(
            main_frame,
            text=self.tr('tzero_intro', ''),
            wraplength=720,
            justify="left",
        )
        info_label.pack(pady=(0, 10))

        file_frame = ttk.LabelFrame(main_frame, text=self.tr('tzero_input_excel', 'Input Excel'), padding="10")
        file_frame.pack(fill=tk.X, pady=8)
        file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=file_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        state = {"df": None, "elements": []}

        elem_x_var = tk.StringVar()
        elem_y_var = tk.StringVar()

        def _refresh_element_combos():
            elems = state["elements"]
            elem_x_combo.config(values=elems)
            elem_y_combo.config(values=elems)
            if elems and not elem_x_var.get():
                elem_x_var.set(elems[0])
            if len(elems) > 1 and not elem_y_var.get():
                elem_y_var.set(elems[1])

        def browse_excel():
            p = filedialog.askopenfilename(
                title=self.tr('tzero_fd_excel', 'Select T-zero Excel'),
                filetypes=[
                    (self.tr('pandat_fd_excel', 'Excel files'), "*.xlsx;*.xls"),
                    (self.tr('filetype_all', 'All files'), "*.*"),
                ],
            )
            if not p:
                return
            file_var.set(p)
            try:
                df = pd.read_excel(p)
            except Exception as e:
                messagebox.showerror(self.tr('plot_load_fail', 'Load Failed'), self.tr('plot_read_excel', 'Failed to read Excel:\n{e}').format(e=str(e)))
                state["df"] = None
                state["elements"] = []
                _refresh_element_combos()
                return
            state["df"] = df
            w_cols = [c for c in df.columns if isinstance(c, str) and c.upper().startswith("W(")]
            elems = []
            for c in w_cols:
                m = re.match(r"w\(([^)]+)\)", c, flags=re.IGNORECASE)
                if m:
                    elems.append(m.group(1).strip().title())
            state["elements"] = sorted(list(dict.fromkeys(elems)))
            _refresh_element_combos()
            status_label.config(
                text=self.tr('plot_tc_loaded_rows', 'Loaded {n} rows from Excel.').format(n=len(df)),
                foreground="green",
            )

        btn_tz_file = ttk.Button(file_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_excel)
        btn_tz_file.pack(side=tk.RIGHT, padx=5)

        controls = ttk.LabelFrame(main_frame, text=self.tr('tzero_settings', 'Settings'), padding="10")
        controls.pack(fill=tk.X, pady=10)

        elements_frame = ttk.Frame(controls)
        elements_frame.pack(fill=tk.X, pady=5)
        lbl_tz_x = ttk.Label(elements_frame, text=self.tr('stp_x_element', 'X Element:'))
        lbl_tz_x.pack(side=tk.LEFT, padx=5)
        elem_x_combo = ttk.Combobox(elements_frame, textvariable=elem_x_var, values=[], width=10)
        elem_x_combo.pack(side=tk.LEFT, padx=5)
        lbl_tz_y = ttk.Label(elements_frame, text=self.tr('stp_y_element', 'Y Element:'))
        lbl_tz_y.pack(side=tk.LEFT, padx=15)
        elem_y_combo = ttk.Combobox(elements_frame, textvariable=elem_y_var, values=[], width=10)
        elem_y_combo.pack(side=tk.LEFT, padx=5)

        viz_frame = ttk.Frame(controls)
        viz_frame.pack(fill=tk.X, pady=5)
        lbl_tz_viz = ttk.Label(viz_frame, text=self.tr('plot_vis_label', 'Visualization:'))
        lbl_tz_viz.pack(side=tk.LEFT, padx=5)
        viz_var = tk.StringVar(value="2D Heatmap")
        rb_tz_v2 = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_2d', '2D Heatmap'), variable=viz_var, value="2D Heatmap")
        rb_tz_v2.pack(side=tk.LEFT, padx=5)
        rb_tz_v3 = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_3d', '3D Static'), variable=viz_var, value="3D Static")
        rb_tz_v3.pack(side=tk.LEFT, padx=5)
        rb_tz_vg = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_gif', '3D Rotation GIF'), variable=viz_var, value="3D Rotation GIF")
        rb_tz_vg.pack(side=tk.LEFT, padx=5)
        rb_tz_vp = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_plotly', 'Plotly 3D'), variable=viz_var, value="Plotly 3D")
        rb_tz_vp.pack(side=tk.LEFT, padx=5)

        smooth_frame = ttk.Frame(controls)
        smooth_frame.pack(fill=tk.X, pady=5)
        lbl_tz_sm = ttk.Label(smooth_frame, text=self.tr('batch_smooth', 'Smoothness:'))
        lbl_tz_sm.pack(side=tk.LEFT, padx=5)
        smoothness_var = tk.DoubleVar(value=100.0)
        smoothness_value_label = ttk.Label(smooth_frame, text="100")
        smoothness_value_label.pack(side=tk.RIGHT, padx=5)

        def _on_smoothness_change(val):
            try:
                smoothness_value_label.config(text=str(int(float(val))))
            except Exception:
                smoothness_value_label.config(text="100")

        ttk.Scale(
            smooth_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=smoothness_var,
            command=_on_smoothness_change,
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        view_frame = ttk.LabelFrame(controls, text=self.tr('batch_view_3d', '3D Static View (Rotation Angles)'), padding="10")
        view_frame.pack(fill=tk.X, pady=5)
        elev_var = tk.DoubleVar(value=30.0)
        azim_var = tk.DoubleVar(value=-60.0)
        elev_row = ttk.Frame(view_frame)
        elev_row.pack(fill=tk.X, pady=2)
        lbl_tz_el = ttk.Label(elev_row, text=self.tr('batch_elev', 'Elevation (deg):'))
        lbl_tz_el.pack(side=tk.LEFT, padx=5)
        ttk.Entry(elev_row, textvariable=elev_var, width=8).pack(side=tk.LEFT, padx=5)
        lbl_tz_elr = ttk.Label(elev_row, text=self.tr('plot_elev_range', '(0–90)'))
        lbl_tz_elr.pack(side=tk.LEFT, padx=5)
        azim_row = ttk.Frame(view_frame)
        azim_row.pack(fill=tk.X, pady=2)
        lbl_tz_az = ttk.Label(azim_row, text=self.tr('batch_azim', 'Azimuth (deg):'))
        lbl_tz_az.pack(side=tk.LEFT, padx=5)
        ttk.Entry(azim_row, textvariable=azim_var, width=8).pack(side=tk.LEFT, padx=5)
        lbl_tz_azr = ttk.Label(azim_row, text=self.tr('plot_azim_range', '(-180–180)'))
        lbl_tz_azr.pack(side=tk.LEFT, padx=5)

        output_settings_frame = ttk.LabelFrame(
            controls,
            text=self.tr('plot_phase_output_settings', 'Output Settings'),
            padding="10",
        )
        output_settings_frame.pack(fill=tk.X, pady=5)

        output_dir_frame = ttk.Frame(output_settings_frame)
        output_dir_frame.pack(fill=tk.X, pady=3)
        lbl_tz_od = ttk.Label(output_dir_frame, text=self.tr('batch_output_dir', 'Output Directory:'))
        lbl_tz_od.pack(side=tk.LEFT, padx=5)
        output_dir_var = tk.StringVar()
        ttk.Entry(output_dir_frame, textvariable=output_dir_var, width=35).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_tz_output_dir():
            dir_path = filedialog.askdirectory(title=self.tr('extp_fd_output', 'Select output directory'))
            if dir_path:
                output_dir_var.set(dir_path)

        btn_tz_out = ttk.Button(output_dir_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_tz_output_dir)
        btn_tz_out.pack(side=tk.RIGHT, padx=5)

        output_prefix_frame = ttk.Frame(output_settings_frame)
        output_prefix_frame.pack(fill=tk.X, pady=3)
        lbl_tz_pfx = ttk.Label(output_prefix_frame, text=self.tr('batch_prefix', 'Output Prefix:'))
        lbl_tz_pfx.pack(side=tk.LEFT, padx=5)
        output_var = tk.StringVar(value="t_zero_surface")
        ttk.Entry(output_prefix_frame, textvariable=output_var, width=35).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        format_frame = ttk.Frame(output_settings_frame)
        format_frame.pack(fill=tk.X, pady=3)
        lbl_tz_fmt = ttk.Label(format_frame, text=self.tr('batch_image_fmt', 'Image Format (2D/3D Static):'))
        lbl_tz_fmt.pack(side=tk.LEFT, padx=5)
        image_format_var = tk.StringVar(value="PNG")
        format_options = ["PNG", "JPEG", "GIF", "BMP", "TIFF", "WebP", "SVG", "AI", "EPS", "PDF"]
        format_combo_tz = ttk.Combobox(
            format_frame,
            textvariable=image_format_var,
            values=format_options,
            state="readonly",
            width=15,
        )
        format_combo_tz.pack(side=tk.LEFT, padx=5)

        gif_params_frame = ttk.LabelFrame(controls, text=self.tr('batch_gif_params', '3D Rotation GIF Parameters'), padding="10")
        gif_params_frame.pack(fill=tk.X, pady=5)
        gif_speed_var = tk.StringVar(value="5")
        gif_interval_var = tk.StringVar(value="50")
        gif_fps_var = tk.StringVar(value="20")
        row1 = ttk.Frame(gif_params_frame)
        row1.pack(fill=tk.X, pady=3)
        lbl_tz_gspd = ttk.Label(row1, text=self.tr('batch_gif_speed', 'Rotation Speed (degrees/frame):'))
        lbl_tz_gspd.pack(side=tk.LEFT, padx=5)
        ttk.Entry(row1, textvariable=gif_speed_var, width=10).pack(side=tk.LEFT, padx=5)
        row2 = ttk.Frame(gif_params_frame)
        row2.pack(fill=tk.X, pady=3)
        lbl_tz_gint = ttk.Label(row2, text=self.tr('batch_gif_interval', 'Frame Interval (ms):'))
        lbl_tz_gint.pack(side=tk.LEFT, padx=5)
        ttk.Entry(row2, textvariable=gif_interval_var, width=10).pack(side=tk.LEFT, padx=5)
        row3 = ttk.Frame(gif_params_frame)
        row3.pack(fill=tk.X, pady=3)
        lbl_tz_gfps = ttk.Label(row3, text=self.tr('batch_gif_fps', 'FPS:'))
        lbl_tz_gfps.pack(side=tk.LEFT, padx=5)
        ttk.Entry(row3, textvariable=gif_fps_var, width=10).pack(side=tk.LEFT, padx=5)

        status_label = ttk.Label(main_frame, text=self.tr('tzero_ready', 'Ready to plot'), foreground="blue")
        status_label.pack(pady=5)

        def _find_t0_column(df):
            for col in df.columns:
                if isinstance(col, str) and col.strip().upper() in {"T0 (K)", "T0(K)", "T0"}:
                    return col
            return None

        def plot_surface():
            try:
                df = state["df"]
                if df is None or len(df) == 0:
                    messagebox.showerror(self.tr('plot_data_missing', 'Data Missing'), self.tr('plot_t0_need', 'Please load T-zero output.xlsx first.'))
                    return

                ex = elem_x_var.get().strip()
                ey = elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror(self.tr('plot_elem_title', 'Element Selection'), self.tr('plot_select_xy', 'Please select X and Y elements first.'))
                    return

                col_x = None
                col_y = None
                for col in df.columns:
                    if isinstance(col, str):
                        if col.upper() == f"w({ex})".upper():
                            col_x = col
                        elif col.upper() == f"w({ey})".upper():
                            col_y = col
                if col_x is None or col_y is None:
                    available_cols = [str(c) for c in df.columns if isinstance(c, str) and c.upper().startswith("W(")][:10]
                    avail = ', '.join(available_cols) if available_cols else 'None'
                    messagebox.showerror(
                        self.tr('plot_col_not_found', 'Column Not Found'),
                        self.tr(
                            'plot_tc_cols_missing',
                            'Required composition columns not found in Excel.\nLooking for: w({ex}), w({ey})\nAvailable w(*) columns (first 10): {avail}',
                        ).format(ex=ex, ey=ey, avail=avail),
                    )
                    return

                col_t0 = _find_t0_column(df)
                if col_t0 is None:
                    messagebox.showerror(self.tr('plot_col_not_found', 'Column Not Found'), self.tr('plot_t0_z', "T0 column not found. Expected 'T0 (K)'."))
                    return

                x_vals = pd.to_numeric(df[col_x], errors='coerce')
                y_vals = pd.to_numeric(df[col_y], errors='coerce')
                z_vals = pd.to_numeric(df[col_t0], errors='coerce')
                mask = x_vals.notna() & y_vals.notna() & z_vals.notna()
                x = x_vals.loc[mask].to_numpy()
                y = y_vals.loc[mask].to_numpy()
                z = z_vals.loc[mask].to_numpy()
                if len(x) == 0:
                    messagebox.showerror(self.tr('plot_no_data_title', 'No Data'), self.tr('plot_no_valid', 'No valid data points after filtering.'))
                    return

                prefix = output_var.get().strip() or "t_zero_surface"
                output_dir = output_dir_var.get().strip()
                base_path = output_dir if output_dir and os.path.exists(output_dir) else "."
                base = os.path.join(base_path, f"{prefix}_{ex}_{ey}")
                label_z = "T0 (K)"

                viz = viz_var.get()
                status_label.config(text=self.tr('plot_status_smooth', 'Creating smooth surface...'), foreground="orange")
                plot_window.update()
                xi_grid, yi_grid, zi_grid = self.create_smooth_surface(
                    x, y, z, grid_resolution=100, smoothness=smoothness_var.get()
                )
                if xi_grid is None:
                    messagebox.showwarning(
                        self.tr('plot_smooth_title', 'Smoothing Failed'),
                        self.tr(
                            'plot_smooth_msg',
                            'Could not create smooth surface. Using scatter/triangulated surface instead. Please install scikit-learn and scipy for smooth surfaces.',
                        ),
                    )

                if viz == "2D Heatmap":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_2d', 'Matplotlib is not installed. Cannot generate 2D heatmap.'))
                        return
                    plt.figure(figsize=(10, 8))
                    plt.xlabel(f"w({ex})")
                    plt.ylabel(f"w({ey})")
                    if xi_grid is not None:
                        contour = plt.contourf(xi_grid, yi_grid, zi_grid, levels=50, cmap='coolwarm', alpha=1.0)
                        plt.colorbar(contour, label=label_z)
                    else:
                        scatter = plt.scatter(x, y, c=z, cmap='coolwarm', s=40, alpha=0.9)
                        plt.colorbar(scatter, label=label_z)
                    plt.grid(False)
                    out_path = f"{base}_Heatmap.png"
                    plt.savefig(out_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    status_label.config(text=f"Heatmap saved: {out_path}", foreground="green")
                    self.open_file_and_offer_save_as(out_path, plot_window)
                elif viz == "3D Static":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_3d', 'Matplotlib is not installed. Cannot generate 3D image.'))
                        return
                    fig = plt.figure(figsize=(12, 10))
                    ax = fig.add_subplot(111, projection='3d')
                    if xi_grid is not None:
                        surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap='coolwarm', alpha=0.98,
                                               linewidth=0, antialiased=True, shade=True)
                        fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                    else:
                        trisurf = ax.plot_trisurf(x, y, z, cmap='coolwarm', linewidth=0.0, antialiased=True, alpha=0.98)
                        fig.colorbar(trisurf, shrink=0.5, aspect=5, label=label_z)
                    ax.set_xlabel(f"w({ex})")
                    ax.set_ylabel(f"w({ey})")
                    ax.set_zlabel(label_z)
                    try:
                        ax.view_init(elev=float(elev_var.get()), azim=float(azim_var.get()))
                    except Exception:
                        pass

                    img_format = image_format_var.get().upper()
                    format_ext_map = {
                        "PNG": "png", "JPEG": "jpg", "GIF": "gif", "BMP": "bmp",
                        "TIFF": "tiff", "WEBP": "webp", "SVG": "svg", "AI": "ai",
                        "EPS": "eps", "PDF": "pdf"
                    }
                    ext = format_ext_map.get(img_format, "png")
                    save_kwargs = {"dpi": 300, "bbox_inches": "tight"}
                    if img_format == "PDF":
                        save_kwargs["format"] = "pdf"
                    elif img_format == "EPS":
                        save_kwargs["format"] = "eps"
                    elif img_format == "SVG":
                        save_kwargs["format"] = "svg"
                    elif img_format == "AI":
                        save_kwargs["format"] = "pdf"
                    elif img_format in ["JPEG", "JPG"]:
                        save_kwargs["format"] = "jpeg"
                    elif img_format == "TIFF":
                        save_kwargs["format"] = "tiff"
                    elif img_format == "WEBP":
                        save_kwargs["format"] = "webp"
                    elif img_format == "BMP":
                        save_kwargs["format"] = "bmp"
                    elif img_format == "GIF":
                        save_kwargs["format"] = "gif"
                    else:
                        save_kwargs["format"] = "png"
                    out_path = f"{base}_3d.{ext}"
                    plt.savefig(out_path, **save_kwargs)
                    plt.close()
                    status_label.config(text=f"3D plot saved: {out_path}", foreground="green")
                    self.open_file_and_offer_save_as(out_path, plot_window)
                elif viz == "3D Rotation GIF":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_gif', 'Matplotlib is not installed. Cannot generate GIF.'))
                        return
                    fig = plt.figure(figsize=(12, 10))
                    ax = fig.add_subplot(111, projection='3d')
                    if xi_grid is not None:
                        surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap='coolwarm', alpha=0.98,
                                               linewidth=0, antialiased=True, shade=True)
                        fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                    else:
                        trisurf = ax.plot_trisurf(x, y, z, cmap='coolwarm', linewidth=0.0, antialiased=True, alpha=0.98)
                        fig.colorbar(trisurf, shrink=0.5, aspect=5, label=label_z)
                    ax.set_xlabel(f"w({ex})")
                    ax.set_ylabel(f"w({ey})")
                    ax.set_zlabel(label_z)

                    def _rotate(angle):
                        ax.view_init(azim=angle)
                        return [ax]

                    try:
                        rotation_step = int(float(gif_speed_var.get()))
                    except Exception:
                        rotation_step = 5
                    try:
                        interval_ms = int(float(gif_interval_var.get()))
                    except Exception:
                        interval_ms = 50
                    try:
                        fps_val = int(float(gif_fps_var.get()))
                    except Exception:
                        fps_val = 20

                    ani = animation.FuncAnimation(fig, _rotate, frames=range(0, 360, rotation_step), interval=interval_ms)
                    out_path = f"{base}_3d_rotation.gif"
                    ani.save(out_path, writer='pillow', fps=fps_val, dpi=100)
                    plt.close()
                    status_label.config(text=f"GIF saved: {out_path}", foreground="green")
                    self.open_file_and_offer_save_as(out_path, plot_window)
                else:
                    if PLOTLY_AVAILABLE:
                        if xi_grid is not None:
                            fig_plotly = go.Figure(data=[
                                go.Surface(
                                    x=xi_grid, y=yi_grid, z=zi_grid,
                                    colorscale='RdBu', reversescale=True, opacity=0.98,
                                    colorbar=dict(title=label_z)
                                )
                            ])
                        else:
                            fig_plotly = go.Figure(data=[go.Scatter3d(
                                x=x, y=y, z=z,
                                mode='markers',
                                marker=dict(size=3, color=z, colorscale='RdBu', reversescale=True, opacity=0.85,
                                            colorbar=dict(title=label_z))
                            )])
                        fig_plotly.update_layout(
                            scene=dict(
                                xaxis_title=f"w({ex})",
                                yaxis_title=f"w({ey})",
                                zaxis_title=label_z,
                            ),
                            width=900, height=700,
                        )
                        out_path = f"{base}_3d_interactive.html"
                        fig_plotly.write_html(out_path)
                        status_label.config(text=f"Interactive 3D plot saved: {out_path}", foreground="green")
                        self.open_file_and_offer_save_as(out_path, plot_window)
                    else:
                        out_path = f"{base}_3d_interactive.html"
                        with open(out_path, 'w', encoding='utf-8') as f:
                            f.write('<html><head><title>3D Interactive Plot</title></head><body>\n')
                            f.write('<h2>3D Interactive Plot - Rotate and zoom with mouse</h2>\n')
                            f.write('<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist@2.24.1/plotly.min.js"></script>\n')
                            f.write('<div id="plot" style="width:900px;height:700px;"></div>\n')
                            f.write('<script>\n')
                            f.write('var data = [{\n')
                            f.write('  type: "scatter3d",\n')
                            f.write('  mode: "markers",\n')
                            f.write('  x: ' + str(x.tolist()) + ',\n')
                            f.write('  y: ' + str(y.tolist()) + ',\n')
                            f.write('  z: ' + str(z.tolist()) + ',\n')
                            f.write('  marker: { size: 3, color: ' + str(z.tolist()) + ', colorscale: "RdBu", reversescale: true, opacity: 0.85, colorbar: {title: "' + label_z + '"} }\n')
                            f.write('}];\n')
                            f.write('var layout = {\n')
                            f.write('  scene: {\n')
                            f.write(f'    xaxis: {{title: "w({ex})"}},\n')
                            f.write(f'    yaxis: {{title: "w({ey})"}},\n')
                            f.write('    zaxis: {title: "' + label_z + '"}\n')
                            f.write('  }\n')
                            f.write('};\n')
                            f.write('Plotly.newPlot("plot", data, layout);\n')
                            f.write('</script>\n')
                            f.write('</body></html>')
                        status_label.config(text=f"Interactive 3D plot saved: {out_path}", foreground="green")
                        self.open_file_and_offer_save_as(out_path, plot_window)

            except Exception as e:
                messagebox.showerror(
                    self.tr('plot_failed', 'Plotting Failed'),
                    self.tr('plot_err_simple', 'An error occurred: {e}').format(e=str(e)),
                )

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=12)

        def _close_t_zero():
            self._unregister_tool_lang_refresh(_refresh_t_zero_lang)
            plot_window.destroy()

        btn_tz_plot = ttk.Button(buttons_frame, text=self.tr('ui_plot', 'Plot'), command=plot_surface)
        btn_tz_plot.pack(side=tk.LEFT, padx=10)
        btn_tz_close = ttk.Button(buttons_frame, text=self.tr('ui_close', 'Close'), command=_close_t_zero)
        btn_tz_close.pack(side=tk.LEFT, padx=10)

        def _refresh_t_zero_lang():
            try:
                if not plot_window.winfo_exists():
                    return
            except tk.TclError:
                return
            plot_window.title(self.tr('tzero_win_title', 'Plot T-zero Surface'))
            title_label.config(text=self.tr('tzero_heading', 'T-zero Surface Plotter'))
            info_label.config(text=self.tr('tzero_intro', ''))
            file_frame.config(text=self.tr('tzero_input_excel', 'Input Excel'))
            btn_tz_file.config(text=self.tr('pandat_browse', 'Browse'))
            controls.config(text=self.tr('tzero_settings', 'Settings'))
            lbl_tz_x.config(text=self.tr('stp_x_element', 'X Element:'))
            lbl_tz_y.config(text=self.tr('stp_y_element', 'Y Element:'))
            lbl_tz_viz.config(text=self.tr('plot_vis_label', 'Visualization:'))
            rb_tz_v2.config(text=self.tr('batch_viz_2d', '2D Heatmap'))
            rb_tz_v3.config(text=self.tr('batch_viz_3d', '3D Static'))
            rb_tz_vg.config(text=self.tr('batch_viz_gif', '3D Rotation GIF'))
            rb_tz_vp.config(text=self.tr('batch_viz_plotly', 'Plotly 3D'))
            lbl_tz_sm.config(text=self.tr('batch_smooth', 'Smoothness:'))
            view_frame.config(text=self.tr('batch_view_3d', '3D Static View (Rotation Angles)'))
            lbl_tz_el.config(text=self.tr('batch_elev', 'Elevation (deg):'))
            lbl_tz_elr.config(text=self.tr('plot_elev_range', '(0–90)'))
            lbl_tz_az.config(text=self.tr('batch_azim', 'Azimuth (deg):'))
            lbl_tz_azr.config(text=self.tr('plot_azim_range', '(-180–180)'))
            output_settings_frame.config(text=self.tr('plot_phase_output_settings', 'Output Settings'))
            lbl_tz_od.config(text=self.tr('batch_output_dir', 'Output Directory:'))
            btn_tz_out.config(text=self.tr('pandat_browse', 'Browse'))
            lbl_tz_pfx.config(text=self.tr('batch_prefix', 'Output Prefix:'))
            lbl_tz_fmt.config(text=self.tr('batch_image_fmt', 'Image Format (2D/3D Static):'))
            gif_params_frame.config(text=self.tr('batch_gif_params', '3D Rotation GIF Parameters'))
            lbl_tz_gspd.config(text=self.tr('batch_gif_speed', 'Rotation Speed (degrees/frame):'))
            lbl_tz_gint.config(text=self.tr('batch_gif_interval', 'Frame Interval (ms):'))
            lbl_tz_gfps.config(text=self.tr('batch_gif_fps', 'FPS:'))
            btn_tz_plot.config(text=self.tr('ui_plot', 'Plot'))
            btn_tz_close.config(text=self.tr('ui_close', 'Close'))
            cur = status_label.cget('text')
            ready_en = self.texts.get('en', {}).get('tzero_ready', 'Ready to plot')
            ready_zh = self.texts.get('zh', {}).get('tzero_ready', '就绪，可绘图')
            if cur.strip() in (ready_en, ready_zh) or 'Ready' in cur or '就绪' in cur:
                if 'Loaded' not in cur and '加载' not in cur and 'rows' not in cur and '行' not in cur:
                    status_label.config(text=self.tr('tzero_ready', 'Ready to plot'))

        plot_window.protocol('WM_DELETE_WINDOW', _close_t_zero)
        self._register_tool_lang_refresh(_refresh_t_zero_lang)
        _refresh_t_zero_lang()

    def center_window(self):
        """Center main window on the screen."""
        try:
            self.root.update_idletasks()
            # Use the configured window size (900x600)
            width = 900
            height = 600
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            # Fallback to default size and center
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - 900) // 2
            y = (screen_height - 600) // 2
            self.root.geometry(f"900x600+{x}+{y}")
    
    def _parse_pandat_phases_from_df(self, df):
        """Parse DataFrame columns to detect phases and Q column from w(*@*) and -T//fw(@*) patterns.
        Returns dict: phases (list), solid_phase (str|None), q_col (str|None), fw_col (str|None),
                     all_fw_cols (list), all_q_cols (list). First * = element, second * = phase.
        """
        if df is None or not hasattr(df, 'columns'):
            return {'phases': [], 'solid_phase': None, 'q_col': None, 'fw_col': None,
                    'all_fw_cols': [], 'all_q_cols': []}
        phases_set = set()
        q_col = None
        solid_phase = None
        fw_col = None
        all_fw_cols = []
        all_q_cols = []
        # w(ELEMENT@PHASE): element 1-3 letters, phase alphanumeric + underscore
        re_w_at = re.compile(r'^w\s*\(\s*([A-Za-z]{1,3})\s*@\s*([A-Za-z0-9_]+)\s*\)$', re.IGNORECASE)
        re_q = re.compile(r'^-T//fw\s*\(\s*@\s*([A-Za-z0-9_]+)\s*\)$', re.IGNORECASE)
        re_fw = re.compile(r'^fw\s*\(\s*@\s*([A-Za-z0-9_]+)\s*\)$', re.IGNORECASE)
        for col in df.columns:
            if not isinstance(col, str):
                continue
            col_str = col.strip()
            m = re_w_at.match(col_str)
            if m:
                phases_set.add(m.group(2))
                continue
            m = re_q.match(col_str)
            if m:
                phase = m.group(1)
                all_q_cols.append((phase, col))
                if q_col is None:
                    q_col = col
                    solid_phase = phase
                continue
            m = re_fw.match(col_str)
            if m:
                phase = m.group(1)
                all_fw_cols.append((phase, col))
                if solid_phase and phase.upper() == solid_phase.upper():
                    fw_col = col
                continue
        phases = sorted(phases_set)
        if solid_phase is None and phases:
            # No -T//fw(@*) found: use first non-LIQUID phase as solid
            for p in phases:
                if p.upper() != 'LIQUID':
                    solid_phase = p
                    break
            if solid_phase and all_fw_cols:
                for p, c in all_fw_cols:
                    if p.upper() == solid_phase.upper():
                        fw_col = c
                        break
        return {'phases': phases, 'solid_phase': solid_phase, 'q_col': q_col, 'fw_col': fw_col,
                'all_fw_cols': all_fw_cols, 'all_q_cols': all_q_cols}
    
    @staticmethod
    def _norm_pandat_colname(c):
        if not isinstance(c, str):
            return None
        return re.sub(r"\s+", "", c).upper()

    def _resolve_pandat_column(self, columns, logical_name):
        """Return the actual column key in *columns* matching logical_name (case/spacing insensitive)."""
        if logical_name is None:
            return None
        target = self._norm_pandat_colname(logical_name)
        if not target:
            return None
        for c in columns:
            if self._norm_pandat_colname(c) == target:
                return c
        return None

    def _resolve_pandat_slope_column(self, columns, elem_upper):
        """Resolve slope column: try dwdT_L(ELEM@LIQUID), then 1/dwdT_L(ELEM@LIQUID).
        Returns (actual_column_name or None, is_inverse) where is_inverse True means stored value is 1/dwdT_L (and was divided by 100 on import)."""
        col = self._resolve_pandat_column(columns, f'dwdT_L({elem_upper}@LIQUID)')
        if col is not None:
            return (col, False)
        col = self._resolve_pandat_column(columns, f'1/dwdT_L({elem_upper}@LIQUID)')
        if col is not None:
            return (col, True)
        return (None, False)

    def _component_result_elements(self, results):
        """Symbols appearing in keys like 'Q (Mg Lever)' / 'Q (Mg Scheil)' for message / results window.
        Keys are formatted as f\"Q ({elem} Lever)\" i.e. one pair of parens around \"{elem} Lever\",
        not \"Q ({elem}) Lever\" — regex must match the former."""
        seen = set()
        for k in results:
            if not isinstance(k, str):
                continue
            m = re.match(r"^Q \((.+?) (Lever|Scheil)\)$", k)
            if m:
                seen.add(m.group(1))
        return sorted(seen, key=lambda s: s.upper())

    @staticmethod
    def _pandat_wt_from_cell(val):
        """Overall composition w(*) in wt% from a cell (fraction or percent)."""
        try:
            v = float(val)
            if pd.isna(v):
                return np.nan
            return v * 100.0 if 0.0 <= v < 1.0 else v
        except (TypeError, ValueError):
            return np.nan

    def _pandat_element_to_col(self, composition, data_df):
        """Map each element in *composition* to the matching w(El) column key in *data_df*."""
        element_to_col = {}
        for element in composition.keys():
            element_upper = element.upper()
            col_name = None
            for existing_col in data_df.columns:
                if isinstance(existing_col, str):
                    col_normalized = existing_col.strip().upper()
                    if col_normalized == f'W({element_upper})':
                        col_name = existing_col
                        break
            if col_name is None:
                for col_option in [f'w({element})', f'w({element.upper()})']:
                    if col_option in data_df.columns:
                        col_name = col_option
                        break
            if col_name is None:
                raise ValueError(
                    f"Column for element '{element}' not found. First columns: {list(data_df.columns)[:12]}"
                )
            element_to_col[element] = col_name
        return element_to_col

    def _pandat_composition_range_errors(self, composition, data_df, element_to_col, dataset_label, tol=0.01):
        """Return list of error strings if any selected wt% is outside the min–max range in *data_df*."""
        errors = []
        for el, target in composition.items():
            col = element_to_col[el]
            wts = data_df[col].map(self._pandat_wt_from_cell)
            wts = wts.dropna()
            if wts.empty:
                errors.append(f"{dataset_label}: no valid numeric data for w({el}).")
                continue
            mn = float(wts.min())
            mx = float(wts.max())
            if target < mn - tol or target > mx + tol:
                errors.append(
                    f"{dataset_label}: {el} = {target:.4f} wt% is outside the tabulated range "
                    f"[{mn:.4f}, {mx:.4f}] wt%."
                )
        return errors

    @staticmethod
    def _newton_divided_difference_eval(x_nodes, y_nodes, x):
        """Evaluate interpolating polynomial through (x_nodes[i], y_nodes[i]) via divided differences."""
        x_nodes = np.asarray(x_nodes, dtype=float)
        y_nodes = np.asarray(y_nodes, dtype=float)
        n = len(x_nodes)
        if n == 0:
            return np.nan
        if n == 1:
            return float(y_nodes[0])
        dd = np.zeros((n, n))
        dd[:, 0] = y_nodes
        for j in range(1, n):
            for i in range(n - j):
                denom = x_nodes[i + j] - x_nodes[i]
                dd[i, j] = (dd[i + 1, j - 1] - dd[i, j - 1]) / denom if abs(denom) > 1e-14 else 0.0
        coef = dd[0, :]
        res = coef[n - 1]
        for k in range(n - 2, -1, -1):
            res = res * (x - x_nodes[k]) + coef[k]
        return float(res)

    def _pandat_interp_scalar_column(self, composition, df, col_name, element_to_col, element_order,
                                     exact_tol=1e-3, m_neighbors=16):
        """Interpolate a numeric column at *composition* using nearby rows: quadratic Newton divided
        differences on three points along the axis from the nearest tabulated composition to the target.
        Returns (value_or_None, mode) where mode is 'exact', 'newton2', 'linear', or 'none'."""
        if col_name is None or col_name not in df.columns:
            return None, 'none'

        element_order = list(element_order)
        if len(element_order) < 1:
            return None, 'none'

        if len(element_order) > 1:
            elems_coords = element_order[:-1]
        else:
            elems_coords = element_order[:]

        z_star = np.array([composition[e] for e in elems_coords], dtype=float)
        positions = []
        Z = []
        for pos in range(len(df)):
            row = df.iloc[pos]
            zr = []
            bad = False
            for e in element_order:
                wv = self._pandat_wt_from_cell(row[element_to_col[e]])
                if np.isnan(wv):
                    bad = True
                    break
            if bad:
                continue
            for e in elems_coords:
                zr.append(self._pandat_wt_from_cell(row[element_to_col[e]]))
            positions.append(pos)
            Z.append(zr)
        if not Z:
            return None, 'none'
        Z = np.asarray(Z, dtype=float)
        dists = np.linalg.norm(Z - z_star, axis=1)
        i0 = int(np.argmin(dists))
        if dists[i0] < exact_tol:
            y0 = pd.to_numeric(df.iloc[positions[i0]][col_name], errors='coerce')
            if pd.isna(y0):
                return None, 'none'
            return float(y0), 'exact'

        z0 = Z[i0]
        u_vec = z_star - z0
        nu = np.linalg.norm(u_vec)
        if nu < 1e-12:
            y0 = pd.to_numeric(df.iloc[positions[i0]][col_name], errors='coerce')
            if pd.isna(y0):
                return None, 'none'
            return float(y0), 'exact'

        u_hat = u_vec / nu
        t_star = float(np.dot(z_star - z0, u_hat))
        t_all = (Z - z0) @ u_hat

        order = np.argsort(dists)
        m = min(m_neighbors, len(order))
        picked_pairs = []
        seen_t = []
        max_collect = max(m, 10)
        for k in range(min(max_collect, len(order))):
            ii = int(order[k])
            ti = float(t_all[ii])
            yv = pd.to_numeric(df.iloc[positions[ii]][col_name], errors='coerce')
            if pd.isna(yv):
                continue
            if any(abs(ti - s) < 1e-9 for s in seen_t):
                continue
            seen_t.append(ti)
            picked_pairs.append((ti, float(yv)))

        if len(picked_pairs) >= 3:
            picked_pairs.sort(key=lambda p: abs(p[0] - t_star))
            picked_pairs = picked_pairs[:3]
            picked_pairs.sort(key=lambda p: p[0])
            xs = [p[0] for p in picked_pairs]
            ys = [p[1] for p in picked_pairs]
            if abs(xs[2] - xs[0]) < 1e-14:
                return ys[1], 'linear'
            val = self._newton_divided_difference_eval(xs, ys, t_star)
            return val, 'newton2'

        if len(picked_pairs) == 2:
            picked_pairs.sort(key=lambda p: p[0])
            (t0, y0), (t1, y1) = picked_pairs
            if abs(t1 - t0) < 1e-14:
                return y0, 'linear'
            y = y0 + (y1 - y0) * (t_star - t0) / (t1 - t0)
            return float(y), 'linear'

        if len(picked_pairs) == 1:
            return picked_pairs[0][1], 'linear'

        y0 = pd.to_numeric(df.iloc[positions[i0]][col_name], errors='coerce')
        if pd.isna(y0):
            return None, 'none'
        return float(y0), 'linear'

    def find_matching_row(self, composition, data_df):
        """Find a row by matching integer wt% parts (legacy). Main Calculate uses interpolation.

        Main-window Calculate no longer calls this; it uses _pandat_interp_scalar_column and
        per-file composition range checks. Column names are case-insensitive (e.g. w(Al) vs w(AL)).
        """
        # Build element-to-column mapping (case-insensitive)
        element_to_col = {}
        for element in composition.keys():
            element_upper = element.upper()
            # Try to find matching column
            col_name = None
            for existing_col in data_df.columns:
                if isinstance(existing_col, str):
                    # Normalize column name: remove spaces, convert to uppercase
                    col_normalized = existing_col.strip().upper()
                    expected_col = f'W({element_upper})'
                    if col_normalized == expected_col:
                        col_name = existing_col
                        break
            if col_name is None:
                # Try direct match with different cases
                for col_option in [f'w({element})', f'w({element.upper()})']:
                    if col_option in data_df.columns:
                        col_name = col_option
                        break
            if col_name is None:
                raise ValueError(f"Column for element '{element}' not found in data. Available columns: {list(data_df.columns)[:10]}")
            element_to_col[element] = col_name
        
        # 首先尝试基于整数部分匹配
        for idx, row in data_df.iterrows():
            match = True
            for element, target_comp in composition.items():
                col_name = element_to_col[element]
                
                # Pandat export may store w(*) as percentage (e.g., 99.8) or fraction (e.g., 0.998)
                val = row[col_name]
                try:
                    v = float(val)
                    if pd.isna(v):
                        match = False
                        break
                except (ValueError, TypeError):
                    match = False
                    break
                
                actual_comp = v * 100.0 if 0.0 <= v < 1.0 else v
                # Compare integer parts only
                target_int = int(round(target_comp))
                actual_int = int(round(actual_comp))
                if target_int != actual_int:
                    match = False
                    break

            if match:
                return idx
        
        # 如果仍然找不到匹配，提供更详细的错误信息
        sample_data = []
        for i in range(min(3, len(data_df))):
            row_data = {}
            for element in composition.keys():
                if element in element_to_col:
                    col_name = element_to_col[element]
                    val = data_df.iloc[i][col_name]
                    try:
                        v = float(val)
                        actual_comp = v * 100.0 if 0.0 <= v < 1.0 else v
                        row_data[element] = actual_comp
                    except:
                        row_data[element] = val
            sample_data.append(row_data)
        
        raise ValueError(
            f"No matching composition found in Pandat data for {composition}.\n"
            f"Looking for: {composition}\n"
            f"Sample rows in data: {sample_data}"
        )
    
    def open_composition_converter(self):
        """Open composition converter tool window"""
        converter_window = tk.Toplevel(self.root)
        converter_window.geometry("900x900")
        self._present_tool_window(converter_window, self.root)

        # Create main frame
        main_frame = ttk.Frame(converter_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=self.tr('conv_heading', 'Composition Converter'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 20))
        
        # Instructions
        info_label = ttk.Label(
            main_frame,
            text=self.tr('conv_intro', ''),
            wraplength=600,
            justify='center',
        )
        info_label.pack(pady=(0, 20))
        
        # Input frame
        input_frame = ttk.LabelFrame(main_frame, text=self.tr('conv_input', 'Input'), padding="15")
        input_frame.pack(fill=tk.BOTH, expand=False, pady=10)
        
        # Unit selection
        unit_frame = ttk.Frame(input_frame)
        unit_frame.pack(pady=10)
        lbl_conv_unit = ttk.Label(unit_frame, text=self.tr('conv_input_unit', 'Input Unit:'))
        lbl_conv_unit.pack(side=tk.LEFT, padx=5)
        input_unit_var = tk.StringVar(value="wt%")
        rb_conv_wt = ttk.Radiobutton(
            unit_frame,
            text=self.tr('conv_wt', 'wt%'),
            variable=input_unit_var,
            value="wt%",
        )
        rb_conv_wt.pack(side=tk.LEFT, padx=5)
        rb_conv_at = ttk.Radiobutton(
            unit_frame,
            text=self.tr('conv_at', 'at%'),
            variable=input_unit_var,
            value="at%",
        )
        rb_conv_at.pack(side=tk.LEFT, padx=5)
        
        # Elements input area
        elements_frame = ttk.Frame(input_frame)
        elements_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Scrollable text area for input
        text_frame = ttk.Frame(elements_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        input_text = tk.Text(text_frame, height=10, width=60, wrap=tk.WORD)
        input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        input_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=input_text.yview)
        input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        input_text.configure(yscrollcommand=input_scrollbar.set)
        
        # Example text (localized)
        example_text = self.tr('conv_example_text', '')
        input_text.insert("1.0", example_text)
        
        # Buttons frame
        buttons_frame = ttk.Frame(input_frame)
        buttons_frame.pack(pady=10)
        
        def convert_composition():
            """Convert composition between wt% and at%"""
            try:
                # Get input text
                input_content = input_text.get("1.0", tk.END).strip()
                if not input_content:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('conv_need_comp', 'Please enter element compositions!'))
                    return
                
                # Parse input
                composition = {}
                lines = input_content.split('\n')
                ex_en = self.texts.get('en', {}).get('conv_example_prefix_en', 'Example input format')
                ex_zh = self.texts.get('zh', {}).get('conv_example_prefix_zh', '输入示例')
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('Example') or line.startswith(ex_en) or line.startswith(ex_zh) or line.startswith('Or:') or line.startswith('或：'):
                        continue
                    
                    # Try to parse element and value
                    parts = line.replace(':', ' ').split()
                    if len(parts) >= 2:
                        element = parts[0].strip()
                        try:
                            value = float(parts[1])
                            if element in PERIODIC_TABLE:
                                composition[element] = value
                        except ValueError:
                            continue
                
                if not composition:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('conv_no_valid', 'No valid elements found! Please check your input format.'))
                    return
                
                # Normalize to 100%
                total = sum(composition.values())
                if total > 0:
                    for el in composition:
                        composition[el] = composition[el] / total * 100
                
                # Convert based on input unit
                input_unit = input_unit_var.get()
                if input_unit == "wt%":
                    # Convert wt% to at%
                    at_composition = self.convert_wt_to_at(composition)
                    result_unit = "at%"
                    source_composition = composition
                    result_composition = at_composition
                else:
                    # Convert at% to wt%
                    wt_composition = self.convert_at_to_wt(composition)
                    result_unit = "wt%"
                    source_composition = composition
                    result_composition = wt_composition
                
                # Display results
                result_text.delete("1.0", tk.END)
                result_text.insert("1.0", self.tr('conv_result_input', 'Input ({unit}):').format(unit=input_unit) + "\n")
                for element, value in sorted(source_composition.items()):
                    result_text.insert(tk.END, f"{element}: {value:.4f} {input_unit}\n")
                
                result_text.insert(tk.END, "\n" + self.tr('conv_result_conv', 'Converted ({unit}):').format(unit=result_unit) + "\n")
                for element, value in sorted(result_composition.items()):
                    result_text.insert(tk.END, f"{element}: {value:.4f} {result_unit}\n")
                
                # Show total
                total_source = sum(source_composition.values())
                total_result = sum(result_composition.values())
                result_text.insert(tk.END, "\n" + self.tr('conv_result_total', 'Total {unit}:').format(unit=input_unit) + f" {total_source:.4f}\n")
                result_text.insert(tk.END, self.tr('conv_result_total', 'Total {unit}:').format(unit=result_unit) + f" {total_result:.4f}\n")
                
            except Exception as e:
                messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('conv_failed', 'Conversion failed: {e}').format(e=str(e)))
        
        btn_conv_go = ttk.Button(buttons_frame, text=self.tr('conv_convert', 'Convert'), command=convert_composition)
        btn_conv_go.pack(side=tk.LEFT, padx=10)
        btn_conv_clear = ttk.Button(buttons_frame, text=self.tr('conv_clear', 'Clear'), command=lambda: input_text.delete("1.0", tk.END))
        btn_conv_clear.pack(side=tk.LEFT, padx=10)
        
        # Output frame
        output_frame = ttk.LabelFrame(main_frame, text=self.tr('conv_result', 'Result'), padding="15")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Result text area
        result_text_frame = ttk.Frame(output_frame)
        result_text_frame.pack(fill=tk.BOTH, expand=True)
        
        result_text = tk.Text(result_text_frame, height=20, width=70, wrap=tk.WORD)
        result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        result_scrollbar = ttk.Scrollbar(result_text_frame, orient=tk.VERTICAL, command=result_text.yview)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        result_text.configure(yscrollcommand=result_scrollbar.set)
        
        def _close_conv():
            self._unregister_tool_lang_refresh(_refresh_conv_lang)
            converter_window.destroy()

        close_button = ttk.Button(main_frame, text=self.tr('ui_close', 'Close'), command=_close_conv)
        close_button.pack(pady=10)

        def _refresh_conv_lang():
            try:
                if not converter_window.winfo_exists():
                    return
            except tk.TclError:
                return
            converter_window.title(self.tr('conv_win_title', 'Composition Converter (wt% ↔ at%)'))
            title_label.config(text=self.tr('conv_heading', 'Composition Converter'))
            info_label.config(text=self.tr('conv_intro', ''))
            input_frame.config(text=self.tr('conv_input', 'Input'))
            lbl_conv_unit.config(text=self.tr('conv_input_unit', 'Input Unit:'))
            rb_conv_wt.config(text=self.tr('conv_wt', 'wt%'))
            rb_conv_at.config(text=self.tr('conv_at', 'at%'))
            btn_conv_go.config(text=self.tr('conv_convert', 'Convert'))
            btn_conv_clear.config(text=self.tr('conv_clear', 'Clear'))
            output_frame.config(text=self.tr('conv_result', 'Result'))
            close_button.config(text=self.tr('ui_close', 'Close'))
            cur = input_text.get("1.0", tk.END).strip()
            ex_old_en = self.texts.get('en', {}).get('conv_example_text', '')
            ex_old_zh = self.texts.get('zh', {}).get('conv_example_text', '')
            if cur == ex_old_en.strip() or cur == ex_old_zh.strip():
                input_text.delete("1.0", tk.END)
                input_text.insert("1.0", self.tr('conv_example_text', ''))

        converter_window.protocol('WM_DELETE_WINDOW', _close_conv)
        self._register_tool_lang_refresh(_refresh_conv_lang)
        _refresh_conv_lang()
    
    def convert_wt_to_at(self, wt_composition):
        """Convert weight percent to atomic percent"""
        if not wt_composition:
            return {}
        
        # Calculate total moles
        total_moles = sum(wt_composition[el] / PERIODIC_TABLE[el]['mass'] 
                         for el in wt_composition)
        
        if total_moles == 0:
            return {}
        
        # Convert to atomic percent
        at_composition = {}
        for element, wt_pct in wt_composition.items():
            at_pct = (wt_pct / PERIODIC_TABLE[element]['mass']) / total_moles * 100
            at_composition[element] = at_pct
        
        return at_composition
    
    def convert_at_to_wt(self, at_composition):
        """Convert atomic percent to weight percent"""
        if not at_composition:
            return {}
        
        # Calculate total atomic mass
        total_atomic_mass = sum(at_composition[el] * PERIODIC_TABLE[el]['mass'] 
                                for el in at_composition)
        
        if total_atomic_mass == 0:
            return {}
        
        # Convert to weight percent
        wt_composition = {}
        for element, at_pct in at_composition.items():
            wt_pct = (at_pct * PERIODIC_TABLE[element]['mass']) / total_atomic_mass * 100
            wt_composition[element] = wt_pct
        
        return wt_composition
    
    def open_therocalc_generator(self):
        """Open Thermo-calc batch file generator tool"""
        generator_window = tk.Toplevel(self.root)
        generator_window.geometry("950x900")
        self._present_tool_window(generator_window, self.root)

        # Create main frame with scrollable area
        canvas = tk.Canvas(generator_window)
        scrollbar = ttk.Scrollbar(generator_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_generator_canvas_configure(event):
            w = event.width
            if w > 1:
                canvas.itemconfigure(canvas_window, width=w)

        canvas.bind("<Configure>", on_generator_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        main_frame = scrollable_frame

        # Title
        title_label = ttk.Label(
            main_frame,
            text=self.tr('tbatch_win_title', 'Thermo-calc Batch File Generator'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 10))

        # Instructions (wraplength follows usable width)
        info_label = ttk.Label(
            main_frame,
            text=self.tr('tbatch_subtitle', ''),
            wraplength=800,
            justify='center',
        )
        info_label.pack(pady=(0, 20))

        def on_generator_scrollable_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            if event.width > 100:
                info_label.configure(wraplength=max(480, event.width - 80))

        scrollable_frame.bind("<Configure>", on_generator_scrollable_configure)
        
        _txt_ft = lambda: (
            (self.tr('filetype_text', 'Text files'), "*.txt"),
            (self.tr('filetype_all', 'All files'), "*.*"),
        )

        # Template files selection
        template0_frame = ttk.LabelFrame(main_frame, text=self.tr('tbatch_tpl0', 'Template0 File'), padding="10")
        template0_frame.pack(fill=tk.X, pady=5)
        
        template0_var = tk.StringVar()
        ttk.Entry(template0_frame, textvariable=template0_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_template0():
            p = filedialog.askopenfilename(title=self.tr('tbatch_fd_tpl0', 'Select Template0 File'), filetypes=_txt_ft())
            if p:
                template0_var.set(p)

        btn_tpl0 = ttk.Button(template0_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_template0)
        btn_tpl0.pack(side=tk.RIGHT, padx=5)
        
        template_frame = ttk.LabelFrame(main_frame, text=self.tr('tbatch_tpl', 'Template File (Loop body)'), padding="10")
        template_frame.pack(fill=tk.X, pady=5)
        
        template_var = tk.StringVar()
        ttk.Entry(template_frame, textvariable=template_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        btn_tpl = ttk.Button(template_frame, text=self.tr('pandat_browse', 'Browse'), command=lambda: browse_template())
        btn_tpl.pack(side=tk.RIGHT, padx=5)
        
        template1_frame = ttk.LabelFrame(main_frame, text=self.tr('tbatch_tpl1', 'Template1 File'), padding="10")
        template1_frame.pack(fill=tk.X, pady=5)
        
        template1_var = tk.StringVar()
        ttk.Entry(template1_frame, textvariable=template1_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_template1():
            p = filedialog.askopenfilename(title=self.tr('tbatch_fd_tpl1', 'Select Template1 File'), filetypes=_txt_ft())
            if p:
                template1_var.set(p)

        btn_tpl1 = ttk.Button(template1_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_template1)
        btn_tpl1.pack(side=tk.RIGHT, padx=5)
        
        # Elements configuration
        elements_frame = ttk.LabelFrame(main_frame, text=self.tr('tbatch_elem_cfg', 'Element Configuration'), padding="10")
        elements_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Elements list with scrollbar
        elements_list_frame = ttk.Frame(elements_frame)
        elements_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Treeview for elements
        elements_tree = ttk.Treeview(elements_list_frame, columns=("Element", "Min", "Max", "Step"), show="headings", height=6)
        elements_tree.heading("Element", text=self.tr('tbatch_tbl_element', 'Element'))
        elements_tree.heading("Min", text=self.tr('tbatch_tbl_min', 'Min'))
        elements_tree.heading("Max", text=self.tr('tbatch_tbl_max', 'Max'))
        elements_tree.heading("Step", text=self.tr('tbatch_tbl_step', 'Step'))
        
        elements_tree.column("Element", width=120, minwidth=70, stretch=True)
        elements_tree.column("Min", width=100, minwidth=60, stretch=True)
        elements_tree.column("Max", width=100, minwidth=60, stretch=True)
        elements_tree.column("Step", width=100, minwidth=60, stretch=True)

        elements_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        elements_scrollbar = ttk.Scrollbar(elements_list_frame, orient=tk.VERTICAL, command=elements_tree.yview)
        elements_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        elements_tree.configure(yscrollcommand=elements_scrollbar.set)

        # Add element frame
        add_element_frame = ttk.Frame(elements_frame)
        add_element_frame.pack(pady=5)

        lbl_tb_el = ttk.Label(add_element_frame, text=self.tr('tbatch_lbl_element', 'Element:'))
        lbl_tb_el.pack(side=tk.LEFT, padx=5)
        element_var = tk.StringVar()
        element_combo = ttk.Combobox(add_element_frame, textvariable=element_var,
                                    values=sorted(PERIODIC_TABLE.keys()), width=10)
        element_combo.pack(side=tk.LEFT, padx=5)
        
        lbl_tb_min = ttk.Label(add_element_frame, text=self.tr('tbatch_lbl_min', 'Min:'))
        lbl_tb_min.pack(side=tk.LEFT, padx=5)
        min_var = tk.StringVar(value="0.0")
        ttk.Entry(add_element_frame, textvariable=min_var, width=10).pack(side=tk.LEFT, padx=5)
        
        lbl_tb_max = ttk.Label(add_element_frame, text=self.tr('tbatch_lbl_max', 'Max:'))
        lbl_tb_max.pack(side=tk.LEFT, padx=5)
        max_var = tk.StringVar(value="1.0")
        ttk.Entry(add_element_frame, textvariable=max_var, width=10).pack(side=tk.LEFT, padx=5)
        
        lbl_tb_step = ttk.Label(add_element_frame, text=self.tr('tbatch_lbl_step', 'Step:'))
        lbl_tb_step.pack(side=tk.LEFT, padx=5)
        step_var = tk.StringVar(value="0.01")
        ttk.Entry(add_element_frame, textvariable=step_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # State for locked elements
        generator_state = {'allowed_elements': None}
        
        def parse_template(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find all placeholders like %Element%
                matches = re.findall(r'%([A-Za-z]+)%', content)
                
                found_elements = set()
                for m in matches:
                    el = m.title()
                    if el in PERIODIC_TABLE:
                        found_elements.add(el)
                
                if not found_elements:
                    generator_state['allowed_elements'] = None
                    element_combo.config(state='normal', values=sorted(PERIODIC_TABLE.keys()))
                    messagebox.showinfo(
                        self.tr('gen_template_info', 'Template Info'),
                        self.tr('gen_no_placeholders', 'No element placeholders (like %Al%) found in template.'),
                    )
                    return

                # Lock elements
                generator_state['allowed_elements'] = sorted(list(found_elements))
                
                # Clear existing
                for item in elements_tree.get_children():
                    elements_tree.delete(item)
                
                # Auto-populate
                for el in generator_state['allowed_elements']:
                    elements_tree.insert("", "end", values=(el, 0.0, 1.0, 0.01))
                
                # Update UI
                element_combo.set("")
                element_combo.config(values=generator_state['allowed_elements'])
                if generator_state['allowed_elements']:
                    element_combo.set(generator_state['allowed_elements'][0])
                
                messagebox.showinfo(
                    self.tr('dlg_success', 'Success'),
                    self.tr(
                        'gen_tpl_loaded_body',
                        'Found elements: {els}\n\nElement selection has been locked to these elements.\nPlease configure Min/Max/Step for each.',
                    ).format(els=', '.join(generator_state['allowed_elements'])),
                )
                    
            except Exception as e:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('gen_tpl_parse_fail', 'Failed to parse template: {e}').format(e=str(e)),
                )

        def browse_template():
            file_path = filedialog.askopenfilename(
                title=self.tr('tbatch_fd_tpl', 'Select Template File'),
                filetypes=_txt_ft(),
            )
            if file_path:
                template_var.set(file_path)
                parse_template(file_path)

        def add_element_config():
            element = element_var.get().strip()
            try:
                min_val = float(min_var.get())
                max_val = float(max_var.get())
                step_val = float(step_var.get())
                
                if element not in PERIODIC_TABLE:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('gen_invalid_el', 'Invalid element: {el}').format(el=element),
                    )
                    return
                
                # Check lock
                if generator_state['allowed_elements'] is not None:
                    if element not in generator_state['allowed_elements']:
                        messagebox.showerror(
                            self.tr('dlg_error', 'Error'),
                            self.tr(
                                'gen_el_not_in_tpl',
                                'Element {el} is not in the template!\nAllowed: {allowed}',
                            ).format(el=element, allowed=', '.join(generator_state['allowed_elements'])),
                        )
                        return

                if min_val < 0 or max_val > 1 or min_val > max_val:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('gen_invalid_range', 'Invalid range! Min should be >= 0, Max should be <= 1, and Min < Max'),
                    )
                    return
                
                if step_val <= 0:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('gen_step_pos', 'Step must be > 0'),
                    )
                    return
                
                # Check if element already exists
                existing_item = None
                for item in elements_tree.get_children():
                    if elements_tree.item(item)['values'][0] == element:
                        existing_item = item
                        break
                
                if existing_item:
                    # Update existing
                    elements_tree.item(existing_item, values=(element, min_val, max_val, step_val))
                else:
                    elements_tree.insert("", "end", values=(element, min_val, max_val, step_val))
                
                if generator_state['allowed_elements'] is None:
                    element_var.set("")
                
                min_var.set("0.0")
                max_var.set("1.0")
                step_var.set("0.01")
                
            except ValueError:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('gen_invalid_nums', 'Please enter valid numbers for Min, Max, and Step!'),
                )
        
        def remove_element_config():
            if not elements_tree.selection():
                return
            
            # Check lock
            if generator_state['allowed_elements'] is not None:
                messagebox.showwarning(
                    self.tr('gen_locked_title', 'Locked'),
                    self.tr('gen_locked', 'Cannot remove elements when locked by template.\nYou can only modify their ranges.'),
                )
                return
                
            elements_tree.delete(elements_tree.selection()[0])

        btn_tb_add = ttk.Button(add_element_frame, text=self.tr('tbatch_add', 'Add Element'), command=add_element_config)
        btn_tb_add.pack(side=tk.LEFT, padx=10)
        btn_tb_remove = ttk.Button(add_element_frame, text=self.tr('tbatch_remove', 'Remove Selected'), command=remove_element_config)
        btn_tb_remove.pack(side=tk.LEFT, padx=5)
        
        # Constraints
        constraints_frame = ttk.LabelFrame(main_frame, text=self.tr('tbatch_constraints', 'Constraints (Optional)'), padding="10")
        constraints_frame.pack(fill=tk.X, pady=10)
        
        constraint_sum_var = tk.BooleanVar(value=True)
        cb_tb_sum = ttk.Checkbutton(
            constraints_frame,
            text=self.tr('tbatch_sum_leq', 'Sum of all elements <= 1'),
            variable=constraint_sum_var,
        )
        cb_tb_sum.pack(side=tk.LEFT, padx=5)
        
        constraint_exclude_zero_var = tk.BooleanVar(value=True)
        cb_tb_zero = ttk.Checkbutton(
            constraints_frame,
            text=self.tr('tbatch_exclude_zeros', 'Exclude all zeros (0, 0, ...)'),
            variable=constraint_exclude_zero_var,
        )
        cb_tb_zero.pack(side=tk.LEFT, padx=5)
        
        # Output file
        output_frame = ttk.LabelFrame(main_frame, text=self.tr('tbatch_output_file', 'Output File'), padding="10")
        output_frame.pack(fill=tk.X, pady=10)
        
        output_var = tk.StringVar(value="Alltcm.tcm")
        ttk.Entry(output_frame, textvariable=output_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_tbatch_out():
            p = filedialog.asksaveasfilename(
                title=self.tr('tbatch_fd_save_out', 'Save Output File'),
                defaultextension=".tcm",
                filetypes=[
                    (self.tr('filetype_tcm', 'TCM files'), "*.tcm"),
                    (self.tr('filetype_all', 'All files'), "*.*"),
                ],
            )
            if p:
                output_var.set(p)

        btn_tb_out = ttk.Button(output_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_tbatch_out)
        btn_tb_out.pack(side=tk.RIGHT, padx=5)
        
        # Status label
        status_label = ttk.Label(main_frame, text=self.tr('tbatch_ready', 'Ready to generate'), foreground="blue")
        status_label.pack(pady=10)
        
        def generate_batch_file():
            """Generate Thermo-calc batch file"""
            try:
                # Validate inputs
                template0_file = template0_var.get()
                template_file = template_var.get()
                template1_file = template1_var.get()
                output_file = output_var.get()
                
                if not template0_file or not os.path.exists(template0_file):
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('gen_need_tpl0', 'Please select a valid Template0 file!'),
                    )
                    return
                
                if not template_file or not os.path.exists(template_file):
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('gen_need_tpl', 'Please select a valid Template file!'),
                    )
                    return
                
                # Template1 is optional
                
                if not output_file:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_need_out', 'Please specify an output file!'))
                    return
                
                # Get element configurations
                element_configs = []
                for item in elements_tree.get_children():
                    values = elements_tree.item(item)['values']
                    element_configs.append({
                        'element': values[0],
                        'min': float(values[1]),
                        'max': float(values[2]),
                        'step': float(values[3])
                    })
                
                if not element_configs:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('gen_need_cfg', 'Please add at least one element configuration!'),
                    )
                    return
                
                status_label.config(text="Generating... This may take a while...", foreground="orange")
                generator_window.update()
                
                # Read template0
                out = []
                with open(template0_file, "r", encoding="utf-8") as f0:
                    out.extend(f0.readlines())
                out.append('\n')
                
                # Read template
                with open(template_file, "r", encoding="utf-8") as f:
                    template_lines = f.readlines()
                
                # Generate all combinations (float64 + stable stepping; output decimals follow step)
                element_names = [cfg['element'] for cfg in element_configs]
                out_decimals = max(
                    _step_to_output_decimals(cfg['step']) for cfg in element_configs
                )
                out_decimals = min(max(out_decimals, 2), 12)
                ranges = [
                    _composition_range_float64(cfg['min'], cfg['max'], cfg['step'])
                    for cfg in element_configs
                ]
                
                # Generate combinations using meshgrid
                mesh = np.meshgrid(*ranges)
                combinations = np.stack([m.flatten() for m in mesh], axis=1)
                
                # Apply constraints
                valid_combinations = []
                for combo in combinations:
                    # Check sum constraint
                    if constraint_sum_var.get():
                        if np.sum(combo) > 1.0 + 1e-6:  # Allow small floating point error
                            continue
                    
                    # Check exclude all zeros
                    if constraint_exclude_zero_var.get():
                        if np.all(combo < 1e-6):
                            continue
                    
                    valid_combinations.append(combo)
                
                # Process each valid combination
                total = len(valid_combinations)
                for idx, combo in enumerate(valid_combinations):
                    # Create data dictionary for replacement
                    data_base = {}
                    for i, element in enumerate(element_names):
                        data_base[element] = f"{float(combo[i]):.{out_decimals}f}"
                    
                    # Replace %Element% placeholders (case-insensitive: %LI% == %Li%)
                    upper_to_val = {k.upper(): v for k, v in data_base.items()}

                    def _repl_batch_ph(m):
                        u = m.group(1).upper()
                        if u in upper_to_val:
                            return upper_to_val[u]
                        return m.group(0)

                    write = []
                    for line in template_lines:
                        if '%' in line:
                            new_line = re.sub(r'%([A-Za-z]+)%', _repl_batch_ph, line)
                        else:
                            new_line = line
                        write.append(new_line)
                    
                    write.append('\n')
                    out.extend(write)
                    
                    # Update progress
                    if (idx + 1) % 100 == 0:
                        status_label.config(text=f"Processing... {idx + 1}/{total} combinations", foreground="orange")
                        generator_window.update()
                
                # Add template1 (optional)
                if template1_file and os.path.exists(template1_file):
                    out.append('\n')
                    with open(template1_file, "r", encoding="utf-8") as f1:
                        out.extend(f1.readlines())
                
                # Write output file
                with open(output_file, 'w', encoding="utf-8") as fp:
                    fp.write(''.join(out))
                
                status_label.config(text=f"Success! Generated {total} combinations. File saved to: {output_file}", foreground="green")
                messagebox.showinfo(
                    self.tr('dlg_success', 'Success'),
                    self.tr('gen_ok', 'Batch file generated successfully!\n\nTotal combinations: {n}\nOutput file: {path}').format(
                        n=total, path=output_file
                    ),
                )
                
            except Exception as e:
                status_label.config(text=f"Error: {str(e)}", foreground="red")
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('gen_fail', 'Failed to generate batch file:\n{e}').format(e=str(e)),
                )
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=20)

        def _close_tbatch():
            self._unregister_tool_lang_refresh(_refresh_tbatch_lang)
            generator_window.destroy()

        btn_tb_gen = ttk.Button(buttons_frame, text=self.tr('tbatch_generate', 'Generate Batch File'), command=generate_batch_file)
        btn_tb_gen.pack(side=tk.LEFT, padx=10)
        btn_tb_close = ttk.Button(buttons_frame, text=self.tr('ui_close', 'Close'), command=_close_tbatch)
        btn_tb_close.pack(side=tk.LEFT, padx=10)

        def _refresh_tbatch_lang():
            try:
                if not generator_window.winfo_exists():
                    return
            except tk.TclError:
                return
            generator_window.title(self.tr('tools_generate', 'Generate Thermo-calc Batch File'))
            title_label.config(text=self.tr('tbatch_win_title', 'Thermo-calc Batch File Generator'))
            info_label.config(text=self.tr('tbatch_subtitle', ''))
            template0_frame.config(text=self.tr('tbatch_tpl0', 'Template0 File'))
            btn_tpl0.config(text=self.tr('pandat_browse', 'Browse'))
            template_frame.config(text=self.tr('tbatch_tpl', 'Template File (Loop body)'))
            btn_tpl.config(text=self.tr('pandat_browse', 'Browse'))
            template1_frame.config(text=self.tr('tbatch_tpl1', 'Template1 File'))
            btn_tpl1.config(text=self.tr('pandat_browse', 'Browse'))
            elements_frame.config(text=self.tr('tbatch_elem_cfg', 'Element Configuration'))
            elements_tree.heading("Element", text=self.tr('tbatch_tbl_element', 'Element'))
            elements_tree.heading("Min", text=self.tr('tbatch_tbl_min', 'Min'))
            elements_tree.heading("Max", text=self.tr('tbatch_tbl_max', 'Max'))
            elements_tree.heading("Step", text=self.tr('tbatch_tbl_step', 'Step'))
            lbl_tb_el.config(text=self.tr('tbatch_lbl_element', 'Element:'))
            lbl_tb_min.config(text=self.tr('tbatch_lbl_min', 'Min:'))
            lbl_tb_max.config(text=self.tr('tbatch_lbl_max', 'Max:'))
            lbl_tb_step.config(text=self.tr('tbatch_lbl_step', 'Step:'))
            btn_tb_add.config(text=self.tr('tbatch_add', 'Add Element'))
            btn_tb_remove.config(text=self.tr('tbatch_remove', 'Remove Selected'))
            constraints_frame.config(text=self.tr('tbatch_constraints', 'Constraints (Optional)'))
            cb_tb_sum.config(text=self.tr('tbatch_sum_leq', 'Sum of all elements <= 1'))
            cb_tb_zero.config(text=self.tr('tbatch_exclude_zeros', 'Exclude all zeros (0, 0, ...)'))
            output_frame.config(text=self.tr('tbatch_output_file', 'Output File'))
            btn_tb_out.config(text=self.tr('pandat_browse', 'Browse'))
            btn_tb_gen.config(text=self.tr('tbatch_generate', 'Generate Batch File'))
            btn_tb_close.config(text=self.tr('ui_close', 'Close'))
            cur = status_label.cget('text')
            if 'Ready' in cur or '就绪' in cur:
                status_label.config(text=self.tr('tbatch_ready', 'Ready to generate'))

        generator_window.protocol('WM_DELETE_WINDOW', _close_tbatch)
        self._register_tool_lang_refresh(_refresh_tbatch_lang)
        _refresh_tbatch_lang()
    
    def open_exp_data_processor(self):
        """Open Thermo-calc results extractor tool (Melting range + T-zero)."""
        processor_window = tk.Toplevel(self.root)
        processor_window.geometry("800x800")
        self._present_tool_window(processor_window, self.root)

        # Create main frame
        main_frame = ttk.Frame(processor_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=self.tr('exptc_heading', 'Extract Thermo-calc Results'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 10))
        
        info_label = ttk.Label(
            main_frame,
            text=self.tr('exptc_intro', ''),
            wraplength=720,
            justify="center",
        )
        info_label.pack(pady=(0, 10))

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        tab_mr = ttk.Frame(notebook, padding="10")
        tab_t0 = ttk.Frame(notebook, padding="10")
        notebook.add(tab_mr, text=self.tr('exptc_tab_mr', 'Melting Range'))
        notebook.add(tab_t0, text=self.tr('exptc_tab_t0', 'T-zero'))

        # -----------------------------
        # Tab 1: Melting range (legacy)
        # -----------------------------
        mr_folder_frame = ttk.LabelFrame(tab_mr, text=self.tr('exptc_mr_folder', 'Select Folder Containing .exp Files'), padding="12")
        mr_folder_frame.pack(fill=tk.X, pady=8)

        mr_folder_var = tk.StringVar()
        ttk.Entry(mr_folder_frame, textvariable=mr_folder_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_exptc_mr_folder():
            p = filedialog.askdirectory(title=self.tr('exptc_fd_mr_folder', 'Select Folder with .exp Files'))
            if p:
                mr_folder_var.set(p)

        btn_exptc_mr_fd = ttk.Button(
            mr_folder_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=browse_exptc_mr_folder,
        )
        btn_exptc_mr_fd.pack(side=tk.RIGHT, padx=5)

        mr_pattern_frame = ttk.LabelFrame(tab_mr, text=self.tr('exptc_mr_pattern', 'Filename Pattern (Optional)'), padding="12")
        mr_pattern_frame.pack(fill=tk.X, pady=8)

        lbl_exptc_mr_pat = ttk.Label(mr_pattern_frame, text=self.tr('exptc_mr_pattern_lbl', 'Pattern:'))
        lbl_exptc_mr_pat.pack(side=tk.LEFT, padx=5)
        # Leave empty to use automatic element parsing from filename like: Al0.04Mg0.09Si_np-T.exp
        mr_pattern_var = tk.StringVar(value="")
        ttk.Entry(mr_pattern_frame, textvariable=mr_pattern_var, width=55).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        lbl_exptc_mr_hint = ttk.Label(
            mr_pattern_frame,
            text=self.tr('exptc_mr_pattern_hint', ''),
            font=("Arial", 8),
            foreground="gray",
        )
        lbl_exptc_mr_hint.pack(side=tk.LEFT, padx=5)

        mr_output_frame = ttk.LabelFrame(tab_mr, text=self.tr('exptc_output_xlsx', 'Output Excel File'), padding="12")
        mr_output_frame.pack(fill=tk.X, pady=8)

        mr_output_var = tk.StringVar(value="melting_range.xlsx")
        ttk.Entry(mr_output_frame, textvariable=mr_output_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_exptc_mr_out():
            p = filedialog.asksaveasfilename(
                title=self.tr('tbatch_fd_save_out', 'Save Output File'),
                defaultextension=".xlsx",
                filetypes=[
                    (self.tr('pandat_fd_excel', 'Excel files'), "*.xlsx"),
                    (self.tr('filetype_all', 'All files'), "*.*"),
                ],
            )
            if p:
                mr_output_var.set(p)

        btn_exptc_mr_out = ttk.Button(
            mr_output_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=browse_exptc_mr_out,
        )
        btn_exptc_mr_out.pack(side=tk.RIGHT, padx=5)

        mr_status_frame = ttk.LabelFrame(tab_mr, text=self.tr('exptc_status', 'Status'), padding="10")
        mr_status_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        mr_status_text = tk.Text(mr_status_frame, height=10, width=70, wrap=tk.WORD, state=tk.DISABLED)
        mr_status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mr_status_scrollbar = ttk.Scrollbar(mr_status_frame, orient=tk.VERTICAL, command=mr_status_text.yview)
        mr_status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        mr_status_text.configure(yscrollcommand=mr_status_scrollbar.set)

        def mr_log(message):
            mr_status_text.config(state=tk.NORMAL)
            mr_status_text.insert(tk.END, message + "\n")
            mr_status_text.see(tk.END)
            mr_status_text.config(state=tk.DISABLED)
            processor_window.update()

        def mr_snap_near_zero(v, eps=1e-7):
            """Treat tiny float noise (e.g. 4e-8) as 0 in Excel output."""
            try:
                fv = float(v)
            except (TypeError, ValueError):
                return v
            return 0.0 if abs(fv) < eps else fv

        def mr_parse_filename_number_element_pairs(file_name):
            """
            Parse filename like 'Al0.04Mg0.09Si_np-T.exp' as:
              w(Mg)=0.04, w(Si)=0.09
            by extracting repeated 'number + element' pairs (e.g. 0.04Mg, 0.09Si).
            """
            base = os.path.splitext(os.path.basename(file_name))[0]
            base = re.sub(r"_np-T$", "", base, flags=re.IGNORECASE)
            base = re.sub(r"_T$", "", base, flags=re.IGNORECASE)
            pairs = re.findall(r"(\d+(?:\.\d+)?)([A-Z][a-z]?)", base)
            comp = {}
            for num, el in pairs:
                try:
                    comp[f"w({el.title()})"] = mr_snap_near_zero(float(num))
                except ValueError:
                    continue
            return comp

        def mr_extract_data_from_exp_file(file_path):
            """Extract Temperature vs LiquidFraction from .exp file for melting range."""
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    lines = file.readlines()

                data_lines = []
                start_collecting = False

                for line in lines:
                    s = line.strip()
                    if s.startswith("$ PLOTTED"):
                        start_collecting = True
                        continue
                    if s.startswith("BLOCKEND"):
                        start_collecting = False
                        continue
                    if start_collecting:
                        split_line = s.split()
                        if len(split_line) >= 2:
                            try:
                                temp = float(split_line[0])
                                liquid_frac = float(split_line[1])
                                data_lines.append([temp, liquid_frac])
                            except ValueError:
                                continue

                if not data_lines:
                    return None
                return pd.DataFrame(data_lines, columns=["Temperature", "LiquidFraction"])
            except Exception as e:
                mr_log(f"Error reading {file_path}: {str(e)}")
                return None

        def mr_find_temperatures(data):
            """Find liquidus and solidus temperatures."""
            try:
                tolerance = 1e-8
                temp_liq_1 = data[
                    (data["LiquidFraction"] >= 1.0 - tolerance) & (data["LiquidFraction"] <= 1.0 + tolerance)
                ]["Temperature"].min()
                temp_liq_0 = data[data["LiquidFraction"].round(10) == 0.0]["Temperature"].max()
                return temp_liq_1, temp_liq_0
            except Exception:
                return None, None

        def mr_process_files():
            """Process all .exp files in folder -> melting range excel."""
            try:
                folder_path = mr_folder_var.get()
                output_file = mr_output_var.get()
                pattern_str = mr_pattern_var.get().strip()

                if not folder_path or not os.path.exists(folder_path):
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_need_folder', 'Please select a valid folder!'))
                    return
                if not output_file:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_need_out', 'Please specify an output file!'))
                    return

                mr_status_text.config(state=tk.NORMAL)
                mr_status_text.delete("1.0", tk.END)
                mr_status_text.config(state=tk.DISABLED)

                mr_log(f"Processing folder: {folder_path}")
                mr_log(f"Output file: {output_file}")

                exp_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".exp")]
                if not exp_files:
                    mr_log("No .exp files found in the selected folder!")
                    messagebox.showwarning(self.tr('dlg_warning', 'Warning'), self.tr('exp_no_exp', 'No .exp files found in the selected folder!'))
                    return
                mr_log(f"Found {len(exp_files)} .exp file(s)")

                pattern = None
                if pattern_str:
                    try:
                        pattern = re.compile(pattern_str)
                        mr_log(f"Using pattern: {pattern_str}")
                    except re.error as e:
                        mr_log(f"Invalid pattern: {str(e)}")
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_regex_bad', 'Invalid regex pattern: {e}').format(e=str(e)))
                        return

                records = []
                processed_count = 0
                error_count = 0

                for file_name in exp_files:
                    file_path = os.path.join(folder_path, file_name)
                    mr_log(f"Processing: {file_name}")

                    comp_cols = {}
                    if pattern:
                        match = pattern.match(file_name)
                        if match:
                            try:
                                for i in range(len(match.groups())):
                                    comp_cols[f"w(Element_{i+1})"] = mr_snap_near_zero(float(match.group(i + 1)))
                            except Exception:
                                comp_cols = {}
                        else:
                            mr_log("  Warning: Filename doesn't match pattern; falling back to auto parse")
                            comp_cols = mr_parse_filename_number_element_pairs(file_name)
                    else:
                        comp_cols = mr_parse_filename_number_element_pairs(file_name)

                    data = mr_extract_data_from_exp_file(file_path)
                    if data is None or data.empty:
                        mr_log("  Error: Could not extract data from file")
                        error_count += 1
                        continue

                    temp_liq_1, temp_liq_0 = mr_find_temperatures(data)
                    if temp_liq_1 is None or temp_liq_0 is None or np.isnan(temp_liq_1) or np.isnan(temp_liq_0):
                        mr_log("  Error: Could not find liquidus or solidus temperature")
                        error_count += 1
                        continue

                    melting_range = temp_liq_1 - temp_liq_0
                    rec = {"File": file_name}
                    rec.update(comp_cols)
                    rec["Liquidus_Temperature"] = float(temp_liq_1)
                    rec["Solidus_Temperature"] = float(temp_liq_0)
                    rec["Melting_Range"] = mr_snap_near_zero(float(melting_range))
                    records.append(rec)
                    processed_count += 1
                    mr_log(
                        f"  Success: Liquidus={temp_liq_1:.2f}K, Solidus={temp_liq_0:.2f}K, Range={melting_range:.2f}K"
                    )

                if not records:
                    mr_log("No valid results to save!")
                    messagebox.showwarning(self.tr('dlg_warning', 'Warning'), self.tr('exp_no_results', 'No valid results extracted from files!'))
                    return

                df = pd.DataFrame(records)
                for col in df.columns:
                    if col.startswith("w("):
                        df[col] = pd.to_numeric(df[col], errors="coerce").map(mr_snap_near_zero).fillna(0.0)
                if "Melting_Range" in df.columns:
                    df["Melting_Range"] = pd.to_numeric(df["Melting_Range"], errors="coerce").map(mr_snap_near_zero)

                w_cols = sorted([c for c in df.columns if c.startswith("w(")])
                out_cols = [c for c in ["Liquidus_Temperature", "Solidus_Temperature", "Melting_Range"] if c in df.columns]
                df = df[["File"] + w_cols + out_cols]
                try:
                    df.to_excel(output_file, index=False)
                    mr_log(f"\nSuccessfully saved {len(df)} results to {output_file}")
                    mr_log(f"Processed: {processed_count}, Errors: {error_count}")
                    messagebox.showinfo(
                        self.tr('dlg_success', 'Success'),
                        self.tr(
                            'exptc_mr_done',
                            'Results extracted successfully!\n\n'
                            'Processed: {ok} files\n'
                            'Errors: {bad} files\n'
                            'Results saved to: {path}',
                        ).format(ok=processed_count, bad=error_count, path=output_file),
                    )
                except Exception as e:
                    mr_log(f"Error saving file: {str(e)}")
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_save_fail', 'Failed to save Excel file:\n{e}').format(e=str(e)))

            except Exception as e:
                mr_log(f"Error: {str(e)}")
                messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_process_fail', 'Processing failed:\n{e}').format(e=str(e)))

        mr_buttons = ttk.Frame(tab_mr)
        mr_buttons.pack(pady=10)
        btn_exptc_mr_proc = ttk.Button(
            mr_buttons,
            text=self.tr('exptc_process', 'Process Files'),
            command=mr_process_files,
        )
        btn_exptc_mr_proc.pack(side=tk.LEFT, padx=10)

        # -----------------------------
        # Tab 2: T-zero extraction
        # -----------------------------
        t0_folder_frame = ttk.LabelFrame(tab_t0, text=self.tr('exptc_t0_folder', 'Select Folder Containing *_T0.exp Files'), padding="12")
        t0_folder_frame.pack(fill=tk.X, pady=8)

        t0_folder_var = tk.StringVar()
        ttk.Entry(t0_folder_frame, textvariable=t0_folder_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_exptc_t0_folder():
            p = filedialog.askdirectory(title=self.tr('exptc_fd_t0_folder', 'Select Folder with *_T0.exp Files'))
            if p:
                t0_folder_var.set(p)

        btn_exptc_t0_fd = ttk.Button(
            t0_folder_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=browse_exptc_t0_folder,
        )
        btn_exptc_t0_fd.pack(side=tk.RIGHT, padx=5)

        t0_filter_frame = ttk.LabelFrame(tab_t0, text=self.tr('exptc_t0_filter', 'Filename Filter (Optional)'), padding="12")
        t0_filter_frame.pack(fill=tk.X, pady=8)
        lbl_exptc_t0_rx = ttk.Label(t0_filter_frame, text=self.tr('exptc_t0_regex_lbl', 'Regex:'))
        lbl_exptc_t0_rx.pack(side=tk.LEFT, padx=5)
        t0_filter_var = tk.StringVar(value=r".*_T0\.exp$")
        ttk.Entry(t0_filter_frame, textvariable=t0_filter_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        lbl_exptc_t0_hint = ttk.Label(
            t0_filter_frame,
            text=self.tr('exptc_t0_filter_hint', 'Only matching filenames will be processed.'),
            font=("Arial", 8),
            foreground="gray",
        )
        lbl_exptc_t0_hint.pack(side=tk.LEFT, padx=5)

        t0_output_frame = ttk.LabelFrame(tab_t0, text=self.tr('exptc_output_xlsx', 'Output Excel File'), padding="12")
        t0_output_frame.pack(fill=tk.X, pady=8)

        t0_output_var = tk.StringVar(value="t_zero.xlsx")
        ttk.Entry(t0_output_frame, textvariable=t0_output_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_exptc_t0_out():
            p = filedialog.asksaveasfilename(
                title=self.tr('tbatch_fd_save_out', 'Save Output File'),
                defaultextension=".xlsx",
                filetypes=[
                    (self.tr('pandat_fd_excel', 'Excel files'), "*.xlsx"),
                    (self.tr('filetype_all', 'All files'), "*.*"),
                ],
            )
            if p:
                t0_output_var.set(p)

        btn_exptc_t0_out = ttk.Button(
            t0_output_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=browse_exptc_t0_out,
        )
        btn_exptc_t0_out.pack(side=tk.RIGHT, padx=5)

        t0_status_frame = ttk.LabelFrame(tab_t0, text=self.tr('exptc_status', 'Status'), padding="10")
        t0_status_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        t0_status_text = tk.Text(t0_status_frame, height=10, width=70, wrap=tk.WORD, state=tk.DISABLED)
        t0_status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        t0_status_scrollbar = ttk.Scrollbar(t0_status_frame, orient=tk.VERTICAL, command=t0_status_text.yview)
        t0_status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        t0_status_text.configure(yscrollcommand=t0_status_scrollbar.set)

        def t0_log(message):
            t0_status_text.config(state=tk.NORMAL)
            t0_status_text.insert(tk.END, message + "\n")
            t0_status_text.see(tk.END)
            t0_status_text.config(state=tk.DISABLED)
            processor_window.update()

        def t0_snap_near_zero_mass_fraction(v, eps=1e-7):
            """Mass fractions: treat tiny float noise (e.g. 5e-9) as 0 for Excel output."""
            try:
                fv = float(v)
            except (TypeError, ValueError):
                return v
            return 0.0 if abs(fv) < eps else fv

        def t0_parse_filename_param(file_name):
            """
            Parse parameter element and its w() from file name like:
              Al-0.030Li_T0.exp  -> ('Li', 0.030)
              AlCu-0.00Li_T0.exp -> ('Li', 0.00)
            Returns (el, val) or (None, None) if not found.
            """
            m = re.search(r"[-_](\d+(?:\.\d+)?)([A-Za-z]{1,2})_T0\.exp$", file_name)
            if not m:
                m = re.search(r"(\d+(?:\.\d+)?)([A-Za-z]{1,2})_T0\.exp$", file_name)
            if not m:
                return None, None
            val = float(m.group(1))
            el = m.group(2).title()
            return el, val

        def t0_extract_xy_from_exp(file_path):
            """
            Extract X element (from XTEXT W(...)) and the first BLOCK's X/Y data.
            Returns (x_el, rows) where rows is list of (x, y).
            """
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                x_el = None
                for line in lines[:50]:
                    m = re.search(r"^\s*XTEXT\s+W\(([^)]+)\)", line.strip(), flags=re.IGNORECASE)
                    if m:
                        x_el = m.group(1).strip().title()
                        break

                rows = []
                # Some .exp files contain multiple blocks; collect all $PLOTTED..BLOCKEND sections.
                start_collecting = False
                seen = set()
                for line in lines:
                    s = line.strip()
                    if s.startswith("$ PLOTTED"):
                        start_collecting = True
                        continue
                    if start_collecting and s.startswith("BLOCKEND"):
                        start_collecting = False
                        continue
                    if start_collecting:
                        parts = s.split()
                        if len(parts) >= 2:
                            try:
                                x = float(parts[0])
                                y = float(parts[1])
                                # Snap tiny x noise to 0 before de-duplication
                                x_s = t0_snap_near_zero_mass_fraction(x)
                                key = (round(float(x_s), 12), round(y, 8))
                                if key not in seen:
                                    rows.append((float(x_s), y))
                                    seen.add(key)
                            except ValueError:
                                continue
                return x_el, rows
            except Exception:
                return None, []

        def t0_process_files():
            try:
                folder_path = t0_folder_var.get()
                output_file = t0_output_var.get()
                filter_str = t0_filter_var.get().strip()

                if not folder_path or not os.path.exists(folder_path):
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_need_folder', 'Please select a valid folder!'))
                    return
                if not output_file:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_need_out', 'Please specify an output file!'))
                    return

                t0_status_text.config(state=tk.NORMAL)
                t0_status_text.delete("1.0", tk.END)
                t0_status_text.config(state=tk.DISABLED)

                t0_log(f"Processing folder: {folder_path}")
                t0_log(f"Output file: {output_file}")

                name_filter = None
                if filter_str:
                    try:
                        name_filter = re.compile(filter_str)
                        t0_log(f"Using filename filter: {filter_str}")
                    except re.error as e:
                        t0_log(f"Invalid regex: {str(e)}")
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_regex_bad', 'Invalid regex pattern: {e}').format(e=str(e)))
                        return

                exp_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".exp")]
                if name_filter:
                    exp_files = [f for f in exp_files if name_filter.match(f)]

                if not exp_files:
                    t0_log("No matching .exp files found!")
                    messagebox.showwarning(self.tr('dlg_warning', 'Warning'), self.tr('exp_t0_no_match', 'No matching .exp files found in the selected folder!'))
                    return

                t0_log(f"Found {len(exp_files)} file(s)")

                records = []
                processed = 0
                errors = 0
                for file_name in sorted(exp_files):
                    file_path = os.path.join(folder_path, file_name)
                    p_el, p_val = t0_parse_filename_param(file_name)
                    if p_el is None:
                        t0_log(f"Skipping (cannot parse filename param): {file_name}")
                        errors += 1
                        continue

                    x_el, rows = t0_extract_xy_from_exp(file_path)
                    if not x_el or not rows:
                        t0_log(f"Skipping (cannot parse exp data): {file_name}")
                        errors += 1
                        continue

                    for x, t0 in rows:
                        records.append(
                            {
                                "File": file_name,
                                f"w({p_el})": t0_snap_near_zero_mass_fraction(p_val),
                                f"w({x_el})": t0_snap_near_zero_mass_fraction(x),
                                "T0 (K)": t0,
                            }
                        )

                    processed += 1
                    t0_log(f"OK: {file_name} -> {len(rows)} points, param w({p_el})={p_val}")

                if not records:
                    t0_log("No records extracted.")
                    messagebox.showwarning(self.tr('dlg_warning', 'Warning'), self.tr('exp_t0_no_data', 'No valid data extracted from files!'))
                    return

                df = pd.DataFrame(records)
                for _col in df.columns:
                    if _col.startswith("w("):
                        df[_col] = df[_col].map(t0_snap_near_zero_mass_fraction)
                # Try to sort by param then x
                try:
                    param_cols = [c for c in df.columns if c.startswith("w(")]
                    if len(param_cols) >= 2:
                        df = df.sort_values(by=[param_cols[0], param_cols[1]])
                except Exception:
                    pass

                # Final de-dup after snapping/rounding (prevents duplicates caused by tiny float noise)
                try:
                    dedup_df = df.copy()
                    for _col in dedup_df.columns:
                        if _col.startswith("w("):
                            dedup_df[_col] = pd.to_numeric(dedup_df[_col], errors="coerce").round(12)
                    if "T0 (K)" in dedup_df.columns:
                        dedup_df["T0 (K)"] = pd.to_numeric(dedup_df["T0 (K)"], errors="coerce").round(8)
                    subset_cols = [c for c in ["File"] + [c for c in dedup_df.columns if c.startswith("w(")] + ["T0 (K)"] if c in dedup_df.columns]
                    df = dedup_df.drop_duplicates(subset=subset_cols, keep="first")
                except Exception:
                    pass

                try:
                    df.to_excel(output_file, index=False)
                    t0_log(f"\nSaved {len(df)} rows to {output_file}")
                    t0_log(f"Processed files: {processed}, Errors: {errors}")
                    messagebox.showinfo(
                        self.tr('dlg_success', 'Success'),
                        self.tr(
                            'exptc_t0_done',
                            'T-zero extracted successfully!\n\n'
                            'Processed: {ok} files\n'
                            'Errors: {bad} files\n'
                            'Rows: {rows}\n'
                            'Saved to: {path}',
                        ).format(ok=processed, bad=errors, rows=len(df), path=output_file),
                    )
                except Exception as e:
                    t0_log(f"Error saving file: {str(e)}")
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_save_fail', 'Failed to save Excel file:\n{e}').format(e=str(e)))

            except Exception as e:
                t0_log(f"Error: {str(e)}")
                messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('exp_process_fail', 'Processing failed:\n{e}').format(e=str(e)))

        t0_buttons = ttk.Frame(tab_t0)
        t0_buttons.pack(pady=10)
        btn_exptc_t0_proc = ttk.Button(
            t0_buttons,
            text=self.tr('exptc_process', 'Process Files'),
            command=t0_process_files,
        )
        btn_exptc_t0_proc.pack(side=tk.LEFT, padx=10)

        # Bottom buttons (shared)
        bottom_buttons = ttk.Frame(main_frame)
        bottom_buttons.pack(pady=5)

        def _close_exptc():
            self._unregister_tool_lang_refresh(_refresh_exptc_lang)
            processor_window.destroy()

        btn_exptc_close = ttk.Button(
            bottom_buttons,
            text=self.tr('extp_close', 'Close'),
            command=_close_exptc,
        )
        btn_exptc_close.pack(side=tk.LEFT, padx=10)

        def _refresh_exptc_lang():
            try:
                if not processor_window.winfo_exists():
                    return
            except tk.TclError:
                return
            processor_window.title(self.tr('exptc_win_title', 'Extract Thermo-calc Results'))
            title_label.config(text=self.tr('exptc_heading', 'Extract Thermo-calc Results'))
            info_label.config(text=self.tr('exptc_intro', ''))
            try:
                notebook.tab(0, text=self.tr('exptc_tab_mr', 'Melting Range'))
                notebook.tab(1, text=self.tr('exptc_tab_t0', 'T-zero'))
            except tk.TclError:
                pass
            mr_folder_frame.config(text=self.tr('exptc_mr_folder', 'Select Folder Containing .exp Files'))
            btn_exptc_mr_fd.config(text=self.tr('pandat_browse', 'Browse'))
            mr_pattern_frame.config(text=self.tr('exptc_mr_pattern', 'Filename Pattern (Optional)'))
            lbl_exptc_mr_pat.config(text=self.tr('exptc_mr_pattern_lbl', 'Pattern:'))
            lbl_exptc_mr_hint.config(text=self.tr('exptc_mr_pattern_hint', ''))
            mr_output_frame.config(text=self.tr('exptc_output_xlsx', 'Output Excel File'))
            btn_exptc_mr_out.config(text=self.tr('pandat_browse', 'Browse'))
            mr_status_frame.config(text=self.tr('exptc_status', 'Status'))
            btn_exptc_mr_proc.config(text=self.tr('exptc_process', 'Process Files'))
            t0_folder_frame.config(text=self.tr('exptc_t0_folder', 'Select Folder Containing *_T0.exp Files'))
            btn_exptc_t0_fd.config(text=self.tr('pandat_browse', 'Browse'))
            t0_filter_frame.config(text=self.tr('exptc_t0_filter', 'Filename Filter (Optional)'))
            lbl_exptc_t0_rx.config(text=self.tr('exptc_t0_regex_lbl', 'Regex:'))
            lbl_exptc_t0_hint.config(text=self.tr('exptc_t0_filter_hint', 'Only matching filenames will be processed.'))
            t0_output_frame.config(text=self.tr('exptc_output_xlsx', 'Output Excel File'))
            btn_exptc_t0_out.config(text=self.tr('pandat_browse', 'Browse'))
            t0_status_frame.config(text=self.tr('exptc_status', 'Status'))
            btn_exptc_t0_proc.config(text=self.tr('exptc_process', 'Process Files'))
            btn_exptc_close.config(text=self.tr('extp_close', 'Close'))

        processor_window.protocol('WM_DELETE_WINDOW', _close_exptc)
        self._register_tool_lang_refresh(_refresh_exptc_lang)
        _refresh_exptc_lang()
    
    def open_extract_pandat_results(self):
        """Open Pandat results extractor tool"""
        extractor_window = tk.Toplevel(self.root)
        extractor_window.geometry("720x680")
        extractor_window.minsize(600, 520)
        self._present_tool_window(extractor_window, self.root)

        # Bottom bar: always visible at bottom of window
        bottom_bar = ttk.Frame(extractor_window, padding="10")
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Scrollable content above the buttons
        canvas = tk.Canvas(extractor_window, highlightthickness=0)
        scrollbar = ttk.Scrollbar(extractor_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding="20")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        main_frame = scrollable_frame
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=self.tr('extp_heading', 'Extract Pandat Results'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 10))
        
        # Instructions
        info_label = ttk.Label(
            main_frame,
            text=self.tr('extp_intro', ''),
            wraplength=650,
            justify='center',
        )
        info_label.pack(pady=(0, 20))
        
        # Lever folder selection
        lever_frame = ttk.LabelFrame(main_frame, text=self.tr('extp_lever_folder', 'Lever/Equilibrium Folder'), padding="15")
        lever_frame.pack(fill=tk.X, pady=10)
        
        lever_folder_var = tk.StringVar()
        ttk.Entry(lever_frame, textvariable=lever_folder_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_extp_lever():
            p = filedialog.askdirectory(title=self.tr('extp_fd_lever', 'Select Lever folder'))
            if p:
                lever_folder_var.set(p)

        btn_extp_lever = ttk.Button(lever_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_extp_lever)
        btn_extp_lever.pack(side=tk.RIGHT, padx=5)
        
        # Scheil folder selection
        scheil_frame = ttk.LabelFrame(main_frame, text=self.tr('extp_scheil_folder', 'Scheil Folder'), padding="15")
        scheil_frame.pack(fill=tk.X, pady=10)
        
        scheil_folder_var = tk.StringVar()
        ttk.Entry(scheil_frame, textvariable=scheil_folder_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_extp_scheil():
            p = filedialog.askdirectory(title=self.tr('extp_fd_scheil', 'Select Scheil folder'))
            if p:
                scheil_folder_var.set(p)

        btn_extp_scheil = ttk.Button(scheil_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_extp_scheil)
        btn_extp_scheil.pack(side=tk.RIGHT, padx=5)
        
        # Output directory
        output_frame = ttk.LabelFrame(main_frame, text=self.tr('extp_output_dir', 'Output Directory'), padding="15")
        output_frame.pack(fill=tk.X, pady=10)
        
        output_dir_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=output_dir_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_extp_out():
            p = filedialog.askdirectory(title=self.tr('extp_fd_output', 'Select output directory'))
            if p:
                output_dir_var.set(p)

        btn_extp_out = ttk.Button(output_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_extp_out)
        btn_extp_out.pack(side=tk.RIGHT, padx=5)
        
        # Status area
        status_frame = ttk.LabelFrame(main_frame, text=self.tr('extp_status', 'Status'), padding="8")
        status_frame.pack(fill=tk.X, pady=10)
        status_label = ttk.Label(status_frame, text=self.tr('extp_ready', 'Ready to extract'), foreground="blue", wraplength=620)
        status_label.pack(anchor="w")
        
        def _find_col(df, names):
            """Find column in df by case-insensitive match. names: list of candidates e.g. ['fs','f_s']"""
            if df is None or not hasattr(df, 'columns'):
                return None
            cols_upper = {str(c).strip().upper(): c for c in df.columns if isinstance(c, str)}
            for n in names:
                nu = str(n).strip().upper()
                if nu in cols_upper:
                    return cols_upper[nu]
            return None
        
        def extract_results():
            """Extract results from CSV/DAT files"""
            try:
                lever_folder = lever_folder_var.get()
                scheil_folder = scheil_folder_var.get()
                output_dir = output_dir_var.get() or os.getcwd()
                
                if not lever_folder or not os.path.exists(lever_folder):
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('extp_need_lever', 'Please select a valid Lever folder!'))
                    return
                
                if not scheil_folder or not os.path.exists(scheil_folder):
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('extp_need_scheil', 'Please select a valid Scheil folder!'))
                    return
                
                status_label.config(text=self.tr('extp_processing', 'Processing files...'), foreground="orange")
                extractor_window.update()
                
                # Initialize data lists
                p_data_list = []
                ts_data_list = []
                p_s_data_list = []
                ts_s_data_list = []
                
                # Process Lever files (.csv and .dat)
                lever_files = sorted([f for f in os.listdir(lever_folder) if f.lower().endswith(('.csv', '.dat'))])
                if not lever_files:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('extp_no_csv', 'No CSV or DAT files found in Lever folder!'))
                    return
                
                # Process each Lever file for P.xlsx
                for lev_file in lever_files:
                    lev_path = os.path.join(lever_folder, lev_file)
                    df = pd.read_csv(lev_path, sep='\t', header=0, skiprows=[1])  # Skip unit row
                    
                    fs_col = _find_col(df, ['fs', 'f_s', 'Fs'])
                    t_col = _find_col(df, ['T', 't', 'Temperature'])
                    if fs_col is None or t_col is None:
                        status_label.config(text=f"Skipped {lev_file}: missing 'fs' or 'T' column. Available: {list(df.columns)[:10]}...", foreground="orange")
                        continue
                    # Filter: fs < 0.000001, get row with max T
                    df['fs_num'] = pd.to_numeric(df[fs_col], errors='coerce')
                    df['T_num'] = pd.to_numeric(df[t_col], errors='coerce')
                    filtered = df[df['fs_num'] < 0.000001].copy()
                    
                    if not filtered.empty:
                        max_t_row = filtered.loc[filtered['T_num'].idxmax()]
                        p_data_list.append(max_t_row)
                
                # Extract columns for P.xlsx: T, fs, w(*), w(*@*), fw(@*), -T//fw(@*), dwdT_L(*@LIQUID)
                # Phases and elements are detected from column names (w(ELEMENT@PHASE)); first * = element, second * = phase
                if p_data_list:
                    p_df = pd.DataFrame(p_data_list)
                    t_col_p = _find_col(p_df, ['T', 't', 'Temperature'])
                    fs_col_p = _find_col(p_df, ['fs', 'f_s', 'Fs'])
                    p_cols = []
                    if t_col_p:
                        p_cols.append(t_col_p)
                    if fs_col_p:
                        p_cols.append(fs_col_p)
                    # fw(@PHASE) and -T//fw(@PHASE) for any phase present in data
                    p_cols.extend([c for c in p_df.columns if isinstance(c, str) and re.match(r'^fw\s*\(\s*@\s*[A-Za-z0-9_]+\s*\)$', c, re.IGNORECASE)])
                    p_cols.extend([c for c in p_df.columns if isinstance(c, str) and re.match(r'^-T//fw\s*\(\s*@\s*[A-Za-z0-9_]+\s*\)$', c, re.IGNORECASE)])
                    # w(*) overall composition
                    p_cols.extend([c for c in p_df.columns if re.match(r'^w\([A-Za-z]{1,3}\)$', c, re.IGNORECASE)])
                    # w(*@*) element-in-phase (any phase)
                    p_cols.extend([c for c in p_df.columns if isinstance(c, str) and re.match(r'^w\([A-Za-z]{1,3}\s*@\s*[A-Za-z0-9_]+\s*\)$', c, re.IGNORECASE)])
                    # dwdT_L(*@LIQUID)
                    p_cols.extend([c for c in p_df.columns if re.search(r'dwdT_L\([A-Za-z]{1,3}@LIQUID\)', c, re.IGNORECASE)])
                    p_cols = list(dict.fromkeys([c for c in p_cols if c in p_df.columns]))
                    p_output = p_df[p_cols].copy()
                    
                    p_output_path = os.path.join(output_dir, 'P.xlsx')
                    try:
                        p_output.to_excel(p_output_path, index=False)
                        status_label.config(text=f"P.xlsx saved: {len(p_output)} rows", foreground="green")
                    except PermissionError:
                        messagebox.showerror(
                            self.tr('dlg_permission', 'Permission Denied'),
                            self.tr(
                                'extp_permission',
                                'Cannot write {path}\n\nClose the file if it is open in Excel or another program, or choose a different output folder.',
                            ).format(path=p_output_path),
                        )
                        return
                
                # Process each Lever file for Ts.xlsx
                for lev_file in lever_files:
                    lev_path = os.path.join(lever_folder, lev_file)
                    df = pd.read_csv(lev_path, sep='\t', header=0, skiprows=[1])
                    fs_col = _find_col(df, ['fs', 'f_s', 'Fs'])
                    t_col = _find_col(df, ['T', 't', 'Temperature'])
                    if fs_col is None or t_col is None:
                        continue
                    df['fs_num'] = pd.to_numeric(df[fs_col], errors='coerce')
                    df['T_num'] = pd.to_numeric(df[t_col], errors='coerce')
                    
                    # Find fs max or fs=1 with max T
                    fs_max = df['fs_num'].max()
                    if abs(fs_max - 1.0) < 0.000001:
                        # fs=1 exists, get row with max T among fs=1
                        fs_one = df[abs(df['fs_num'] - 1.0) < 0.000001].copy()
                        max_t_row = fs_one.loc[fs_one['T_num'].idxmax()]
                    else:
                        # No fs=1, get row with fs max
                        max_fs_row = df[df['fs_num'] == fs_max].iloc[0]
                        max_t_row = max_fs_row
                    
                    ts_data_list.append(max_t_row)
                
                # Extract columns for Ts.xlsx: T, fs, w(*)
                if ts_data_list:
                    ts_df = pd.DataFrame(ts_data_list)
                    t_c = _find_col(ts_df, ['T', 't', 'Temperature'])
                    fs_c = _find_col(ts_df, ['fs', 'f_s', 'Fs'])
                    ts_cols = [c for c in (t_c, fs_c) if c is not None]
                    # Add w(*) columns (e.g., w(AL), w(MG), w(SI))
                    ts_cols.extend([c for c in ts_df.columns if re.match(r'^w\([A-Za-z]{1,3}\)$', c, re.IGNORECASE)])
                    ts_cols = list(dict.fromkeys([c for c in ts_cols if c in ts_df.columns]))
                    ts_output = ts_df[ts_cols].copy()
                    
                    ts_output_path = os.path.join(output_dir, 'Ts.xlsx')
                    try:
                        ts_output.to_excel(ts_output_path, index=False)
                        status_label.config(text=f"Ts.xlsx saved: {len(ts_output)} rows", foreground="green")
                    except PermissionError:
                        messagebox.showerror(
                            self.tr('dlg_permission', 'Permission Denied'),
                            self.tr(
                                'extp_permission',
                                'Cannot write {path}\n\nClose the file if it is open in Excel or another program, or choose a different output folder.',
                            ).format(path=ts_output_path),
                        )
                        return
                
                # Process Scheil files (same logic as Lever); accept both .csv and .dat (e.g. All table_Scheil CSV)
                scheil_files = sorted([f for f in os.listdir(scheil_folder) if f.lower().endswith(('.csv', '.dat'))])
                fcc_split_message_shown = False
                liquid_split_message_shown = False
                if scheil_files:
                    # Process for P-S.xlsx
                    for sch_file in scheil_files:
                        sch_path = os.path.join(scheil_folder, sch_file)
                        df = pd.read_csv(sch_path, sep='\t', header=0, skiprows=[1])

                        # Detect split FCC phases: fw(@FCC_A1#1), fw(@FCC_A1#2) or any fw(@*#digit)
                        fcc_split_cols = [
                            c for c in df.columns
                            if isinstance(c, str) and re.search(r'^fw\s*\(\s*@\s*[A-Za-z0-9_]+#\d+\s*\)$', c, re.IGNORECASE)
                        ]
                        if fcc_split_cols:
                            if not fcc_split_message_shown:
                                fcc_split_message_shown = True
                                if self.language == 'zh':
                                    _title = "FCC 相分离"
                                    _msg = (
                                        "检测到 FCC 分离成两个成分不同的 FCC 相（存在 fw(@FCC_A1#1)、fw(@FCC_A1#2) 等列）。\n\n"
                                        "将使用 T 对 fw(@FCC_A1#1) 求导计算 -T//fw(@FCC_A1) 并补充到 P-S.xlsx；若已有 -T//fw(@FCC_A1) 数值则保留。"
                                    )
                                else:
                                    _title = "FCC phase split"
                                    _msg = (
                                        "Detected FCC split into two compositionally different FCC phases "
                                        "(columns such as fw(@FCC_A1#1), fw(@FCC_A1#2) are present).\n\n"
                                        "-T//fw(@FCC_A1) will be computed from d(T)/d(fw(@FCC_A1#1)) and filled in P-S.xlsx; "
                                        "existing -T//fw(@FCC_A1) values are kept."
                                    )
                                messagebox.showinfo(_title, _msg, parent=extractor_window)
                            if self.language == 'zh':
                                status_label.config(
                                    text=f"FCC 分离已检测（如 {sch_file}）。正在用 fw(@FCC_A1#1) 计算 -T//fw(@FCC_A1)...",
                                    foreground="orange"
                                )
                            else:
                                status_label.config(
                                    text=f"FCC split detected (e.g. {sch_file}). Computing -T//fw(@FCC_A1) from fw(@FCC_A1#1)...",
                                    foreground="orange"
                                )
                            extractor_window.update()
                            base_fw_col = fcc_split_cols[0]
                            # Find or create -T//fw(@FCC_A1) column
                            q_col = None
                            for c in df.columns:
                                if isinstance(c, str) and c.strip().upper() == '-T//FW(@FCC_A1)':
                                    q_col = c
                                    break
                            if q_col is None:
                                q_col = '-T//fw(@FCC_A1)'
                            t_col_full = _find_col(df, ['T', 't', 'Temperature'])
                            if t_col_full and base_fw_col in df.columns:
                                t_vals = pd.to_numeric(df[t_col_full], errors='coerce')
                                fw_vals = pd.to_numeric(df[base_fw_col], errors='coerce')
                                mask = t_vals.notna() & fw_vals.notna()
                                if mask.sum() >= 3:
                                    # Sort by T for a stable numerical derivative
                                    idx_mask = df.index[mask]
                                    t_sorted = t_vals.loc[idx_mask].to_numpy()
                                    fw_sorted = fw_vals.loc[idx_mask].to_numpy()
                                    order = np.argsort(t_sorted)
                                    t_sorted = t_sorted[order]
                                    fw_sorted = fw_sorted[order]
                                    d_fw_dT = np.gradient(fw_sorted, t_sorted)
                                    q_sorted = -t_sorted * d_fw_dT
                                    q_series = pd.Series(index=idx_mask[order], data=q_sorted, dtype=float)
                                    if q_col not in df.columns:
                                        df[q_col] = np.nan
                                    existing_q = pd.to_numeric(df[q_col], errors='coerce')
                                    need_fill = existing_q.isna()
                                    df.loc[need_fill & q_series.notna(), q_col] = q_series[need_fill & q_series.notna()]

                        # Detect split Liquid phases: dwdT_L(*@LIQUID#1), dwdT_L(*@LIQUID#2) etc.
                        liquid_split_cols = [
                            c for c in df.columns
                            if isinstance(c, str) and re.match(r'^dwdT_L\s*\(\s*[A-Za-z]{1,3}\s*@\s*LIQUID#1\s*\)$', c, re.IGNORECASE)
                        ]
                        if liquid_split_cols:
                            if not liquid_split_message_shown:
                                liquid_split_message_shown = True
                                if self.language == 'zh':
                                    _ltitle = "Liquid 相分离"
                                    _lmsg = (
                                        "检测到 Liquid 分离成两个成分不同的 Liquid 相（存在 dwdT_L(*@LIQUID#1)、dwdT_L(*@LIQUID#2) 等列）。\n\n"
                                        "将使用对应的 dwdT_L(*@LIQUID#1) 补充到 dwdT_L(*@LIQUID) 并写入 P-S.xlsx；若 dwdT_L(*@LIQUID) 已有数值则保留。"
                                    )
                                else:
                                    _ltitle = "Liquid phase split"
                                    _lmsg = (
                                        "Detected Liquid split into two compositionally different Liquid phases "
                                        "(columns such as dwdT_L(*@LIQUID#1), dwdT_L(*@LIQUID#2) are present).\n\n"
                                        "dwdT_L(*@LIQUID) will be filled from the corresponding dwdT_L(*@LIQUID#1) in P-S.xlsx; "
                                        "existing dwdT_L(*@LIQUID) values are kept."
                                    )
                                messagebox.showinfo(_ltitle, _lmsg, parent=extractor_window)
                            if self.language == 'zh':
                                status_label.config(
                                    text=f"Liquid 分离已检测（如 {sch_file}）。正在用 dwdT_L(*@LIQUID#1) 补充 dwdT_L(*@LIQUID)...",
                                    foreground="orange"
                                )
                            else:
                                status_label.config(
                                    text=f"Liquid split detected (e.g. {sch_file}). Filling dwdT_L(*@LIQUID) from dwdT_L(*@LIQUID#1)...",
                                    foreground="orange"
                                )
                            extractor_window.update()
                            for col_hash1 in liquid_split_cols:
                                m = re.match(r'^dwdT_L\s*\(\s*([A-Za-z]{1,3})\s*@\s*LIQUID#1\s*\)$', col_hash1, re.IGNORECASE)
                                if not m:
                                    continue
                                elem = m.group(1)
                                target_col = f"dwdT_L({elem}@LIQUID)"
                                if target_col not in df.columns:
                                    df[target_col] = np.nan
                                src_vals = pd.to_numeric(df[col_hash1], errors='coerce')
                                existing = pd.to_numeric(df[target_col], errors='coerce')
                                need = existing.isna() & src_vals.notna()
                                df.loc[need, target_col] = src_vals[need]

                        # If phase-split compositions/phase-fractions exist (w(*@*#1), fw(@*#1)),
                        # use the #1 columns to back-fill base w(*@*) and fw(@*) columns before extracting rows.
                        # This is per-element and per-phase, and only fills missing values.
                        # 1) w(ELEM@PHASE#1) -> w(ELEM@PHASE)
                        for col_w_hash1 in df.columns:
                            if not isinstance(col_w_hash1, str):
                                continue
                            m_w = re.match(
                                r'^w\s*\(\s*([A-Za-z]{1,3})\s*@\s*([A-Za-z0-9_]+)#1\s*\)$',
                                col_w_hash1,
                                re.IGNORECASE
                            )
                            if not m_w:
                                continue
                            elem = m_w.group(1)
                            phase = m_w.group(2)
                            target_w = f"w({elem}@{phase})"
                            if target_w not in df.columns:
                                df[target_w] = np.nan
                            src_vals_w = pd.to_numeric(df[col_w_hash1], errors='coerce')
                            existing_w = pd.to_numeric(df[target_w], errors='coerce')
                            need_w = existing_w.isna() & src_vals_w.notna()
                            df.loc[need_w, target_w] = src_vals_w[need_w]

                        # 2) fw(@PHASE#1) -> fw(@PHASE)
                        for col_fw_hash1 in df.columns:
                            if not isinstance(col_fw_hash1, str):
                                continue
                            m_fw = re.match(
                                r'^fw\s*\(\s*@\s*([A-Za-z0-9_]+)#1\s*\)$',
                                col_fw_hash1,
                                re.IGNORECASE
                            )
                            if not m_fw:
                                continue
                            phase = m_fw.group(1)
                            target_fw = f"fw(@{phase})"
                            if target_fw not in df.columns:
                                df[target_fw] = np.nan
                            src_vals_fw = pd.to_numeric(df[col_fw_hash1], errors='coerce')
                            existing_fw = pd.to_numeric(df[target_fw], errors='coerce')
                            need_fw = existing_fw.isna() & src_vals_fw.notna()
                            df.loc[need_fw, target_fw] = src_vals_fw[need_fw]

                        fs_col = _find_col(df, ['fs', 'f_s', 'Fs'])
                        t_col = _find_col(df, ['T', 't', 'Temperature'])
                        if fs_col is None or t_col is None:
                            continue
                        df['fs_num'] = pd.to_numeric(df[fs_col], errors='coerce')
                        df['T_num'] = pd.to_numeric(df[t_col], errors='coerce')
                        filtered = df[df['fs_num'] < 0.000001].copy()
                        
                        if not filtered.empty:
                            max_t_row = filtered.loc[filtered['T_num'].idxmax()]
                            p_s_data_list.append(max_t_row)
                    
                    if p_s_data_list:
                        p_s_df = pd.DataFrame(p_s_data_list)
                        t_c = _find_col(p_s_df, ['T', 't', 'Temperature'])
                        fs_c = _find_col(p_s_df, ['fs', 'f_s', 'Fs'])
                        p_s_cols = [c for c in (t_c, fs_c) if c is not None]
                        p_s_cols.extend([c for c in p_s_df.columns if isinstance(c, str) and re.match(r'^fw\s*\(\s*@\s*[A-Za-z0-9_]+\s*\)$', c, re.IGNORECASE)])
                        p_s_cols.extend([c for c in p_s_df.columns if isinstance(c, str) and re.match(r'^-T//fw\s*\(\s*@\s*[A-Za-z0-9_]+\s*\)$', c, re.IGNORECASE)])
                        p_s_cols.extend([c for c in p_s_df.columns if re.match(r'^w\([A-Za-z]{1,3}\)$', c, re.IGNORECASE)])
                        p_s_cols.extend([c for c in p_s_df.columns if isinstance(c, str) and re.match(r'^w\([A-Za-z]{1,3}\s*@\s*[A-Za-z0-9_]+\s*\)$', c, re.IGNORECASE)])
                        p_s_cols.extend([c for c in p_s_df.columns if re.search(r'dwdT_L\([A-Za-z]{1,3}@LIQUID\)', c, re.IGNORECASE)])
                        p_s_cols = list(dict.fromkeys([c for c in p_s_cols if c in p_s_df.columns]))
                        p_s_output = p_s_df[p_s_cols].copy()
                        # P-S.xlsx must include fw(@FCC_A1) and -T//fw(@FCC_A1); add with 0 if missing from source
                        for fixed in ['fw(@FCC_A1)', '-T//fw(@FCC_A1)']:
                            if fixed not in p_s_output.columns:
                                p_s_output[fixed] = 0
                        # Fill missing w(*) and w(*@*) with 0
                        w_cols_ps = [c for c in p_s_output.columns if isinstance(c, str) and (re.match(r'^w\([A-Za-z]{1,3}\)$', c, re.IGNORECASE) or re.match(r'^w\([A-Za-z]{1,3}\s*@\s*[A-Za-z0-9_]+\s*\)$', c, re.IGNORECASE))]
                        if w_cols_ps:
                            p_s_output[w_cols_ps] = p_s_output[w_cols_ps].apply(pd.to_numeric, errors='coerce').fillna(0)
                        
                        p_s_output_path = os.path.join(output_dir, 'P-S.xlsx')
                        try:
                            p_s_output.to_excel(p_s_output_path, index=False)
                        except PermissionError:
                            messagebox.showerror(
                            self.tr('dlg_permission', 'Permission Denied'),
                            self.tr(
                                'extp_permission',
                                'Cannot write {path}\n\nClose the file if it is open in Excel or another program, or choose a different output folder.',
                            ).format(path=p_s_output_path),
                        )
                            return
                    
                    # Process for Ts-S.xlsx
                    for sch_file in scheil_files:
                        sch_path = os.path.join(scheil_folder, sch_file)
                        df = pd.read_csv(sch_path, sep='\t', header=0, skiprows=[1])
                        fs_col = _find_col(df, ['fs', 'f_s', 'Fs'])
                        t_col = _find_col(df, ['T', 't', 'Temperature'])
                        if fs_col is None or t_col is None:
                            continue
                        df['fs_num'] = pd.to_numeric(df[fs_col], errors='coerce')
                        df['T_num'] = pd.to_numeric(df[t_col], errors='coerce')
                        
                        fs_max = df['fs_num'].max()
                        if abs(fs_max - 1.0) < 0.000001:
                            fs_one = df[abs(df['fs_num'] - 1.0) < 0.000001].copy()
                            max_t_row = fs_one.loc[fs_one['T_num'].idxmax()]
                        else:
                            max_fs_row = df[df['fs_num'] == fs_max].iloc[0]
                            max_t_row = max_fs_row
                        
                        ts_s_data_list.append(max_t_row)
                    
                    if ts_s_data_list:
                        ts_s_df = pd.DataFrame(ts_s_data_list)
                        t_c = _find_col(ts_s_df, ['T', 't', 'Temperature'])
                        fs_c = _find_col(ts_s_df, ['fs', 'f_s', 'Fs'])
                        ts_s_cols = [c for c in (t_c, fs_c) if c is not None]
                        # Add w(*) columns
                        ts_s_cols.extend([c for c in ts_s_df.columns if re.match(r'^w\([A-Z]+\)$', c, re.IGNORECASE)])
                        # Remove duplicates and keep only existing columns
                        ts_s_cols = list(dict.fromkeys([c for c in ts_s_cols if c in ts_s_df.columns]))
                        ts_s_output = ts_s_df[ts_s_cols].copy()
                        # Fill missing w(*) with 0
                        w_cols_tss = [c for c in ts_s_output.columns if isinstance(c, str) and re.match(r'^w\([A-Za-z]{1,3}\)$', c, re.IGNORECASE)]
                        if w_cols_tss:
                            ts_s_output[w_cols_tss] = ts_s_output[w_cols_tss].apply(pd.to_numeric, errors='coerce').fillna(0)
                        
                        ts_s_output_path = os.path.join(output_dir, 'Ts-S.xlsx')
                        try:
                            ts_s_output.to_excel(ts_s_output_path, index=False)
                        except PermissionError:
                            messagebox.showerror(
                            self.tr('dlg_permission', 'Permission Denied'),
                            self.tr(
                                'extp_permission',
                                'Cannot write {path}\n\nClose the file if it is open in Excel or another program, or choose a different output folder.',
                            ).format(path=ts_s_output_path),
                        )
                            return
                
                status_label.config(
                    text=f"Success! Files saved to: {output_dir}\n"
                         f"P.xlsx: {len(p_data_list) if p_data_list else 0} rows\n"
                         f"Ts.xlsx: {len(ts_data_list) if ts_data_list else 0} rows\n"
                         f"P-S.xlsx: {len(p_s_data_list) if p_s_data_list else 0} rows\n"
                         f"Ts-S.xlsx: {len(ts_s_data_list) if ts_s_data_list else 0} rows",
                    foreground="green"
                )
                messagebox.showinfo(
                    self.tr('dlg_success', 'Success'),
                    self.tr(
                        'extp_success',
                        'Results extracted successfully!\n\nOutput directory: {dir}\n\nP.xlsx: {np} rows\nTs.xlsx: {nts} rows\nP-S.xlsx: {nps} rows\nTs-S.xlsx: {ntss} rows',
                    ).format(
                        dir=output_dir,
                        np=len(p_data_list) if p_data_list else 0,
                        nts=len(ts_data_list) if ts_data_list else 0,
                        nps=len(p_s_data_list) if p_s_data_list else 0,
                        ntss=len(ts_s_data_list) if ts_s_data_list else 0,
                    ),
                )
                
            except Exception as e:
                status_label.config(text=f"Error: {str(e)}", foreground="red")
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('extp_extract_fail', 'Failed to extract results:\n{e}').format(e=str(e)),
                )
                import traceback
                traceback.print_exc()
        
        # Buttons in bottom bar (always visible) - after extract_results is defined
        btn_inner = ttk.Frame(bottom_bar)
        btn_inner.pack(expand=True)

        def _close_extp():
            self._unregister_tool_lang_refresh(_refresh_extp_lang)
            extractor_window.destroy()

        btn_extp_run = ttk.Button(btn_inner, text=self.tr('extp_extract_btn', 'Extract Results'), command=extract_results)
        btn_extp_run.pack(side=tk.LEFT, padx=10)
        btn_extp_close = ttk.Button(btn_inner, text=self.tr('extp_close', 'Close'), command=_close_extp)
        btn_extp_close.pack(side=tk.LEFT, padx=10)

        def _refresh_extp_lang():
            try:
                if not extractor_window.winfo_exists():
                    return
            except tk.TclError:
                return
            extractor_window.title(self.tr('extp_win_title', 'Extract Pandat Results'))
            title_label.config(text=self.tr('extp_heading', 'Extract Pandat Results'))
            info_label.config(text=self.tr('extp_intro', ''))
            lever_frame.config(text=self.tr('extp_lever_folder', 'Lever/Equilibrium Folder'))
            btn_extp_lever.config(text=self.tr('pandat_browse', 'Browse'))
            scheil_frame.config(text=self.tr('extp_scheil_folder', 'Scheil Folder'))
            btn_extp_scheil.config(text=self.tr('pandat_browse', 'Browse'))
            output_frame.config(text=self.tr('extp_output_dir', 'Output Directory'))
            btn_extp_out.config(text=self.tr('pandat_browse', 'Browse'))
            status_frame.config(text=self.tr('extp_status', 'Status'))
            btn_extp_run.config(text=self.tr('extp_extract_btn', 'Extract Results'))
            btn_extp_close.config(text=self.tr('extp_close', 'Close'))
            cur = status_label.cget('text')
            if 'Ready' in cur or '就绪' in cur:
                status_label.config(text=self.tr('extp_ready', 'Ready to extract'))

        extractor_window.protocol('WM_DELETE_WINDOW', _close_extp)
        self._register_tool_lang_refresh(_refresh_extp_lang)
        _refresh_extp_lang()

    def open_partition_vector_plotter(self):
        """Open solid-liquid partition coefficient vector plotter tool"""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_k_dep_vec', 'Matplotlib is not installed. Cannot generate partition coefficient vectors.'))
            return
        win = tk.Toplevel(self.root)
        win.title(self.tr('plot_kvec', 'Plot Solid-Liquid Partition Coefficients'))
        win.geometry("900x800")
        self._present_tool_window(win, self.root)

        # Scrollable layout (similar style to liquidus vector plotter)
        canvas = tk.Canvas(win)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        outer_frame = ttk.Frame(scrollable_frame, padding="20")
        outer_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(outer_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_liquid_points = ttk.Frame(notebook, padding="20")
        tab_same_temp = ttk.Frame(notebook, padding="20")
        tab_isocomp = ttk.Frame(notebook, padding="20")
        notebook.add(
            tab_liquid_points,
            text=self.tr('partition_tab_liquid_points', 'Liquidus'),
        )
        notebook.add(
            tab_same_temp,
            text=self.tr('partition_tab_same_temp', 'isotherm'),
        )
        notebook.add(
            tab_isocomp,
            text=self.tr('partition_tab_isocomposition', 'isocomposition'),
        )

        # Keep using `main_frame` variable for the existing (P/P-S based) UI.
        main_frame = tab_liquid_points

        title_label = ttk.Label(
            main_frame,
            text=self.tr('plot_kvec', 'Plot Solid-Liquid Partition Coefficients'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 10))

        info_label = ttk.Label(
            main_frame,
            text=self.tr(
                'plot_k_liq_intro',
                'Plot k-vectors defined by k = w(*@solid)/w(*@LIQUID) from imported Pandat P or P-S data.\n'
                'The solid phase is chosen automatically from -T//fw(@*) columns and matching w(*@PHASE) columns.',
            ),
            wraplength=780,
            justify="left",
        )
        info_label.pack(pady=(0, 10))

        # Dataset selection
        dataset_frame = ttk.LabelFrame(
            main_frame, text=self.tr('stp_solidification_mode', 'Solidification Mode'), padding="10"
        )
        dataset_frame.pack(fill=tk.X, pady=5)
        dataset_var = tk.StringVar(value="Equilibrium")
        k_rb_eq = ttk.Radiobutton(
            dataset_frame,
            text=self.tr('plot_k_mode_eq', 'Equilibrium/Lever (P file)'),
            variable=dataset_var,
            value="Equilibrium",
        )
        k_rb_eq.pack(side=tk.LEFT, padx=10)
        k_rb_scheil = ttk.Radiobutton(
            dataset_frame,
            text=self.tr('plot_k_mode_scheil', 'Scheil (P-S file)'),
            variable=dataset_var,
            value="Scheil",
        )
        k_rb_scheil.pack(side=tk.LEFT, padx=10)

        # Element selection
        elem_frame = ttk.LabelFrame(
            main_frame, text=self.tr('el_frame_title', 'Element Selection'), padding="10"
        )
        elem_frame.pack(fill=tk.X, pady=5)
        k_lbl_x_el = ttk.Label(elem_frame, text=self.tr('stp_x_element', 'X Element:'))
        k_lbl_x_el.pack(side=tk.LEFT, padx=5)
        elem_x_var = tk.StringVar()
        elem_y_var = tk.StringVar()
        elements = self.available_elements if self.available_elements else sorted(PERIODIC_TABLE.keys())
        elem_x_combo = ttk.Combobox(
            elem_frame, textvariable=elem_x_var, values=elements, width=10, state="readonly"
        )
        elem_x_combo.pack(side=tk.LEFT, padx=5)
        k_lbl_y_el = ttk.Label(elem_frame, text=self.tr('stp_y_element', 'Y Element:'))
        k_lbl_y_el.pack(side=tk.LEFT, padx=15)
        elem_y_combo = ttk.Combobox(
            elem_frame, textvariable=elem_y_var, values=elements, width=10, state="readonly"
        )
        elem_y_combo.pack(side=tk.LEFT, padx=5)
        if elements:
            elem_x_var.set(elements[0])
        if len(elements) > 1:
            elem_y_var.set(elements[1])

        # Output name
        output_frame = ttk.LabelFrame(main_frame, text=self.tr('stp_output', 'Output'), padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        k_lbl_fn_prefix = ttk.Label(output_frame, text=self.tr('stp_filename_prefix', 'Filename prefix:'))
        k_lbl_fn_prefix.pack(side=tk.LEFT, padx=5)
        prefix_var = tk.StringVar(value="k_vectors")
        ttk.Entry(output_frame, textvariable=prefix_var, width=20).pack(side=tk.LEFT, padx=5)

        # Visualization options (similar idea to Liquidus tool, for |k-1|)
        vis_frame = ttk.LabelFrame(
            main_frame, text=self.tr('plot_k_vis_frame', 'Visualization (|k-1| Field)'), padding="10"
        )
        vis_frame.pack(fill=tk.X, pady=5)
        plot_heatmap_var = tk.BooleanVar(value=True)
        plot_3d_static_var = tk.BooleanVar(value=True)
        plot_3d_gif_var = tk.BooleanVar(value=True)
        plot_plotly_var = tk.BooleanVar(value=True)
        k_cb_hm = ttk.Checkbutton(
            vis_frame, text=self.tr('plot_k_vis_heatmap', '2D Heatmap'), variable=plot_heatmap_var
        )
        k_cb_hm.pack(side=tk.LEFT, padx=5)
        k_cb_3d = ttk.Checkbutton(
            vis_frame, text=self.tr('plot_k_vis_3d', '3D Static'), variable=plot_3d_static_var
        )
        k_cb_3d.pack(side=tk.LEFT, padx=5)
        k_cb_gif = ttk.Checkbutton(
            vis_frame, text=self.tr('plot_k_vis_gif', '3D Rotation GIF'), variable=plot_3d_gif_var
        )
        k_cb_gif.pack(side=tk.LEFT, padx=5)
        k_cb_pl = ttk.Checkbutton(
            vis_frame, text=self.tr('plot_k_vis_plotly', 'Plotly 3D'), variable=plot_plotly_var
        )
        k_cb_pl.pack(side=tk.LEFT, padx=5)

        # Output settings (directory and basic GIF settings)
        output_settings_frame = ttk.LabelFrame(
            main_frame, text=self.tr('stp_output_settings', 'Output Settings'), padding="10"
        )
        output_settings_frame.pack(fill=tk.X, pady=5)
        k_lbl_outdir = ttk.Label(
            output_settings_frame, text=self.tr('stp_output_directory', 'Output directory:')
        )
        k_lbl_outdir.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        output_dir_var = tk.StringVar()
        output_dir_entry = ttk.Entry(output_settings_frame, textvariable=output_dir_var, width=40)
        output_dir_entry.grid(row=0, column=1, padx=5, pady=2, sticky="we")

        def browse_output_dir():
            d = filedialog.askdirectory(title=self.tr('dlg_select_output_dir', 'Select Output Directory'))
            if d:
                output_dir_var.set(d)

        k_btn_browse_out = ttk.Button(
            output_settings_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=browse_output_dir,
        )
        k_btn_browse_out.grid(row=0, column=2, padx=5, pady=2)

        k_lbl_gif_fps = ttk.Label(output_settings_frame, text=self.tr('plot_k_gif_fps', 'GIF FPS:'))
        k_lbl_gif_fps.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        gif_fps_var = tk.StringVar(value="20")
        ttk.Entry(output_settings_frame, textvariable=gif_fps_var, width=6).grid(
            row=1, column=1, padx=5, pady=2, sticky="w"
        )
        k_lbl_rot_step = ttk.Label(
            output_settings_frame, text=self.tr('plot_k_rot_step', 'Rotation step (deg):')
        )
        k_lbl_rot_step.grid(row=1, column=2, padx=5, pady=2, sticky="w")
        rotation_step_var = tk.StringVar(value="5")
        ttk.Entry(output_settings_frame, textvariable=rotation_step_var, width=6).grid(
            row=1, column=3, padx=5, pady=2, sticky="w"
        )
        output_settings_frame.columnconfigure(1, weight=1)

        # Image format (same options as Plot Liquidus Vectors → Output Settings)
        k_format_frame = ttk.Frame(output_settings_frame)
        k_format_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 2))
        k_lbl_img_fmt = ttk.Label(
            k_format_frame, text=self.tr('plot_k_img_fmt_2d3d', 'Image Format (2D/3D static):')
        )
        k_lbl_img_fmt.pack(side=tk.LEFT, padx=5)
        image_format_var = tk.StringVar(value="PNG")
        k_format_options = ["PNG", "JPEG", "GIF", "BMP", "TIFF", "WebP", "SVG", "PDF", "EPS"]
        ttk.Combobox(
            k_format_frame,
            textvariable=image_format_var,
            values=k_format_options,
            state="readonly",
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        # Status
        status_label = ttk.Label(
            main_frame, text=self.tr('plot_k_status_ready', 'Ready'), foreground="blue"
        )
        status_label.pack(pady=10)

        def _find_k_columns_auto_phase(df, ex, ey):
            """
            Find w(ex), w(ey), w(ex@solid), w(ey@solid), w(ex@LIQUID), w(ey@LIQUID)
            where the solid phase is inferred from -T//fw(@PHASE) and matching w(*@PHASE) columns.
            Prefer FCC_A1 if multiple phases satisfy the condition.
            """
            cols = [c for c in df.columns if isinstance(c, str)]
            upper_map = {c: c.strip().upper() for c in cols}

            def _find_exact(prefix):
                for c, cu in upper_map.items():
                    if cu == prefix:
                        return c
                return None

            ex_u = ex.upper()
            ey_u = ey.upper()

            wx = _find_exact(f"W({ex_u})")
            wy = _find_exact(f"W({ey_u})")
            if wx is None or wy is None:
                raise ValueError(f"Missing global composition columns w({ex}) or w({ey}).\nFound: {cols}")

            # Liquid compositions
            wxliq = _find_exact(f"W({ex_u}@LIQUID)")
            wyliq = _find_exact(f"W({ey_u}@LIQUID)")
            if wxliq is None or wyliq is None:
                raise ValueError(
                    f"Missing liquid composition columns w({ex}@LIQUID) or w({ey}@LIQUID).\nFound: {cols}"
                )

            # Candidate solid phases from -T//fw(@PHASE)
            phase_candidates = set()
            for c, cu in upper_map.items():
                # Example pattern: -T//FW(@FCC_A1)
                m = re.match(r"^-T//FW\(@([A-Z0-9_ ]+)\)", cu)
                if m:
                    phase_candidates.add(m.group(1))

            valid_phases = []
            for ph in phase_candidates:
                col_ex_s = _find_exact(f"W({ex_u}@{ph})")
                col_ey_s = _find_exact(f"W({ey_u}@{ph})")
                if col_ex_s is not None and col_ey_s is not None:
                    valid_phases.append((ph, col_ex_s, col_ey_s))

            if not valid_phases:
                raise ValueError(
                    "Cannot infer solid phase for k from -T//fw(@*) columns and w(*@PHASE) columns."
                )

            # Prefer FCC_A1 if available, otherwise take the first valid one
            solid_phase, w_ex_s, w_ey_s = None, None, None
            for ph, col_ex_s, col_ey_s in valid_phases:
                if ph == "FCC_A1":
                    solid_phase, w_ex_s, w_ey_s = ph, col_ex_s, col_ey_s
                    break
            if solid_phase is None:
                solid_phase, w_ex_s, w_ey_s = valid_phases[0]

            return wx, wy, w_ex_s, w_ey_s, wxliq, wyliq, solid_phase

        def plot_k_vectors():
            try:
                ds = dataset_var.get()
                if ds == "Equilibrium":
                    df_src = self.pandat_p_data
                    if df_src is None or len(df_src) == 0:
                        messagebox.showerror(
                            self.tr('dlg_error', 'Error'),
                            self.tr(
                                'plot_k_no_p',
                                'No P file data found. Please import P file via Import → Pandat to ThermoQ first.',
                            ),
                        )
                        return
                else:
                    df_src = self.pandat_p_s_data
                    if df_src is None or len(df_src) == 0:
                        messagebox.showerror(
                            self.tr('dlg_error', 'Error'),
                            self.tr(
                                'plot_k_no_ps',
                                'No P-S file data found. Please import P-S file via Import → Pandat to ThermoQ first.',
                            ),
                        )
                        return

                ex = elem_x_var.get().strip()
                ey = elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('plot_k_select_xy', 'Please select X and Y elements!'),
                    )
                    return

                status_label.config(
                    text=self.tr('plot_k_processing', 'Processing data...'), foreground="orange"
                )
                win.update()

                df = df_src.copy()
                df = df.rename(columns={c: c.strip() if isinstance(c, str) else c for c in df.columns})

                (
                    wx_col,
                    wy_col,
                    wxs_col,
                    wys_col,
                    wxliq_col,
                    wyliq_col,
                    solid_phase,
                ) = _find_k_columns_auto_phase(df, ex, ey)

                wx = pd.to_numeric(df[wx_col], errors="coerce")
                wy = pd.to_numeric(df[wy_col], errors="coerce")
                wxs = pd.to_numeric(df[wxs_col], errors="coerce")
                wys = pd.to_numeric(df[wys_col], errors="coerce")
                wxliq = pd.to_numeric(df[wxliq_col], errors="coerce")
                wyliq = pd.to_numeric(df[wyliq_col], errors="coerce")

                mask = (
                    wx.notna()
                    & wy.notna()
                    & wxs.notna()
                    & wys.notna()
                    & wxliq.notna()
                    & wyliq.notna()
                    & (wxliq != 0)
                    & (wyliq != 0)
                )
                if mask.sum() < 2:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr(
                            'plot_k_no_points',
                            'Not enough valid data points to plot partition coefficient vectors.',
                        ),
                    )
                    return

                wx = wx[mask]
                wy = wy[mask]
                kx = (wxs[mask] / wxliq[mask]).astype(float)
                ky = (wys[mask] / wyliq[mask]).astype(float)

                # k-vectors as deviation from 1
                dx = kx - 1.0
                dy = ky - 1.0
                k_dev_mag = np.sqrt(dx.values ** 2 + dy.values ** 2)

                x_min, x_max = float(wx.min()), float(wx.max())
                y_min, y_max = float(wy.min()), float(wy.max())

                prefix = prefix_var.get().strip() or "k_vectors"
                base_dir = output_dir_var.get().strip()
                if base_dir and os.path.isdir(base_dir):
                    base_path = base_dir
                else:
                    base_path = "."

                # Image format for 2D quiver, heatmap, and 3D static (same logic as liquidus vector plotter)
                img_format = image_format_var.get().upper()
                format_ext_map = {
                    "PNG": "png",
                    "JPEG": "jpg",
                    "GIF": "gif",
                    "BMP": "bmp",
                    "TIFF": "tiff",
                    "WEBP": "webp",
                    "SVG": "svg",
                    "PDF": "pdf",
                    "EPS": "eps",
                }
                ext = format_ext_map.get(img_format, "png")
                save_kwargs = {"dpi": 300, "bbox_inches": "tight"}
                if img_format == "PDF":
                    save_kwargs["format"] = "pdf"
                elif img_format == "EPS":
                    save_kwargs["format"] = "eps"
                elif img_format == "SVG":
                    save_kwargs["format"] = "svg"
                elif img_format in ["JPEG", "JPG"]:
                    save_kwargs["format"] = "jpeg"
                elif img_format == "TIFF":
                    save_kwargs["format"] = "tiff"
                elif img_format == "WEBP":
                    save_kwargs["format"] = "webp"
                elif img_format == "BMP":
                    save_kwargs["format"] = "bmp"
                elif img_format == "GIF":
                    save_kwargs["format"] = "gif"
                else:
                    save_kwargs["format"] = "png"

                # Simple scaling to avoid overly long arrows
                axis_span = max(x_max - x_min, y_max - y_min, 1e-9)
                max_abs = float(np.nanmax(np.abs(np.r_[dx.values, dy.values])))
                if not np.isfinite(max_abs) or max_abs == 0:
                    max_abs = 1.0
                scale_factor = 0.15 * axis_span / max_abs
                dx_plot = dx.values * scale_factor
                dy_plot = dy.values * scale_factor

                # 1) 2D quiver views (U / V / resultant), similar to original implementation
                fig1, ax1 = plt.subplots(figsize=(7, 6), dpi=140)
                ax1.quiver(
                    wx.values,
                    wy.values,
                    dx_plot,
                    np.zeros_like(dx_plot),
                    angles="xy",
                    scale_units="xy",
                    scale=1,
                    width=0.003,
                    color="tab:blue",
                )
                ax1.set_xlabel(f"w({ex})")
                ax1.set_ylabel(f"w({ey})")
                ax1.set_title(f"U arrows: k({ex}) = w({ex}@{solid_phase})/w({ex}@LIQUID)")
                ax1.grid(False)
                ax1.set_aspect("equal", adjustable="box")
                fig1.tight_layout()
                out1 = os.path.join(base_path, f"{prefix}_{ex}_U.{ext}")
                fig1.savefig(out1, **save_kwargs)
                plt.close(fig1)
                self.open_file_and_offer_save_as(out1, win)

                fig2, ax2 = plt.subplots(figsize=(7, 6), dpi=140)
                ax2.quiver(
                    wx.values,
                    wy.values,
                    np.zeros_like(dy_plot),
                    dy_plot,
                    angles="xy",
                    scale_units="xy",
                    scale=1,
                    width=0.003,
                    color="tab:orange",
                )
                ax2.set_xlabel(f"w({ex})")
                ax2.set_ylabel(f"w({ey})")
                ax2.set_title(f"V arrows: k({ey}) = w({ey}@{solid_phase})/w({ey}@LIQUID)")
                ax2.grid(False)
                ax2.set_aspect("equal", adjustable="box")
                fig2.tight_layout()
                out2 = os.path.join(base_path, f"{prefix}_{ey}_V.{ext}")
                fig2.savefig(out2, **save_kwargs)
                plt.close(fig2)
                self.open_file_and_offer_save_as(out2, win)

                fig3, ax3 = plt.subplots(figsize=(7, 6), dpi=140)
                ax3.quiver(
                    wx.values,
                    wy.values,
                    dx_plot,
                    dy_plot,
                    angles="xy",
                    scale_units="xy",
                    scale=1,
                    width=0.003,
                    color="tab:green",
                )
                ax3.set_xlabel(f"w({ex})")
                ax3.set_ylabel(f"w({ey})")
                ax3.set_title("Resultant Z: deviation of partition coefficients (k-1)")
                ax3.grid(False)
                ax3.set_aspect("equal", adjustable="box")
                fig3.tight_layout()
                out3 = os.path.join(base_path, f"{prefix}_Z.{ext}")
                fig3.savefig(out3, **save_kwargs)
                plt.close(fig3)
                self.open_file_and_offer_save_as(out3, win)

                # 2) 2D heatmap of |k-1| magnitude (optional)
                if plot_heatmap_var.get():
                    fig_hm, ax_hm = plt.subplots(figsize=(7, 6), dpi=140)
                    tcf = ax_hm.tricontourf(wx.values, wy.values, k_dev_mag, levels=30, cmap="viridis")
                    cbar = fig_hm.colorbar(tcf, ax=ax_hm)
                    cbar.set_label("|k - 1|")
                    ax_hm.set_xlabel(f"w({ex})")
                    ax_hm.set_ylabel(f"w({ey})")
                    ax_hm.set_title("2D Heatmap of |k-1| magnitude")
                    fig_hm.tight_layout()
                    out_hm = os.path.join(base_path, f"{prefix}_k_heatmap.{ext}")
                    fig_hm.savefig(out_hm, **save_kwargs)
                    plt.close(fig_hm)
                    self.open_file_and_offer_save_as(out_hm, win)

                # 3) 3D static trisurface of |k-1| (optional)
                if plot_3d_static_var.get():
                    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

                    fig_3d = plt.figure(figsize=(8, 7), dpi=140)
                    ax_3d = fig_3d.add_subplot(111, projection="3d")
                    surf = ax_3d.plot_trisurf(
                        wx.values,
                        wy.values,
                        k_dev_mag,
                        cmap="viridis",
                        linewidth=0.2,
                        antialiased=True,
                    )
                    cbar3 = fig_3d.colorbar(surf, ax=ax_3d, shrink=0.7, aspect=15)
                    cbar3.set_label("|k - 1|")
                    ax_3d.set_xlabel(f"w({ex})")
                    ax_3d.set_ylabel(f"w({ey})")
                    ax_3d.set_zlabel("|k - 1|")
                    ax_3d.set_title("3D Static Surface of |k-1|")
                    fig_3d.tight_layout()
                    out_3d = os.path.join(base_path, f"{prefix}_k_3d.{ext}")
                    fig_3d.savefig(out_3d, **save_kwargs)
                    plt.close(fig_3d)
                    self.open_file_and_offer_save_as(out_3d, win)

                # 4) 3D rotation GIF (matplotlib, optional)
                if plot_3d_gif_var.get():
                    fig_gif = plt.figure(figsize=(8, 7), dpi=140)
                    ax_gif = fig_gif.add_subplot(111, projection="3d")
                    surf_gif = ax_gif.plot_trisurf(
                        wx.values,
                        wy.values,
                        k_dev_mag,
                        cmap="viridis",
                        linewidth=0.2,
                        antialiased=True,
                    )
                    fig_gif.colorbar(surf_gif, ax=ax_gif, shrink=0.7, aspect=15)
                    ax_gif.set_xlabel(f"w({ex})")
                    ax_gif.set_ylabel(f"w({ey})")
                    ax_gif.set_zlabel("|k - 1|")
                    ax_gif.set_title("3D Rotation of |k-1| surface")

                    def _rotate(angle):
                        ax_gif.view_init(elev=30, azim=angle)
                        return fig_gif,

                    try:
                        rotation_step = int(float(rotation_step_var.get()))
                    except Exception:
                        rotation_step = 5
                    if rotation_step <= 0:
                        rotation_step = 5
                    try:
                        gif_fps = int(float(gif_fps_var.get()))
                    except Exception:
                        gif_fps = 20
                    if gif_fps <= 0:
                        gif_fps = 20
                    interval_ms = max(int(1000 / gif_fps), 10)

                    ani = animation.FuncAnimation(
                        fig_gif,
                        _rotate,
                        frames=range(0, 360, rotation_step),
                        interval=interval_ms,
                    )
                    out_gif = os.path.join(base_path, f"{prefix}_k_3d_rotation.gif")
                    ani.save(out_gif, writer="pillow", fps=gif_fps, dpi=100)
                    plt.close(fig_gif)
                    self.open_file_and_offer_save_as(out_gif, win)

                # 5) Plotly 3D scatter of |k-1| (optional)
                if plot_plotly_var.get():
                    out_html = None
                    if PLOTLY_AVAILABLE:
                        fig_pl = go.Figure(
                            data=[
                                go.Scatter3d(
                                    x=wx.values,
                                    y=wy.values,
                                    z=k_dev_mag,
                                    mode="markers",
                                    marker=dict(
                                        size=4,
                                        color=k_dev_mag,
                                        colorscale="Viridis",
                                        colorbar=dict(title="|k - 1|"),
                                        opacity=0.9,
                                    ),
                                )
                            ]
                        )
                        fig_pl.update_layout(
                            scene=dict(
                                xaxis_title=f"w({ex})",
                                yaxis_title=f"w({ey})",
                                zaxis_title="|k - 1|",
                            ),
                            width=900,
                            height=700,
                            title="Plotly 3D view of |k-1|",
                        )
                        out_html = os.path.join(base_path, f"{prefix}_k_3d_interactive.html")
                        fig_pl.write_html(out_html)
                    else:
                        out_html = os.path.join(base_path, f"{prefix}_k_3d_interactive.html")
                        with open(out_html, "w", encoding="utf-8") as f:
                            f.write(
                                "<html><body><p>Plotly is not available. "
                                "Install plotly to see interactive 3D plots.</p></body></html>"
                            )
                    if out_html:
                        self.open_file_and_offer_save_as(out_html, win)

                status_label.config(
                    text=self.tr(
                        'plot_k_done_all_viz',
                        'Done. Generated 2D quiver, heatmap, 3D static, GIF and Plotly 3D for k-vectors.',
                    ),
                    foreground="green",
                )
            except Exception as e:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('plot_k_fail', 'Failed to plot partition coefficient vectors:\n{e}').format(
                        e=str(e)
                    ),
                )

        k_btn_plot_tab1 = ttk.Button(
            main_frame, text=self.tr('btn_plot_vectors', 'Plot Vectors'), command=plot_k_vectors
        )
        k_btn_plot_tab1.pack(pady=10)

        # =========================
        # Tab 2: Same temperature from All table (csv/dat)
        # =========================
        tab2_title = ttk.Label(
            tab_same_temp,
            text=self.tr('partition_tab_same_temp', 'Same Temperature'),
            font=('Arial', 14, 'bold'),
        )
        tab2_title.pack(pady=(0, 10))

        tab2_info = ttk.Label(
            tab_same_temp,
            text=self.tr(
                'stp_tab2_info',
                'Compute U/V/Z vectors at a user-defined temperature T using All table_Lever / All table_Scheil csv/dat files.\n'
                'If T does not exist in a file, values are estimated by quadratic Newton divided-difference interpolation.',
            ),
            wraplength=780,
            justify="left",
        )
        tab2_info.pack(pady=(0, 15))

        tab2_status_label = ttk.Label(
            tab_same_temp, text=self.tr('plot_k_status_ready', 'Ready'), foreground="blue"
        )
        tab2_status_label.pack(pady=(0, 10))

        # Solidification mode (All table)
        tab2_dataset_frame = ttk.LabelFrame(
            tab_same_temp,
            text=self.tr('stp_solidification_mode', 'Solidification Mode'),
            padding="10",
        )
        tab2_dataset_frame.pack(fill=tk.X, pady=5)

        tab2_dataset_var = tk.StringVar(value="Lever")
        tab2_rb_lever = ttk.Radiobutton(
            tab2_dataset_frame,
            text=self.tr('stp_dataset_lever', 'All table_Lever (Equilibrium/Lever)'),
            variable=tab2_dataset_var,
            value="Lever",
            command=lambda: update_tab2_elements_from_selected_folder(),
        )
        tab2_rb_lever.pack(side=tk.LEFT, padx=10)
        tab2_rb_scheil = ttk.Radiobutton(
            tab2_dataset_frame,
            text=self.tr('stp_dataset_scheil', 'All table_Scheil (Scheil)'),
            variable=tab2_dataset_var,
            value="Scheil",
            command=lambda: update_tab2_elements_from_selected_folder(),
        )
        tab2_rb_scheil.pack(side=tk.LEFT, padx=10)

        # Folder selection
        tab2_folder_frame = ttk.LabelFrame(
            tab_same_temp,
            text=self.tr('stp_all_table_folders', 'All table Folders'),
            padding="10",
        )
        tab2_folder_frame.pack(fill=tk.X, pady=5)

        lever_dir_var2 = tk.StringVar()
        scheil_dir_var2 = tk.StringVar()

        lever_row = ttk.Frame(tab2_folder_frame)
        lever_row.pack(fill=tk.X, pady=3)
        tab2_lbl_lever_path = ttk.Label(
            lever_row, text=self.tr('stp_all_table_lever', 'All table_Lever folder:')
        )
        tab2_lbl_lever_path.pack(side=tk.LEFT)
        ttk.Entry(lever_row, textvariable=lever_dir_var2, width=55).pack(side=tk.LEFT, padx=5)
        def _browse_lever_dir():
            d = filedialog.askdirectory(
                title=self.tr('dlg_select_all_table_lever_folder', 'Select All table_Lever folder')
            )
            if d:
                lever_dir_var2.set(d)
                update_tab2_elements_from_selected_folder()

        tab2_btn_lever_browse = ttk.Button(
            lever_row,
            text=self.tr('pandat_browse', 'Browse'),
            command=_browse_lever_dir,
        )
        tab2_btn_lever_browse.pack(side=tk.LEFT, padx=5)

        scheil_row = ttk.Frame(tab2_folder_frame)
        scheil_row.pack(fill=tk.X, pady=3)
        tab2_lbl_scheil_path = ttk.Label(
            scheil_row, text=self.tr('stp_all_table_scheil', 'All table_Scheil folder:')
        )
        tab2_lbl_scheil_path.pack(side=tk.LEFT)
        ttk.Entry(scheil_row, textvariable=scheil_dir_var2, width=55).pack(side=tk.LEFT, padx=5)
        def _browse_scheil_dir():
            d = filedialog.askdirectory(
                title=self.tr('dlg_select_all_table_scheil_folder', 'Select All table_Scheil folder')
            )
            if d:
                scheil_dir_var2.set(d)
                update_tab2_elements_from_selected_folder()

        tab2_btn_scheil_browse = ttk.Button(
            scheil_row,
            text=self.tr('pandat_browse', 'Browse'),
            command=_browse_scheil_dir,
        )
        tab2_btn_scheil_browse.pack(side=tk.LEFT, padx=5)

        # Element selection
        tab2_elem_frame = ttk.LabelFrame(
            tab_same_temp,
            text=self.tr('stp_elem_selection', 'Element Selection'),
            padding="10",
        )
        tab2_elem_frame.pack(fill=tk.X, pady=5)
        tab2_lbl_x_el = ttk.Label(tab2_elem_frame, text=self.tr('stp_x_element', 'X Element:'))
        tab2_lbl_x_el.pack(side=tk.LEFT, padx=5)
        elem_x_var2 = tk.StringVar()
        elem_y_var2 = tk.StringVar()
        elements = self.available_elements if self.available_elements else sorted(PERIODIC_TABLE.keys())
        elem_x_combo2 = ttk.Combobox(
            tab2_elem_frame,
            textvariable=elem_x_var2,
            values=elements,
            width=10,
            state="readonly",
        )
        elem_x_combo2.pack(side=tk.LEFT, padx=5)
        tab2_lbl_y_el = ttk.Label(tab2_elem_frame, text=self.tr('stp_y_element', 'Y Element:'))
        tab2_lbl_y_el.pack(side=tk.LEFT, padx=15)
        elem_y_combo2 = ttk.Combobox(
            tab2_elem_frame,
            textvariable=elem_y_var2,
            values=elements,
            width=10,
            state="readonly",
        )
        elem_y_combo2.pack(side=tk.LEFT, padx=5)
        if elements:
            elem_x_var2.set(elements[0])
        if len(elements) > 1:
            elem_y_var2.set(elements[1])

        # Detect elements from selected All table folder (lock dropdown options)
        def update_tab2_elements_from_selected_folder():
            try:
                folder = lever_dir_var2.get().strip() if tab2_dataset_var.get() == "Lever" else scheil_dir_var2.get().strip()
                if not folder or not os.path.isdir(folder):
                    return

                files = [f for f in os.listdir(folder) if f.lower().endswith((".csv", ".dat"))]
                if not files:
                    return

                upper_periodic = {k.upper(): k for k in PERIODIC_TABLE.keys()}
                found = set()

                # Union elements from the first few files (fast but more robust)
                for fn in files[: min(10, len(files))]:
                    path = os.path.join(folder, fn)
                    try:
                        dfh = pd.read_csv(path, sep="\t", header=[0, 1], nrows=0, engine="python")
                    except Exception:
                        dfh = pd.read_csv(path, sep=r"[\t,]+", header=[0, 1], nrows=0, engine="python")

                    flat_cols = []
                    for c in dfh.columns:
                        if isinstance(c, tuple):
                            flat_cols.append(str(c[0]).strip())
                        else:
                            flat_cols.append(str(c).strip())

                    for col in flat_cols:
                        if not col:
                            continue
                        cu = re.sub(r"\s+", "", str(col)).upper()
                        # Match w(AL) and w(AL@...) style columns
                        m = re.match(r"^W\(([A-Z]+)\)$", cu)
                        if m:
                            up = m.group(1).upper()
                            found.add(upper_periodic.get(up, up.capitalize()))
                            continue
                        m2 = re.match(r"^W\(([A-Z]+)@", cu)
                        if m2:
                            up = m2.group(1).upper()
                            found.add(upper_periodic.get(up, up.capitalize()))

                found = sorted(found)
                if not found:
                    return

                elem_x_combo2['values'] = found
                elem_y_combo2['values'] = found

                # Set defaults if current values are not valid anymore
                if elem_x_var2.get() not in found:
                    elem_x_var2.set(found[0])
                if elem_y_var2.get() not in found:
                    elem_y_var2.set(found[1] if len(found) > 1 else found[0])

                tab2_status_label.config(
                    text=self.tr('stp_detected_elements', 'Detected elements: {els}').format(els=', '.join(found)),
                    foreground="green",
                )
            except Exception:
                # Silent fail to keep UI responsive; plotting will show detailed errors later.
                return

        # Initial detection (if folders already set)
        update_tab2_elements_from_selected_folder()

        # Temperature input
        tab2_temp_frame = ttk.LabelFrame(
            tab_same_temp,
            text=self.tr('stp_temperature', 'Temperature'),
            padding="10",
        )
        tab2_temp_frame.pack(fill=tk.X, pady=5)
        target_temp_var2 = tk.StringVar()
        tab2_lbl_target_temp = ttk.Label(
            tab2_temp_frame, text=self.tr('stp_target_temp', 'Target Temperature (K):')
        )
        tab2_lbl_target_temp.pack(side=tk.LEFT, padx=5)
        ttk.Entry(tab2_temp_frame, textvariable=target_temp_var2, width=20).pack(side=tk.LEFT, padx=5)

        # Output
        tab2_output_frame = ttk.LabelFrame(tab_same_temp, text=self.tr('stp_output', 'Output'), padding="10")
        tab2_output_frame.pack(fill=tk.X, pady=5)
        tab2_lbl_fn_prefix = ttk.Label(
            tab2_output_frame, text=self.tr('stp_filename_prefix', 'Filename prefix:')
        )
        tab2_lbl_fn_prefix.pack(side=tk.LEFT, padx=5)
        prefix_var2 = tk.StringVar(value="k_vectors_T")
        ttk.Entry(tab2_output_frame, textvariable=prefix_var2, width=25).pack(side=tk.LEFT, padx=5)

        # Output settings (directory + image format)
        tab2_output_settings_frame = ttk.LabelFrame(
            tab_same_temp,
            text=self.tr('stp_output_settings', 'Output Settings'),
            padding="10",
        )
        tab2_output_settings_frame.pack(fill=tk.X, pady=5)

        tab2_output_dir_var = tk.StringVar()
        tab2_lbl_outdir = ttk.Label(
            tab2_output_settings_frame, text=self.tr('stp_output_directory', 'Output directory:')
        )
        tab2_lbl_outdir.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(tab2_output_settings_frame, textvariable=tab2_output_dir_var, width=45).grid(
            row=0, column=1, padx=5, pady=2, sticky="we"
        )

        def _browse_tab2_dir():
            d = filedialog.askdirectory(title=self.tr('dlg_select_output_dir', 'Select Output Directory'))
            if d:
                tab2_output_dir_var.set(d)

        tab2_btn_browse_out = ttk.Button(
            tab2_output_settings_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=_browse_tab2_dir,
        )
        tab2_btn_browse_out.grid(row=0, column=2, padx=5, pady=2)

        tab2_lbl_img_fmt = ttk.Label(
            tab2_output_settings_frame, text=self.tr('stp_image_format', 'Image Format:')
        )
        tab2_lbl_img_fmt.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        image_format_var2 = tk.StringVar(value="PNG")
        format_options = ["PNG", "JPEG", "GIF", "BMP", "TIFF", "WebP", "SVG", "PDF", "EPS"]
        ttk.Combobox(
            tab2_output_settings_frame,
            textvariable=image_format_var2,
            values=format_options,
            state="readonly",
            width=15,
        ).grid(row=1, column=1, padx=5, pady=2, sticky="w")
        tab2_output_settings_frame.columnconfigure(1, weight=1)

        def _normalize_col(col):
            return re.sub(r"\s+", "", str(col), flags=re.UNICODE).upper()

        def _read_all_table_file(path):
            """
            Read Pandat "All table_*" exported files.
            The first two rows are column names and unit row.
            """
            try:
                df0 = pd.read_csv(path, sep="\t", header=[0, 1], engine="python")
            except Exception:
                df0 = pd.read_csv(path, sep=r"[\t,]+", header=[0, 1], engine="python")

            # Flatten multi-index columns (level 0 contains column names)
            cols = []
            for i, c in enumerate(df0.columns):
                if isinstance(c, tuple):
                    c0 = c[0]
                else:
                    c0 = c
                c0s = str(c0).strip() if c0 is not None else ""
                cols.append(c0s if c0s else f"__COL_{i}__")
            df0.columns = cols
            return df0

        def _quad_newton_interp(x_nodes, y_nodes, x):
            """Quadratic Newton divided-difference interpolation at x."""
            x_nodes = np.array(x_nodes, dtype=float)
            y_nodes = np.array(y_nodes, dtype=float)
            # If duplicated nodes, fallback to linear between closest two
            if np.min(np.abs(np.diff(np.sort(x_nodes)))) < 1e-12:
                # Linear fallback
                idx = np.argsort(np.abs(x_nodes - x))[:2]
                xs = x_nodes[idx]
                ys = y_nodes[idx]
                order = np.argsort(xs)
                xs = xs[order]
                ys = ys[order]
                if xs[1] == xs[0]:
                    return float(ys[0])
                return float(ys[0] + (ys[1] - ys[0]) * (x - xs[0]) / (xs[1] - xs[0]))

            order = np.argsort(x_nodes)
            x0, x1, x2 = x_nodes[order]
            y0, y1, y2 = y_nodes[order]

            f01 = (y1 - y0) / (x1 - x0)
            f12 = (y2 - y1) / (x2 - x1)
            f012 = (f12 - f01) / (x2 - x0)
            return float(y0 + (x - x0) * f01 + (x - x0) * (x - x1) * f012)

        def _interp_col_at_t(df, t_target, col_t, col_y):
            """Interpolate df[col_y] at t_target along df[col_t] (quadratic, Newton)."""
            t_arr = pd.to_numeric(df[col_t], errors="coerce").to_numpy(dtype=float)
            y_arr = pd.to_numeric(df[col_y], errors="coerce").to_numpy(dtype=float)
            mask = np.isfinite(t_arr) & np.isfinite(y_arr)
            if mask.sum() < 2:
                return None
            t_arr = t_arr[mask]
            y_arr = y_arr[mask]

            # Exact match
            tol = max(1e-6, abs(t_target) * 1e-8)
            idx = int(np.argmin(np.abs(t_arr - t_target)))
            if abs(t_arr[idx] - t_target) <= tol:
                return float(y_arr[idx])

            if mask.sum() < 3:
                # Linear fallback using nearest two
                idx2 = np.argsort(np.abs(t_arr - t_target))[:2]
                xs = t_arr[idx2]
                ys = y_arr[idx2]
                order = np.argsort(xs)
                xs = xs[order]
                ys = ys[order]
                if xs[1] == xs[0]:
                    return float(ys[0])
                return float(ys[0] + (ys[1] - ys[0]) * (t_target - xs[0]) / (xs[1] - xs[0]))

            # Pick 3 closest nodes for quadratic interpolation
            idx3 = np.argsort(np.abs(t_arr - t_target))[:3]
            x_nodes = t_arr[idx3]
            y_nodes = y_arr[idx3]
            return _quad_newton_interp(x_nodes, y_nodes, t_target)

        def _find_col_by_norm(df, target_norm):
            for c in df.columns:
                if _normalize_col(c) == target_norm:
                    return c
            return None

        def plot_k_vectors_same_temperature():
            try:
                ex = elem_x_var2.get().strip()
                ey = elem_y_var2.get().strip()
                if not ex or not ey:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_select_xy', 'Please select X and Y elements!'))
                    return

                # Target temperature
                try:
                    t_target = float(target_temp_var2.get().strip())
                except Exception:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_invalid_temp', 'Invalid target temperature.'),
                    )
                    return

                dataset_mode = tab2_dataset_var.get()
                if dataset_mode == "Lever":
                    all_dir = lever_dir_var2.get().strip()
                else:
                    all_dir = scheil_dir_var2.get().strip()
                if not all_dir or not os.path.isdir(all_dir):
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('stp_need_folder', 'Please select a valid All table folder!'))
                    return

                file_names = [f for f in os.listdir(all_dir) if f.lower().endswith(('.csv', '.dat'))]
                if not file_names:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('stp_need_folder', 'Please select a valid All table folder!'))
                    return

                # Load all files first to find global temperature range
                df_list = []
                global_tmin = float("inf")
                global_tmax = float("-inf")

                tab2_status_label.config(text=self.tr('stp_loading', 'Loading All table files...'), foreground="orange")
                win.update()

                for fn in file_names:
                    path = os.path.join(all_dir, fn)
                    try:
                        df = _read_all_table_file(path)
                    except Exception:
                        continue

                    col_t = None
                    for c in df.columns:
                        if isinstance(c, str) and c.strip().upper() == "T":
                            col_t = c
                            break
                    if col_t is None:
                        continue

                    t_arr = pd.to_numeric(df[col_t], errors="coerce").to_numpy(dtype=float)
                    t_arr = t_arr[np.isfinite(t_arr)]
                    if t_arr.size == 0:
                        continue

                    global_tmin = min(global_tmin, float(np.min(t_arr)))
                    global_tmax = max(global_tmax, float(np.max(t_arr)))
                    df_list.append((path, df, col_t))

                if not df_list or not np.isfinite(global_tmin) or not np.isfinite(global_tmax):
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('stp_no_valid_points', 'No valid data points at/near the selected temperature!'))
                    return

                if t_target < global_tmin or t_target > global_tmax:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_temp_out_of_range', 'Target temperature {t} K is outside data range [{tmin}, {tmax}] K.').format(
                            t=t_target, tmin=f"{global_tmin:.6g}", tmax=f"{global_tmax:.6g}"
                        ),
                    )
                    return

                # Candidate solid phases from -T//fw(@*) columns (union)
                candidate_phases = set()
                for _, df, _ in df_list:
                    for c in df.columns:
                        if not isinstance(c, str):
                            continue
                        m = re.match(r"^\-T//fw\(@([^\)]+)\)$", c.strip(), flags=re.IGNORECASE)
                        if m:
                            candidate_phases.add(m.group(1))

                if not candidate_phases:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_solid_phase_infer_fail', 'Cannot infer solid phase from -T//fw(@*) columns.'),
                    )
                    return

                # Find required columns once per df using normalized matching
                pts_x = []
                pts_y = []
                pts_dx = []
                pts_dy = []

                for path, df, col_t in df_list:
                    # Global w(ex), w(ey)
                    col_wx = _find_col_by_norm(df, _normalize_col(f"w({ex})"))
                    col_wy = _find_col_by_norm(df, _normalize_col(f"w({ey})"))
                    if col_wx is None or col_wy is None:
                        continue

                    # Liquid compositions
                    col_wx_liq = _find_col_by_norm(df, _normalize_col(f"w({ex}@LIQUID)"))
                    col_wy_liq = _find_col_by_norm(df, _normalize_col(f"w({ey}@LIQUID)"))
                    if col_wx_liq is None or col_wy_liq is None:
                        continue

                    # Global composition (constant across temperature in each simulation file)
                    try:
                        x_val = float(pd.to_numeric(df[col_wx], errors="coerce").dropna().iloc[0])
                        y_val = float(pd.to_numeric(df[col_wy], errors="coerce").dropna().iloc[0])
                    except Exception:
                        continue

                    best = None  # (fw_s, pref, phase, kx, ky)

                    # Choose best solid phase by largest fw(@phase) at T_target (if column exists)
                    for ph in candidate_phases:
                        col_wx_s = _find_col_by_norm(df, _normalize_col(f"w({ex}@{ph})"))
                        col_wy_s = _find_col_by_norm(df, _normalize_col(f"w({ey}@{ph})"))
                        if col_wx_s is None or col_wy_s is None:
                            continue

                        col_fw_s = _find_col_by_norm(df, _normalize_col(f"fw(@{ph})"))

                        wx_s = _interp_col_at_t(df, t_target, col_t, col_wx_s)
                        wy_s = _interp_col_at_t(df, t_target, col_t, col_wy_s)
                        wx_liq = _interp_col_at_t(df, t_target, col_t, col_wx_liq)
                        wy_liq = _interp_col_at_t(df, t_target, col_t, col_wy_liq)
                        if wx_s is None or wy_s is None or wx_liq is None or wy_liq is None:
                            continue
                        if wx_liq == 0 or wy_liq == 0:
                            continue

                        kx = float(wx_s / wx_liq)
                        ky = float(wy_s / wy_liq)

                        fw_val = None
                        if col_fw_s is not None:
                            fw_val = _interp_col_at_t(df, t_target, col_t, col_fw_s)

                        score = fw_val if fw_val is not None else 0.0
                        pref = 1 if str(ph).upper() == "FCC_A1" else 0
                        if best is None:
                            best = (score, pref, ph, kx, ky)
                        else:
                            best_score, best_pref, best_phase, _, _ = best
                            if score > best_score or (
                                score == best_score
                                and (pref > best_pref or (pref == best_pref and str(ph) < str(best_phase)))
                            ):
                                best = (score, pref, ph, kx, ky)

                    if best is None:
                        continue

                    _, _, _, kx, ky = best
                    dx = kx - 1.0
                    dy = ky - 1.0

                    if not (np.isfinite(dx) and np.isfinite(dy)):
                        continue

                    pts_x.append(x_val)
                    pts_y.append(y_val)
                    pts_dx.append(dx)
                    pts_dy.append(dy)

                if len(pts_x) < 1:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('stp_no_valid_points', 'No valid data points at/near the selected temperature!'))
                    return

                pts_x = np.array(pts_x, dtype=float)
                pts_y = np.array(pts_y, dtype=float)
                pts_dx = np.array(pts_dx, dtype=float)
                pts_dy = np.array(pts_dy, dtype=float)

                prefix2 = prefix_var2.get().strip() or "k_vectors_T"
                output_dir = tab2_output_dir_var.get().strip()
                base_path = output_dir if output_dir and os.path.isdir(output_dir) else "."

                img_format = image_format_var2.get().upper()
                format_ext_map = {
                    "PNG": "png",
                    "JPEG": "jpg",
                    "GIF": "gif",
                    "BMP": "bmp",
                    "TIFF": "tiff",
                    "WEBP": "webp",
                    "SVG": "svg",
                    "PDF": "pdf",
                    "EPS": "eps",
                }
                ext = format_ext_map.get(img_format, "png")
                save_kwargs = {"dpi": 300, "bbox_inches": "tight"}
                if img_format == "PDF":
                    save_kwargs["format"] = "pdf"
                elif img_format == "EPS":
                    save_kwargs["format"] = "eps"
                elif img_format == "SVG":
                    save_kwargs["format"] = "svg"
                elif img_format in ["JPEG", "JPG"]:
                    save_kwargs["format"] = "jpeg"
                elif img_format == "TIFF":
                    save_kwargs["format"] = "tiff"
                elif img_format == "WEBP":
                    save_kwargs["format"] = "webp"
                elif img_format == "BMP":
                    save_kwargs["format"] = "bmp"
                elif img_format == "GIF":
                    save_kwargs["format"] = "gif"
                else:
                    save_kwargs["format"] = "png"

                # Scale arrows similarly to other vector plots
                x_min, x_max = float(np.min(pts_x)), float(np.max(pts_x))
                y_min, y_max = float(np.min(pts_y)), float(np.max(pts_y))
                axis_span = max(x_max - x_min, y_max - y_min, 1e-9)
                max_abs = float(np.nanmax(np.abs(np.r_[pts_dx, pts_dy])))
                if not np.isfinite(max_abs) or max_abs == 0:
                    max_abs = 1.0
                scale_factor = 0.15 * axis_span / max_abs
                dx_plot = pts_dx * scale_factor
                dy_plot = pts_dy * scale_factor

                # U
                fig1, ax1 = plt.subplots(figsize=(7, 6), dpi=140)
                ax1.quiver(
                    pts_x,
                    pts_y,
                    dx_plot,
                    np.zeros_like(dx_plot),
                    angles="xy",
                    scale_units="xy",
                    scale=1,
                    width=0.003,
                    color="tab:blue",
                )
                ax1.set_xlabel(f"w({ex})")
                ax1.set_ylabel(f"w({ey})")
                ax1.set_title(f"U at T={t_target:g}: k({ex})-1 (dx)")
                ax1.grid(False)
                ax1.set_aspect("equal", adjustable="box")
                fig1.tight_layout()
                out1 = os.path.join(base_path, f"{prefix2}_{ex}_U_T{t_target:.4g}.{ext}")
                fig1.savefig(out1, **save_kwargs)
                plt.close(fig1)
                self.open_file_and_offer_save_as(out1, win)

                # V
                fig2, ax2 = plt.subplots(figsize=(7, 6), dpi=140)
                ax2.quiver(
                    pts_x,
                    pts_y,
                    np.zeros_like(dy_plot),
                    dy_plot,
                    angles="xy",
                    scale_units="xy",
                    scale=1,
                    width=0.003,
                    color="tab:orange",
                )
                ax2.set_xlabel(f"w({ex})")
                ax2.set_ylabel(f"w({ey})")
                ax2.set_title(f"V at T={t_target:g}: k({ey})-1 (dy)")
                ax2.grid(False)
                ax2.set_aspect("equal", adjustable="box")
                fig2.tight_layout()
                out2 = os.path.join(base_path, f"{prefix2}_{ey}_V_T{t_target:.4g}.{ext}")
                fig2.savefig(out2, **save_kwargs)
                plt.close(fig2)
                self.open_file_and_offer_save_as(out2, win)

                # Z
                fig3, ax3 = plt.subplots(figsize=(7, 6), dpi=140)
                ax3.quiver(
                    pts_x,
                    pts_y,
                    dx_plot,
                    dy_plot,
                    angles="xy",
                    scale_units="xy",
                    scale=1,
                    width=0.003,
                    color="tab:green",
                )
                ax3.set_xlabel(f"w({ex})")
                ax3.set_ylabel(f"w({ey})")
                ax3.set_title(f"Z at T={t_target:g}: resultant (k-1)")
                ax3.grid(False)
                ax3.set_aspect("equal", adjustable="box")
                fig3.tight_layout()
                out3 = os.path.join(base_path, f"{prefix2}_Z_T{t_target:.4g}.{ext}")
                fig3.savefig(out3, **save_kwargs)
                plt.close(fig3)
                self.open_file_and_offer_save_as(out3, win)

                win._partition_k_tab2_last_t = t_target
                tab2_status_label.config(
                    text=self.tr('stp_done', 'Done. Generated U/V/Z at T={t} from All table files.').format(
                        t=f"{t_target:g}"
                    ),
                    foreground="green",
                )
            except Exception as e:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('plot_k_fail', 'Failed to plot partition coefficient vectors:\n{e}').format(e=str(e)),
                )

        tab2_btn_plot = ttk.Button(
            tab_same_temp,
            text=self.tr('stp_plot_button', 'Plot U/V/Z at T'),
            command=plot_k_vectors_same_temperature,
        )
        tab2_btn_plot.pack(pady=10)

        # =========================
        # Tab 3: Isocomposition (fixed overall alloy composition)
        # =========================
        iso_title = ttk.Label(
            tab_isocomp,
            text=self.tr('iso_tab_title', 'isocomposition'),
            font=('Arial', 14, 'bold'),
        )
        iso_title.pack(pady=(0, 10))

        iso_info = ttk.Label(
            tab_isocomp,
            text=self.tr(
                'iso_info',
                'Compute tie-line projection and 3D plot for a user-defined alloy composition O using All table_Lever / All table_Scheil csv/dat files.\n'
                'For each temperature, f is from w(X@LIQUID), and S is from w(X@solid) inferred from -T//fw(@*).',
            ),
            wraplength=780,
            justify="left",
        )
        iso_info.pack(pady=(0, 15))

        iso_status_label = ttk.Label(
            tab_isocomp,
            text=self.tr('plot_k_status_ready', 'Ready'),
            foreground="blue",
        )
        iso_status_label.pack(pady=(0, 10))

        # Dataset selection (Lever vs Scheil)
        iso_dataset_frame = ttk.LabelFrame(
            tab_isocomp,
            text=self.tr('stp_solidification_mode', 'Solidification Mode'),
            padding="10",
        )
        iso_dataset_frame.pack(fill=tk.X, pady=5)

        iso_dataset_var = tk.StringVar(value="Lever")
        iso_rb_lever = ttk.Radiobutton(
            iso_dataset_frame,
            text=self.tr('stp_dataset_lever', 'All table_Lever (Equilibrium/Lever)'),
            variable=iso_dataset_var,
            value="Lever",
            command=lambda: update_iso_elements_from_selected_folder(),
        )
        iso_rb_lever.pack(side=tk.LEFT, padx=10)
        iso_rb_scheil = ttk.Radiobutton(
            iso_dataset_frame,
            text=self.tr('stp_dataset_scheil', 'All table_Scheil (Scheil)'),
            variable=iso_dataset_var,
            value="Scheil",
            command=lambda: update_iso_elements_from_selected_folder(),
        )
        iso_rb_scheil.pack(side=tk.LEFT, padx=10)

        # Folder selection
        iso_folder_frame = ttk.LabelFrame(
            tab_isocomp,
            text=self.tr('stp_all_table_folders', 'All table Folders'),
            padding="10",
        )
        iso_folder_frame.pack(fill=tk.X, pady=5)

        iso_lever_dir_var = tk.StringVar()
        iso_scheil_dir_var = tk.StringVar()

        iso_lever_row = ttk.Frame(iso_folder_frame)
        iso_lever_row.pack(fill=tk.X, pady=3)
        iso_lbl_lever_path = ttk.Label(
            iso_lever_row,
            text=self.tr('stp_all_table_lever', 'All table_Lever folder:'),
        )
        iso_lbl_lever_path.pack(side=tk.LEFT)
        ttk.Entry(iso_lever_row, textvariable=iso_lever_dir_var, width=55).pack(side=tk.LEFT, padx=5)

        iso_btn_lever_browse = ttk.Button(
            iso_lever_row,
            text=self.tr('pandat_browse', 'Browse'),
            command=lambda: _browse_iso_lever_dir(),
        )
        iso_btn_lever_browse.pack(side=tk.LEFT, padx=5)

        iso_scheil_row = ttk.Frame(iso_folder_frame)
        iso_scheil_row.pack(fill=tk.X, pady=3)
        iso_lbl_scheil_path = ttk.Label(
            iso_scheil_row,
            text=self.tr('stp_all_table_scheil', 'All table_Scheil folder:'),
        )
        iso_lbl_scheil_path.pack(side=tk.LEFT)
        ttk.Entry(iso_scheil_row, textvariable=iso_scheil_dir_var, width=55).pack(side=tk.LEFT, padx=5)

        iso_btn_scheil_browse = ttk.Button(
            iso_scheil_row,
            text=self.tr('pandat_browse', 'Browse'),
            command=lambda: _browse_iso_scheil_dir(),
        )
        iso_btn_scheil_browse.pack(side=tk.LEFT, padx=5)

        def _browse_iso_lever_dir():
            d = filedialog.askdirectory(
                title=self.tr('dlg_select_all_table_lever_folder', 'Select All table_Lever folder'),
            )
            if d:
                iso_lever_dir_var.set(d)
                update_iso_elements_from_selected_folder()

        def _browse_iso_scheil_dir():
            d = filedialog.askdirectory(
                title=self.tr('dlg_select_all_table_scheil_folder', 'Select All table_Scheil folder'),
            )
            if d:
                iso_scheil_dir_var.set(d)
                update_iso_elements_from_selected_folder()

        # Element selection (lock options by imported folders)
        iso_elem_frame = ttk.LabelFrame(
            tab_isocomp,
            text=self.tr('stp_elem_selection', 'Element Selection'),
            padding="10",
        )
        iso_elem_frame.pack(fill=tk.X, pady=5)
        iso_lbl_x_el = ttk.Label(iso_elem_frame, text=self.tr('stp_x_element', 'X Element:'))
        iso_lbl_x_el.pack(side=tk.LEFT, padx=5)
        iso_elem_x_var = tk.StringVar()
        iso_elem_y_var = tk.StringVar()
        iso_elements = self.available_elements if self.available_elements else sorted(PERIODIC_TABLE.keys())
        iso_elem_x_combo = ttk.Combobox(
            iso_elem_frame,
            textvariable=iso_elem_x_var,
            values=iso_elements,
            width=10,
            state="readonly",
        )
        iso_elem_x_combo.pack(side=tk.LEFT, padx=5)
        iso_lbl_y_el = ttk.Label(iso_elem_frame, text=self.tr('stp_y_element', 'Y Element:'))
        iso_lbl_y_el.pack(side=tk.LEFT, padx=15)
        iso_elem_y_combo = ttk.Combobox(
            iso_elem_frame,
            textvariable=iso_elem_y_var,
            values=iso_elements,
            width=10,
            state="readonly",
        )
        iso_elem_y_combo.pack(side=tk.LEFT, padx=5)
        if iso_elements:
            iso_elem_x_var.set(iso_elements[0])
        if len(iso_elements) > 1:
            iso_elem_y_var.set(iso_elements[1])

        def update_iso_elements_from_selected_folder():
            try:
                folder = (
                    iso_lever_dir_var.get().strip()
                    if iso_dataset_var.get() == "Lever"
                    else iso_scheil_dir_var.get().strip()
                )
                if not folder or not os.path.isdir(folder):
                    return

                files = [f for f in os.listdir(folder) if f.lower().endswith((".csv", ".dat"))]
                if not files:
                    return

                upper_periodic = {k.upper(): k for k in PERIODIC_TABLE.keys()}
                found = set()

                for fn in files[: min(10, len(files))]:
                    path = os.path.join(folder, fn)
                    try:
                        dfh = pd.read_csv(path, sep="\t", header=[0, 1], nrows=0, engine="python")
                    except Exception:
                        dfh = pd.read_csv(path, sep=r"[\t,]+", header=[0, 1], nrows=0, engine="python")

                    flat_cols = []
                    for c in dfh.columns:
                        if isinstance(c, tuple):
                            flat_cols.append(str(c[0]).strip())
                        else:
                            flat_cols.append(str(c).strip())

                    for col in flat_cols:
                        if not col:
                            continue
                        cu = re.sub(r"\s+", "", str(col)).upper()
                        m = re.match(r"^W\(([A-Z]+)\)$", cu)
                        if m:
                            up = m.group(1).upper()
                            found.add(upper_periodic.get(up, up.capitalize()))
                            continue
                        m2 = re.match(r"^W\(([A-Z]+)@", cu)
                        if m2:
                            up = m2.group(1).upper()
                            found.add(upper_periodic.get(up, up.capitalize()))

                found = sorted(found)
                if not found:
                    return

                iso_elem_x_combo["values"] = found
                iso_elem_y_combo["values"] = found

                if iso_elem_x_var.get() not in found:
                    iso_elem_x_var.set(found[0])
                if iso_elem_y_var.get() not in found:
                    iso_elem_y_var.set(found[1] if len(found) > 1 else found[0])

                iso_status_label.config(
                    text=self.tr('stp_detected_elements', 'Detected elements: {els}').format(els=', '.join(found)),
                    foreground="green",
                )
            except Exception:
                return

        # Initial detection (if folders already set)
        update_iso_elements_from_selected_folder()

        # Alloy composition O (user-defined overall composition)
        iso_o_frame = ttk.LabelFrame(
            tab_isocomp,
            text=self.tr('iso_o_frame_title', 'Alloy composition O'),
            padding="10",
        )
        iso_o_frame.pack(fill=tk.X, pady=5)

        iso_o_wx_var = tk.StringVar()
        iso_o_wy_var = tk.StringVar()
        iso_lbl_o_wx = ttk.Label(iso_o_frame, text=self.tr('iso_o_wx', 'O: w(X) (wt%):'))
        iso_lbl_o_wx.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(iso_o_frame, textvariable=iso_o_wx_var, width=12).grid(row=0, column=1, padx=5, pady=2, sticky="w")
        iso_lbl_o_wy = ttk.Label(iso_o_frame, text=self.tr('iso_o_wy', 'O: w(Y) (wt%):'))
        iso_lbl_o_wy.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(iso_o_frame, textvariable=iso_o_wy_var, width=12).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        # Temperature range and sampling
        iso_t_frame = ttk.LabelFrame(
            tab_isocomp,
            text=self.tr('iso_t_frame_title', 'Temperature range'),
            padding="10",
        )
        iso_t_frame.pack(fill=tk.X, pady=5)

        iso_tmin_var = tk.StringVar()
        iso_tmax_var = tk.StringVar()
        iso_npts_var = tk.StringVar(value="8")

        iso_lbl_tmin = ttk.Label(iso_t_frame, text=self.tr('iso_tmin', 'T min (auto, K):'))
        iso_lbl_tmin.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(iso_t_frame, textvariable=iso_tmin_var, width=12, state="disabled").grid(
            row=0, column=1, padx=5, pady=2, sticky="w"
        )

        iso_lbl_tmax = ttk.Label(iso_t_frame, text=self.tr('iso_tmax', 'T max (auto, K):'))
        iso_lbl_tmax.grid(row=0, column=2, padx=5, pady=2, sticky="w")
        ttk.Entry(iso_t_frame, textvariable=iso_tmax_var, width=12, state="disabled").grid(
            row=0, column=3, padx=5, pady=2, sticky="w"
        )

        iso_lbl_npts = ttk.Label(iso_t_frame, text=self.tr('iso_npts', 'Number of temperature points:'))
        iso_lbl_npts.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(iso_t_frame, textvariable=iso_npts_var, width=12).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        # Auto-fill temperature range (from fs < 1 rows) after user inputs O.
        # Keep it debounced because we may need to scan many csv/dat files.
        def _iso_auto_temp_update():
            try:
                ex = iso_elem_x_var.get().strip()
                ey = iso_elem_y_var.get().strip()
                if not ex or not ey:
                    return

                try:
                    o_wx = float(iso_o_wx_var.get().strip())
                    o_wy = float(iso_o_wy_var.get().strip())
                except Exception:
                    return

                dataset_mode = iso_dataset_var.get()
                all_dir = (
                    iso_lever_dir_var.get().strip()
                    if dataset_mode == "Lever"
                    else iso_scheil_dir_var.get().strip()
                )
                if not all_dir or not os.path.isdir(all_dir):
                    return

                file_names = [f for f in os.listdir(all_dir) if f.lower().endswith((".csv", ".dat"))]
                if not file_names:
                    return

                def _normalize_col(col):
                    return re.sub(r"\s+", "", str(col), flags=re.UNICODE).upper()

                def _read_all_table_file(path):
                    try:
                        df0 = pd.read_csv(path, sep="\t", header=[0, 1], engine="python")
                    except Exception:
                        df0 = pd.read_csv(path, sep=r"[\t,]+", header=[0, 1], engine="python")
                    cols = []
                    for i, c in enumerate(df0.columns):
                        if isinstance(c, tuple):
                            c0 = c[0]
                        else:
                            c0 = c
                        c0s = str(c0).strip() if c0 is not None else ""
                        cols.append(c0s if c0s else f"__COL_{i}__")
                    df0.columns = cols
                    return df0

                def _find_col_by_norm(df, target_norm):
                    target_norm = _normalize_col(target_norm)
                    for c in df.columns:
                        if _normalize_col(c) == target_norm:
                            return c
                    return None

                # Scan each file once: determine its (wX, wY) constants from fs<1 rows,
                # and compute its temperature range from those same rows.
                ex_u = ex.upper()
                ey_u = ey.upper()
                candidates = []  # (x_val, y_val, tmin, tmax)
                for fn in file_names:
                    path = os.path.join(all_dir, fn)
                    try:
                        df = _read_all_table_file(path)
                    except Exception:
                        continue

                    col_t = _find_col_by_norm(df, "T")
                    col_fs = _find_col_by_norm(df, "fs")
                    if col_t is None or col_fs is None:
                        # Try loose match for fs
                        if col_fs is None:
                            for c in df.columns:
                                if isinstance(c, str) and _normalize_col(c).startswith("FS"):
                                    col_fs = c
                                    break
                        if col_t is None:
                            continue

                    if col_fs is None or col_t is None:
                        continue

                    fs_arr = pd.to_numeric(df[col_fs], errors="coerce").to_numpy(dtype=float)
                    t_arr = pd.to_numeric(df[col_t], errors="coerce").to_numpy(dtype=float)
                    # Only fs strictly smaller than 1.0; fs==1 rows are excluded.
                    mask = np.isfinite(fs_arr) & np.isfinite(t_arr) & (fs_arr < 1.0)
                    if mask.sum() < 2:
                        continue
                    df_fs = df.loc[mask].copy()

                    col_wx = _find_col_by_norm(df_fs, f"w({ex_u})")
                    col_wy = _find_col_by_norm(df_fs, f"w({ey_u})")
                    if col_wx is None or col_wy is None:
                        continue

                    try:
                        x_val = float(pd.to_numeric(df_fs[col_wx], errors="coerce").dropna().iloc[0])
                        y_val = float(pd.to_numeric(df_fs[col_wy], errors="coerce").dropna().iloc[0])
                    except Exception:
                        continue

                    # Unit normalization: if data seems to be fraction, convert to wt% for UI.
                    candidates.append((x_val, y_val, float(np.min(t_arr[mask])), float(np.max(t_arr[mask]))))

                if not candidates:
                    return

                xs = np.array([c[0] for c in candidates], dtype=float)
                ys = np.array([c[1] for c in candidates], dtype=float)
                comp_scale = 1.0
                try:
                    mx = float(np.nanmedian(xs))
                    my = float(np.nanmedian(ys))
                    if 0.0 <= mx <= 1.5 and 0.0 <= my <= 1.5:
                        comp_scale = 100.0
                except Exception:
                    comp_scale = 1.0

                if comp_scale != 1.0:
                    o_wx *= comp_scale
                    o_wy *= comp_scale

                for idx in range(len(candidates)):
                    x_val, y_val, tmin, tmax = candidates[idx]
                    if comp_scale != 1.0:
                        x_val *= comp_scale
                        y_val *= comp_scale
                    candidates[idx] = (x_val, y_val, tmin, tmax)

                dists = [float(np.hypot(c[0] - o_wx, c[1] - o_wy)) for c in candidates]
                order = np.argsort(dists)
                tol_exact = 1e-4
                min_idx = int(order[0])
                min_dist = float(dists[min_idx])

                if min_dist <= tol_exact:
                    selected = [candidates[min_idx]]
                else:
                    k_near = min(3, len(candidates))
                    selected = [candidates[i] for i in order[:k_near]]

                tmins = [c[2] for c in selected]
                tmaxs = [c[3] for c in selected]
                tmin_auto = float(max(tmins))
                tmax_auto = float(min(tmaxs))
                if not (np.isfinite(tmin_auto) and np.isfinite(tmax_auto) and tmin_auto < tmax_auto):
                    return

                iso_tmin_var.set(f"{tmin_auto:.6g}")
                iso_tmax_var.set(f"{tmax_auto:.6g}")
            except Exception:
                # Silent fail; plotting will still validate in v2.
                return

        def _schedule_iso_auto_temp_update(*_args):
            try:
                after_id = getattr(win, "_iso_auto_temp_after_id", None)
                if after_id:
                    try:
                        win.after_cancel(after_id)
                    except Exception:
                        pass
                win._iso_auto_temp_after_id = win.after(600, _iso_auto_temp_update)
            except Exception:
                pass

        # Debounced triggers
        iso_o_wx_var.trace_add("write", _schedule_iso_auto_temp_update)
        iso_o_wy_var.trace_add("write", _schedule_iso_auto_temp_update)

        # Initial fill (if already set)
        _iso_auto_temp_update()

        # Output settings (directory + image format)
        iso_output_frame = ttk.LabelFrame(
            tab_isocomp,
            text=self.tr('stp_output', 'Output'),
            padding="10",
        )
        iso_output_frame.pack(fill=tk.X, pady=5)
        iso_lbl_fn_prefix = ttk.Label(iso_output_frame, text=self.tr('stp_filename_prefix', 'Filename prefix:'))
        iso_lbl_fn_prefix.pack(side=tk.LEFT, padx=5)
        iso_prefix_var = tk.StringVar(value="isocomposition")
        ttk.Entry(iso_output_frame, textvariable=iso_prefix_var, width=20).pack(side=tk.LEFT, padx=5)

        iso_output_settings_frame = ttk.LabelFrame(
            tab_isocomp,
            text=self.tr('stp_output_settings', 'Output Settings'),
            padding="10",
        )
        iso_output_settings_frame.pack(fill=tk.X, pady=5)

        iso_output_dir_var = tk.StringVar()
        iso_lbl_outdir = ttk.Label(
            iso_output_settings_frame,
            text=self.tr('stp_output_directory', 'Output directory:'),
        )
        iso_lbl_outdir.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(iso_output_settings_frame, textvariable=iso_output_dir_var, width=45).grid(
            row=0, column=1, padx=5, pady=2, sticky="we"
        )

        def _browse_iso_outdir():
            d = filedialog.askdirectory(title=self.tr('dlg_select_output_dir', 'Select Output Directory'))
            if d:
                iso_output_dir_var.set(d)

        iso_btn_browse_out = ttk.Button(
            iso_output_settings_frame,
            text=self.tr('pandat_browse', 'Browse'),
            command=_browse_iso_outdir,
        )
        iso_btn_browse_out.grid(row=0, column=2, padx=5, pady=2)

        iso_lbl_img_fmt = ttk.Label(
            iso_output_settings_frame,
            text=self.tr('stp_image_format', 'Image Format:'),
        )
        iso_lbl_img_fmt.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        iso_img_format_var = tk.StringVar(value="PNG")
        iso_format_options = ["PNG", "JPEG", "GIF", "BMP", "TIFF", "WebP", "SVG", "PDF", "EPS"]
        ttk.Combobox(
            iso_output_settings_frame,
            textvariable=iso_img_format_var,
            values=iso_format_options,
            state="readonly",
            width=15,
        ).grid(row=1, column=1, padx=5, pady=2, sticky="w")
        iso_output_settings_frame.columnconfigure(1, weight=1)

        def plot_iso_composition_curves():
            try:
                ex = iso_elem_x_var.get().strip()
                ey = iso_elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_select_xy', 'Please select X and Y elements!'))
                    return

                try:
                    o_wx = float(iso_o_wx_var.get().strip())
                    o_wy = float(iso_o_wy_var.get().strip())
                except Exception:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('iso_need_o', 'Please enter O composition values (w(X), w(Y)).'))
                    return

                dataset_mode = iso_dataset_var.get()
                all_dir = iso_lever_dir_var.get().strip() if dataset_mode == "Lever" else iso_scheil_dir_var.get().strip()
                if not all_dir or not os.path.isdir(all_dir):
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('stp_need_folder', 'Please select a valid All table folder!'))
                    return

                file_names = [f for f in os.listdir(all_dir) if f.lower().endswith(('.csv', '.dat'))]
                if not file_names:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('stp_need_folder', 'Please select a valid All table folder!'))
                    return

                # Temperature sampling
                npts = int(float(iso_npts_var.get().strip() or "8"))
                npts = max(3, min(npts, 60))
                # Temperature range is auto-detected from fs < 1 data; UI inputs are disabled.
                tmin_in = ""
                tmax_in = ""

                iso_status_label.config(text=self.tr('stp_loading', 'Loading All table files...'), foreground="orange")
                win.update()

                # Helper functions (duplicated locally to keep Tab2 unchanged)
                def _normalize_col(col):
                    return re.sub(r"\s+", "", str(col), flags=re.UNICODE).upper()

                def _read_all_table_file(path):
                    try:
                        df0 = pd.read_csv(path, sep="\t", header=[0, 1], engine="python")
                    except Exception:
                        df0 = pd.read_csv(path, sep=r"[\t,]+", header=[0, 1], engine="python")
                    cols = []
                    for i, c in enumerate(df0.columns):
                        if isinstance(c, tuple):
                            c0 = c[0]
                        else:
                            c0 = c
                        c0s = str(c0).strip() if c0 is not None else ""
                        cols.append(c0s if c0s else f"__COL_{i}__")
                    df0.columns = cols
                    return df0

                def _quad_newton_interp(x_nodes, y_nodes, x):
                    x_nodes = np.array(x_nodes, dtype=float)
                    y_nodes = np.array(y_nodes, dtype=float)
                    if np.min(np.abs(np.diff(np.sort(x_nodes)))) < 1e-12:
                        idx = np.argsort(np.abs(x_nodes - x))[:2]
                        xs = x_nodes[idx]
                        ys = y_nodes[idx]
                        order = np.argsort(xs)
                        xs = xs[order]
                        ys = ys[order]
                        if xs[1] == xs[0]:
                            return float(ys[0])
                        return float(ys[0] + (ys[1] - ys[0]) * (x - xs[0]) / (xs[1] - xs[0]))
                    order = np.argsort(x_nodes)
                    x0, x1, x2 = x_nodes[order]
                    y0, y1, y2 = y_nodes[order]
                    f01 = (y1 - y0) / (x1 - x0)
                    f12 = (y2 - y1) / (x2 - x1)
                    f012 = (f12 - f01) / (x2 - x0)
                    return float(y0 + (x - x0) * f01 + (x - x0) * (x - x1) * f012)

                def _interp_col_at_t(df, t_target, col_t, col_y):
                    t_arr = pd.to_numeric(df[col_t], errors="coerce").to_numpy(dtype=float)
                    y_arr = pd.to_numeric(df[col_y], errors="coerce").to_numpy(dtype=float)
                    mask = np.isfinite(t_arr) & np.isfinite(y_arr)
                    if mask.sum() < 2:
                        return None
                    t_arr = t_arr[mask]
                    y_arr = y_arr[mask]
                    tol = max(1e-6, abs(t_target) * 1e-8)
                    idx = int(np.argmin(np.abs(t_arr - t_target)))
                    if abs(t_arr[idx] - t_target) <= tol:
                        return float(y_arr[idx])
                    if mask.sum() < 3:
                        idx2 = np.argsort(np.abs(t_arr - t_target))[:2]
                        xs = t_arr[idx2]
                        ys = y_arr[idx2]
                        order = np.argsort(xs)
                        xs = xs[order]
                        ys = ys[order]
                        if xs[1] == xs[0]:
                            return float(ys[0])
                        return float(ys[0] + (ys[1] - ys[0]) * (t_target - xs[0]) / (xs[1] - xs[0]))
                    idx3 = np.argsort(np.abs(t_arr - t_target))[:3]
                    x_nodes = t_arr[idx3]
                    y_nodes = y_arr[idx3]
                    return _quad_newton_interp(x_nodes, y_nodes, t_target)

                def _find_col_by_norm(df, target_norm):
                    for c in df.columns:
                        if _normalize_col(c) == target_norm:
                            return c
                    return None

                # 1) Scan files for global T range and available phases
                df_infos = []
                global_tmin = float("inf")
                global_tmax = float("-inf")
                candidate_phases = set()

                for fn in file_names:
                    path = os.path.join(all_dir, fn)
                    try:
                        df = _read_all_table_file(path)
                    except Exception:
                        continue

                    col_t = None
                    for c in df.columns:
                        if isinstance(c, str) and c.strip().upper() == "T":
                            col_t = c
                            break
                    if col_t is None:
                        continue

                    t_arr = pd.to_numeric(df[col_t], errors="coerce").to_numpy(dtype=float)
                    t_arr = t_arr[np.isfinite(t_arr)]
                    if t_arr.size == 0:
                        continue

                    global_tmin = min(global_tmin, float(np.min(t_arr)))
                    global_tmax = max(global_tmax, float(np.max(t_arr)))

                    # Overall composition constants in this file
                    col_wx = _find_col_by_norm(df, _normalize_col(f"w({ex})"))
                    col_wy = _find_col_by_norm(df, _normalize_col(f"w({ey})"))
                    if col_wx is None or col_wy is None:
                        continue
                    try:
                        x_val = float(pd.to_numeric(df[col_wx], errors="coerce").dropna().iloc[0])
                        y_val = float(pd.to_numeric(df[col_wy], errors="coerce").dropna().iloc[0])
                    except Exception:
                        continue

                    col_wx_liq = _find_col_by_norm(df, _normalize_col(f"w({ex}@LIQUID)"))
                    col_wy_liq = _find_col_by_norm(df, _normalize_col(f"w({ey}@LIQUID)"))
                    if col_wx_liq is None or col_wy_liq is None:
                        continue

                    col_fs = _find_col_by_norm(df, _normalize_col("fs"))
                    if col_fs is None:
                        col_fs = _find_col_by_norm(df, _normalize_col("f_s"))
                    if col_fs is None:
                        col_fs = _find_col_by_norm(df, _normalize_col("Fs"))
                    if col_fs is None:
                        # fs column is required to define the coexistence temperature range (fs < 1)
                        continue

                    for c in df.columns:
                        if not isinstance(c, str):
                            continue
                        m = re.match(r"^\-T//fw\(@([^\)]+)\)$", c.strip(), flags=re.IGNORECASE)
                        if m:
                            candidate_phases.add(m.group(1))

                    df_infos.append(
                        {
                            "path": path,
                            "df": df,
                            "col_t": col_t,
                            "col_fs": col_fs,
                            "x_val": x_val,
                            "y_val": y_val,
                            "col_wx_liq": col_wx_liq,
                            "col_wy_liq": col_wy_liq,
                        }
                    )

                if not df_infos:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('stp_no_valid_points', 'No valid data points at/near the selected temperature!'))
                    return
                if not candidate_phases:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_solid_phase_infer_fail', 'Cannot infer solid phase from -T//fw(@*) columns.'),
                    )
                    return

                # 2) Pick temperature range
                global_tmin_fs = float("inf")
                global_tmax_fs = float("-inf")
                for info in df_infos:
                    df = info["df"]
                    col_t = info["col_t"]
                    col_fs = info["col_fs"]
                    t_arr = pd.to_numeric(df[col_t], errors="coerce").to_numpy(dtype=float)
                    fs_arr = pd.to_numeric(df[col_fs], errors="coerce").to_numpy(dtype=float)
                    mask = np.isfinite(t_arr) & np.isfinite(fs_arr) & (fs_arr >= 0.0) & (fs_arr < 1.0)
                    if mask.sum() < 2:
                        continue
                    global_tmin_fs = min(global_tmin_fs, float(np.min(t_arr[mask])))
                    global_tmax_fs = max(global_tmax_fs, float(np.max(t_arr[mask])))

                # Fallback: if fs-based range fails, use the full T range.
                if not np.isfinite(global_tmin_fs) or not np.isfinite(global_tmax_fs) or global_tmin_fs >= global_tmax_fs:
                    global_tmin_fs = global_tmin
                    global_tmax_fs = global_tmax

                tmin = float(global_tmin_fs)
                tmax = float(global_tmax_fs)
                try:
                    if np.isfinite(tmin) and np.isfinite(tmax):
                        iso_tmin_var.set(f"{tmin:.6g}")
                        iso_tmax_var.set(f"{tmax:.6g}")
                except Exception:
                    pass

                if not (np.isfinite(tmin) and np.isfinite(tmax)) or tmin >= tmax:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('stp_invalid_temp', 'Invalid target temperature.'))
                    return

                temps_desc = np.linspace(tmax, tmin, npts, dtype=float)  # high -> low
                temps_asc = temps_desc[::-1]

                # 3) Build a 1D composition parameter s (based on (w(X), w(Y)) overall points)
                pts = np.array([[d["x_val"], d["y_val"]] for d in df_infos], dtype=float)
                # Unit normalization: if data appears to be in 0..1 fraction, convert to wt% (0..100).
                # This keeps plot axes in the expected 0..100 range and avoids huge negative values caused by interpolation overshoot.
                comp_scale = 1.0
                try:
                    mx = float(np.nanmedian(pts[:, 0]))
                    my = float(np.nanmedian(pts[:, 1]))
                    if 0.0 <= mx <= 1.5 and 0.0 <= my <= 1.5:
                        comp_scale = 100.0
                except Exception:
                    comp_scale = 1.0

                if comp_scale != 1.0:
                    pts *= comp_scale
                    o_wx *= comp_scale
                    o_wy *= comp_scale

                # Strict binary: use W(X) as the only independent composition coordinate.
                s_nodes = pts[:, 0].astype(float)
                s_target = float(o_wx)

                smin = float(np.min(s_nodes))
                smax = float(np.max(s_nodes))
                tol_s = max(1e-8, 1e-6 * abs(s_target))
                if s_target < smin - tol_s or s_target > smax + tol_s:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('iso_o_out_of_range', 'Target alloy composition is outside data composition range.'),
                    )
                    return

                def _interp_on_s(values_by_file, s_nodes_local, s_t):
                    # values_by_file: array length m
                    m = len(s_nodes_local)
                    if m == 0:
                        return None
                    # Exact match?
                    idx_exact = int(np.argmin(np.abs(s_nodes_local - s_t)))
                    if abs(s_nodes_local[idx_exact] - s_t) <= max(1e-10, 1e-8 * abs(s_t)):
                        return float(values_by_file[idx_exact])
                    k = min(3, m)
                    idx_near = np.argsort(np.abs(s_nodes_local - s_t))[:k]
                    x_nodes = s_nodes_local[idx_near]
                    y_nodes = values_by_file[idx_near]
                    # If less than 3 nodes or duplicates, fallback inside _quad_newton_interp
                    if k == 3:
                        val = _quad_newton_interp(x_nodes, y_nodes, s_t)
                        if not np.isfinite(val) or val < -1e-6 or val > 100.0 + 1e-6:
                            # Quadratic overshoot: fallback to linear using nearest 2
                            idx2 = np.argsort(np.abs(s_nodes_local - s_t))[:2]
                            x2 = s_nodes_local[idx2]
                            y2 = values_by_file[idx2]
                            order = np.argsort(x2)
                            x0, x1 = x2[order]
                            y0, y1 = y2[order]
                            if x1 == x0:
                                val = float(y0)
                            else:
                                val = float(y0 + (y1 - y0) * (s_t - x0) / (x1 - x0))
                        # Clamp to expected wt% range
                        val = float(min(max(val, 0.0), 100.0))
                        return val
                    # Linear fallback
                    order = np.argsort(x_nodes)
                    x0, x1 = x_nodes[order]
                    y0, y1 = y_nodes[order]
                    if x1 == x0:
                        return float(min(max(y0, 0.0), 100.0))
                    val = float(y0 + (y1 - y0) * (s_t - x0) / (x1 - x0))
                    return float(min(max(val, 0.0), 100.0))

                # 4) Precompute f(T) and S(T) for each file at sampled temperatures
                m = len(df_infos)
                fx_files = np.full((m, npts), np.nan, dtype=float)
                fy_files = np.full((m, npts), np.nan, dtype=float)
                sx_files = np.full((m, npts), np.nan, dtype=float)
                sy_files = np.full((m, npts), np.nan, dtype=float)

                # Prepare per-file phase columns once
                for j, info in enumerate(df_infos):
                    df = info["df"]
                    col_t = info["col_t"]
                    col_fs = info["col_fs"]
                    col_wx_liq = info["col_wx_liq"]
                    col_wy_liq = info["col_wy_liq"]

                    # Resolve columns for each candidate phase
                    phase_cols = {}
                    for ph in candidate_phases:
                        col_wx_s = _find_col_by_norm(df, _normalize_col(f"w({ex}@{ph})"))
                        col_wy_s = _find_col_by_norm(df, _normalize_col(f"w({ey}@{ph})"))
                        # Prefer -T//fw(@PHASE) score for phase identity (as required).
                        col_dash_fw_s = _find_col_by_norm(df, _normalize_col(f"-T//fw(@{ph})"))
                        # Fallback score if dash column is missing.
                        col_fw_s = _find_col_by_norm(df, _normalize_col(f"fw(@{ph})"))
                        if col_wx_s is None or col_wy_s is None:
                            continue
                        phase_cols[ph] = {
                            "col_wx_s": col_wx_s,
                            "col_wy_s": col_wy_s,
                            "col_dash_fw_s": col_dash_fw_s,
                            "col_fw_s": col_fw_s,
                        }

                    phase_list = sorted(phase_cols.keys(), key=lambda x: str(x))
                    if not phase_list:
                        continue

                    prev_phase = None
                    for i, tval in enumerate(temps_desc):
                        fs_val = _interp_col_at_t(df, tval, col_t, col_fs)
                        # Only use coexistence region: fs < 1
                        if fs_val is None or not np.isfinite(fs_val) or fs_val >= 1.0:
                            continue

                        wx_liq = _interp_col_at_t(df, tval, col_t, col_wx_liq)
                        wy_liq = _interp_col_at_t(df, tval, col_t, col_wy_liq)
                        if wx_liq is None or wy_liq is None:
                            continue

                        # Choose best solid phase at this T (by fw score), with continuity
                        best = None  # (score, pref, phase, wx_s, wy_s)
                        for ph in phase_list:
                            wx_s = _interp_col_at_t(df, tval, col_t, phase_cols[ph]["col_wx_s"])
                            wy_s = _interp_col_at_t(df, tval, col_t, phase_cols[ph]["col_wy_s"])
                            if wx_s is None or wy_s is None:
                                continue
                            score_val = None
                            if phase_cols[ph]["col_dash_fw_s"] is not None:
                                score_val = _interp_col_at_t(df, tval, col_t, phase_cols[ph]["col_dash_fw_s"])
                            if score_val is None and phase_cols[ph]["col_fw_s"] is not None:
                                score_val = _interp_col_at_t(df, tval, col_t, phase_cols[ph]["col_fw_s"])
                            score = score_val if score_val is not None else 0.0
                            pref = 1 if str(ph).upper() == "FCC_A1" else 0
                            if best is None:
                                best = (score, pref, ph, wx_s, wy_s)
                            else:
                                best_score, best_pref, best_ph, _, _ = best
                                if score > best_score or (score == best_score and (pref > best_pref or (pref == best_pref and str(ph) < str(best_ph)))):
                                    best = (score, pref, ph, wx_s, wy_s)

                        if best is None:
                            continue
                        best_score, best_pref, best_ph, wx_s_best, wy_s_best = best

                        if prev_phase is not None and prev_phase in phase_cols:
                            # Keep previous phase if it's close to the best (prevents flicker)
                            prev_col = phase_cols[prev_phase]
                            wx_s_prev = _interp_col_at_t(df, tval, col_t, prev_col["col_wx_s"])
                            wy_s_prev = _interp_col_at_t(df, tval, col_t, prev_col["col_wy_s"])
                            score_prev = None
                            if prev_col["col_dash_fw_s"] is not None:
                                score_prev = _interp_col_at_t(df, tval, col_t, prev_col["col_dash_fw_s"])
                            if score_prev is None and prev_col["col_fw_s"] is not None:
                                score_prev = _interp_col_at_t(df, tval, col_t, prev_col["col_fw_s"])
                            score_prev = score_prev if score_prev is not None else 0.0
                            if score_prev >= 0.95 * best_score:
                                best_ph = prev_phase
                                wx_s_best = wx_s_prev
                                wy_s_best = wy_s_prev
                        # Store compositions in wt% (0..100) for consistent axes
                        fx_files[j, i] = float(wx_liq) * comp_scale
                        fy_files[j, i] = float(wy_liq) * comp_scale
                        sx_files[j, i] = float(wx_s_best) * comp_scale
                        sy_files[j, i] = float(wy_s_best) * comp_scale

                        prev_phase = best_ph

                # 5) Interpolate in composition-space (s) for the user-defined O at each temperature
                fxo = np.full(npts, np.nan, dtype=float)
                fyo = np.full(npts, np.nan, dtype=float)
                sxo = np.full(npts, np.nan, dtype=float)
                syo = np.full(npts, np.nan, dtype=float)

                # IMPORTANT: mask must be done per-temperature i.
                # Otherwise, some i might interpolate with NaN values and break tie-line collinearity.
                for i in range(npts):
                    mask_i = (
                        np.isfinite(fx_files[:, i])
                        & np.isfinite(fy_files[:, i])
                        & np.isfinite(sx_files[:, i])
                        & np.isfinite(sy_files[:, i])
                    )
                    if mask_i.sum() < 2:
                        continue
                    s_nodes_i = s_nodes[mask_i]
                    fx_i = fx_files[mask_i, i]
                    fy_i = fy_files[mask_i, i]
                    sx_i = sx_files[mask_i, i]
                    sy_i = sy_files[mask_i, i]

                    fxo[i] = _interp_on_s(fx_i, s_nodes_i, s_target)
                    fyo[i] = _interp_on_s(fy_i, s_nodes_i, s_target)
                    sxo[i] = _interp_on_s(sx_i, s_nodes_i, s_target)
                    syo[i] = _interp_on_s(sy_i, s_nodes_i, s_target)
                    # Safety clamp
                    if np.isfinite(fxo[i]):
                        fxo[i] = float(np.clip(fxo[i], 0.0, 100.0))
                    if np.isfinite(fyo[i]):
                        fyo[i] = float(np.clip(fyo[i], 0.0, 100.0))
                    if np.isfinite(sxo[i]):
                        sxo[i] = float(np.clip(sxo[i], 0.0, 100.0))
                    if np.isfinite(syo[i]):
                        syo[i] = float(np.clip(syo[i], 0.0, 100.0))

                if not (np.isfinite(fxo).all() and np.isfinite(sxo).all()):
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('stp_no_valid_points', 'No valid data points at/near the selected temperature!'))
                    return

                prefix3 = iso_prefix_var.get().strip() or "isocomposition"
                output_dir = iso_output_dir_var.get().strip()
                base_path = output_dir if output_dir and os.path.isdir(output_dir) else "."

                img_format = iso_img_format_var.get().upper()
                format_ext_map = {
                    "PNG": "png",
                    "JPEG": "jpg",
                    "GIF": "gif",
                    "BMP": "bmp",
                    "TIFF": "tiff",
                    "WEBP": "webp",
                    "SVG": "svg",
                    "PDF": "pdf",
                    "EPS": "eps",
                }
                ext = format_ext_map.get(img_format, "png")
                save_kwargs = {"dpi": 300, "bbox_inches": "tight"}
                if img_format == "PDF":
                    save_kwargs["format"] = "pdf"
                elif img_format == "EPS":
                    save_kwargs["format"] = "eps"
                elif img_format == "SVG":
                    save_kwargs["format"] = "svg"
                elif img_format in ["JPEG", "JPG"]:
                    save_kwargs["format"] = "jpeg"
                elif img_format == "TIFF":
                    save_kwargs["format"] = "tiff"
                elif img_format == "WEBP":
                    save_kwargs["format"] = "webp"
                elif img_format == "BMP":
                    save_kwargs["format"] = "bmp"
                elif img_format == "GIF":
                    save_kwargs["format"] = "gif"
                else:
                    save_kwargs["format"] = "png"

                # Smooth curves in T (parameterization)
                tt_dense = None
                fxo_a = fxo[::-1]
                fyo_a = fyo[::-1]
                sxo_a = sxo[::-1]
                syo_a = syo[::-1]
                t_a = temps_asc

                try:
                    from scipy.interpolate import CubicSpline
                    if len(t_a) >= 4:
                        tt_dense = np.linspace(t_a[0], t_a[-1], 200)
                        cs_f_x = CubicSpline(t_a, fxo_a)
                        cs_f_y = CubicSpline(t_a, fyo_a)
                        cs_s_x = CubicSpline(t_a, sxo_a)
                        cs_s_y = CubicSpline(t_a, syo_a)
                        fxo_s = cs_f_x(tt_dense)
                        fyo_s = cs_f_y(tt_dense)
                        sxo_s = cs_s_x(tt_dense)
                        syo_s = cs_s_y(tt_dense)
                    else:
                        tt_dense = t_a
                        fxo_s, fyo_s, sxo_s, syo_s = fxo_a, fyo_a, sxo_a, syo_a
                except Exception:
                    tt_dense = t_a
                    fxo_s, fyo_s, sxo_s, syo_s = fxo_a, fyo_a, sxo_a, syo_a

                # CubicSpline can overshoot outside wt% range; clamp to keep axes in 0..100.
                fxo_s = np.clip(fxo_s, 0.0, 100.0)
                fyo_s = np.clip(fyo_s, 0.0, 100.0)
                sxo_s = np.clip(sxo_s, 0.0, 100.0)
                syo_s = np.clip(syo_s, 0.0, 100.0)

                # 2D projection plot
                fig2d, ax2d = plt.subplots(figsize=(7, 6), dpi=140)
                ax2d.plot(fxo_s, fyo_s, color="tab:blue", lw=2, label="f (Liquid composition)")
                ax2d.plot(sxo_s, syo_s, color="tab:orange", lw=2, label="S (Solid composition)")

                # Tie-lines for each temperature sample
                for i in range(npts):
                    ax2d.plot(
                        [fxo[i], sxo[i]],
                        [fyo[i], syo[i]],
                        color="gray",
                        lw=1,
                        alpha=0.35,
                        ls="--",
                    )

                ax2d.scatter([o_wx], [o_wy], color="red", s=40, marker="o", label="O (overall)")
                ax2d.set_xlabel(f"W({ex})")
                ax2d.set_ylabel(f"W({ey})")
                ax2d.set_title(self.tr('iso_2d_title', '2D Projection (isocomposition)'))
                ax2d.grid(False)
                ax2d.set_aspect("equal", adjustable="box")
                ax2d.legend(loc="best")
                fig2d.tight_layout()

                out2d = os.path.join(base_path, f"{prefix3}_iso_2Dproj.{ext}")
                fig2d.savefig(out2d, **save_kwargs)
                plt.close(fig2d)
                self.open_file_and_offer_save_as(out2d, win)

                # 3D static plot (T as Z axis)
                from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
                fig3d = plt.figure(figsize=(8, 7), dpi=140)
                ax3d = fig3d.add_subplot(111, projection="3d")

                ax3d.plot(fxo_s, fyo_s, tt_dense, color="tab:blue", lw=2)
                ax3d.plot(sxo_s, syo_s, tt_dense, color="tab:orange", lw=2)
                # Vertical line for overall composition O
                ax3d.plot([o_wx, o_wx], [o_wy, o_wy], [t_a[0], t_a[-1]], color="red", lw=1.5, ls="--")

                # Tie-lines at sampled temperatures
                for i in range(npts):
                    ax3d.plot(
                        [fxo[i], sxo[i]],
                        [fyo[i], syo[i]],
                        [temps_desc[i], temps_desc[i]],
                        color="gray",
                        alpha=0.25,
                        lw=1,
                        ls="--",
                    )

                ax3d.set_xlabel(f"W({ex})")
                ax3d.set_ylabel(f"W({ey})")
                ax3d.set_zlabel("T (K)")
                ax3d.set_title(self.tr('iso_3d_title', '3D Isocomposition (T as Z)'))
                fig3d.tight_layout()

                out3d = os.path.join(base_path, f"{prefix3}_iso_3Dstatic.{ext}")
                fig3d.savefig(out3d, **save_kwargs)
                plt.close(fig3d)
                self.open_file_and_offer_save_as(out3d, win)

                # Plotly 3D interactive (animation by temperature)
                out_html_iso = os.path.join(base_path, f"{prefix3}_iso_3Dinteractive.html")
                if PLOTLY_AVAILABLE:
                    try:
                        x_title = f"W({ex})"
                        y_title = f"W({ey})"

                        # Trace indices fixed across frames:
                        # 0: f line (liquid) up to current T
                        # 1: S line (solid) up to current T
                        # 2: tie line at current T
                        # 3: f point at current T
                        # 4: S point at current T
                        # 5: O vertical reference line (static)
                        o_trace = go.Scatter3d(
                            x=[o_wx, o_wx],
                            y=[o_wy, o_wy],
                            z=[float(temps_desc[-1]), float(temps_desc[0])],
                            mode="lines",
                            name="O",
                            line=dict(color="red", width=3, dash="dash"),
                        )

                        i0 = 0
                        f_line0 = go.Scatter3d(
                            x=fxo[: i0 + 1],
                            y=fyo[: i0 + 1],
                            z=temps_desc[: i0 + 1],
                            mode="lines",
                            name="f (liquid)",
                            line=dict(color="tab:blue", width=4),
                        )
                        s_line0 = go.Scatter3d(
                            x=sxo[: i0 + 1],
                            y=syo[: i0 + 1],
                            z=temps_desc[: i0 + 1],
                            mode="lines",
                            name="S (solid)",
                            line=dict(color="tab:orange", width=4),
                        )
                        tie0 = go.Scatter3d(
                            x=[fxo[i0], sxo[i0]],
                            y=[fyo[i0], syo[i0]],
                            z=[temps_desc[i0], temps_desc[i0]],
                            mode="lines",
                            name="tie line",
                            line=dict(color="gray", width=3, dash="dash"),
                            opacity=0.7,
                        )
                        f_m0 = go.Scatter3d(
                            x=[fxo[i0]],
                            y=[fyo[i0]],
                            z=[temps_desc[i0]],
                            mode="markers",
                            name="f point",
                            marker=dict(color="tab:blue", size=5),
                        )
                        s_m0 = go.Scatter3d(
                            x=[sxo[i0]],
                            y=[syo[i0]],
                            z=[temps_desc[i0]],
                            mode="markers",
                            name="S point",
                            marker=dict(color="tab:orange", size=5),
                        )

                        fig_pl = go.Figure(data=[f_line0, s_line0, tie0, f_m0, s_m0, o_trace])

                        frames = []
                        for i in range(npts):
                            f_line_i = go.Scatter3d(
                                x=fxo[: i + 1],
                                y=fyo[: i + 1],
                                z=temps_desc[: i + 1],
                                mode="lines",
                                name="f (liquid)",
                                line=dict(color="tab:blue", width=4),
                            )
                            s_line_i = go.Scatter3d(
                                x=sxo[: i + 1],
                                y=syo[: i + 1],
                                z=temps_desc[: i + 1],
                                mode="lines",
                                name="S (solid)",
                                line=dict(color="tab:orange", width=4),
                            )
                            tie_i = go.Scatter3d(
                                x=[fxo[i], sxo[i]],
                                y=[fyo[i], syo[i]],
                                z=[temps_desc[i], temps_desc[i]],
                                mode="lines",
                                name="tie line",
                                line=dict(color="gray", width=3, dash="dash"),
                                opacity=0.7,
                            )
                            f_m_i = go.Scatter3d(
                                x=[fxo[i]],
                                y=[fyo[i]],
                                z=[temps_desc[i]],
                                mode="markers",
                                name="f point",
                                marker=dict(color="tab:blue", size=5),
                            )
                            s_m_i = go.Scatter3d(
                                x=[sxo[i]],
                                y=[syo[i]],
                                z=[temps_desc[i]],
                                mode="markers",
                                name="S point",
                                marker=dict(color="tab:orange", size=5),
                            )
                            frames.append(
                                go.Frame(
                                    name=str(i),
                                    data=[f_line_i, s_line_i, tie_i, f_m_i, s_m_i, o_trace],
                                )
                            )
                        fig_pl.frames = frames

                        slider_steps = [
                            {
                                "args": [
                                    [str(i)],
                                    {
                                        "frame": {"duration": 220, "redraw": True},
                                        "mode": "immediate",
                                    },
                                ],
                                "label": f"{temps_desc[i]:.3g}",
                                "method": "animate",
                            }
                            for i in range(npts)
                        ]

                        fig_pl.update_layout(
                            scene=dict(
                                xaxis_title=x_title,
                                yaxis_title=y_title,
                                zaxis_title="T (K)",
                            ),
                            width=950,
                            height=760,
                            title=self.tr('iso_plotly_3d_title', '3D Isocomposition Interactive (Plotly)'),
                            showlegend=True,
                            sliders=[{"steps": slider_steps, "active": 0}],
                            updatemenus=[
                                {
                                    "type": "buttons",
                                    "showactive": False,
                                    "x": 0.05,
                                    "y": 0.05,
                                    "buttons": [
                                        {
                                            "label": "Play",
                                            "method": "animate",
                                            "args": [
                                                None,
                                                {
                                                    "frame": {"duration": 220, "redraw": True},
                                                    "fromcurrent": True,
                                                    "transition": {"duration": 0},
                                                },
                                            ],
                                        },
                                        {
                                            "label": "Pause",
                                            "method": "animate",
                                            "args": [
                                                [None],
                                                {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"},
                                            ],
                                        },
                                    ],
                                }
                            ],
                        )

                        fig_pl.write_html(out_html_iso)
                        self.open_file_and_offer_save_as(out_html_iso, win)
                    except Exception:
                        pass
                else:
                    with open(out_html_iso, "w", encoding="utf-8") as f:
                        f.write(
                            "<html><body>"
                            "<p>Plotly is not available. Install plotly to view interactive 3D plots.</p>"
                            "</body></html>"
                        )
                    self.open_file_and_offer_save_as(out_html_iso, win)

                # 3D dynamic GIF (high -> low)
                fig_anim = plt.figure(figsize=(8, 7), dpi=120)
                ax_anim = fig_anim.add_subplot(111, projection="3d")

                # Static background lines
                ax_anim.plot(fxo_s, fyo_s, tt_dense, color="tab:blue", lw=1, alpha=0.25)
                ax_anim.plot(sxo_s, syo_s, tt_dense, color="tab:orange", lw=1, alpha=0.25)
                ax_anim.plot([o_wx, o_wx], [o_wy, o_wy], [t_a[0], t_a[-1]], color="red", lw=1.0, ls="--", alpha=0.8)

                ax_anim.set_xlabel(f"W({ex})")
                ax_anim.set_ylabel(f"W({ey})")
                ax_anim.set_zlabel("T (K)")
                ax_anim.set_title(self.tr('iso_dyn_title', '3D Dynamic (high -> low)'))

                # Artists to update
                line_f, = ax_anim.plot([], [], [], color="tab:blue", lw=2)
                line_s, = ax_anim.plot([], [], [], color="tab:orange", lw=2)
                tie_line, = ax_anim.plot([], [], [], color="gray", lw=2, alpha=0.6, ls="--")
                # 3D scatter updates via _offsets3d
                scat_f = ax_anim.scatter([], [], [], color="tab:blue", s=40)
                scat_s = ax_anim.scatter([], [], [], color="tab:orange", s=40)

                def _set_scatter(scatter, x, y, z):
                    scatter._offsets3d = (np.array([x], dtype=float), np.array([y], dtype=float), np.array([z], dtype=float))

                def _update(frame_idx):
                    line_f.set_data(fxo[: frame_idx + 1], fyo[: frame_idx + 1])
                    line_f.set_3d_properties(temps_desc[: frame_idx + 1])
                    line_s.set_data(sxo[: frame_idx + 1], syo[: frame_idx + 1])
                    line_s.set_3d_properties(temps_desc[: frame_idx + 1])

                    x_f = fxo[frame_idx]
                    y_f = fyo[frame_idx]
                    x_s = sxo[frame_idx]
                    y_s = syo[frame_idx]
                    t_cur = temps_desc[frame_idx]
                    tie_line.set_data([x_f, x_s], [y_f, y_s])
                    tie_line.set_3d_properties([t_cur, t_cur])

                    _set_scatter(scat_f, x_f, y_f, t_cur)
                    _set_scatter(scat_s, x_s, y_s, t_cur)
                    return (line_f, line_s, tie_line, scat_f, scat_s)

                def _init():
                    line_f.set_data([], [])
                    line_f.set_3d_properties([])
                    line_s.set_data([], [])
                    line_s.set_3d_properties([])
                    tie_line.set_data([], [])
                    tie_line.set_3d_properties([])
                    _set_scatter(scat_f, np.nan, np.nan, np.nan)
                    _set_scatter(scat_s, np.nan, np.nan, np.nan)
                    return (line_f, line_s, tie_line, scat_f, scat_s)

                ani = animation.FuncAnimation(
                    fig_anim,
                    _update,
                    frames=range(npts),
                    init_func=_init,
                    interval=180,
                    blit=False,
                )
                out_gif = os.path.join(base_path, f"{prefix3}_iso_3Ddynamic.gif")
                ani.save(out_gif, writer="pillow", fps=10, dpi=100)
                plt.close(fig_anim)
                self.open_file_and_offer_save_as(out_gif, win)

                iso_status_label.config(text=self.tr('iso_done', 'Done. Generated 2D projection and 3D plots for isocomposition.'), foreground="green")
            except Exception as e:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('plot_k_fail', 'Failed to plot partition coefficient vectors:\n{e}').format(e=str(e)),
                )

        def plot_iso_composition_curves_v2():
            """
            isocomposition (steps per spec):
            1) Use user O to find nearest composition csv/dat files (Lever or Scheil).
            2) Filter fs < 1 to determine temperature range.
            3) Compute f(T) from W(*@LIQUID) and S(T) from W(*@solid) (solid phase from -T//fw(@*)).
            4) If O not exactly found, estimate values by quadratic Newton divided-difference interpolation over composition.
            """
            try:
                ex = iso_elem_x_var.get().strip()
                ey = iso_elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('plot_k_select_xy', 'Please select X and Y elements!'),
                    )
                    return

                try:
                    o_wx = float(iso_o_wx_var.get().strip())
                    o_wy = float(iso_o_wy_var.get().strip())
                except Exception:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('iso_need_o', 'Please enter O composition values (w(X), w(Y)).'),
                    )
                    return

                dataset_mode = iso_dataset_var.get()
                all_dir = (
                    iso_lever_dir_var.get().strip()
                    if dataset_mode == "Lever"
                    else iso_scheil_dir_var.get().strip()
                )
                if not all_dir or not os.path.isdir(all_dir):
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_need_folder', 'Please select a valid All table folder!'),
                    )
                    return

                file_names = [f for f in os.listdir(all_dir) if f.lower().endswith(('.csv', '.dat'))]
                if not file_names:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_need_folder', 'Please select a valid All table folder!'),
                    )
                    return

                # Temperature sampling
                npts = int(float(iso_npts_var.get().strip() or "8"))
                npts = max(3, min(npts, 60))
                tmin_in = iso_tmin_var.get().strip()
                tmax_in = iso_tmax_var.get().strip()

                iso_status_label.config(text=self.tr('stp_loading', 'Loading All table files...'), foreground="orange")
                win.update()

                def _normalize_col(col):
                    return re.sub(r"\s+", "", str(col), flags=re.UNICODE).upper()

                def _read_all_table_file(path):
                    try:
                        df0 = pd.read_csv(path, sep="\t", header=[0, 1], engine="python")
                    except Exception:
                        df0 = pd.read_csv(path, sep=r"[\t,]+", header=[0, 1], engine="python")
                    cols = []
                    for i, c in enumerate(df0.columns):
                        if isinstance(c, tuple):
                            c0 = c[0]
                        else:
                            c0 = c
                        c0s = str(c0).strip() if c0 is not None else ""
                        cols.append(c0s if c0s else f"__COL_{i}__")
                    df0.columns = cols
                    return df0

                def _quad_newton_interp(x_nodes, y_nodes, x):
                    x_nodes = np.array(x_nodes, dtype=float)
                    y_nodes = np.array(y_nodes, dtype=float)
                    order_all = np.argsort(x_nodes)
                    x_nodes = x_nodes[order_all]
                    y_nodes = y_nodes[order_all]
                    if len(x_nodes) < 2:
                        return None
                    # If duplicates exist, fallback to linear with two nearest distinct nodes
                    dxs = np.abs(np.diff(x_nodes))
                    if np.min(dxs) < 1e-12:
                        idx2 = np.argsort(np.abs(x_nodes - x))[:2]
                        x2 = x_nodes[idx2]
                        y2 = y_nodes[idx2]
                        if x2[1] == x2[0]:
                            return float(y2[0])
                        order = np.argsort(x2)
                        x0, x1 = x2[order]
                        y0, y1 = y2[order]
                        return float(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
                    if len(x_nodes) == 2:
                        x0, x1 = x_nodes
                        y0, y1 = y_nodes
                        return float(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
                    # Quadratic (3 nodes)
                    x0, x1, x2 = x_nodes[0], x_nodes[1], x_nodes[2]
                    y0, y1, y2 = y_nodes[0], y_nodes[1], y_nodes[2]
                    f01 = (y1 - y0) / (x1 - x0)
                    f12 = (y2 - y1) / (x2 - x1)
                    f012 = (f12 - f01) / (x2 - x0)
                    return float(y0 + (x - x0) * f01 + (x - x0) * (x - x1) * f012)

                def _interp_col_at_t(df, t_target, col_t, col_y):
                    t_arr = pd.to_numeric(df[col_t], errors="coerce").to_numpy(dtype=float)
                    y_arr = pd.to_numeric(df[col_y], errors="coerce").to_numpy(dtype=float)
                    mask = np.isfinite(t_arr) & np.isfinite(y_arr)
                    if mask.sum() < 2:
                        return None
                    t_arr = t_arr[mask]
                    y_arr = y_arr[mask]
                    tol = max(1e-6, abs(t_target) * 1e-8)
                    idx = int(np.argmin(np.abs(t_arr - t_target)))
                    if abs(t_arr[idx] - t_target) <= tol:
                        return float(y_arr[idx])
                    if mask.sum() < 3:
                        idx2 = np.argsort(np.abs(t_arr - t_target))[:2]
                        x2 = t_arr[idx2]
                        y2 = y_arr[idx2]
                        if x2[1] == x2[0]:
                            return float(y2[0])
                        order = np.argsort(x2)
                        x0, x1 = x2[order]
                        y0, y1 = y2[order]
                        return float(y0 + (y1 - y0) * (t_target - x0) / (x1 - x0))
                    idx3 = np.argsort(np.abs(t_arr - t_target))[:3]
                    x_nodes = t_arr[idx3]
                    y_nodes = y_arr[idx3]
                    return _quad_newton_interp(x_nodes, y_nodes, t_target)

                def _find_col_by_norm(df, target_norm):
                    target_norm = _normalize_col(target_norm)
                    for c in df.columns:
                        if _normalize_col(c) == target_norm:
                            return c
                    return None

                # First pass: load all valid compositions (fs < 1 exists)
                df_infos = []
                phase_union = set()
                comp_xy = []

                ex_u = ex.upper()
                ey_u = ey.upper()

                for fn in file_names:
                    path = os.path.join(all_dir, fn)
                    try:
                        df = _read_all_table_file(path)
                    except Exception:
                        continue

                    col_t = None
                    for c in df.columns:
                        if isinstance(c, str) and _normalize_col(c) == "T":
                            col_t = c
                            break
                    if col_t is None:
                        continue

                    col_fs = None
                    for c in df.columns:
                        if isinstance(c, str) and _normalize_col(c) == "FS":
                            col_fs = c
                            break
                    if col_fs is None:
                        # Fallback: accept columns like "FS( ... )" or "FS_Something"
                        for c in df.columns:
                            if not isinstance(c, str):
                                continue
                            nc = _normalize_col(c)
                            if nc.startswith("FS"):
                                col_fs = c
                                break
                    if col_fs is None:
                        continue

                    fs_arr = pd.to_numeric(df[col_fs], errors="coerce").to_numpy(dtype=float)
                    t_arr = pd.to_numeric(df[col_t], errors="coerce").to_numpy(dtype=float)
                    # Spec: filter fs strictly smaller than 1.0 (exclude fs==1 rows).
                    mask_fs = np.isfinite(fs_arr) & np.isfinite(t_arr) & (fs_arr < 1.0)
                    if mask_fs.sum() < 2:
                        continue
                    df_fs = df.loc[mask_fs].copy()

                    col_wx = _find_col_by_norm(df_fs, f"w({ex_u})")
                    col_wy = _find_col_by_norm(df_fs, f"w({ey_u})")
                    if col_wx is None or col_wy is None:
                        continue
                    try:
                        x_val = float(pd.to_numeric(df_fs[col_wx], errors="coerce").dropna().iloc[0])
                        y_val = float(pd.to_numeric(df_fs[col_wy], errors="coerce").dropna().iloc[0])
                    except Exception:
                        continue

                    col_wx_liq = _find_col_by_norm(df_fs, f"w({ex_u}@LIQUID)")
                    col_wy_liq = _find_col_by_norm(df_fs, f"w({ey_u}@LIQUID)")
                    if col_wx_liq is None or col_wy_liq is None:
                        continue

                    # Candidate solid phases from -T//fw(@PHASE) column names
                    phases = set()
                    for c in df.columns:
                        if not isinstance(c, str):
                            continue
                        cu = _normalize_col(c)
                        m = re.match(r"^\-T//FW\(@([A-Z0-9_]+)\)$", cu, flags=re.IGNORECASE)
                        if m:
                            phases.add(m.group(1).upper())

                    if not phases:
                        continue

                    phase_union |= phases

                    df_infos.append(
                        {
                            "path": path,
                            "df_fs": df_fs,
                            "col_t": col_t,
                            "col_fs": col_fs,
                            "x_val": x_val,
                            "y_val": y_val,
                            "col_wx_liq": col_wx_liq,
                            "col_wy_liq": col_wy_liq,
                            "phases": sorted(phases),
                        }
                    )
                    comp_xy.append((x_val, y_val))

                if len(df_infos) < 2:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_no_valid_points', 'No valid data points at/near the selected temperature!'),
                    )
                    return

                # Unit normalization to 0..100
                xs = np.array([p[0] for p in comp_xy], dtype=float)
                ys = np.array([p[1] for p in comp_xy], dtype=float)
                comp_scale = 1.0
                try:
                    mx = float(np.nanmedian(xs))
                    my = float(np.nanmedian(ys))
                    if 0.0 <= mx <= 1.5 and 0.0 <= my <= 1.5:
                        comp_scale = 100.0
                except Exception:
                    comp_scale = 1.0

                if comp_scale != 1.0:
                    for info in df_infos:
                        info["x_val"] *= comp_scale
                        info["y_val"] *= comp_scale
                    o_wx *= comp_scale
                    o_wy *= comp_scale
                else:
                    # Data are already wt%. Only scale user input when it clearly looks like
                    # mass fraction: both strictly in (0,1) and plausible total (excludes 1 wt%
                    # entered as 1,1 and excludes a lone "1" meaning 100%).
                    if (
                        0.0 < o_wx < 1.0
                        and 0.0 < o_wy < 1.0
                        and (o_wx + o_wy) <= 1.05
                    ):
                        o_wx *= 100.0
                        o_wy *= 100.0

                # Composition out of range check (use 2D bbox in W(X)-W(Y))
                pts_all = np.array([[info["x_val"], info["y_val"]] for info in df_infos], dtype=float)
                minx = float(np.min(pts_all[:, 0]))
                maxx = float(np.max(pts_all[:, 0]))
                miny = float(np.min(pts_all[:, 1]))
                maxy = float(np.max(pts_all[:, 1]))
                tol_bbox = 1e-3  # wt% tolerance
                if (
                    o_wx < minx - tol_bbox
                    or o_wx > maxx + tol_bbox
                    or o_wy < miny - tol_bbox
                    or o_wy > maxy + tol_bbox
                ):
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('iso_o_out_of_range', 'Selected alloy composition is outside data composition range.'),
                    )
                    return

                # For later interpolation we still need a 1D parameter direction.
                idx_minx = int(np.argmin(pts_all[:, 0]))
                idx_maxx = int(np.argmax(pts_all[:, 0]))
                p0 = pts_all[idx_minx]
                p1 = pts_all[idx_maxx]
                dvec = p1 - p0
                if float(np.linalg.norm(dvec)) < 1e-12:
                    dvec = np.array([1.0, 0.0], dtype=float)
                d_hat = dvec / float(np.linalg.norm(dvec))

                # Pick nearest 3 compositions for quadratic interpolation
                dists = [float(np.hypot(info["x_val"] - o_wx, info["y_val"] - o_wy)) for info in df_infos]
                order = np.argsort(dists)
                min_idx = int(order[0])
                min_dist = float(dists[min_idx])
                tol_exact = 1e-4  # wt% tolerance for "exact composition" match
                if min_dist <= tol_exact:
                    selected = [df_infos[min_idx]]
                else:
                    k_near = min(3, len(df_infos))
                    if k_near < 2:
                        messagebox.showerror(
                            self.tr('dlg_error', 'Error'),
                            self.tr('iso_o_out_of_range', 'Selected alloy composition is outside data composition range.'),
                        )
                        return
                    selected = [df_infos[i] for i in order[:k_near]]

                k_near = len(selected)

                # Build u parameter for selected
                pts_sel = np.array([[info["x_val"], info["y_val"]] for info in selected], dtype=float)
                if k_near >= 2:
                    p0s = pts_sel[0]
                    p1s = pts_sel[1]
                    dv = p1s - p0s
                    if float(np.linalg.norm(dv)) < 1e-12:
                        dv = np.array([1.0, 0.0], dtype=float)
                    d_hats = dv / float(np.linalg.norm(dv))
                else:
                    p0s = pts_sel[0]
                    d_hats = np.array([1.0, 0.0], dtype=float)
                u_nodes = np.array([float(np.dot(pt - p0s, d_hats)) for pt in pts_sel], dtype=float)
                u_target_s = float(np.dot((np.array([o_wx, o_wy], dtype=float) - p0s), d_hats))

                # Temperature range from fs < 1 within selected compositions
                tmins = []
                tmaxs = []
                for info in selected:
                    col_t = info["col_t"]
                    df_fs = info["df_fs"]
                    tvals = pd.to_numeric(df_fs[col_t], errors="coerce").to_numpy(dtype=float)
                    tvals = tvals[np.isfinite(tvals)]
                    if tvals.size == 0:
                        continue
                    tmins.append(float(np.min(tvals)))
                    tmaxs.append(float(np.max(tvals)))
                if not tmins or not tmaxs:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_no_valid_points', 'No valid data points at/near the selected temperature!'),
                    )
                    return
                tmin_auto = max(tmins)
                tmax_auto = min(tmaxs)
                if tmin_auto >= tmax_auto:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_no_valid_points', 'No valid data points at/near the selected temperature!'),
                    )
                    return

                # Keep the UI in sync with auto-detected range.
                try:
                    iso_tmin_var.set(f"{tmin_auto:.6g}")
                    iso_tmax_var.set(f"{tmax_auto:.6g}")
                except Exception:
                    pass

                # Temperature range is auto-detected from fs < 1 data
                tmin = tmin_auto
                tmax = tmax_auto
                if tmin >= tmax:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_invalid_temp', 'Invalid target temperature.'),
                    )
                    return

                temps_desc = np.linspace(tmax, tmin, npts, dtype=float)  # high -> low
                temps_asc = temps_desc[::-1]

                def _interp_on_u(values_by_sel, u_nodes_local, u_t):
                    m = len(u_nodes_local)
                    if m < 2:
                        return None
                    idx_near = np.argsort(np.abs(u_nodes_local - u_t))[: min(3, m)]
                    x_nodes = u_nodes_local[idx_near]
                    y_nodes = np.array(values_by_sel, dtype=float)[idx_near]
                    if len(idx_near) == 2:
                        x0, x1 = x_nodes
                        y0, y1 = y_nodes
                        if x1 == x0:
                            return float(y0)
                        order = np.argsort(x_nodes)
                        x0, x1 = x_nodes[order]
                        y0, y1 = y_nodes[order]
                        val = y0 + (y1 - y0) * (u_t - x0) / (x1 - x0)
                        return float(val)
                    return _quad_newton_interp(x_nodes, y_nodes, u_t)

                # Build f(T) and S(T) for each selected composition (no cross-composition interpolation yet)
                k_sel = len(selected)
                fxo_sel = np.full((k_sel, npts), np.nan, dtype=float)
                fyo_sel = np.full((k_sel, npts), np.nan, dtype=float)
                sxo_sel = np.full((k_sel, npts), np.nan, dtype=float)
                syo_sel = np.full((k_sel, npts), np.nan, dtype=float)

                for j, info in enumerate(selected):
                    df_fs = info["df_fs"]
                    col_t = info["col_t"]
                    col_wx_liq = info["col_wx_liq"]
                    col_wy_liq = info["col_wy_liq"]
                    phases = info["phases"]

                    prev_phase = None

                    # Resolve phase columns (once)
                    phase_meta = {}
                    for ph in phases:
                        ph_u = str(ph).upper()
                        col_wx_s = _find_col_by_norm(df_fs, f"w({ex_u}@{ph_u})")
                        col_wy_s = _find_col_by_norm(df_fs, f"w({ey_u}@{ph_u})")
                        if col_wx_s is None or col_wy_s is None:
                            continue
                        col_fw = _find_col_by_norm(df_fs, f"fw(@{ph_u})")
                        col_neg = _find_col_by_norm(df_fs, f"-T//fw(@{ph_u})")
                        phase_meta[ph_u] = {
                            "col_wx_s": col_wx_s,
                            "col_wy_s": col_wy_s,
                            "col_fw": col_fw,
                            "col_neg": col_neg,
                        }
                    phases_eff = sorted(phase_meta.keys())
                    if not phases_eff:
                        continue

                    for i, tval in enumerate(temps_desc):
                        # f from liquid
                        wx_liq = _interp_col_at_t(df_fs, tval, col_t, col_wx_liq)
                        wy_liq = _interp_col_at_t(df_fs, tval, col_t, col_wy_liq)
                        if wx_liq is None or wy_liq is None:
                            continue
                        # Pick best solid phase by fw(@phase) (fallback: -T//fw)
                        best = None  # (score, phase, wx_s, wy_s)
                        for ph_u in phases_eff:
                            meta = phase_meta[ph_u]
                            wx_s = _interp_col_at_t(df_fs, tval, col_t, meta["col_wx_s"])
                            wy_s = _interp_col_at_t(df_fs, tval, col_t, meta["col_wy_s"])
                            if wx_s is None or wy_s is None:
                                continue
                            score = 0.0
                            if meta["col_fw"] is not None:
                                fw_val = _interp_col_at_t(df_fs, tval, col_t, meta["col_fw"])
                                if fw_val is not None:
                                    score = float(fw_val)
                            elif meta["col_neg"] is not None:
                                neg_val = _interp_col_at_t(df_fs, tval, col_t, meta["col_neg"])
                                if neg_val is not None:
                                    score = float(-neg_val)  # larger => more solid

                            pref = 1 if ph_u == "FCC_A1" else 0
                            if best is None:
                                best = (score, pref, ph_u, wx_s, wy_s)
                            else:
                                best_score, best_pref, _, _, _ = best
                                if score > best_score or (score == best_score and pref > best_pref):
                                    best = (score, pref, ph_u, wx_s, wy_s)

                        if best is None:
                            continue
                        best_score, best_pref, best_phase, wx_s_best, wy_s_best = best

                        # Continuity: keep previous phase if close in score
                        if prev_phase is not None and prev_phase in phase_meta:
                            meta_prev = phase_meta[prev_phase]
                            wx_s_prev = _interp_col_at_t(df_fs, tval, col_t, meta_prev["col_wx_s"])
                            wy_s_prev = _interp_col_at_t(df_fs, tval, col_t, meta_prev["col_wy_s"])
                            if wx_s_prev is not None and wy_s_prev is not None:
                                score_prev = 0.0
                                if meta_prev["col_fw"] is not None:
                                    fw_prev = _interp_col_at_t(df_fs, tval, col_t, meta_prev["col_fw"])
                                    if fw_prev is not None:
                                        score_prev = float(fw_prev)
                                elif meta_prev["col_neg"] is not None:
                                    neg_prev = _interp_col_at_t(df_fs, tval, col_t, meta_prev["col_neg"])
                                    if neg_prev is not None:
                                        score_prev = float(-neg_prev)
                                if score_prev >= 0.95 * best_score:
                                    best_phase = prev_phase
                                    wx_s_best = wx_s_prev
                                    wy_s_best = wy_s_prev

                        prev_phase = best_phase
                        # If dataset is in fraction (0..1), comp_scale makes it wt% (0..100)
                        fxo_sel[j, i] = float(wx_liq) * comp_scale
                        fyo_sel[j, i] = float(wy_liq) * comp_scale
                        sxo_sel[j, i] = float(wx_s_best) * comp_scale
                        syo_sel[j, i] = float(wy_s_best) * comp_scale

                # Cross-composition interpolation to the user O (for each T)
                fxo = np.full(npts, np.nan, dtype=float)
                fyo = np.full(npts, np.nan, dtype=float)
                sxo = np.full(npts, np.nan, dtype=float)
                syo = np.full(npts, np.nan, dtype=float)

                if k_sel == 1:
                    fxo = fxo_sel[0, :].copy()
                    fyo = fyo_sel[0, :].copy()
                    sxo = sxo_sel[0, :].copy()
                    syo = syo_sel[0, :].copy()
                else:
                    for i in range(npts):
                        vals_fx = fxo_sel[:, i]
                        vals_fy = fyo_sel[:, i]
                        vals_sx = sxo_sel[:, i]
                        vals_sy = syo_sel[:, i]
                        # Use only finite nodes
                        ok_fx = np.isfinite(vals_fx)
                        ok_any = ok_fx & np.isfinite(vals_fy) & np.isfinite(vals_sx) & np.isfinite(vals_sy)
                        if ok_any.sum() < 2:
                            continue

                        u_nodes_ok = u_nodes[ok_any]
                        vals_fx_ok = vals_fx[ok_any]
                        vals_fy_ok = vals_fy[ok_any]
                        vals_sx_ok = vals_sx[ok_any]
                        vals_sy_ok = vals_sy[ok_any]

                        fxo[i] = _interp_on_u(vals_fx_ok, u_nodes_ok, u_target_s)
                        fyo[i] = _interp_on_u(vals_fy_ok, u_nodes_ok, u_target_s)
                        sxo[i] = _interp_on_u(vals_sx_ok, u_nodes_ok, u_target_s)
                        syo[i] = _interp_on_u(vals_sy_ok, u_nodes_ok, u_target_s)

                # Clamp to 0..100 for expected axes
                fxo = np.clip(fxo.astype(float), 0.0, 100.0)
                fyo = np.clip(fyo.astype(float), 0.0, 100.0)
                sxo = np.clip(sxo.astype(float), 0.0, 100.0)
                syo = np.clip(syo.astype(float), 0.0, 100.0)

                if not np.isfinite(fxo).all() or not np.isfinite(sxo).all():
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('stp_no_valid_points', 'No valid data points at/near the selected temperature!'),
                    )
                    return

                # Output settings
                prefix3 = iso_prefix_var.get().strip() or "isocomposition"
                output_dir = iso_output_dir_var.get().strip()
                base_path = output_dir if output_dir and os.path.isdir(output_dir) else "."

                img_format = iso_img_format_var.get().upper()
                format_ext_map = {
                    "PNG": "png",
                    "JPEG": "jpg",
                    "GIF": "gif",
                    "BMP": "bmp",
                    "TIFF": "tiff",
                    "WEBP": "webp",
                    "SVG": "svg",
                    "PDF": "pdf",
                    "EPS": "eps",
                }
                ext = format_ext_map.get(img_format, "png")
                save_kwargs = {"dpi": 300, "bbox_inches": "tight"}
                if img_format == "PDF":
                    save_kwargs["format"] = "pdf"
                elif img_format == "EPS":
                    save_kwargs["format"] = "eps"
                elif img_format == "SVG":
                    save_kwargs["format"] = "svg"
                elif img_format in ["JPEG", "JPG"]:
                    save_kwargs["format"] = "jpeg"
                elif img_format == "TIFF":
                    save_kwargs["format"] = "tiff"
                elif img_format == "WEBP":
                    save_kwargs["format"] = "webp"
                elif img_format == "BMP":
                    save_kwargs["format"] = "bmp"
                elif img_format == "GIF":
                    save_kwargs["format"] = "gif"
                else:
                    save_kwargs["format"] = "png"

                # Smooth curves in T for nicer appearance
                t_dense = temps_asc
                fxo_s, fyo_s, sxo_s, syo_s = fxo[::-1], fyo[::-1], sxo[::-1], syo[::-1]
                if len(t_dense) >= 4:
                    try:
                        from scipy.interpolate import CubicSpline
                        tt_dense = np.linspace(t_dense[0], t_dense[-1], 200)
                        cs_fx = CubicSpline(t_dense, fxo_s)
                        cs_fy = CubicSpline(t_dense, fyo_s)
                        cs_sx = CubicSpline(t_dense, sxo_s)
                        cs_sy = CubicSpline(t_dense, syo_s)
                        fxo_s = cs_fx(tt_dense)
                        fyo_s = cs_fy(tt_dense)
                        sxo_s = cs_sx(tt_dense)
                        syo_s = cs_sy(tt_dense)
                        t_dense = tt_dense
                    except Exception:
                        t_dense = temps_asc

                # 2D projection plot
                fig2d, ax2d = plt.subplots(figsize=(7, 6), dpi=140)
                ax2d.plot(fxo_s, fyo_s, color="tab:blue", lw=2, label="f (Liquid)")
                ax2d.plot(sxo_s, syo_s, color="tab:orange", lw=2, label="S (Solid)")
                ax2d.scatter([o_wx], [o_wy], color="red", s=45, marker="o", label="O (overall)")
                # Dashed f-O and S-O for each temperature sample
                for i in range(npts):
                    ax2d.plot([fxo[i], o_wx], [fyo[i], o_wy], color="gray", lw=1.2, linestyle="--", alpha=0.45)
                    ax2d.plot([sxo[i], o_wx], [syo[i], o_wy], color="gray", lw=1.2, linestyle="--", alpha=0.45)
                # Node markers
                ax2d.scatter(fxo, fyo, color="tab:blue", s=18)
                ax2d.scatter(sxo, syo, color="tab:orange", s=18)
                ax2d.set_xlabel(f"W({ex})")
                ax2d.set_ylabel(f"W({ey})")
                ax2d.set_xlim(0, 100)
                ax2d.set_ylim(0, 100)
                ax2d.set_title(self.tr('iso_2d_title', '2D Projection (isocomposition)'))
                ax2d.grid(False)
                ax2d.set_aspect("equal", adjustable="box")
                ax2d.legend(loc="best")
                fig2d.tight_layout()
                out2d = os.path.join(base_path, f"{prefix3}_iso_2Dproj.{ext}")
                fig2d.savefig(out2d, **save_kwargs)
                plt.close(fig2d)
                self.open_file_and_offer_save_as(out2d, win)

                # 3D static plot
                fig3d = plt.figure(figsize=(8, 7), dpi=140)
                ax3d = fig3d.add_subplot(111, projection="3d")
                ax3d.plot(fxo_s, fyo_s, t_dense, color="tab:blue", lw=2)
                ax3d.plot(sxo_s, syo_s, t_dense, color="tab:orange", lw=2)
                for i in range(npts):
                    ti = temps_desc[i]
                    ax3d.plot([fxo[i], o_wx], [fyo[i], o_wy], [ti, ti], color="gray", lw=1.2, linestyle="--", alpha=0.45)
                    ax3d.plot([sxo[i], o_wx], [syo[i], o_wy], [ti, ti], color="gray", lw=1.2, linestyle="--", alpha=0.45)
                ax3d.set_xlabel(f"W({ex})")
                ax3d.set_ylabel(f"W({ey})")
                ax3d.set_zlabel("T (K)")
                ax3d.set_xlim(0, 100)
                ax3d.set_ylim(0, 100)
                ax3d.set_title(self.tr('iso_3d_title', '3D Isocomposition (T as Z)'))
                fig3d.tight_layout()
                out3d = os.path.join(base_path, f"{prefix3}_iso_3Dstatic.{ext}")
                fig3d.savefig(out3d, **save_kwargs)
                plt.close(fig3d)
                self.open_file_and_offer_save_as(out3d, win)

                # 3D dynamic GIF (high -> low)
                fig_anim = plt.figure(figsize=(8, 7), dpi=120)
                ax_anim = fig_anim.add_subplot(111, projection="3d")
                ax_anim.plot(fxo_s, fyo_s, t_dense, color="tab:blue", lw=1.2, alpha=0.25)
                ax_anim.plot(sxo_s, syo_s, t_dense, color="tab:orange", lw=1.2, alpha=0.25)
                ax_anim.set_xlim(0, 100)
                ax_anim.set_ylim(0, 100)
                ax_anim.set_xlabel(f"W({ex})")
                ax_anim.set_ylabel(f"W({ey})")
                ax_anim.set_zlabel("T (K)")
                ax_anim.set_title(self.tr('iso_dyn_title', '3D Dynamic (high -> low)'))

                line_f, = ax_anim.plot([], [], [], color="tab:blue", lw=2)
                line_s, = ax_anim.plot([], [], [], color="tab:orange", lw=2)
                tie_f, = ax_anim.plot([], [], [], color="gray", lw=1.5, linestyle="--", alpha=0.6)
                tie_s, = ax_anim.plot([], [], [], color="gray", lw=1.5, linestyle="--", alpha=0.6)

                scat_f = ax_anim.scatter([], [], [], color="tab:blue", s=45)
                scat_s = ax_anim.scatter([], [], [], color="tab:orange", s=45)

                def _set_scatter(scatter, x, y, z):
                    scatter._offsets3d = (np.array([x], dtype=float), np.array([y], dtype=float), np.array([z], dtype=float))

                def _update(frame_idx):
                    line_f.set_data(fxo[: frame_idx + 1], fyo[: frame_idx + 1])
                    line_f.set_3d_properties(temps_desc[: frame_idx + 1])
                    line_s.set_data(sxo[: frame_idx + 1], syo[: frame_idx + 1])
                    line_s.set_3d_properties(temps_desc[: frame_idx + 1])

                    ti = temps_desc[frame_idx]
                    tie_f.set_data([fxo[frame_idx], o_wx], [fyo[frame_idx], o_wy])
                    tie_f.set_3d_properties([ti, ti])
                    tie_s.set_data([sxo[frame_idx], o_wx], [syo[frame_idx], o_wy])
                    tie_s.set_3d_properties([ti, ti])

                    _set_scatter(scat_f, fxo[frame_idx], fyo[frame_idx], ti)
                    _set_scatter(scat_s, sxo[frame_idx], syo[frame_idx], ti)
                    return (line_f, line_s, tie_f, tie_s, scat_f, scat_s)

                def _init():
                    line_f.set_data([], [])
                    line_f.set_3d_properties([])
                    line_s.set_data([], [])
                    line_s.set_3d_properties([])
                    tie_f.set_data([], [])
                    tie_f.set_3d_properties([])
                    tie_s.set_data([], [])
                    tie_s.set_3d_properties([])
                    _set_scatter(scat_f, np.nan, np.nan, np.nan)
                    _set_scatter(scat_s, np.nan, np.nan, np.nan)
                    return (line_f, line_s, tie_f, tie_s, scat_f, scat_s)

                ani = animation.FuncAnimation(fig_anim, _update, frames=range(npts), init_func=_init, interval=180, blit=False)
                out_gif = os.path.join(base_path, f"{prefix3}_iso_3Ddynamic.gif")
                ani.save(out_gif, writer="pillow", fps=10, dpi=100)
                plt.close(fig_anim)
                self.open_file_and_offer_save_as(out_gif, win)

                # Plotly interactive animation (high -> low)
                out_html_iso = os.path.join(base_path, f"{prefix3}_iso_3Dinteractive.html")
                if PLOTLY_AVAILABLE:
                    try:
                        o_trace = go.Scatter3d(
                            x=[o_wx],
                            y=[o_wy],
                            z=[float(temps_desc[0])],
                            mode="markers",
                            name="O",
                            marker=dict(color="red", size=5),
                        )
                        f_line0 = go.Scatter3d(
                            x=[fxo[0]],
                            y=[fyo[0]],
                            z=[float(temps_desc[0])],
                            mode="lines",
                            name="f (Liquid)",
                            line=dict(color="tab:blue", width=4),
                        )
                        s_line0 = go.Scatter3d(
                            x=[sxo[0]],
                            y=[syo[0]],
                            z=[float(temps_desc[0])],
                            mode="lines",
                            name="S (Solid)",
                            line=dict(color="tab:orange", width=4),
                        )
                        tie_f0 = go.Scatter3d(
                            x=[fxo[0], o_wx],
                            y=[fyo[0], o_wy],
                            z=[float(temps_desc[0]), float(temps_desc[0])],
                            mode="lines",
                            name="f-O",
                            line=dict(color="gray", width=3, dash="dash"),
                            opacity=0.6,
                        )
                        tie_s0 = go.Scatter3d(
                            x=[sxo[0], o_wx],
                            y=[syo[0], o_wy],
                            z=[float(temps_desc[0]), float(temps_desc[0])],
                            mode="lines",
                            name="S-O",
                            line=dict(color="gray", width=3, dash="dash"),
                            opacity=0.6,
                        )
                        f_m0 = go.Scatter3d(
                            x=[fxo[0]],
                            y=[fyo[0]],
                            z=[float(temps_desc[0])],
                            mode="markers",
                            name="f point",
                            marker=dict(color="tab:blue", size=6),
                        )
                        s_m0 = go.Scatter3d(
                            x=[sxo[0]],
                            y=[syo[0]],
                            z=[float(temps_desc[0])],
                            mode="markers",
                            name="S point",
                            marker=dict(color="tab:orange", size=6),
                        )

                        fig_pl = go.Figure(
                            data=[f_line0, s_line0, tie_f0, tie_s0, o_trace, f_m0, s_m0],
                        )

                        frames = []
                        for i in range(npts):
                            ti = float(temps_desc[i])
                            f_line_i = go.Scatter3d(
                                x=fxo[: i + 1],
                                y=fyo[: i + 1],
                                z=temps_desc[: i + 1],
                                mode="lines",
                                name="f (Liquid)",
                                line=dict(color="tab:blue", width=4),
                            )
                            s_line_i = go.Scatter3d(
                                x=sxo[: i + 1],
                                y=syo[: i + 1],
                                z=temps_desc[: i + 1],
                                mode="lines",
                                name="S (Solid)",
                                line=dict(color="tab:orange", width=4),
                            )
                            tie_f_i = go.Scatter3d(
                                x=[fxo[i], o_wx],
                                y=[fyo[i], o_wy],
                                z=[ti, ti],
                                mode="lines",
                                name="f-O",
                                line=dict(color="gray", width=3, dash="dash"),
                                opacity=0.6,
                            )
                            tie_s_i = go.Scatter3d(
                                x=[sxo[i], o_wx],
                                y=[syo[i], o_wy],
                                z=[ti, ti],
                                mode="lines",
                                name="S-O",
                                line=dict(color="gray", width=3, dash="dash"),
                                opacity=0.6,
                            )
                            o_m_i = go.Scatter3d(
                                x=[o_wx],
                                y=[o_wy],
                                z=[ti],
                                mode="markers",
                                name="O",
                                marker=dict(color="red", size=5),
                            )
                            f_m_i = go.Scatter3d(
                                x=[fxo[i]],
                                y=[fyo[i]],
                                z=[ti],
                                mode="markers",
                                name="f point",
                                marker=dict(color="tab:blue", size=6),
                            )
                            s_m_i = go.Scatter3d(
                                x=[sxo[i]],
                                y=[syo[i]],
                                z=[ti],
                                mode="markers",
                                name="S point",
                                marker=dict(color="tab:orange", size=6),
                            )
                            frames.append(
                                go.Frame(
                                    name=str(i),
                                    data=[f_line_i, s_line_i, tie_f_i, tie_s_i, o_m_i, f_m_i, s_m_i],
                                )
                            )
                        fig_pl.frames = frames

                        slider_steps = [
                            {
                                "args": [[str(i)], {"frame": {"duration": 220, "redraw": True}, "mode": "immediate"}],
                                "label": f"{temps_desc[i]:.3g}",
                                "method": "animate",
                            }
                            for i in range(npts)
                        ]
                        fig_pl.update_layout(
                            scene=dict(
                                xaxis_title=f"W({ex})",
                                yaxis_title=f"W({ey})",
                                zaxis_title="T (K)",
                            ),
                            width=950,
                            height=760,
                            title=self.tr('iso_plotly_3d_title', '3D Isocomposition Interactive (Plotly)'),
                            showlegend=True,
                            sliders=[{"steps": slider_steps, "active": 0}],
                            updatemenus=[
                                {
                                    "type": "buttons",
                                    "showactive": False,
                                    "x": 0.05,
                                    "y": 0.05,
                                    "buttons": [
                                        {
                                            "label": "Play",
                                            "method": "animate",
                                            "args": [
                                                None,
                                                {"frame": {"duration": 220, "redraw": True}, "transition": {"duration": 0}, "fromcurrent": True},
                                            ],
                                        },
                                        {
                                            "label": "Pause",
                                            "method": "animate",
                                            "args": [
                                                [None],
                                                {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}},
                                            ],
                                        },
                                    ],
                                }
                            ],
                        )
                        fig_pl.write_html(out_html_iso)
                        self.open_file_and_offer_save_as(out_html_iso, win)
                    except Exception:
                        pass
                else:
                    with open(out_html_iso, "w", encoding="utf-8") as f:
                        f.write(
                            "<html><body>"
                            "<p>Plotly is not available. Install plotly to view interactive 3D plots.</p>"
                            "</body></html>"
                        )
                    self.open_file_and_offer_save_as(out_html_iso, win)

                iso_status_label.config(
                    text=self.tr('iso_done', 'Done. Generated 2D projection and 3D plots for isocomposition.'),
                    foreground="green",
                )
            except Exception as e:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('plot_k_fail', 'Failed to plot partition coefficient vectors:\n{e}').format(e=str(e)),
                )

        iso_btn_plot = ttk.Button(
            tab_isocomp,
            text=self.tr('iso_plot_button', 'Plot isocomposition'),
            command=plot_iso_composition_curves_v2,
        )
        iso_btn_plot.pack(pady=10)

        def _refresh_partition_plotter_language():
            """Update labels when user switches Help → Language while this window is open."""
            try:
                if not win.winfo_exists():
                    return
            except tk.TclError:
                return
            try:
                notebook.tab(0, text=self.tr('partition_tab_liquid_points', 'Liquidus'))
                notebook.tab(1, text=self.tr('partition_tab_same_temp', 'isotherm'))
                notebook.tab(2, text=self.tr('partition_tab_isocomposition', 'isocomposition'))
            except tk.TclError:
                pass
            win.title(self.tr('plot_kvec', 'Plot Solid-Liquid Partition Coefficients'))
            title_label.config(text=self.tr('plot_kvec', 'Plot Solid-Liquid Partition Coefficients'))
            info_label.config(
                text=self.tr(
                    'plot_k_liq_intro',
                    'Plot k-vectors defined by k = w(*@solid)/w(*@LIQUID) from imported Pandat P or P-S data.\n'
                    'The solid phase is chosen automatically from -T//fw(@*) columns and matching w(*@PHASE) columns.',
                )
            )
            dataset_frame.config(text=self.tr('stp_solidification_mode', 'Solidification Mode'))
            k_rb_eq.config(text=self.tr('plot_k_mode_eq', 'Equilibrium/Lever (P file)'))
            k_rb_scheil.config(text=self.tr('plot_k_mode_scheil', 'Scheil (P-S file)'))
            elem_frame.config(text=self.tr('el_frame_title', 'Element Selection'))
            k_lbl_x_el.config(text=self.tr('stp_x_element', 'X Element:'))
            k_lbl_y_el.config(text=self.tr('stp_y_element', 'Y Element:'))
            output_frame.config(text=self.tr('stp_output', 'Output'))
            k_lbl_fn_prefix.config(text=self.tr('stp_filename_prefix', 'Filename prefix:'))
            vis_frame.config(text=self.tr('plot_k_vis_frame', 'Visualization (|k-1| Field)'))
            k_cb_hm.config(text=self.tr('plot_k_vis_heatmap', '2D Heatmap'))
            k_cb_3d.config(text=self.tr('plot_k_vis_3d', '3D Static'))
            k_cb_gif.config(text=self.tr('plot_k_vis_gif', '3D Rotation GIF'))
            k_cb_pl.config(text=self.tr('plot_k_vis_plotly', 'Plotly 3D'))
            output_settings_frame.config(text=self.tr('stp_output_settings', 'Output Settings'))
            k_lbl_outdir.config(text=self.tr('stp_output_directory', 'Output directory:'))
            k_btn_browse_out.config(text=self.tr('pandat_browse', 'Browse'))
            k_lbl_gif_fps.config(text=self.tr('plot_k_gif_fps', 'GIF FPS:'))
            k_lbl_rot_step.config(text=self.tr('plot_k_rot_step', 'Rotation step (deg):'))
            k_lbl_img_fmt.config(text=self.tr('plot_k_img_fmt_2d3d', 'Image Format (2D/3D static):'))
            k_btn_plot_tab1.config(text=self.tr('btn_plot_vectors', 'Plot Vectors'))
            # Status lines (refresh translated text if still in a known state)
            try:
                fg1 = status_label.cget('foreground')
                if fg1 == 'blue':
                    status_label.config(text=self.tr('plot_k_status_ready', 'Ready'))
                elif fg1 == 'orange':
                    status_label.config(text=self.tr('plot_k_processing', 'Processing data...'))
                elif fg1 == 'green':
                    status_label.config(
                        text=self.tr(
                            'plot_k_done_all_viz',
                            'Done. Generated 2D quiver, heatmap, 3D static, GIF and Plotly 3D for k-vectors.',
                        )
                    )
            except tk.TclError:
                pass
            try:
                fg2 = tab2_status_label.cget('foreground')
                if fg2 == 'blue':
                    tab2_status_label.config(text=self.tr('plot_k_status_ready', 'Ready'))
                elif fg2 == 'orange':
                    tab2_status_label.config(text=self.tr('stp_loading', 'Loading All table files...'))
                elif fg2 == 'green':
                    t_last = getattr(win, '_partition_k_tab2_last_t', None)
                    if t_last is not None:
                        tab2_status_label.config(
                            text=self.tr(
                                'stp_done', 'Done. Generated U/V/Z at T={t} from All table files.'
                            ).format(t=f"{float(t_last):g}")
                        )
            except tk.TclError:
                pass
            # Tab2
            tab2_title.config(text=self.tr('partition_tab_same_temp', 'isotherm'))
            tab2_info.config(
                text=self.tr(
                    'stp_tab2_info',
                    'Compute U/V/Z vectors at a user-defined temperature T using All table_Lever / All table_Scheil csv/dat files.\n'
                    'If T does not exist in a file, values are estimated by quadratic Newton divided-difference interpolation.',
                )
            )
            tab2_dataset_frame.config(text=self.tr('stp_solidification_mode', 'Solidification Mode'))
            tab2_rb_lever.config(text=self.tr('stp_dataset_lever', 'All table_Lever (Equilibrium/Lever)'))
            tab2_rb_scheil.config(text=self.tr('stp_dataset_scheil', 'All table_Scheil (Scheil)'))
            tab2_folder_frame.config(text=self.tr('stp_all_table_folders', 'All table Folders'))
            tab2_lbl_lever_path.config(text=self.tr('stp_all_table_lever', 'All table_Lever folder:'))
            tab2_lbl_scheil_path.config(text=self.tr('stp_all_table_scheil', 'All table_Scheil folder:'))
            tab2_btn_lever_browse.config(text=self.tr('pandat_browse', 'Browse'))
            tab2_btn_scheil_browse.config(text=self.tr('pandat_browse', 'Browse'))
            tab2_elem_frame.config(text=self.tr('stp_elem_selection', 'Element Selection'))
            tab2_lbl_x_el.config(text=self.tr('stp_x_element', 'X Element:'))
            tab2_lbl_y_el.config(text=self.tr('stp_y_element', 'Y Element:'))
            tab2_temp_frame.config(text=self.tr('stp_temperature', 'Temperature'))
            tab2_lbl_target_temp.config(text=self.tr('stp_target_temp', 'Target Temperature (K):'))
            tab2_output_frame.config(text=self.tr('stp_output', 'Output'))
            tab2_lbl_fn_prefix.config(text=self.tr('stp_filename_prefix', 'Filename prefix:'))
            tab2_output_settings_frame.config(text=self.tr('stp_output_settings', 'Output Settings'))
            tab2_lbl_outdir.config(text=self.tr('stp_output_directory', 'Output directory:'))
            tab2_btn_browse_out.config(text=self.tr('pandat_browse', 'Browse'))
            tab2_lbl_img_fmt.config(text=self.tr('stp_image_format', 'Image Format:'))
            tab2_btn_plot.config(text=self.tr('stp_plot_button', 'Plot U/V/Z at T'))

            # Tab3 (isocomposition)
            iso_title.config(text=self.tr('iso_tab_title', 'isocomposition'))
            iso_info.config(text=self.tr('iso_info', 'Compute tie-line projection and 3D plot for a user-defined alloy composition O using All table_Lever / All table_Scheil csv/dat files.'))
            iso_dataset_frame.config(text=self.tr('stp_solidification_mode', 'Solidification Mode'))
            iso_rb_lever.config(text=self.tr('stp_dataset_lever', 'All table_Lever (Equilibrium/Lever)'))
            iso_rb_scheil.config(text=self.tr('stp_dataset_scheil', 'All table_Scheil (Scheil)'))
            iso_folder_frame.config(text=self.tr('stp_all_table_folders', 'All table Folders'))
            iso_lbl_lever_path.config(text=self.tr('stp_all_table_lever', 'All table_Lever folder:'))
            iso_lbl_scheil_path.config(text=self.tr('stp_all_table_scheil', 'All table_Scheil folder:'))
            iso_btn_lever_browse.config(text=self.tr('pandat_browse', 'Browse'))
            iso_btn_scheil_browse.config(text=self.tr('pandat_browse', 'Browse'))
            iso_elem_frame.config(text=self.tr('stp_elem_selection', 'Element Selection'))
            iso_lbl_x_el.config(text=self.tr('stp_x_element', 'X Element:'))
            iso_lbl_y_el.config(text=self.tr('stp_y_element', 'Y Element:'))
            iso_o_frame.config(text=self.tr('iso_o_frame_title', 'Alloy composition O'))
            iso_lbl_o_wx.config(text=self.tr('iso_o_wx', 'O: w(X) (wt%):'))
            iso_lbl_o_wy.config(text=self.tr('iso_o_wy', 'O: w(Y) (wt%):'))
            iso_t_frame.config(text=self.tr('iso_t_frame_title', 'Temperature range'))
            iso_lbl_tmin.config(text=self.tr('iso_tmin', 'T min (K):'))
            iso_lbl_tmax.config(text=self.tr('iso_tmax', 'T max (K):'))
            iso_lbl_npts.config(text=self.tr('iso_npts', 'Number of temperature points:'))
            iso_output_frame.config(text=self.tr('stp_output', 'Output'))
            iso_lbl_fn_prefix.config(text=self.tr('stp_filename_prefix', 'Filename prefix:'))
            iso_output_settings_frame.config(text=self.tr('stp_output_settings', 'Output Settings'))
            iso_lbl_outdir.config(text=self.tr('stp_output_directory', 'Output directory:'))
            iso_btn_browse_out.config(text=self.tr('pandat_browse', 'Browse'))
            iso_lbl_img_fmt.config(text=self.tr('stp_image_format', 'Image Format:'))
            iso_btn_plot.config(text=self.tr('iso_plot_button', 'Plot isocomposition'))

            # Status line (Tab3)
            try:
                fg3 = iso_status_label.cget('foreground')
                if fg3 == 'blue':
                    iso_status_label.config(text=self.tr('plot_k_status_ready', 'Ready'), foreground="blue")
                elif fg3 == 'orange':
                    iso_status_label.config(text=self.tr('stp_loading', 'Loading All table files...'), foreground="orange")
                elif fg3 == 'green':
                    iso_status_label.config(text=self.tr('iso_done', 'Done. Generated 2D projection and 3D plots for isocomposition.'), foreground="green")
            except tk.TclError:
                pass

        self._partition_plotter_lang_refresh = _refresh_partition_plotter_language

        def _on_partition_win_destroy(event):
            if event.widget is win:
                if getattr(self, '_partition_plotter_lang_refresh', None) is _refresh_partition_plotter_language:
                    self._partition_plotter_lang_refresh = None

        win.bind('<Destroy>', _on_partition_win_destroy)

    def open_liquidus_vector_plotter(self):
        """Open liquidus vector plotter tool"""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_liq_dep_vec', 'Matplotlib is not installed. Cannot generate vector plots.'))
            return
        
        vector_window = tk.Toplevel(self.root)
        vector_window.geometry("800x800")
        self._present_tool_window(vector_window, self.root)

        # Create scrollable frame
        canvas = tk.Canvas(vector_window)
        scrollbar = ttk.Scrollbar(vector_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # bind_all keeps firing after this Toplevel is closed unless we unbind — guard + cleanup.
        def _unbind_liqvec_mousewheel():
            try:
                if platform.system() == "Linux":
                    vector_window.unbind_all("<Button-4>")
                    vector_window.unbind_all("<Button-5>")
                else:
                    vector_window.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass

        def _on_liqvec_destroy(event):
            if event.widget is vector_window:
                _unbind_liqvec_mousewheel()

        vector_window.bind("<Destroy>", _on_liqvec_destroy)

        def _close_liquidus_vector_window():
            self._unregister_tool_lang_refresh(_refresh_liqvec_lang)
            _unbind_liqvec_mousewheel()
            vector_window.destroy()

        vector_window.protocol("WM_DELETE_WINDOW", _close_liquidus_vector_window)

        # Bind mouse wheel to canvas (Windows and Mac)
        def _on_mousewheel(event):
            try:
                if not vector_window.winfo_exists() or not canvas.winfo_exists():
                    return
            except tk.TclError:
                return
            if platform.system() == 'Windows':
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif platform.system() == 'Darwin':  # Mac
                canvas.yview_scroll(int(-1*event.delta), "units")
            else:  # Linux
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
        
        # Bind mouse wheel events
        if platform.system() == 'Linux':
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)
        else:
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Create main frame inside scrollable frame
        main_frame = ttk.Frame(scrollable_frame, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=self.tr('liqvec_heading', 'Liquidus Vector Plotter'),
            font=('Arial', 14, 'bold'),
        )
        title_label.pack(pady=(0, 10))
        
        # Instructions
        info_label = ttk.Label(
            main_frame,
            text=self.tr('liqvec_intro', ''),
            wraplength=650,
            justify='center',
        )
        info_label.pack(pady=(0, 20))
        
        # Dataset selection (Equilibrium/Lever or Scheil)
        dataset_frame = ttk.LabelFrame(main_frame, text=self.tr('liqvec_solid_mode', 'Solidification Mode'), padding="15")
        dataset_frame.pack(fill=tk.X, pady=10)
        
        dataset_var = tk.StringVar(value="Equilibrium")
        rb_lv_eq = ttk.Radiobutton(
            dataset_frame,
            text=self.tr('plot_k_mode_eq', 'Equilibrium/Lever (P file)'),
            variable=dataset_var,
            value="Equilibrium",
        )
        rb_lv_eq.pack(side=tk.LEFT, padx=10)
        rb_lv_sc = ttk.Radiobutton(
            dataset_frame,
            text=self.tr('plot_k_mode_scheil', 'Scheil (P-S file)'),
            variable=dataset_var,
            value="Scheil",
        )
        rb_lv_sc.pack(side=tk.LEFT, padx=10)
        
        # Element selection
        element_frame = ttk.LabelFrame(main_frame, text=self.tr('liqvec_elem_sel', 'Element Selection'), padding="15")
        element_frame.pack(fill=tk.X, pady=10)
        
        def update_element_options():
            """Update element dropdown options based on Pandat data"""
            # Get available elements from imported Pandat data
            elements = self.available_elements if self.available_elements else sorted(PERIODIC_TABLE.keys())
            elem_x_combo['values'] = elements
            elem_y_combo['values'] = elements
            # Set default values if current values are not in the list
            if elem_x_var.get() not in elements and elements:
                elem_x_var.set(elements[0])
            if elem_y_var.get() not in elements and len(elements) > 1:
                elem_y_var.set(elements[1])
            elif elem_y_var.get() not in elements and elements:
                elem_y_var.set(elements[0])
        
        lbl_lv_x = ttk.Label(element_frame, text=self.tr('stp_x_element', 'X Element:'))
        lbl_lv_x.pack(side=tk.LEFT, padx=5)
        elem_x_var = tk.StringVar(value="")
        elem_x_combo = ttk.Combobox(element_frame, textvariable=elem_x_var, values=[], width=10, state="readonly")
        elem_x_combo.pack(side=tk.LEFT, padx=5)
        
        lbl_lv_y = ttk.Label(element_frame, text=self.tr('stp_y_element', 'Y Element:'))
        lbl_lv_y.pack(side=tk.LEFT, padx=15)
        elem_y_var = tk.StringVar(value="")
        elem_y_combo = ttk.Combobox(element_frame, textvariable=elem_y_var, values=[], width=10, state="readonly")
        elem_y_combo.pack(side=tk.LEFT, padx=5)
        
        # Status label (created early so it can be accessed by on_dataset_changed)
        status_label = ttk.Label(main_frame, text=self.tr('plot_ready', 'Ready to plot'), foreground="blue")
        status_label.pack(pady=10)
        
        # Update element options when dataset changes
        def on_dataset_changed():
            update_element_options()
            if self.available_elements:
                status_label.config(
                    text=self.tr('el_avail_pandat', 'Available elements from Pandat data: {els}').format(
                        els=', '.join(sorted(self.available_elements))
                    ),
                    foreground="green",
                )
            else:
                status_label.config(text=self.tr('liqvec_no_pandat', ''), foreground="orange")
        
        dataset_var.trace_add("write", lambda *args: on_dataset_changed())
        # Initial update
        on_dataset_changed()
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text=self.tr('liqvec_options', 'Options'), padding="15")
        options_frame.pack(fill=tk.X, pady=10)
        
        # Export processed data (before clean and fill)
        export_processed_frame = ttk.LabelFrame(main_frame, text=self.tr('liqvec_export_proc', 'Export Processed Data'), padding="15")
        export_processed_frame.pack(fill=tk.X, pady=10)
        
        processed_export_var = tk.StringVar()
        processed_export_entry = ttk.Entry(export_processed_frame, textvariable=processed_export_var, width=50)
        processed_export_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_processed_export():
            file_path = filedialog.asksaveasfilename(
                title=self.tr('liqvec_proc_export_title', 'Export processed data'),
                defaultextension=".xlsx",
                filetypes=[
                    (self.tr('pandat_fd_excel', 'Excel files'), "*.xlsx"),
                    (self.tr('filetype_all', 'All files'), "*.*"),
                ],
            )
            if file_path:
                processed_export_var.set(file_path)
        
        def export_processed_data():
            """Export processed data (T, w(*), 1/dwdT_L(*@LIQUID)) before clean and fill"""
            try:
                # Get dataset based on solidification mode
                ds = dataset_var.get()
                if ds == "Equilibrium":
                    source_df = self.pandat_p_data
                    if source_df is None or len(source_df) == 0:
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_no_p', 'No P file data found. Please import P file via Import → Pandat to ThermoQ first.'))
                        return
                else:  # Scheil
                    source_df = self.pandat_p_s_data
                    if source_df is None or len(source_df) == 0:
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_no_ps', 'No P-S file data found. Please import P-S file via Import → Pandat to ThermoQ first.'))
                        return
                
                status_label.config(text=self.tr('liqvec_proc_export_status', 'Processing data for export...'), foreground="orange")
                vector_window.update()
                
                # Create a copy of the source dataframe
                df = source_df.copy()
                df = _standardize_columns(df)
                
                # Find T column
                col_t = None
                for col in df.columns:
                    if isinstance(col, str) and col.strip().upper() == 'T':
                        col_t = col
                        break
                
                if col_t is None:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_liq_t_missing', 'Temperature column T not found in data!'))
                    return
                
                # Find w(*) columns for all elements
                w_cols = {}
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.strip().upper()
                        match = re.match(r'^W\(([A-Z]+)\)$', col_upper)
                        if match:
                            element = match.group(1).capitalize()
                            if element in PERIODIC_TABLE:
                                w_cols[element] = col
                
                # Find dwdT_L(*@LIQUID) columns and calculate 1/dwdT_L(*@LIQUID)
                dwdt_cols = {}
                inv_dwdt_cols = {}
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.strip().upper()
                        # Match dwdT_L(ELEMENT@LIQUID) pattern
                        match = re.match(r'^DWDT_L\(([A-Z]+)@LIQUID\)$', col_upper)
                        if match:
                            element = match.group(1).capitalize()
                            if element in PERIODIC_TABLE:
                                dwdt_cols[element] = col
                                # Calculate 1/dwdT_L(*@LIQUID) = 1 / dwdT_L(*@LIQUID)
                                inv_col_name = f"1/dwdT_L({element}@LIQUID)"
                                # Convert to numeric and calculate inverse
                                dwdt_values = pd.to_numeric(df[col], errors='coerce')
                                # Avoid division by zero
                                inv_values = np.where(dwdt_values != 0, 1.0 / dwdt_values, np.nan)
                                df[inv_col_name] = inv_values
                                inv_dwdt_cols[element] = inv_col_name
                
                # Select columns: T, w(*) for all elements, 1/dwdT_L(*@LIQUID)
                selected_cols = [col_t]
                selected_cols.extend(w_cols.values())
                selected_cols.extend(inv_dwdt_cols.values())
                
                # Create new dataframe with selected columns
                processed_df = df[selected_cols].copy()
                processed_df = processed_df.replace(r"^\s*$", np.nan, regex=True).dropna(how="all")
                
                # Get export path
                export_path = processed_export_var.get().strip()
                if not export_path:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('export_need_path', 'Please specify export path!'))
                    return
                
                # Export to Excel
                try:
                    processed_df.to_excel(export_path, index=False)
                    status_label.config(text=f"Processed data exported to: {os.path.basename(export_path)}", foreground="green")
                    messagebox.showinfo(
                    self.tr('dlg_success', 'Success'),
                    self.tr('export_ok_proc', 'Processed data exported successfully to:\n{path}').format(path=export_path),
                )
                except Exception as e:
                    messagebox.showerror(
                    self.tr('export_err_title', 'Export Error'),
                    self.tr('export_fail_proc_xlsx', 'Failed to export processed Excel file:\n{e}').format(e=str(e)),
                )
                    
            except Exception as e:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('export_fail_proc', 'Failed to export processed data:\n{e}').format(e=str(e)),
                )
        
        btn_lv_pebrowse = ttk.Button(export_processed_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_processed_export)
        btn_lv_pebrowse.pack(side=tk.RIGHT, padx=5)
        
        btn_lv_pexp = ttk.Button(export_processed_frame, text=self.tr('ui_export', 'Export'), command=export_processed_data)
        btn_lv_pexp.pack(side=tk.RIGHT, padx=5)
        
        clean_fill_var = tk.BooleanVar(value=False)
        clean_fill_cb = ttk.Checkbutton(
            options_frame,
            text=self.tr('liqvec_clean_fill', 'Clean and fill data before plotting'),
            variable=clean_fill_var,
        )
        clean_fill_cb.pack(side=tk.LEFT, padx=5)
        
        # Excel export path (only shown when clean_fill is checked)
        excel_export_frame = ttk.LabelFrame(main_frame, text=self.tr('liqvec_export_clean_frame', 'Export Cleaned Data (Excel)'), padding="15")
        excel_export_frame.pack(fill=tk.X, pady=10)
        
        excel_export_var = tk.StringVar()
        excel_export_entry = ttk.Entry(excel_export_frame, textvariable=excel_export_var, width=50)
        excel_export_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_excel_export():
            file_path = filedialog.asksaveasfilename(
                title=self.tr('liqvec_fd_clean', 'Save Cleaned Excel File'),
                defaultextension=".xlsx",
                filetypes=[
                    (self.tr('pandat_fd_excel', 'Excel files'), "*.xlsx"),
                    (self.tr('filetype_all', 'All files'), "*.*"),
                ],
            )
            if file_path:
                excel_export_var.set(file_path)
        
        def export_cleaned_data():
            """Export cleaned data (after clean and fill)"""
            try:
                # Get dataset based on solidification mode
                ds = dataset_var.get()
                if ds == "Equilibrium":
                    source_df = self.pandat_p_data
                    if source_df is None or len(source_df) == 0:
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_no_p', 'No P file data found. Please import P file via Import → Pandat to ThermoQ first.'))
                        return
                else:  # Scheil
                    source_df = self.pandat_p_s_data
                    if source_df is None or len(source_df) == 0:
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_no_ps', 'No P-S file data found. Please import P-S file via Import → Pandat to ThermoQ first.'))
                        return
                
                status_label.config(text=self.tr('liqvec_clean_prep_status', 'Processing and cleaning data for export...'), foreground="orange")
                vector_window.update()
                
                # Create a copy of the source dataframe
                df = source_df.copy()
                df = _standardize_columns(df)
                
                # Find T column
                col_t = None
                for col in df.columns:
                    if isinstance(col, str) and col.strip().upper() == 'T':
                        col_t = col
                        break
                
                if col_t is None:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_liq_t_missing', 'Temperature column T not found in data!'))
                    return
                
                # Find w(*) columns for all elements
                w_cols = {}
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.strip().upper()
                        match = re.match(r'^W\(([A-Z]+)\)$', col_upper)
                        if match:
                            element = match.group(1).capitalize()
                            if element in PERIODIC_TABLE:
                                w_cols[element] = col
                
                # Find dwdT_L(*@LIQUID) columns and calculate 1/dwdT_L(*@LIQUID)
                dwdt_cols = {}
                inv_dwdt_cols = {}
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.strip().upper()
                        # Match dwdT_L(ELEMENT@LIQUID) pattern
                        match = re.match(r'^DWDT_L\(([A-Z]+)@LIQUID\)$', col_upper)
                        if match:
                            element = match.group(1).capitalize()
                            if element in PERIODIC_TABLE:
                                dwdt_cols[element] = col
                                # Calculate 1/dwdT_L(*@LIQUID) = 1 / dwdT_L(*@LIQUID)
                                inv_col_name = f"1/dwdT_L({element}@LIQUID)"
                                # Convert to numeric and calculate inverse
                                dwdt_values = pd.to_numeric(df[col], errors='coerce')
                                # Avoid division by zero
                                inv_values = np.where(dwdt_values != 0, 1.0 / dwdt_values, np.nan)
                                df[inv_col_name] = inv_values
                                inv_dwdt_cols[element] = inv_col_name
                
                # Select columns: T, w(*) for all elements, 1/dwdT_L(*@LIQUID)
                selected_cols = [col_t]
                selected_cols.extend(w_cols.values())
                selected_cols.extend(inv_dwdt_cols.values())
                
                # Create new dataframe with selected columns
                df = df[selected_cols].copy()
                df = df.replace(r"^\s*$", np.nan, regex=True).dropna(how="all")
                
                # Clean and fill data (same as Composition space batch Excel export)
                status_label.config(text=self.tr('liqvec_status_clean_fill', 'Cleaning and filling data...'), foreground="orange")
                vector_window.update()

                ex = elem_x_var.get().strip()
                ey = elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_select_xy', 'Please select X and Y elements!'))
                    return
                try:
                    cleaned_df = self._liquidus_clean_fill_dataframe(df, ex, ey)
                except ValueError as ve:
                    code = str(ve)
                    if code == "need_xy":
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_select_xy', 'Please select X and Y elements!'))
                    elif code == "no_T":
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_liq_t_missing', 'Temperature column T not found!'))
                    elif code.startswith("MISSING_W:"):
                        parts = code.split(":", 3)
                        avail = parts[3] if len(parts) > 3 else ""
                        messagebox.showerror(
                            self.tr('dlg_error', 'Error'),
                            self.tr(
                                'plot_liq_el_missing',
                                'Element {el} not found in data. Available elements: {avail}',
                            ).format(el=f'{ex} / {ey}', avail=avail or '—'),
                        )
                    elif code.startswith("MISSING_DWDT:"):
                        miss_el = code.split(":", 1)[1] if ":" in code else ex
                        messagebox.showerror(
                            self.tr('dlg_error', 'Error'),
                            self.tr('plot_liq_dwdT_missing', 'Column dwdT_L({el}@LIQUID) not found in data!').format(el=miss_el),
                        )
                    else:
                        messagebox.showerror(self.tr('dlg_error', 'Error'), code)
                    return
                
                # Get export path
                export_path = excel_export_var.get().strip()
                if not export_path:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('export_need_path', 'Please specify export path!'))
                    return
                
                # Export to Excel
                try:
                    cleaned_df.to_excel(export_path, index=False)
                    status_label.config(text=f"Cleaned data exported to: {os.path.basename(export_path)}", foreground="green")
                    messagebox.showinfo(
                    self.tr('dlg_success', 'Success'),
                    self.tr('export_ok_clean', 'Cleaned data exported successfully to:\n{path}').format(path=export_path),
                )
                except Exception as e:
                    messagebox.showerror(
                    self.tr('export_err_title', 'Export Error'),
                    self.tr('export_fail_clean_xlsx', 'Failed to export cleaned Excel file:\n{e}').format(e=str(e)),
                )
                    
            except Exception as e:
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('export_fail_clean', 'Failed to export cleaned data:\n{e}').format(e=str(e)),
                )
        
        btn_lv_xlbrowse = ttk.Button(excel_export_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_excel_export)
        btn_lv_xlbrowse.pack(side=tk.RIGHT, padx=5)
        
        btn_lv_xlexp = ttk.Button(excel_export_frame, text=self.tr('ui_export', 'Export'), command=export_cleaned_data)
        btn_lv_xlexp.pack(side=tk.RIGHT, padx=5)
        
        # Initially hide Excel export frame
        excel_export_frame.pack_forget()
        
        def toggle_excel_export():
            if clean_fill_var.get():
                excel_export_frame.pack(fill=tk.X, pady=10, before=output_frame)
            else:
                excel_export_frame.pack_forget()
        
        clean_fill_var.trace_add("write", lambda *args: toggle_excel_export())
        
        # Visualization options for Z vectors on liquidus surface
        viz_frame = ttk.LabelFrame(main_frame, text=self.tr('liqvec_viz_frame', 'Visualization'), padding="15")
        viz_frame.pack(fill=tk.X, pady=10)
        
        viz_var = tk.StringVar(value="2D Heatmap")
        rb_lv_v2 = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_2d', '2D Heatmap'), variable=viz_var, value="2D Heatmap")
        rb_lv_v2.pack(side=tk.LEFT, padx=5)
        rb_lv_v3 = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_3d', '3D Static'), variable=viz_var, value="3D Static")
        rb_lv_v3.pack(side=tk.LEFT, padx=5)
        rb_lv_vg = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_gif', '3D Rotation GIF'), variable=viz_var, value="3D Rotation GIF")
        rb_lv_vg.pack(side=tk.LEFT, padx=5)
        rb_lv_vp = ttk.Radiobutton(viz_frame, text=self.tr('batch_viz_plotly', 'Plotly 3D'), variable=viz_var, value="Plotly 3D")
        rb_lv_vp.pack(side=tk.LEFT, padx=5)
        
        # Smoothness control for liquidus surface
        smooth_frame = ttk.Frame(viz_frame)
        smooth_frame.pack(fill=tk.X, pady=5)
        lbl_lv_sm = ttk.Label(smooth_frame, text=self.tr('batch_smooth', 'Smoothness:'))
        lbl_lv_sm.pack(side=tk.LEFT, padx=5)
        smoothness_var = tk.DoubleVar(value=100.0)
        smoothness_value_label = ttk.Label(smooth_frame, text="100")
        smoothness_value_label.pack(side=tk.RIGHT, padx=5)
        
        def _on_smoothness_change(val):
            try:
                smoothness_value_label.config(text=str(int(float(val))))
            except Exception:
                smoothness_value_label.config(text="100")
        
        smooth_scale = ttk.Scale(
            smooth_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=smoothness_var,
            command=_on_smoothness_change
        )
        smooth_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Arrow settings (length & head size)
        arrow_settings_frame = ttk.LabelFrame(viz_frame, text=self.tr('liqvec_arrow_3d', 'Arrow Settings (3D)'), padding="10")
        arrow_settings_frame.pack(fill=tk.X, pady=5)
        
        # Matplotlib 3D (Static/GIF) settings
        mpl_arrow_frame = ttk.LabelFrame(arrow_settings_frame, text=self.tr('liqvec_mpl_arrow', '3D Static / 3D Rotation GIF (Matplotlib)'), padding="8")
        mpl_arrow_frame.pack(fill=tk.X, pady=5)
        
        mpl_arrow_len_scale_var = tk.DoubleVar(value=1.0)
        mpl_arrow_head_scale_var = tk.DoubleVar(value=1.0)
        
        mpl_len_row = ttk.Frame(mpl_arrow_frame)
        mpl_len_row.pack(fill=tk.X, pady=2)
        lbl_lv_mlen = ttk.Label(mpl_len_row, text=self.tr('liqvec_arrow_len', 'Arrow Length Scale:'))
        lbl_lv_mlen.pack(side=tk.LEFT, padx=5)
        mpl_len_val = ttk.Label(mpl_len_row, text="1.00")
        mpl_len_val.pack(side=tk.RIGHT, padx=5)
        def _on_mpl_len_change(val):
            try:
                mpl_len_val.config(text=f"{float(val):.2f}")
            except Exception:
                mpl_len_val.config(text="1.00")
        ttk.Scale(mpl_len_row, from_=0.1, to=5.0, orient="horizontal",
                  variable=mpl_arrow_len_scale_var, command=_on_mpl_len_change).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        mpl_head_row = ttk.Frame(mpl_arrow_frame)
        mpl_head_row.pack(fill=tk.X, pady=2)
        lbl_lv_mhead = ttk.Label(mpl_head_row, text=self.tr('liqvec_arrow_head', 'Arrow Head Size:'))
        lbl_lv_mhead.pack(side=tk.LEFT, padx=5)
        mpl_head_val = ttk.Label(mpl_head_row, text="1.00")
        mpl_head_val.pack(side=tk.RIGHT, padx=5)
        def _on_mpl_head_change(val):
            try:
                mpl_head_val.config(text=f"{float(val):.2f}")
            except Exception:
                mpl_head_val.config(text="1.00")
        ttk.Scale(mpl_head_row, from_=0.2, to=3.0, orient="horizontal",
                  variable=mpl_arrow_head_scale_var, command=_on_mpl_head_change).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Plotly 3D settings
        plotly_arrow_frame = ttk.LabelFrame(arrow_settings_frame, text=self.tr('liqvec_plotly_arrow', 'Plotly 3D (Interactive)'), padding="8")
        plotly_arrow_frame.pack(fill=tk.X, pady=5)
        
        plotly_arrow_len_scale_var = tk.DoubleVar(value=2.0)
        plotly_arrow_head_scale_var = tk.DoubleVar(value=2.0)
        
        plotly_len_row = ttk.Frame(plotly_arrow_frame)
        plotly_len_row.pack(fill=tk.X, pady=2)
        lbl_lv_plen = ttk.Label(plotly_len_row, text=self.tr('liqvec_plotly_len', 'Arrow Length Scale (relative):'))
        lbl_lv_plen.pack(side=tk.LEFT, padx=5)
        plotly_len_val = ttk.Label(plotly_len_row, text="2.00")
        plotly_len_val.pack(side=tk.RIGHT, padx=5)
        def _on_plotly_len_change(val):
            try:
                plotly_len_val.config(text=f"{float(val):.2f}")
            except Exception:
                plotly_len_val.config(text="2.00")
        ttk.Scale(plotly_len_row, from_=0.05, to=5.0, orient="horizontal",
                  variable=plotly_arrow_len_scale_var, command=_on_plotly_len_change).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        plotly_head_row = ttk.Frame(plotly_arrow_frame)
        plotly_head_row.pack(fill=tk.X, pady=2)
        lbl_lv_phead = ttk.Label(plotly_head_row, text=self.tr('liqvec_plotly_head', 'Arrow Head Fraction:'))
        lbl_lv_phead.pack(side=tk.LEFT, padx=5)
        plotly_head_val = ttk.Label(plotly_head_row, text="2.00")
        plotly_head_val.pack(side=tk.RIGHT, padx=5)
        def _on_plotly_head_change(val):
            try:
                plotly_head_val.config(text=f"{float(val):.2f}")
            except Exception:
                plotly_head_val.config(text="2.00")
        ttk.Scale(plotly_head_row, from_=0.2, to=4.0, orient="horizontal",
                  variable=plotly_arrow_head_scale_var, command=_on_plotly_head_change).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 3D Static view (camera) settings for Liquidus Vector Plotter
        lv_view_frame = ttk.LabelFrame(viz_frame, text=self.tr('batch_view_3d', '3D Static View (Rotation Angles)'), padding="10")
        lv_view_frame.pack(fill=tk.X, pady=5)
        lv_elev_var = tk.DoubleVar(value=30.0)
        lv_azim_var = tk.DoubleVar(value=-60.0)

        lv_elev_row = ttk.Frame(lv_view_frame)
        lv_elev_row.pack(fill=tk.X, pady=2)
        lbl_lv_elev = ttk.Label(lv_elev_row, text=self.tr('batch_elev', 'Elevation (deg):'))
        lbl_lv_elev.pack(side=tk.LEFT, padx=5)
        ttk.Entry(lv_elev_row, textvariable=lv_elev_var, width=8).pack(side=tk.LEFT, padx=5)
        lbl_lv_elev_r = ttk.Label(lv_elev_row, text=self.tr('plot_elev_range', '(0–90)'))
        lbl_lv_elev_r.pack(side=tk.LEFT, padx=5)

        lv_azim_row = ttk.Frame(lv_view_frame)
        lv_azim_row.pack(fill=tk.X, pady=2)
        lbl_lv_azim = ttk.Label(lv_azim_row, text=self.tr('batch_azim', 'Azimuth (deg):'))
        lbl_lv_azim.pack(side=tk.LEFT, padx=5)
        ttk.Entry(lv_azim_row, textvariable=lv_azim_var, width=8).pack(side=tk.LEFT, padx=5)
        lbl_lv_azim_r = ttk.Label(lv_azim_row, text=self.tr('plot_azim_range', '(-180–180)'))
        lbl_lv_azim_r.pack(side=tk.LEFT, padx=5)
        
        # 3D Rotation GIF parameters (only shown when 3D Rotation GIF is selected)
        gif_params_frame = ttk.LabelFrame(viz_frame, text=self.tr('batch_gif_params', '3D Rotation GIF Parameters'), padding="10")
        gif_params_frame.pack(fill=tk.X, pady=5)
        
        gif_speed_frame = ttk.Frame(gif_params_frame)
        gif_speed_frame.pack(fill=tk.X, pady=3)
        lbl_lv_gspd = ttk.Label(gif_speed_frame, text=self.tr('batch_gif_speed', 'Rotation Speed (degrees/frame):'))
        lbl_lv_gspd.pack(side=tk.LEFT, padx=5)
        gif_speed_var = tk.StringVar(value="5")
        ttk.Entry(gif_speed_frame, textvariable=gif_speed_var, width=10).pack(side=tk.LEFT, padx=5)
        
        gif_interval_frame = ttk.Frame(gif_params_frame)
        gif_interval_frame.pack(fill=tk.X, pady=3)
        lbl_lv_gint = ttk.Label(gif_interval_frame, text=self.tr('batch_gif_interval', 'Frame Interval (ms):'))
        lbl_lv_gint.pack(side=tk.LEFT, padx=5)
        gif_interval_var = tk.StringVar(value="50")
        ttk.Entry(gif_interval_frame, textvariable=gif_interval_var, width=10).pack(side=tk.LEFT, padx=5)
        
        gif_fps_frame = ttk.Frame(gif_params_frame)
        gif_fps_frame.pack(fill=tk.X, pady=3)
        lbl_lv_gfps = ttk.Label(gif_fps_frame, text=self.tr('batch_gif_fps', 'FPS:'))
        lbl_lv_gfps.pack(side=tk.LEFT, padx=5)
        gif_fps_var = tk.StringVar(value="20")
        ttk.Entry(gif_fps_frame, textvariable=gif_fps_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Initially hide GIF parameters
        gif_params_frame.pack_forget()
        
        def toggle_gif_params():
            if viz_var.get() == "3D Rotation GIF":
                gif_params_frame.pack(fill=tk.X, pady=5)
            else:
                gif_params_frame.pack_forget()
        
        viz_var.trace_add("write", lambda *args: toggle_gif_params())
        
        # Output settings
        output_frame = ttk.LabelFrame(main_frame, text=self.tr('plot_phase_output_settings', 'Output Settings'), padding="15")
        output_frame.pack(fill=tk.X, pady=10)
        
        # Output directory
        output_dir_frame = ttk.Frame(output_frame)
        output_dir_frame.pack(fill=tk.X, pady=5)
        lbl_lv_od = ttk.Label(output_dir_frame, text=self.tr('batch_output_dir', 'Output Directory:'))
        lbl_lv_od.pack(side=tk.LEFT, padx=5)
        output_dir_var = tk.StringVar()
        ttk.Entry(output_dir_frame, textvariable=output_dir_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        def browse_output_dir():
            dir_path = filedialog.askdirectory(title=self.tr('extp_fd_output', 'Select output directory'))
            if dir_path:
                output_dir_var.set(dir_path)
        btn_lv_out = ttk.Button(output_dir_frame, text=self.tr('pandat_browse', 'Browse'), command=browse_output_dir)
        btn_lv_out.pack(side=tk.RIGHT, padx=5)
        
        # Output prefix
        output_prefix_frame = ttk.Frame(output_frame)
        output_prefix_frame.pack(fill=tk.X, pady=5)
        lbl_lv_pfx = ttk.Label(output_prefix_frame, text=self.tr('batch_prefix', 'Output Prefix:'))
        lbl_lv_pfx.pack(side=tk.LEFT, padx=5)
        output_var = tk.StringVar(value="liquid_vectors")
        ttk.Entry(output_prefix_frame, textvariable=output_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Image format selection
        format_frame = ttk.Frame(output_frame)
        format_frame.pack(fill=tk.X, pady=5)
        lbl_lv_ifmt = ttk.Label(format_frame, text=self.tr('batch_image_fmt', 'Image Format (2D/3D Static):'))
        lbl_lv_ifmt.pack(side=tk.LEFT, padx=5)
        image_format_var = tk.StringVar(value="PNG")
        format_options = ["PNG", "JPEG", "GIF", "BMP", "TIFF", "WebP", "SVG", "PDF", "EPS"]
        format_combo = ttk.Combobox(format_frame, textvariable=image_format_var, values=format_options, 
                                   state="readonly", width=15)
        format_combo.pack(side=tk.LEFT, padx=5)
        
        def _standardize_columns(df):
            """Standardize column names"""
            df = df.rename(columns={c: c.strip() for c in df.columns})
            return df
        
        def _find_required_columns(df, ex, ey):
            """Find required columns for elements"""
            norm = {c: re.sub(r"\s+", "", c, flags=re.UNICODE).lower() for c in df.columns}
            rev = {v: k for k, v in norm.items()}
            
            def find_by_exact(key):
                return rev.get(key)
            
            def find_by_regex(patterns):
                for c in df.columns:
                    s = c.lower()
                    if all(re.search(p, s, flags=re.IGNORECASE) for p in patterns):
                        return c
                return None
            
            wx = find_by_exact(f"w({ex.lower()})") or find_by_regex([rf"^w\({ex.lower()}\)"])
            wy = find_by_exact(f"w({ey.lower()})") or find_by_regex([rf"^w\({ey.lower()}\)"])
            
            inv_x = find_by_exact(f"1/dwdt_l({ex.lower()}@liquid)") or find_by_regex([
                r"1/dwdt_l\(", rf"{ex.lower()}@liquid\)"
            ])
            inv_y = find_by_exact(f"1/dwdt_l({ey.lower()}@liquid)") or find_by_regex([
                r"1/dwdt_l\(", rf"{ey.lower()}@liquid\)"
            ])
            
            if not (wx and wy and inv_x and inv_y):
                raise ValueError(
                    f"Missing required columns. Need: 'w({ex})', 'w({ey})', "
                    f"'1/dwdT_L({ex}@LIQUID)', '1/dwdT_L({ey}@LIQUID)'. "
                    f"Found: {list(df.columns)}"
                )
            
            return wx, wy, inv_x, inv_y
        
        def plot_vectors():
            """Plot liquidus vectors"""
            try:
                # Get dataset based on solidification mode
                ds = dataset_var.get()
                if ds == "Equilibrium":
                    source_df = self.pandat_p_data
                    if source_df is None or len(source_df) == 0:
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_no_p', 'No P file data found. Please import P file via Import → Pandat to ThermoQ first.'))
                        return
                else:  # Scheil
                    source_df = self.pandat_p_s_data
                    if source_df is None or len(source_df) == 0:
                        messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_no_ps', 'No P-S file data found. Please import P-S file via Import → Pandat to ThermoQ first.'))
                        return
                
                ex = elem_x_var.get().strip()
                ey = elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_select_xy', 'Please select X and Y elements!'))
                    return
                
                if ex not in PERIODIC_TABLE or ey not in PERIODIC_TABLE:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('plot_liq_invalid_els', 'Invalid elements: {ex} or {ey}').format(ex=ex, ey=ey),
                    )
                    return
                
                status_label.config(text=self.tr('liqvec_plot_proc_status', 'Processing data...'), foreground="orange")
                vector_window.update()
                
                # Create a copy of the source dataframe
                df = source_df.copy()
                df = _standardize_columns(df)
                
                # Find T column
                col_t = None
                for col in df.columns:
                    if isinstance(col, str) and col.strip().upper() == 'T':
                        col_t = col
                        break
                
                if col_t is None:
                    messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_liq_t_missing', 'Temperature column T not found in data!'))
                    return
                
                # Find w(*) columns for all elements
                w_cols = {}
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.strip().upper()
                        match = re.match(r'^W\(([A-Z]+)\)$', col_upper)
                        if match:
                            element = match.group(1).capitalize()
                            if element in PERIODIC_TABLE:
                                w_cols[element] = col
                
                # Find dwdT_L(*@LIQUID) columns and calculate 1/dwdT_L(*@LIQUID)
                dwdt_cols = {}
                inv_dwdt_cols = {}
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.strip().upper()
                        # Match dwdT_L(ELEMENT@LIQUID) pattern
                        match = re.match(r'^DWDT_L\(([A-Z]+)@LIQUID\)$', col_upper)
                        if match:
                            element = match.group(1).capitalize()
                            if element in PERIODIC_TABLE:
                                dwdt_cols[element] = col
                                # Calculate 1/dwdT_L(*@LIQUID) = 1 / dwdT_L(*@LIQUID)
                                inv_col_name = f"1/dwdT_L({element}@LIQUID)"
                                # Convert to numeric and calculate inverse
                                dwdt_values = pd.to_numeric(df[col], errors='coerce')
                                # Avoid division by zero
                                inv_values = np.where(dwdt_values != 0, 1.0 / dwdt_values, np.nan)
                                df[inv_col_name] = inv_values
                                inv_dwdt_cols[element] = inv_col_name
                
                # Select columns: T, w(*) for all elements
                selected_cols = [col_t]
                selected_cols.extend(w_cols.values())
                selected_cols.extend(inv_dwdt_cols.values())
                
                # Create new dataframe with selected columns
                df = df[selected_cols].copy()
                df = df.replace(r"^\s*$", np.nan, regex=True).dropna(how="all")
                
                # Check if required elements exist
                if ex not in w_cols:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr(
                            'plot_liq_el_missing',
                            'Element {el} not found in data. Available elements: {avail}',
                        ).format(el=ex, avail=', '.join(sorted(w_cols.keys()))),
                    )
                    return
                if ey not in w_cols:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr(
                            'plot_liq_el_missing',
                            'Element {el} not found in data. Available elements: {avail}',
                        ).format(el=ey, avail=', '.join(sorted(w_cols.keys()))),
                    )
                    return
                if ex not in inv_dwdt_cols:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('plot_liq_dwdT_missing', 'Column dwdT_L({el}@LIQUID) not found in data!').format(el=ex),
                    )
                    return
                if ey not in inv_dwdt_cols:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('plot_liq_dwdT_missing', 'Column dwdT_L({el}@LIQUID) not found in data!').format(el=ey),
                    )
                    return
                
                col_wx = w_cols[ex]
                col_wy = w_cols[ey]
                col_inv_x = inv_dwdt_cols[ex]
                col_inv_y = inv_dwdt_cols[ey]
                
                # Clean and fill if requested (same routine as batch “Save Excel (cleaned + batch)”)
                cleaned_df = None
                if clean_fill_var.get():
                    status_label.config(text=self.tr('liqvec_status_clean_fill', 'Cleaning and filling data...'), foreground="orange")
                    vector_window.update()
                    try:
                        df = self._liquidus_clean_fill_dataframe(df, ex, ey)
                    except ValueError as ve:
                        code = str(ve)
                        if code == "need_xy":
                            messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_k_select_xy', 'Please select X and Y elements!'))
                        elif code == "no_T":
                            messagebox.showerror(self.tr('dlg_error', 'Error'), self.tr('plot_liq_t_missing', 'Temperature column T not found!'))
                        elif code.startswith("MISSING_W:"):
                            parts = code.split(":", 3)
                            avail = parts[3] if len(parts) > 3 else ""
                            messagebox.showerror(
                                self.tr('dlg_error', 'Error'),
                                self.tr(
                                    'plot_liq_el_missing',
                                    'Element {el} not found in data. Available elements: {avail}',
                                ).format(el=f'{ex} / {ey}', avail=avail or '—'),
                            )
                        elif code.startswith("MISSING_DWDT:"):
                            miss_el = code.split(":", 1)[1] if ":" in code else ex
                            messagebox.showerror(
                                self.tr('dlg_error', 'Error'),
                                self.tr('plot_liq_dwdT_missing', 'Column dwdT_L({el}@LIQUID) not found in data!').format(el=miss_el),
                            )
                        else:
                            messagebox.showerror(self.tr('dlg_error', 'Error'), code)
                        return
                    cleaned_df = df.copy()

                    # Export cleaned Excel if path is specified
                    excel_export_path = excel_export_var.get().strip()
                    if excel_export_path:
                        try:
                            cleaned_df.to_excel(excel_export_path, index=False)
                            status_label.config(text=f"Cleaned data exported to: {os.path.basename(excel_export_path)}", foreground="green")
                            messagebox.showinfo(
                                self.tr('dlg_success', 'Success'),
                                self.tr('export_ok_clean', 'Cleaned data exported successfully to:\n{path}').format(path=excel_export_path),
                            )
                        except Exception as e:
                            messagebox.showerror(
                                self.tr('export_err_title', 'Export Error'),
                                self.tr('export_fail_clean_xlsx', 'Failed to export cleaned Excel file:\n{e}').format(e=str(e)),
                            )
                
                status_label.config(text=self.tr('liqvec_plot_proc_status', 'Processing data...'), foreground="orange")
                vector_window.update()
                
                # Convert to numeric
                wx = pd.to_numeric(df[col_wx], errors="coerce")
                wy = pd.to_numeric(df[col_wy], errors="coerce")
                u = pd.to_numeric(df[col_inv_x], errors="coerce")
                v = pd.to_numeric(df[col_inv_y], errors="coerce")
                
                valid = ~(wx.isna() | wy.isna() | u.isna() | v.isna())
                wx, wy, u, v = wx[valid], wy[valid], u[valid], v[valid]
                
                if len(wx) == 0:
                    messagebox.showerror(
                        self.tr('dlg_error', 'Error'),
                        self.tr('plot_liq_no_points_filter', 'No valid data points found after filtering!'),
                    )
                    return
                
                # Scale U and V
                denom_u = u.min()
                denom_v = v.min()
                if denom_u == 0 or np.isnan(denom_u):
                    raise ValueError(f"Column 1/dwdT_L({ex}@LIQUID) has invalid minimum for scaling.")
                if denom_v == 0 or np.isnan(denom_v):
                    raise ValueError(f"Column 1/dwdT_L({ey}@LIQUID) has invalid minimum for scaling.")
                
                dx = u / denom_u
                dy = v / denom_v
                
                # Clip to data domain
                x_min, x_max = float(wx.min()), float(wx.max())
                y_min, y_max = float(wy.min()), float(wy.max())
                
                # Get temperature data for 3D plot
                t_data = pd.to_numeric(df[col_t], errors="coerce")[valid]
                
                prefix = output_var.get().strip() or "liquid_vectors"
                # Get output directory
                output_dir = output_dir_var.get().strip()
                if output_dir and os.path.exists(output_dir):
                    base_path = output_dir
                else:
                    base_path = "."
                
                # Get image format
                img_format = image_format_var.get().upper()
                format_ext_map = {
                    "PNG": "png", "JPEG": "jpg", "GIF": "gif", "BMP": "bmp",
                    "TIFF": "tiff", "WEBP": "webp", "SVG": "svg", "PDF": "pdf", "EPS": "eps"
                }
                ext = format_ext_map.get(img_format, "png")
                
                status_label.config(text="Generating plots...", foreground="orange")
                vector_window.update()
                
                # Determine save parameters based on format
                save_kwargs = {"dpi": 300, "bbox_inches": "tight"}
                if img_format == "PDF":
                    save_kwargs["format"] = "pdf"
                elif img_format == "EPS":
                    save_kwargs["format"] = "eps"
                elif img_format == "SVG":
                    save_kwargs["format"] = "svg"
                elif img_format in ["JPEG", "JPG"]:
                    save_kwargs["format"] = "jpeg"
                elif img_format == "TIFF":
                    save_kwargs["format"] = "tiff"
                elif img_format == "WEBP":
                    save_kwargs["format"] = "webp"
                elif img_format == "BMP":
                    save_kwargs["format"] = "bmp"
                elif img_format == "GIF":
                    save_kwargs["format"] = "gif"
                else:  # PNG default
                    save_kwargs["format"] = "png"
                
                # Figure 1: U arrows (horizontal)
                fig1, ax1 = plt.subplots(figsize=(7, 6), dpi=140)
                x1 = np.clip(wx.values + dx.values, x_min, x_max)
                u_plot = x1 - wx.values
                ax1.quiver(wx.values, wy.values, u_plot, np.zeros_like(u_plot), 
                          angles="xy", scale_units="xy", scale=1, width=0.003, color="tab:blue")
                ax1.set_xlabel(col_wx)
                ax1.set_ylabel(col_wy)
                ax1.set_title(f"U arrows (scaled by ratio to min of 1/dwdT_L({ex}@LIQUID))")
                ax1.grid(False)
                ax1.set_aspect("equal", adjustable="box")
                fig1.tight_layout()
                out1 = os.path.join(base_path, f"{prefix}_{ex}_horizontal.{ext}")
                fig1.savefig(out1, **save_kwargs)
                plt.close(fig1)
                self.open_file_and_offer_save_as(out1, vector_window)
                
                # Figure 2: V arrows (vertical)
                fig2, ax2 = plt.subplots(figsize=(7, 6), dpi=140)
                y1 = np.clip(wy.values + dy.values, y_min, y_max)
                v_plot = y1 - wy.values
                ax2.quiver(wx.values, wy.values, np.zeros_like(v_plot), v_plot, 
                          angles="xy", scale_units="xy", scale=1, width=0.003, color="tab:orange")
                ax2.set_xlabel(col_wx)
                ax2.set_ylabel(col_wy)
                ax2.set_title(f"V arrows (scaled by ratio to min of 1/dwdT_L({ey}@LIQUID))")
                ax2.grid(False)
                ax2.set_aspect("equal", adjustable="box")
                fig2.tight_layout()
                out2 = os.path.join(base_path, f"{prefix}_{ey}_vertical.{ext}")
                fig2.savefig(out2, **save_kwargs)
                plt.close(fig2)
                self.open_file_and_offer_save_as(out2, vector_window)
                
                # Figure 3: Resultant Z vector
                fig3, ax3 = plt.subplots(figsize=(7, 6), dpi=140)
                z_dx = u_plot
                z_dy = v_plot
                ax3.quiver(wx.values, wy.values, z_dx, z_dy, 
                          angles="xy", scale_units="xy", scale=1, width=0.003, color="tab:green")
                ax3.set_xlabel(col_wx)
                ax3.set_ylabel(col_wy)
                ax3.set_title(f"Resultant Z = vector sum of U and V (scaled)")
                ax3.grid(False)
                ax3.set_aspect("equal", adjustable="box")
                fig3.tight_layout()
                out3 = os.path.join(base_path, f"{prefix}_Z_resultant.{ext}")
                fig3.savefig(out3, **save_kwargs)
                plt.close(fig3)
                self.open_file_and_offer_save_as(out3, vector_window)
                
                # Figure 4: Z vectors on liquidus surface (with visualization options)
                out4 = None
                if len(t_data) > 0 and not t_data.isna().all():
                    try:
                        # Create smooth liquidus surface
                        status_label.config(text="Creating smooth liquidus surface...", foreground="orange")
                        vector_window.update()
                        
                        # Get smooth surface for temperature
                        t_smooth = self.create_smooth_surface(
                            wx.values, wy.values, t_data.values, 
                            grid_resolution=100,
                            smoothness=smoothness_var.get()
                        )
                        
                        if t_smooth is not None:
                            xi_grid_smooth, yi_grid_smooth, zi_grid = t_smooth
                        else:
                            xi_grid_smooth, yi_grid_smooth, zi_grid = None, None, None
                        
                        # Get visualization type
                        viz = viz_var.get()
                        
                        # Normalize arrow size by dividing by the maximum absolute component.
                        # Then scale arrows to a fixed fraction of the x/y axis span so they don't become excessively long.
                        z_dx_arr = np.asarray(z_dx, dtype=float)
                        z_dy_arr = np.asarray(z_dy, dtype=float)
                        max_abs = float(np.nanmax(np.abs(np.r_[z_dx_arr, z_dy_arr])))
                        if (not np.isfinite(max_abs)) or max_abs == 0:
                            max_abs = 1.0
                        axis_span = max(float(x_max - x_min), float(y_max - y_min), 1e-9)
                        arrow_scale_xy = 0.10 * axis_span
                        z_dx_norm = (z_dx_arr / max_abs) * arrow_scale_xy
                        z_dy_norm = (z_dy_arr / max_abs) * arrow_scale_xy
                        
                        # Calculate z_surface_values for vectors
                        z_surface_values = []
                        if xi_grid_smooth is not None:
                            for i in range(len(wx.values)):
                                x_idx = np.argmin(np.abs(xi_grid_smooth[0, :] - wx.values[i]))
                                y_idx = np.argmin(np.abs(yi_grid_smooth[:, 0] - wy.values[i]))
                                z_surf = zi_grid[y_idx, x_idx]
                                z_surface_values.append(z_surf)
                        else:
                            z_surface_values = t_data.values
                        z_surface_values = np.array(z_surface_values)

                        # Helper: sample surface Z at an arbitrary (x, y) so vector tails lie on the surface
                        wx_arr = np.asarray(wx.values, dtype=float)
                        wy_arr = np.asarray(wy.values, dtype=float)
                        t_arr = np.asarray(t_data.values, dtype=float)

                        def _surface_z_at(xp, yp):
                            try:
                                if xi_grid_smooth is not None and zi_grid is not None:
                                    xi_1d = xi_grid_smooth[0, :]
                                    yi_1d = yi_grid_smooth[:, 0]
                                    x_idx = int(np.argmin(np.abs(xi_1d - xp)))
                                    y_idx = int(np.argmin(np.abs(yi_1d - yp)))
                                    return float(zi_grid[y_idx, x_idx])
                            except Exception:
                                pass
                            # Fallback: nearest neighbor from available points
                            try:
                                j = int(np.argmin((wx_arr - xp) ** 2 + (wy_arr - yp) ** 2))
                                return float(t_arr[j])
                            except Exception:
                                return float("nan")
                        
                        if viz == "2D Heatmap":
                            if not MATPLOTLIB_AVAILABLE:
                                messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_2d', 'Matplotlib is not installed. Cannot generate 2D heatmap.'))
                                return
                            plt.figure(figsize=(10, 8))
                            plt.xlabel(f"{col_wx} (%)")
                            plt.ylabel(f"{col_wy} (%)")
                            if xi_grid_smooth is not None:
                                # Use smooth surface
                                contour = plt.contourf(xi_grid_smooth, yi_grid_smooth, zi_grid, levels=50, cmap='coolwarm', alpha=1.0)
                                plt.colorbar(contour, label='T (Temperature)')
                            else:
                                # Fallback to scatter
                                scatter = plt.scatter(wx.values, wy.values, c=t_data.values, cmap='coolwarm', s=40, alpha=0.9)
                                plt.colorbar(scatter, label='T (Temperature)')
                            
                            # Overlay Z vectors
                            plt.quiver(wx.values, wy.values, z_dx_norm, z_dy_norm,
                                     angles="xy", scale_units="xy", scale=1, width=0.003, color="green", alpha=0.7)
                            
                            plt.grid(False)
                            out4 = os.path.join(base_path, f"{prefix}_Z_on_liquidus_Heatmap.{ext}")
                            plt.savefig(out4, dpi=300, bbox_inches='tight')
                            plt.close()
                            status_label.config(text=f"Heatmap saved: {out4}", foreground="green")
                            self.open_file_and_offer_save_as(out4, vector_window)
                            
                        elif viz == "3D Static":
                            if not MATPLOTLIB_AVAILABLE:
                                messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_3d', 'Matplotlib is not installed. Cannot generate 3D image.'))
                                return
                            fig4 = plt.figure(figsize=(12, 10))
                            ax4 = fig4.add_subplot(111, projection='3d')
                            if xi_grid_smooth is not None:
                                # Use smooth surface
                                surf = ax4.plot_surface(xi_grid_smooth, yi_grid_smooth, zi_grid, cmap='coolwarm', alpha=0.98, 
                                                      linewidth=0, antialiased=True, shade=True)
                                fig4.colorbar(surf, shrink=0.5, aspect=5, label='T (Temperature)')
                            else:
                                # Fallback: use triangulated surface
                                trisurf = ax4.plot_trisurf(wx.values, wy.values, t_data.values, cmap='coolwarm', 
                                                          linewidth=0.0, antialiased=True, alpha=0.98)
                                fig4.colorbar(trisurf, shrink=0.5, aspect=5, label='T (Temperature)')
                            
                            # Plot Z vectors on surface (tails on surface, arrows extend above)
                            mpl_len_scale = float(mpl_arrow_len_scale_var.get())
                            mpl_head_scale = float(mpl_arrow_head_scale_var.get())
                            arrow_head_ratio = max(0.05, min(0.8, 0.30 * mpl_head_scale))
                            for i in range(0, len(wx.values), max(1, len(wx.values) // 100)):
                                x_start = wx.values[i]
                                y_start = wy.values[i]
                                z_start = z_surface_values[i] if len(z_surface_values) > i else t_data.values[i]
                                
                                dx_3d = z_dx_norm[i] * mpl_len_scale
                                dy_3d = z_dy_norm[i] * mpl_len_scale
                                # Only ensure the tail lies on the liquidus surface; keep arrow pointing above surface
                                dz_3d = 0.0
                                
                                ax4.quiver(x_start, y_start, z_start, 
                                          dx_3d, dy_3d, dz_3d,
                                          color='green', arrow_length_ratio=arrow_head_ratio, linewidth=1.5)
                            
                            ax4.set_xlabel(f"{col_wx} (%)")
                            ax4.set_ylabel(f"{col_wy} (%)")
                            ax4.set_zlabel('T (Temperature)')
                            ax4.set_title('Z Vectors on Liquidus Surface')
                            # Apply user-selected view angles for 3D Static
                            try:
                                ax4.view_init(elev=float(lv_elev_var.get()), azim=float(lv_azim_var.get()))
                            except Exception:
                                pass
                            
                            out4 = os.path.join(base_path, f"{prefix}_Z_on_liquidus_3d.{ext}")
                            plt.savefig(out4, **save_kwargs)
                            plt.close()
                            status_label.config(text=f"3D plot saved: {out4}", foreground="green")
                            self.open_file_and_offer_save_as(out4, vector_window)
                            
                        elif viz == "3D Rotation GIF":
                            if not MATPLOTLIB_AVAILABLE:
                                messagebox.showerror(self.tr('plot_dep_title', 'Dependency Missing'), self.tr('plot_dep_gif', 'Matplotlib is not installed. Cannot generate GIF.'))
                                return
                            fig4 = plt.figure(figsize=(12, 10))
                            ax4 = fig4.add_subplot(111, projection='3d')
                            if xi_grid_smooth is not None:
                                # Use smooth surface
                                surf = ax4.plot_surface(xi_grid_smooth, yi_grid_smooth, zi_grid, cmap='coolwarm', alpha=0.98, 
                                                      linewidth=0, antialiased=True, shade=True)
                                fig4.colorbar(surf, shrink=0.5, aspect=5, label='T (Temperature)')
                            else:
                                # Fallback: use triangulated surface
                                trisurf = ax4.plot_trisurf(wx.values, wy.values, t_data.values, cmap='coolwarm', 
                                                          linewidth=0.0, antialiased=True, alpha=0.98)
                                fig4.colorbar(trisurf, shrink=0.5, aspect=5, label='T (Temperature)')
                            
                            # Plot Z vectors on surface (tails on surface, arrows extend above)
                            mpl_len_scale = float(mpl_arrow_len_scale_var.get())
                            mpl_head_scale = float(mpl_arrow_head_scale_var.get())
                            arrow_head_ratio = max(0.05, min(0.8, 0.30 * mpl_head_scale))
                            for i in range(0, len(wx.values), max(1, len(wx.values) // 100)):
                                x_start = wx.values[i]
                                y_start = wy.values[i]
                                z_start = z_surface_values[i] if len(z_surface_values) > i else t_data.values[i]
                                
                                dx_3d = z_dx_norm[i] * mpl_len_scale
                                dy_3d = z_dy_norm[i] * mpl_len_scale
                                dz_3d = 0.0
                                
                                ax4.quiver(x_start, y_start, z_start, 
                                          dx_3d, dy_3d, dz_3d,
                                          color='green', arrow_length_ratio=arrow_head_ratio, linewidth=1.5)
                            
                            ax4.set_xlabel(f"{col_wx} (%)")
                            ax4.set_ylabel(f"{col_wy} (%)")
                            ax4.set_zlabel('T (Temperature)')
                            ax4.set_title('Z Vectors on Liquidus Surface')
                            
                            def _rotate(angle):
                                ax4.view_init(azim=angle)
                                return [ax4]
                            
                            # Get GIF parameters
                            try:
                                rotation_step = int(float(gif_speed_var.get()))
                            except:
                                rotation_step = 5
                            try:
                                interval_ms = int(float(gif_interval_var.get()))
                            except:
                                interval_ms = 50
                            try:
                                fps_val = int(float(gif_fps_var.get()))
                            except:
                                fps_val = 20
                            
                            ani = animation.FuncAnimation(fig4, _rotate, frames=range(0, 360, rotation_step), interval=interval_ms)
                            out4 = os.path.join(base_path, f"{prefix}_Z_on_liquidus_3d_rotation.gif")
                            ani.save(out4, writer='pillow', fps=fps_val, dpi=100)
                            plt.close()
                            status_label.config(text=f"GIF saved: {out4}", foreground="green")
                            self.open_file_and_offer_save_as(out4, vector_window)
                            
                        else:  # Plotly 3D
                            if PLOTLY_AVAILABLE:
                                if xi_grid_smooth is not None:
                                    # Use smooth surface
                                    fig_plotly = go.Figure(data=[
                                        go.Surface(x=xi_grid_smooth, y=yi_grid_smooth, z=zi_grid, 
                                                  colorscale='RdBu', reversescale=True, opacity=0.98,
                                                  colorbar=dict(title='T (Temperature)'))
                                    ])
                                else:
                                    # Fallback to scatter
                                    fig_plotly = go.Figure(data=[go.Scatter3d(
                                        x=wx.values, y=wy.values, z=t_data.values,
                                        mode='markers',
                                        marker=dict(size=3, color=t_data.values, colorscale='RdBu', reversescale=True, opacity=0.85,
                                                    colorbar=dict(title='T (Temperature)'))
                                    )])
                                
                                # Add Z vectors as quiver (using cone markers)
                                # Sample vectors for clarity
                                sample_indices = list(range(0, len(wx.values), max(1, len(wx.values) // 50)))
                                x_starts = wx.values[sample_indices]
                                y_starts = wy.values[sample_indices]
                                z_starts = z_surface_values[sample_indices] if len(z_surface_values) > 0 else t_data.values[sample_indices]
                                
                                # Plotly 3D: keep arrow HEAD size uniform/small; show differences mainly by arrow LENGTH.
                                # Draw shafts with Scatter3d(lines), then draw only arrowheads with fixed-size cones.
                                plotly_vec_scale = float(plotly_arrow_len_scale_var.get())  # length multiplier only
                                u_vec = z_dx_arr[sample_indices] * plotly_vec_scale
                                v_vec = z_dy_arr[sample_indices] * plotly_vec_scale
                                w_vec = np.zeros_like(u_vec)
                                
                                x_ends = x_starts + u_vec
                                y_ends = y_starts + v_vec
                                z_ends = z_starts + w_vec
                                
                                # Shafts (no markers/dots)
                                x_lines, y_lines, z_lines = [], [], []
                                for xs, ys, zs, xe, ye, ze in zip(x_starts, y_starts, z_starts, x_ends, y_ends, z_ends):
                                    x_lines.extend([xs, xe, None])
                                    y_lines.extend([ys, ye, None])
                                    z_lines.extend([zs, ze, None])
                                
                                fig_plotly.add_trace(go.Scatter3d(
                                    x=x_lines, y=y_lines, z=z_lines,
                                    mode="lines",
                                    line=dict(color="green", width=4),
                                    showlegend=False,
                                    name="Z vector shafts"
                                ))
                                
                                # Arrowheads: unit directions + fixed-size cones at tips
                                mags = np.sqrt(u_vec**2 + v_vec**2 + w_vec**2)
                                mags = np.where((~np.isfinite(mags)) | (mags == 0), 1.0, mags)
                                u_dir = u_vec / mags
                                v_dir = v_vec / mags
                                w_dir = w_vec / mags
                                
                                fig_plotly.add_trace(go.Cone(
                                    x=x_ends, y=y_ends, z=z_ends,
                                    u=u_dir, v=v_dir, w=w_dir,
                                    anchor="tip",
                                    colorscale=[[0, "green"], [1, "green"]],
                                    showscale=False,
                                    sizemode="absolute",
                                    sizeref=max(axis_span * 0.015 * float(plotly_arrow_head_scale_var.get()), 1e-6),
                                    name="Z vector heads"
                                ))
                                
                                fig_plotly.update_layout(
                                    scene=dict(
                                        xaxis_title=f"{col_wx} (%)",
                                        yaxis_title=f"{col_wy} (%)",
                                        zaxis_title='T (Temperature)',
                                    ),
                                    width=900, height=700,
                                )
                                out4 = os.path.join(base_path, f"{prefix}_Z_on_liquidus_3d_interactive.html")
                                fig_plotly.write_html(out4)
                                status_label.config(text=f"Interactive 3D plot saved: {out4}", foreground="green")
                                self.open_file_and_offer_save_as(out4, vector_window)
                            else:
                                # Fallback HTML without plotly
                                out4 = os.path.join(base_path, f"{prefix}_Z_on_liquidus_3d_interactive.html")
                                with open(out4, 'w', encoding='utf-8') as f:
                                    f.write('<html><head><title>Z Vectors on Liquidus Surface 3D Interactive Plot</title></head><body>\n')
                                    f.write('<h2>Z Vectors on Liquidus Surface 3D Interactive Plot - Rotate and zoom with mouse</h2>\n')
                                    f.write('<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist@2.24.1/plotly.min.js"></script>\n')
                                    f.write('<div id="plot" style="width:900px;height:700px;"></div>\n')
                                    f.write('<script>\n')
                                    if xi_grid_smooth is not None:
                                        f.write('var surface = {\n')
                                        f.write('  type: "surface",\n')
                                        f.write('  x: ' + str(xi_grid_smooth.tolist()) + ',\n')
                                        f.write('  y: ' + str(yi_grid_smooth.tolist()) + ',\n')
                                        f.write('  z: ' + str(zi_grid.tolist()) + ',\n')
                                        f.write('  colorscale: "RdBu",\n')
                                        f.write('  reversescale: true,\n')
                                        f.write('  opacity: 0.9,\n')
                                        f.write('  colorbar: {title: "T (Temperature)"}\n')
                                        f.write('};\n')
                                    else:
                                        f.write('var surface = {\n')
                                        f.write('  type: "scatter3d",\n')
                                        f.write('  mode: "markers",\n')
                                        f.write('  x: ' + str(wx.values.tolist()) + ',\n')
                                        f.write('  y: ' + str(wy.values.tolist()) + ',\n')
                                        f.write('  z: ' + str(t_data.values.tolist()) + ',\n')
                                        f.write('  marker: { size: 3, color: ' + str(t_data.values.tolist()) + ', colorscale: "RdBu", reversescale: true, opacity: 0.85, colorbar: {title: "T (Temperature)"} }\n')
                                        f.write('};\n')
                                    
                                    # Add vectors
                                    f.write('var vectors = [\n')
                                    sample_indices = range(0, len(wx.values), max(1, len(wx.values) // 50))
                                    # Plotly HTML fallback: DO NOT normalize by max_abs (use original arrow lengths),
                                    # but apply the same visual multiplier as Plotly cones.
                                    plotly_vec_scale = float(plotly_arrow_len_scale_var.get())
                                    for i in sample_indices:
                                        x_start = float(wx.values[i])
                                        y_start = float(wy.values[i])
                                        z_start = float(z_surface_values[i] if len(z_surface_values) > i else t_data.values[i])
                                        dx_3d = float(z_dx_arr[i] * plotly_vec_scale)
                                        dy_3d = float(z_dy_arr[i] * plotly_vec_scale)
                                        f.write('  {type: "scatter3d", mode: "lines", x: [' + str(x_start) + ', ' + str(x_start + dx_3d) + '], y: [' + str(y_start) + ', ' + str(y_start + dy_3d) + '], z: [' + str(z_start) + ', ' + str(z_start) + '], line: {color: "green", width: 3}, showlegend: false},\n')
                                    f.write('];\n')
                                    
                                    f.write('var data = [surface, ...vectors];\n')
                                    f.write('var layout = {\n')
                                    f.write('  scene: {\n')
                                    f.write(f'    xaxis: {{title: "{col_wx} (%)"}},\n')
                                    f.write(f'    yaxis: {{title: "{col_wy} (%)"}},\n')
                                    f.write('    zaxis: {title: "T (Temperature)"}\n')
                                    f.write('  }\n')
                                    f.write('};\n')
                                    f.write('Plotly.newPlot("plot", data, layout);\n')
                                    f.write('</script>\n')
                                    f.write('</body></html>')
                                status_label.config(text=f"Interactive 3D plot saved: {out4}", foreground="green")
                                self.open_file_and_offer_save_as(out4, vector_window)
                        
                        # Update success message
                        if out4:
                            status_label.config(
                                text=f"Success! Saved:\n{os.path.basename(out1)}\n{os.path.basename(out2)}\n{os.path.basename(out3)}\n{os.path.basename(out4)}",
                                foreground="green"
                            )
                            messagebox.showinfo(
                                self.tr('dlg_success', 'Success'),
                                self.tr(
                                    'liqvec_ok_4',
                                    'Vector plots generated successfully!\n\nU horizontal: {u}\nV vertical: {v}\nZ resultant: {z}\nZ on liquidus ({viz}): {zliq}',
                                ).format(u=out1, v=out2, z=out3, viz=viz, zliq=out4),
                            )
                        else:
                            status_label.config(
                                text=f"Success! Saved:\n{os.path.basename(out1)}\n{os.path.basename(out2)}\n{os.path.basename(out3)}",
                                foreground="green"
                            )
                            messagebox.showinfo(
                                self.tr('dlg_success', 'Success'),
                                self.tr(
                                    'liqvec_ok_3',
                                    'Vector plots generated successfully!\n\nU horizontal: {u}\nV vertical: {v}\nZ resultant: {z}',
                                ).format(u=out1, v=out2, z=out3),
                            )
                    except Exception as e:
                        # If visualization plot fails, just show the 3 regular plots
                        status_label.config(
                            text=f"Success! Saved:\n{os.path.basename(out1)}\n{os.path.basename(out2)}\n{os.path.basename(out3)}\n(Visualization plot failed: {str(e)})",
                            foreground="orange"
                        )
                        messagebox.showwarning(
                            self.tr('dlg_partial', 'Partial Success'),
                            self.tr(
                                'liqvec_partial',
                                'Vector plots generated, but visualization plot failed:\n{err}\n\nU horizontal: {u}\nV vertical: {v}\nZ resultant: {z}',
                            ).format(err=str(e), u=out1, v=out2, z=out3),
                        )
                else:
                    # No temperature data available
                    status_label.config(
                        text=f"Success! Saved:\n{os.path.basename(out1)}\n{os.path.basename(out2)}\n{os.path.basename(out3)}",
                        foreground="green"
                    )
                    messagebox.showinfo(
                        self.tr('dlg_success', 'Success'),
                        self.tr(
                            'liqvec_ok_no_t',
                            'Vector plots generated successfully!\n\nU horizontal: {u}\nV vertical: {v}\nZ resultant: {z}\n\nNote: Z vectors on liquidus surface plot skipped (no temperature data)',
                        ).format(u=out1, v=out2, z=out3),
                    )
                
            except Exception as e:
                status_label.config(text=f"Error: {str(e)}", foreground="red")
                messagebox.showerror(
                    self.tr('dlg_error', 'Error'),
                    self.tr('plot_liq_gen_fail', 'Failed to generate vector plots:\n{e}').format(e=str(e)),
                )
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=20)
        
        btn_lv_plot = ttk.Button(buttons_frame, text=self.tr('btn_plot_vectors', 'Plot Vectors'), command=plot_vectors)
        btn_lv_plot.pack(side=tk.LEFT, padx=10)
        btn_lv_close = ttk.Button(buttons_frame, text=self.tr('ui_close', 'Close'), command=_close_liquidus_vector_window)
        btn_lv_close.pack(side=tk.LEFT, padx=10)

        def _refresh_liqvec_lang():
            try:
                if not vector_window.winfo_exists():
                    return
            except tk.TclError:
                return
            vector_window.title(self.tr('liqvec_win_title', 'Plot Liquidus Vectors'))
            title_label.config(text=self.tr('liqvec_heading', 'Liquidus Vector Plotter'))
            info_label.config(text=self.tr('liqvec_intro', ''))
            dataset_frame.config(text=self.tr('liqvec_solid_mode', 'Solidification Mode'))
            rb_lv_eq.config(text=self.tr('plot_k_mode_eq', 'Equilibrium/Lever (P file)'))
            rb_lv_sc.config(text=self.tr('plot_k_mode_scheil', 'Scheil (P-S file)'))
            element_frame.config(text=self.tr('liqvec_elem_sel', 'Element Selection'))
            lbl_lv_x.config(text=self.tr('stp_x_element', 'X Element:'))
            lbl_lv_y.config(text=self.tr('stp_y_element', 'Y Element:'))
            options_frame.config(text=self.tr('liqvec_options', 'Options'))
            export_processed_frame.config(text=self.tr('liqvec_export_proc', 'Export Processed Data'))
            btn_lv_pebrowse.config(text=self.tr('pandat_browse', 'Browse'))
            btn_lv_pexp.config(text=self.tr('ui_export', 'Export'))
            clean_fill_cb.config(text=self.tr('liqvec_clean_fill', 'Clean and fill data before plotting'))
            excel_export_frame.config(text=self.tr('liqvec_export_clean_frame', 'Export Cleaned Data (Excel)'))
            btn_lv_xlbrowse.config(text=self.tr('pandat_browse', 'Browse'))
            btn_lv_xlexp.config(text=self.tr('ui_export', 'Export'))
            viz_frame.config(text=self.tr('liqvec_viz_frame', 'Visualization'))
            rb_lv_v2.config(text=self.tr('batch_viz_2d', '2D Heatmap'))
            rb_lv_v3.config(text=self.tr('batch_viz_3d', '3D Static'))
            rb_lv_vg.config(text=self.tr('batch_viz_gif', '3D Rotation GIF'))
            rb_lv_vp.config(text=self.tr('batch_viz_plotly', 'Plotly 3D'))
            lbl_lv_sm.config(text=self.tr('batch_smooth', 'Smoothness:'))
            arrow_settings_frame.config(text=self.tr('liqvec_arrow_3d', 'Arrow Settings (3D)'))
            mpl_arrow_frame.config(text=self.tr('liqvec_mpl_arrow', '3D Static / 3D Rotation GIF (Matplotlib)'))
            lbl_lv_mlen.config(text=self.tr('liqvec_arrow_len', 'Arrow Length Scale:'))
            lbl_lv_mhead.config(text=self.tr('liqvec_arrow_head', 'Arrow Head Size:'))
            plotly_arrow_frame.config(text=self.tr('liqvec_plotly_arrow', 'Plotly 3D (Interactive)'))
            lbl_lv_plen.config(text=self.tr('liqvec_plotly_len', 'Arrow Length Scale (relative):'))
            lbl_lv_phead.config(text=self.tr('liqvec_plotly_head', 'Arrow Head Fraction:'))
            lv_view_frame.config(text=self.tr('batch_view_3d', '3D Static View (Rotation Angles)'))
            lbl_lv_elev.config(text=self.tr('batch_elev', 'Elevation (deg):'))
            lbl_lv_elev_r.config(text=self.tr('plot_elev_range', '(0–90)'))
            lbl_lv_azim.config(text=self.tr('batch_azim', 'Azimuth (deg):'))
            lbl_lv_azim_r.config(text=self.tr('plot_azim_range', '(-180–180)'))
            gif_params_frame.config(text=self.tr('batch_gif_params', '3D Rotation GIF Parameters'))
            lbl_lv_gspd.config(text=self.tr('batch_gif_speed', 'Rotation Speed (degrees/frame):'))
            lbl_lv_gint.config(text=self.tr('batch_gif_interval', 'Frame Interval (ms):'))
            lbl_lv_gfps.config(text=self.tr('batch_gif_fps', 'FPS:'))
            output_frame.config(text=self.tr('plot_phase_output_settings', 'Output Settings'))
            lbl_lv_od.config(text=self.tr('batch_output_dir', 'Output Directory:'))
            btn_lv_out.config(text=self.tr('pandat_browse', 'Browse'))
            lbl_lv_pfx.config(text=self.tr('batch_prefix', 'Output Prefix:'))
            lbl_lv_ifmt.config(text=self.tr('batch_image_fmt', 'Image Format (2D/3D Static):'))
            btn_lv_plot.config(text=self.tr('btn_plot_vectors', 'Plot Vectors'))
            btn_lv_close.config(text=self.tr('ui_close', 'Close'))
            on_dataset_changed()

        self._register_tool_lang_refresh(_refresh_liqvec_lang)
        _refresh_liqvec_lang()

def main():
    # Create the root window first
    root = tk.Tk()
    root.withdraw()  # Hide it initially
    
    # Create and show splash screen
    splash = SplashScreen(root)
    
    # Create main application
    app = ThermoQGUI(root)
    
    # Simulate loading time (you can remove this in production)
    root.after(2000, lambda: [splash.destroy(), app.show()])
    
    # Start the application
    root.mainloop()

if __name__ == "__main__":
    main() 
