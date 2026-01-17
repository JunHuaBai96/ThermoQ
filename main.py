import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import time
import re
import pandas as pd
import numpy as np
from periodic_table import PERIODIC_TABLE

class ElementSelector:
    def __init__(self, parent):
        self.parent = parent
        self.selected_elements = {}  # Dictionary to store selected elements and their compositions (always in wt%)
        self.main_element = None  # The first added element will be considered main element
        
        # Create main frame with yellow background
        self.frame = ttk.LabelFrame(parent, text="Element Selection", padding="10")
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=5)
        
        # Create element selection area
        self.create_element_selection()
        
        # Create selected elements display area
        self.create_selected_elements_display()
    
    def create_element_selection(self):
        # Create a frame for element selection
        selection_frame = ttk.Frame(self.frame)
        selection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Create element dropdown
        ttk.Label(selection_frame, text="Element:").grid(row=0, column=0, padx=5, pady=5)
        self.element_var = tk.StringVar()
        self.element_dropdown = ttk.Combobox(selection_frame, textvariable=self.element_var, 
                                           values=sorted(PERIODIC_TABLE.keys()), width=10)
        self.element_dropdown.grid(row=0, column=1, padx=5, pady=5)
        
        # Create composition entry (always in wt%)
        ttk.Label(selection_frame, text="Composition (wt%):").grid(row=0, column=2, padx=5, pady=5)
        self.composition_var = tk.StringVar()
        self.composition_entry = ttk.Entry(selection_frame, textvariable=self.composition_var, width=10)
        self.composition_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Add button
        ttk.Button(selection_frame, text="Add Element", 
                  command=self.add_element).grid(row=0, column=4, padx=5, pady=5)

        # Hint: first added element is the main element
        self.main_hint_label = ttk.Label(self.frame, text="Hint: The first added element will be the main element", foreground="gray")
        self.main_hint_label.grid(row=2, column=0, sticky='w', padx=5, pady=(0,5))
        
    
    def create_selected_elements_display(self):
        # Create a frame for displaying selected elements
        display_frame = ttk.LabelFrame(self.frame, text="Selected Elements", padding="5")
        display_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Create treeview for displaying elements
        self.tree = ttk.Treeview(display_frame, columns=("Element", "Name", "Composition"), 
                                show="headings", height=5)
        self.tree.heading("Element", text="Element")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Composition", text="Composition (wt%)")
        
        self.tree.column("Element", width=80)
        self.tree.column("Name", width=150)
        self.tree.column("Composition", width=120)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Add remove button
        ttk.Button(display_frame, text="Remove Selected", 
                  command=self.remove_element).grid(row=1, column=0, pady=5)
    
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
                        status_text = f"Total composition: {total_wt:.2f} wt% ✓"
                        status_color = "green"
                    else:
                        status_text = f"Total composition: {total_wt:.2f} wt% (should be 100.00 wt%)"
                        status_color = "red"
                    
                    # Create status label with wraplength to prevent text cutoff
                    self.sum_status_label = ttk.Label(self.frame, text=status_text, foreground=status_color, wraplength=500)
                    self.sum_status_label.grid(row=3, column=0, sticky='w', padx=5, pady=(0,5))
                    
                    # Set main element if not set yet
                    if self.main_element is None:
                        self.main_element = element
                        # Show current main element label
                        if hasattr(self, 'main_element_label'):
                            self.main_element_label.destroy()
                        self.main_element_label = ttk.Label(self.frame, text=f"Main element: {self.main_element}", foreground="blue")
                        self.main_element_label.grid(row=2, column=0, sticky='w', padx=5, pady=(0,5))
                    self.element_var.set("")
                    self.composition_var.set("")
                else:
                    tk.messagebox.showwarning("Warning", "Element already added!")
            else:
                tk.messagebox.showerror("Error", "Invalid element or composition!")
        except ValueError:
            tk.messagebox.showerror("Error", "Please enter a valid number for composition!")
    
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
                    status_text = f"Total composition: {total_wt:.2f} wt% ✓"
                    status_color = "green"
                else:
                    status_text = f"Total composition: {total_wt:.2f} wt% (should be 100.00 wt%)"
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
                    self.main_element_label = ttk.Label(self.frame, text=f"Main element: {self.main_element}", foreground="blue")
                    self.main_element_label.grid(row=2, column=0, sticky='w', padx=5, pady=(0,5))
    
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
        # Increase default window size for better layout visibility
        self.root.geometry("1200x800")
        # Set a sensible minimum to prevent cramped UI
        self.root.minsize(1000, 700)
        self.root.withdraw()  # Hide main window initially
        
        # Set yellow background for main window
        self.root.configure(bg='yellow')
        
        # Initialize Pandat data storage
        self.pandat_p_data = None  # P.xls data (Equilibrium/Lever solidification)
        self.pandat_ts_data = None  # Ts.xlsx data (Equilibrium/Lever solidification)
        self.pandat_p_s_data = None  # P-S.xlsx data (Scheil solidification)
        self.pandat_ts_s_data = None  # Ts-S.xlsx data (Scheil solidification)
        self.available_elements = []  # Elements available from Pandat data
        
        # Create menu bar
        self.menu_bar = tk.Menu(root)
        self.root.config(menu=self.menu_bar)
        
        # Create File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Exit", command=root.quit)
        
        # Create Import menu
        self.import_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Import", menu=self.import_menu)
        self.import_menu.add_command(label="Pandat to ThermoQ", command=self.open_pandat_import)
        
        # Create Tools menu
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(label="Composition Converter (wt% ↔ at%)", command=self.open_composition_converter)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="Generate Therocalc Batch File", command=self.open_therocalc_generator)
        self.tools_menu.add_command(label="Extract Therocalc Results", command=self.open_exp_data_processor)
        
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
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame grid weights
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Logo section
        try:
            logo_img = Image.open("images/Simplified logo.png")
            logo_size = (100, 100)
            logo_img = logo_img.resize(logo_size, Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            
            logo_label = ttk.Label(main_frame, image=self.logo_photo)
            logo_label.grid(row=0, column=0, rowspan=2, padx=(0, 20), pady=10)
        except Exception as e:
            print(f"Error loading logo: {e}")
        
        # Create element selector
        self.element_selector = ElementSelector(main_frame)
        self.element_selector.frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, columnspan=2, pady=20)
        
        # Calculate and Results buttons
        ttk.Button(buttons_frame, text="Calculate", command=self.calculate).grid(row=0, column=0, padx=10)
        ttk.Button(buttons_frame, text="Show Results", command=self.show_results).grid(row=0, column=1, padx=10)

    def show(self):
        # Center window on screen after splash
        self.center_window()
        self.root.deiconify()

    def calculate(self):
        # Get the selected elements and their compositions
        composition = self.element_selector.get_composition()
        
        # Validate composition
        if not composition:
            messagebox.showerror("Error", "Please select at least one element!")
            return
        
        # Check if Pandat data is loaded
        if self.pandat_p_data is None or self.pandat_ts_data is None:
            messagebox.showerror("Error", "Please import Pandat data first using 'Import > Pandat to ThermoQ'!")
            return
        
        # Composition is already in weight percent (wt%)
        wt_composition = composition
        
        # Validate composition sum equals 100%
        total_composition = sum(wt_composition.values())
        if abs(total_composition - 100.0) > 0.01:  # Allow small floating point errors
            messagebox.showerror("Error", f"Total composition must equal 100%! Current total: {total_composition:.2f}%")
            return
        
        # Perform ΔT calculation
        try:
            result = self.calculate_delta_t(wt_composition)
            
            # Store result for display
            self.last_result = {
                'type': 'delta_t',
                'composition': wt_composition,
                'result': result
            }
            
            # Show result
            messagebox.showinfo("Calculation Result", 
                f"Calculation Type: ΔT (Melting Range)\n"
                f"Composition: {', '.join([f'{elem}: {comp:.2f}wt%' for elem, comp in wt_composition.items()])}\n"
                f"Result: {result:.4f}")
                
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Failed to calculate: {str(e)}")

    def show_results(self):
        # Add results display logic here
        print("Showing calculation results...")
        
    def open_pandat_import(self):
        # Create a new window for Pandat import
        import_window = tk.Toplevel(self.root)
        import_window.title("Pandat to ThermoQ")
        import_window.geometry("600x500")
        import_window.grab_set()  # Make window modal
        
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
        info_label = ttk.Label(main_frame, 
            text="Note: P/Ts files are for Equilibrium (Lever) solidification.\nP-S/Ts-S files are for Scheil solidification.",
            foreground="blue", font=('Arial', 9))
        info_label.pack(pady=5)
        
        # P file selection (Equilibrium/Lever solidification)
        p_frame = ttk.LabelFrame(main_frame, text="P File (Equilibrium/Lever Solidification - Liquidus Data)", padding="10")
        p_frame.pack(fill=tk.X, pady=5)
        
        p_file_var = tk.StringVar()
        p_entry = ttk.Entry(p_frame, textvariable=p_file_var, width=60)
        p_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_p_file():
            file_path = filedialog.askopenfilename(
                title="Select P File",
                filetypes=[("Excel files", "*.xls *.xlsx"), ("XLS files", "*.xls"), ("XLSX files", "*.xlsx")]
            )
            if file_path:
                p_file_var.set(file_path)
        
        ttk.Button(p_frame, text="Browse", command=browse_p_file).pack(side=tk.RIGHT, padx=5)
        
        # Ts file selection (Equilibrium/Lever solidification)
        ts_frame = ttk.LabelFrame(main_frame, text="Ts File (Equilibrium/Lever Solidification - Solidus Temperature)", padding="10")
        ts_frame.pack(fill=tk.X, pady=5)
        
        ts_file_var = tk.StringVar()
        ts_entry = ttk.Entry(ts_frame, textvariable=ts_file_var, width=60)
        ts_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_ts_file():
            file_path = filedialog.askopenfilename(
                title="Select Ts File",
                filetypes=[("Excel files", "*.xls *.xlsx"), ("XLS files", "*.xls"), ("XLSX files", "*.xlsx")]
            )
            if file_path:
                ts_file_var.set(file_path)
        
        ttk.Button(ts_frame, text="Browse", command=browse_ts_file).pack(side=tk.RIGHT, padx=5)
        
        # P-S file selection (Scheil solidification)
        p_s_frame = ttk.LabelFrame(main_frame, text="P-S File (Scheil Solidification - Liquidus Data)", padding="10")
        p_s_frame.pack(fill=tk.X, pady=5)
        
        p_s_file_var = tk.StringVar()
        p_s_entry = ttk.Entry(p_s_frame, textvariable=p_s_file_var, width=60)
        p_s_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_p_s_file():
            file_path = filedialog.askopenfilename(
                title="Select P-S File",
                filetypes=[("Excel files", "*.xls *.xlsx"), ("XLS files", "*.xls"), ("XLSX files", "*.xlsx")]
            )
            if file_path:
                p_s_file_var.set(file_path)
        
        ttk.Button(p_s_frame, text="Browse", command=browse_p_s_file).pack(side=tk.RIGHT, padx=5)
        
        # Ts-S file selection (Scheil solidification)
        ts_s_frame = ttk.LabelFrame(main_frame, text="Ts-S File (Scheil Solidification - Solidus Temperature)", padding="10")
        ts_s_frame.pack(fill=tk.X, pady=5)
        
        ts_s_file_var = tk.StringVar()
        ts_s_entry = ttk.Entry(ts_s_frame, textvariable=ts_s_file_var, width=60)
        ts_s_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_ts_s_file():
            file_path = filedialog.askopenfilename(
                title="Select Ts-S File",
                filetypes=[("Excel files", "*.xls *.xlsx"), ("XLS files", "*.xls"), ("XLSX files", "*.xlsx")]
            )
            if file_path:
                ts_s_file_var.set(file_path)
        
        ttk.Button(ts_s_frame, text="Browse", command=browse_ts_s_file).pack(side=tk.RIGHT, padx=5)
        
        # Status label
        status_label = ttk.Label(main_frame, text="Please select at least P and Ts files to proceed", foreground="red")
        status_label.pack(pady=10)
        
        # Import button
        def import_pandat_data():
            p_file = p_file_var.get()
            ts_file = ts_file_var.get()
            p_s_file = p_s_file_var.get()
            ts_s_file = ts_s_file_var.get()
            
            if not p_file or not ts_file:
                messagebox.showerror("Error", "Please select at least P and Ts files (Equilibrium/Lever solidification)!")
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
                            if col_str and any(s in col_str for s in ['w(', '-T//fs', 'w_S', 'w_L', '1/dwdT_L(']):
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
                
                # Update element selector to activate only available elements
                self.update_element_availability()
                
                # Build success message
                success_msg = "Pandat data loaded successfully!\n"
                success_msg += f"P file (Equilibrium): {len(self.pandat_p_data)} rows\n"
                success_msg += f"Ts file (Equilibrium): {len(self.pandat_ts_data)} rows\n"
                if self.pandat_p_s_data is not None:
                    success_msg += f"P-S file (Scheil): {len(self.pandat_p_s_data)} rows\n"
                if self.pandat_ts_s_data is not None:
                    success_msg += f"Ts-S file (Scheil): {len(self.pandat_ts_s_data)} rows\n"
                success_msg += f"Recognized elements: {', '.join(self.available_elements) if self.available_elements else 'None'}"
                
                status_label.config(text=f"Successfully loaded Pandat data! Recognized elements: {', '.join(self.available_elements) if self.available_elements else 'None'}", 
                                  foreground="green")
                
                messagebox.showinfo("Success", success_msg)
                
                import_window.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load Pandat data: {str(e)}")
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Import Data", command=import_pandat_data).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=import_window.destroy).pack(side=tk.LEFT, padx=10)
    
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
                text=f"Available elements from Pandat data: {', '.join(sorted(self.available_elements))}", 
                foreground="blue",
                font=('Arial', 8)
            )
            self.element_selector.availability_label.grid(row=4, column=0, pady=5, sticky='w')
        else:
            # If no Pandat data loaded, show all elements
            self.element_selector.element_dropdown['values'] = sorted(PERIODIC_TABLE.keys())
            
            # Remove availability label if it exists
            if hasattr(self.element_selector, 'availability_label'):
                self.element_selector.availability_label.destroy()
                delattr(self.element_selector, 'availability_label')

    def center_window(self):
        """Center main window on the screen."""
        try:
            self.root.update_idletasks()
            # Use the configured window size (1200x800)
            width = 1200
            height = 800
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            # Fallback to default size and center
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - 1200) // 2
            y = (screen_height - 800) // 2
            self.root.geometry(f"1200x800+{x}+{y}")
    
    def find_matching_row(self, composition):
        """Find the row in Pandat data that matches the given composition"""
        tolerance = 0.5  # 增加容错度到0.5%，以便找到更多可能的匹配
        
        # 首先尝试精确匹配
        for idx, row in self.pandat_p_data.iterrows():
            match = True
            for element, target_comp in composition.items():
                col_name = f'w({element})'
                if col_name in self.pandat_p_data.columns:
                    # Pandat export may store w(*) as percentage (e.g., 99.8) or fraction (e.g., 0.998)
                    val = row[col_name]
                    try:
                        # If val is not numeric, fail this row
                        v = float(val)
                    except Exception:
                        match = False
                        break
                    actual_comp = v * 100.0 if v <= 1.0 else v
                    if abs(actual_comp - target_comp) > tolerance:
                        match = False
                        break
                else:
                    match = False
                    break

            if match:
                return idx
        
        # 如果没有精确匹配，尝试找到最接近的行
        # 对于二元合金，我们只需要确保元素存在，不需要精确匹配成分
        if len(composition) == 2:
            elements = list(composition.keys())
            # 检查是否有包含这两个元素的行
            for idx, row in self.pandat_p_data.iterrows():
                all_elements_present = True
                for element in elements:
                    col_name = f'w({element})'
                    if col_name not in self.pandat_p_data.columns:
                        all_elements_present = False
                        break
                    # 确保该元素在这一行中有值
                    val = row[col_name]
                    try:
                        v = float(val)
                        if v <= 0:
                            all_elements_present = False
                            break
                    except Exception:
                        all_elements_present = False
                        break
                
                if all_elements_present:
                    return idx
        
        # 如果仍然找不到匹配，则抛出错误
        raise ValueError(f"No matching composition found in Pandat data for {composition}")
    
    def calculate_delta_t(self, composition):
        """Calculate ΔT (melting range) = T_P - T_Ts"""
        # Find matching row in both datasets
        p_idx = self.find_matching_row(composition)
        ts_idx = self.find_matching_row(composition)
        
        # Get temperatures
        t_p = self.pandat_p_data.iloc[p_idx]['T']
        t_ts = self.pandat_ts_data.iloc[ts_idx]['T']
        
        return t_p - t_ts
    
    def open_composition_converter(self):
        """Open composition converter tool window"""
        converter_window = tk.Toplevel(self.root)
        converter_window.title("Composition Converter (wt% ↔ at%)")
        converter_window.geometry("800x800")
        converter_window.grab_set()  # Make window modal
        
        # Create main frame
        main_frame = ttk.Frame(converter_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Composition Converter", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Instructions
        info_label = ttk.Label(main_frame, 
            text="Enter element compositions and convert between weight percent (wt%) and atomic percent (at%)",
            wraplength=600, justify='center')
        info_label.pack(pady=(0, 20))
        
        # Input frame
        input_frame = ttk.LabelFrame(main_frame, text="Input", padding="15")
        input_frame.pack(fill=tk.BOTH, expand=False, pady=10)
        
        # Unit selection
        unit_frame = ttk.Frame(input_frame)
        unit_frame.pack(pady=10)
        ttk.Label(unit_frame, text="Input Unit:").pack(side=tk.LEFT, padx=5)
        input_unit_var = tk.StringVar(value="wt%")
        ttk.Radiobutton(unit_frame, text="wt%", variable=input_unit_var, value="wt%").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(unit_frame, text="at%", variable=input_unit_var, value="at%").pack(side=tk.LEFT, padx=5)
        
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
        
        # Example text
        example_text = """Example input format (one element per line):
Al 90.0
Mg 8.0
Si 2.0

Or:
Al: 90.0
Mg: 8.0
Si: 2.0"""
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
                    messagebox.showerror("Error", "Please enter element compositions!")
                    return
                
                # Parse input
                composition = {}
                lines = input_content.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('Example'):
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
                    messagebox.showerror("Error", "No valid elements found! Please check your input format.")
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
                result_text.insert("1.0", f"Input ({input_unit}):\n")
                for element, value in sorted(source_composition.items()):
                    result_text.insert(tk.END, f"{element}: {value:.4f} {input_unit}\n")
                
                result_text.insert(tk.END, f"\nConverted ({result_unit}):\n")
                for element, value in sorted(result_composition.items()):
                    result_text.insert(tk.END, f"{element}: {value:.4f} {result_unit}\n")
                
                # Show total
                total_source = sum(source_composition.values())
                total_result = sum(result_composition.values())
                result_text.insert(tk.END, f"\nTotal {input_unit}: {total_source:.4f}\n")
                result_text.insert(tk.END, f"Total {result_unit}: {total_result:.4f}\n")
                
            except Exception as e:
                messagebox.showerror("Error", f"Conversion failed: {str(e)}")
        
        ttk.Button(buttons_frame, text="Convert", command=convert_composition).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Clear", command=lambda: input_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=10)
        
        # Output frame
        output_frame = ttk.LabelFrame(main_frame, text="Result", padding="15")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Result text area
        result_text_frame = ttk.Frame(output_frame)
        result_text_frame.pack(fill=tk.BOTH, expand=True)
        
        result_text = tk.Text(result_text_frame, height=20, width=70, wrap=tk.WORD)
        result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        result_scrollbar = ttk.Scrollbar(result_text_frame, orient=tk.VERTICAL, command=result_text.yview)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        result_text.configure(yscrollcommand=result_scrollbar.set)
        
        # Close button
        close_button = ttk.Button(main_frame, text="Close", command=converter_window.destroy)
        close_button.pack(pady=10)
    
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
        """Open Therocalc batch file generator tool"""
        generator_window = tk.Toplevel(self.root)
        generator_window.title("Generate Therocalc Batch File")
        generator_window.geometry("900x800")
        generator_window.grab_set()  # Make window modal
        
        # Create main frame with scrollable area
        canvas = tk.Canvas(generator_window)
        scrollbar = ttk.Scrollbar(generator_window, orient="vertical", command=canvas.yview)
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
        
        # Title
        title_label = ttk.Label(main_frame, text="Therocalc Batch File Generator", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Instructions
        info_label = ttk.Label(main_frame, 
            text="Generate Therocalc batch file (.tcm) by combining template files with element combinations",
            wraplength=800, justify='center')
        info_label.pack(pady=(0, 20))
        
        # Template files selection
        template0_frame = ttk.LabelFrame(main_frame, text="Template0 File (Header)", padding="10")
        template0_frame.pack(fill=tk.X, pady=5)
        
        template0_var = tk.StringVar()
        ttk.Entry(template0_frame, textvariable=template0_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(template0_frame, text="Browse", 
                  command=lambda: template0_var.set(filedialog.askopenfilename(
                      title="Select Template0 File", filetypes=[("Text files", "*.txt"), ("All files", "*.*")]))).pack(side=tk.RIGHT, padx=5)
        
        template_frame = ttk.LabelFrame(main_frame, text="Template File (with placeholders like %Element%)", padding="10")
        template_frame.pack(fill=tk.X, pady=5)
        
        template_var = tk.StringVar()
        ttk.Entry(template_frame, textvariable=template_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(template_frame, text="Browse", 
                  command=lambda: template_var.set(filedialog.askopenfilename(
                      title="Select Template File", filetypes=[("Text files", "*.txt"), ("All files", "*.*")]))).pack(side=tk.RIGHT, padx=5)
        
        template1_frame = ttk.LabelFrame(main_frame, text="Template1 File (Footer)", padding="10")
        template1_frame.pack(fill=tk.X, pady=5)
        
        template1_var = tk.StringVar()
        ttk.Entry(template1_frame, textvariable=template1_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(template1_frame, text="Browse", 
                  command=lambda: template1_var.set(filedialog.askopenfilename(
                      title="Select Template1 File", filetypes=[("Text files", "*.txt"), ("All files", "*.*")]))).pack(side=tk.RIGHT, padx=5)
        
        # Elements configuration
        elements_frame = ttk.LabelFrame(main_frame, text="Element Configuration", padding="10")
        elements_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Elements list with scrollbar
        elements_list_frame = ttk.Frame(elements_frame)
        elements_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Treeview for elements
        elements_tree = ttk.Treeview(elements_list_frame, columns=("Element", "Min", "Max", "Step"), show="headings", height=6)
        elements_tree.heading("Element", text="Element")
        elements_tree.heading("Min", text="Min")
        elements_tree.heading("Max", text="Max")
        elements_tree.heading("Step", text="Step")
        
        elements_tree.column("Element", width=100)
        elements_tree.column("Min", width=100)
        elements_tree.column("Max", width=100)
        elements_tree.column("Step", width=100)
        
        elements_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        elements_scrollbar = ttk.Scrollbar(elements_list_frame, orient=tk.VERTICAL, command=elements_tree.yview)
        elements_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        elements_tree.configure(yscrollcommand=elements_scrollbar.set)
        
        # Add element frame
        add_element_frame = ttk.Frame(elements_frame)
        add_element_frame.pack(pady=5)
        
        ttk.Label(add_element_frame, text="Element:").pack(side=tk.LEFT, padx=5)
        element_var = tk.StringVar()
        element_combo = ttk.Combobox(add_element_frame, textvariable=element_var, 
                                    values=sorted(PERIODIC_TABLE.keys()), width=10)
        element_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(add_element_frame, text="Min:").pack(side=tk.LEFT, padx=5)
        min_var = tk.StringVar(value="0.0")
        ttk.Entry(add_element_frame, textvariable=min_var, width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(add_element_frame, text="Max:").pack(side=tk.LEFT, padx=5)
        max_var = tk.StringVar(value="1.0")
        ttk.Entry(add_element_frame, textvariable=max_var, width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(add_element_frame, text="Step:").pack(side=tk.LEFT, padx=5)
        step_var = tk.StringVar(value="0.01")
        ttk.Entry(add_element_frame, textvariable=step_var, width=10).pack(side=tk.LEFT, padx=5)
        
        def add_element_config():
            element = element_var.get().strip()
            try:
                min_val = float(min_var.get())
                max_val = float(max_var.get())
                step_val = float(step_var.get())
                
                if element not in PERIODIC_TABLE:
                    messagebox.showerror("Error", f"Invalid element: {element}")
                    return
                
                if min_val < 0 or max_val > 1 or min_val > max_val:
                    messagebox.showerror("Error", "Invalid range! Min should be >= 0, Max should be <= 1, and Min < Max")
                    return
                
                if step_val <= 0:
                    messagebox.showerror("Error", "Step must be > 0")
                    return
                
                # Check if element already exists
                for item in elements_tree.get_children():
                    if elements_tree.item(item)['values'][0] == element:
                        messagebox.showwarning("Warning", f"Element {element} already added!")
                        return
                
                elements_tree.insert("", "end", values=(element, min_val, max_val, step_val))
                element_var.set("")
                min_var.set("0.0")
                max_var.set("1.0")
                step_var.set("0.01")
                
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for Min, Max, and Step!")
        
        ttk.Button(add_element_frame, text="Add Element", command=add_element_config).pack(side=tk.LEFT, padx=10)
        ttk.Button(add_element_frame, text="Remove Selected", 
                  command=lambda: elements_tree.delete(elements_tree.selection()[0]) if elements_tree.selection() else None).pack(side=tk.LEFT, padx=5)
        
        # Constraints
        constraints_frame = ttk.LabelFrame(main_frame, text="Constraints (Optional)", padding="10")
        constraints_frame.pack(fill=tk.X, pady=10)
        
        constraint_sum_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(constraints_frame, text="Sum of all elements <= 1", 
                       variable=constraint_sum_var).pack(side=tk.LEFT, padx=5)
        
        constraint_exclude_zero_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(constraints_frame, text="Exclude all zeros (0, 0, ...)", 
                       variable=constraint_exclude_zero_var).pack(side=tk.LEFT, padx=5)
        
        # Output file
        output_frame = ttk.LabelFrame(main_frame, text="Output File", padding="10")
        output_frame.pack(fill=tk.X, pady=10)
        
        output_var = tk.StringVar(value="Alltcm.tcm")
        ttk.Entry(output_frame, textvariable=output_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Browse", 
                  command=lambda: output_var.set(filedialog.asksaveasfilename(
                      title="Save Output File", defaultextension=".tcm",
                      filetypes=[("TCM files", "*.tcm"), ("All files", "*.*")]))).pack(side=tk.RIGHT, padx=5)
        
        # Status label
        status_label = ttk.Label(main_frame, text="Ready to generate", foreground="blue")
        status_label.pack(pady=10)
        
        def generate_batch_file():
            """Generate Therocalc batch file"""
            try:
                # Validate inputs
                template0_file = template0_var.get()
                template_file = template_var.get()
                template1_file = template1_var.get()
                output_file = output_var.get()
                
                if not template0_file or not os.path.exists(template0_file):
                    messagebox.showerror("Error", "Please select a valid Template0 file!")
                    return
                
                if not template_file or not os.path.exists(template_file):
                    messagebox.showerror("Error", "Please select a valid Template file!")
                    return
                
                if not template1_file or not os.path.exists(template1_file):
                    messagebox.showerror("Error", "Please select a valid Template1 file!")
                    return
                
                if not output_file:
                    messagebox.showerror("Error", "Please specify an output file!")
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
                    messagebox.showerror("Error", "Please add at least one element configuration!")
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
                
                # Generate all combinations
                element_names = [cfg['element'] for cfg in element_configs]
                ranges = [np.arange(cfg['min'], cfg['max'] + cfg['step'], cfg['step']).astype(np.float32) 
                         for cfg in element_configs]
                
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
                        data_base[element] = f"{combo[i]:.2f}"
                    
                    # Replace placeholders in template
                    write = []
                    for line in template_lines:
                        new_line = line
                        if '%' in line:
                            for key in data_base:
                                new_line = new_line.replace(f'%{key}%', data_base[key])
                        write.append(new_line)
                    
                    write.append('\n')
                    out.extend(write)
                    
                    # Update progress
                    if (idx + 1) % 100 == 0:
                        status_label.config(text=f"Processing... {idx + 1}/{total} combinations", foreground="orange")
                        generator_window.update()
                
                # Add template1
                out.append('\n')
                with open(template1_file, "r", encoding="utf-8") as f1:
                    out.extend(f1.readlines())
                
                # Write output file
                with open(output_file, 'w', encoding="utf-8") as fp:
                    fp.write(''.join(out))
                
                status_label.config(text=f"Success! Generated {total} combinations. File saved to: {output_file}", foreground="green")
                messagebox.showinfo("Success", f"Batch file generated successfully!\n\nTotal combinations: {total}\nOutput file: {output_file}")
                
            except Exception as e:
                status_label.config(text=f"Error: {str(e)}", foreground="red")
                messagebox.showerror("Error", f"Failed to generate batch file:\n{str(e)}")
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="Generate Batch File", command=generate_batch_file).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Close", command=generator_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def open_exp_data_processor(self):
        """Open Therocalc results extractor tool"""
        processor_window = tk.Toplevel(self.root)
        processor_window.title("Extract Therocalc Results")
        processor_window.geometry("800x600")
        processor_window.grab_set()  # Make window modal
        
        # Create main frame
        main_frame = ttk.Frame(processor_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Extract Therocalc Results", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Instructions
        info_label = ttk.Label(main_frame, 
            text="Extract liquidus temperature, solidus temperature, and melting range from .exp files",
            wraplength=700, justify='center')
        info_label.pack(pady=(0, 20))
        
        # Folder selection
        folder_frame = ttk.LabelFrame(main_frame, text="Select Folder Containing .exp Files", padding="15")
        folder_frame.pack(fill=tk.X, pady=10)
        
        folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=folder_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(folder_frame, text="Browse", 
                  command=lambda: folder_var.set(filedialog.askdirectory(title="Select Folder with .exp Files"))).pack(side=tk.RIGHT, padx=5)
        
        # Filename pattern configuration
        pattern_frame = ttk.LabelFrame(main_frame, text="Filename Pattern (Optional)", padding="15")
        pattern_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(pattern_frame, text="Pattern:").pack(side=tk.LEFT, padx=5)
        pattern_var = tk.StringVar(value=r"Al(\d+\.\d+)Fe(\d+\.\d+)Si_np-T\.exp")
        pattern_entry = ttk.Entry(pattern_frame, textvariable=pattern_var, width=50)
        pattern_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        help_label = ttk.Label(pattern_frame, 
            text="Leave empty to process all .exp files\nUse regex groups to extract element fractions",
            font=('Arial', 8), foreground="gray")
        help_label.pack(side=tk.LEFT, padx=5)
        
        # Output file
        output_frame = ttk.LabelFrame(main_frame, text="Output Excel File", padding="15")
        output_frame.pack(fill=tk.X, pady=10)
        
        output_var = tk.StringVar(value="output.xlsx")
        ttk.Entry(output_frame, textvariable=output_var, width=70).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Browse", 
                  command=lambda: output_var.set(filedialog.asksaveasfilename(
                      title="Save Output File", defaultextension=".xlsx",
                      filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]))).pack(side=tk.RIGHT, padx=5)
        
        # Progress/Status area
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="15")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        status_text = tk.Text(status_frame, height=10, width=70, wrap=tk.WORD, state=tk.DISABLED)
        status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        status_scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=status_text.yview)
        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        status_text.configure(yscrollcommand=status_scrollbar.set)
        
        def log_status(message):
            """Add message to status text"""
            status_text.config(state=tk.NORMAL)
            status_text.insert(tk.END, message + "\n")
            status_text.see(tk.END)
            status_text.config(state=tk.DISABLED)
            processor_window.update()
        
        def extract_data_from_exp_file(file_path):
            """Extract data from .exp file"""
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                
                data_lines = []
                start_collecting = False
                
                for line in lines:
                    if line.strip().startswith("$ PLOTTED"):
                        start_collecting = True
                        continue
                    if line.strip().startswith("BLOCKEND"):
                        start_collecting = False
                        continue
                    if start_collecting:
                        split_line = line.strip().split()
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
                log_status(f"Error reading {file_path}: {str(e)}")
                return None
        
        def find_temperatures(data):
            """Find liquidus and solidus temperatures"""
            try:
                tolerance = 1e-8
                # Liquidus: LiquidFraction = 1.0
                temp_liq_1 = data[(data['LiquidFraction'] >= 1.0 - tolerance) & 
                                 (data['LiquidFraction'] <= 1.0 + tolerance)]['Temperature'].min()
                # Solidus: LiquidFraction = 0.0
                temp_liq_0 = data[data['LiquidFraction'].round(10) == 0.0]['Temperature'].max()
                return temp_liq_1, temp_liq_0
            except Exception:
                return None, None
        
        def process_files():
            """Process all .exp files in the selected folder"""
            try:
                folder_path = folder_var.get()
                output_file = output_var.get()
                pattern_str = pattern_var.get().strip()
                
                if not folder_path or not os.path.exists(folder_path):
                    messagebox.showerror("Error", "Please select a valid folder!")
                    return
                
                if not output_file:
                    messagebox.showerror("Error", "Please specify an output file!")
                    return
                
                status_text.config(state=tk.NORMAL)
                status_text.delete("1.0", tk.END)
                status_text.config(state=tk.DISABLED)
                
                log_status(f"Processing folder: {folder_path}")
                log_status(f"Output file: {output_file}")
                
                results = []
                exp_files = [f for f in os.listdir(folder_path) if f.endswith(".exp")]
                
                if not exp_files:
                    log_status("No .exp files found in the selected folder!")
                    messagebox.showwarning("Warning", "No .exp files found in the selected folder!")
                    return
                
                log_status(f"Found {len(exp_files)} .exp file(s)")
                
                # Compile pattern if provided
                pattern = None
                if pattern_str:
                    try:
                        pattern = re.compile(pattern_str)
                        log_status(f"Using pattern: {pattern_str}")
                    except re.error as e:
                        log_status(f"Invalid pattern: {str(e)}")
                        messagebox.showerror("Error", f"Invalid regex pattern: {str(e)}")
                        return
                
                processed_count = 0
                error_count = 0
                
                for file_name in exp_files:
                    file_path = os.path.join(folder_path, file_name)
                    log_status(f"Processing: {file_name}")
                    
                    # Extract element fractions from filename if pattern provided
                    element_fractions = []
                    if pattern:
                        match = pattern.match(file_name)
                        if match:
                            element_fractions = [float(match.group(i+1)) for i in range(len(match.groups()))]
                        else:
                            log_status(f"  Warning: Filename doesn't match pattern, skipping element extraction")
                    
                    # Extract data from file
                    data = extract_data_from_exp_file(file_path)
                    if data is None or data.empty:
                        log_status(f"  Error: Could not extract data from file")
                        error_count += 1
                        continue
                    
                    # Find temperatures
                    temp_liq_1, temp_liq_0 = find_temperatures(data)
                    
                    if temp_liq_1 is None or temp_liq_0 is None:
                        log_status(f"  Error: Could not find liquidus or solidus temperature")
                        error_count += 1
                        continue
                    
                    # Calculate melting range
                    melting_range = temp_liq_1 - temp_liq_0
                    
                    # Prepare result row
                    result_row = []
                    # Add element fractions if extracted
                    result_row.extend(element_fractions)
                    # Add temperatures and melting range
                    result_row.extend([temp_liq_1, temp_liq_0, melting_range])
                    
                    results.append(result_row)
                    processed_count += 1
                    log_status(f"  Success: Liquidus={temp_liq_1:.2f}K, Solidus={temp_liq_0:.2f}K, Range={melting_range:.2f}K")
                
                if not results:
                    log_status("No valid results to save!")
                    messagebox.showwarning("Warning", "No valid results extracted from files!")
                    return
                
                # Create DataFrame
                if pattern and len(element_fractions) > 0:
                    # Determine column names based on pattern groups
                    num_groups = len(element_fractions)
                    columns = [f"Element_{i+1}_fraction" for i in range(num_groups)]
                    columns.extend(["Liquidus_Temperature", "Solidus_Temperature", "Melting_Range"])
                else:
                    columns = ["Liquidus_Temperature", "Solidus_Temperature", "Melting_Range"]
                
                df = pd.DataFrame(results, columns=columns)
                
                # Save to Excel
                try:
                    df.to_excel(output_file, index=False)
                    log_status(f"\nSuccessfully saved {len(results)} results to {output_file}")
                    log_status(f"Processed: {processed_count}, Errors: {error_count}")
                    messagebox.showinfo("Success", 
                        f"Results extracted successfully!\n\n"
                        f"Processed: {processed_count} files\n"
                        f"Errors: {error_count} files\n"
                        f"Results saved to: {output_file}")
                except Exception as e:
                    log_status(f"Error saving file: {str(e)}")
                    messagebox.showerror("Error", f"Failed to save Excel file:\n{str(e)}")
                
            except Exception as e:
                log_status(f"Error: {str(e)}")
                messagebox.showerror("Error", f"Processing failed:\n{str(e)}")
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="Process Files", command=process_files).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Close", command=processor_window.destroy).pack(side=tk.LEFT, padx=10)

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