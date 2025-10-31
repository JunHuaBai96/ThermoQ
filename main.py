import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import time
import re
import pandas as pd
from periodic_table import PERIODIC_TABLE

class ElementSelector:
    def __init__(self, parent):
        self.parent = parent
        self.selected_elements = {}  # Dictionary to store selected elements and their compositions
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
    
    def add_element(self):
        element = self.element_var.get()
        try:
            composition = float(self.composition_var.get())
            if element in PERIODIC_TABLE and 0 <= composition <= 100:
                if element not in self.selected_elements:
                    # Store composition in wt% (no conversion needed)
                    self.selected_elements[element] = composition
                    self.tree.insert("", "end", values=(
                        element,
                        PERIODIC_TABLE[element]['name'],
                        f"{composition:.2f} wt%"
                    ))
                    # Set main element if not set yet
                    if self.main_element is None:
                        self.main_element = element
                        # Show current main element label
                        if hasattr(self, 'main_element_label'):
                            self.main_element_label.destroy()
                        self.main_element_label = ttk.Label(self.frame, text=f"Main element: {self.main_element}", foreground="blue")
                        self.main_element_label.grid(row=3, column=0, sticky='w', padx=5, pady=(0,5))
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
            # If main element removed, reset to next available or None
            if self.main_element == element:
                self.main_element = next(iter(self.selected_elements.keys()), None)
                if hasattr(self, 'main_element_label'):
                    self.main_element_label.destroy()
                if self.main_element:
                    self.main_element_label = ttk.Label(self.frame, text=f"Main element: {self.main_element}", foreground="blue")
                    self.main_element_label.grid(row=3, column=0, sticky='w', padx=5, pady=(0,5))
    
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
        self.pandat_p_data = None  # P.xls data
        self.pandat_ts_data = None  # Ts.xlsx data
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
        
        # Calculation options frame
        options_frame = ttk.LabelFrame(main_frame, text="Calculation Options", padding="15")
        options_frame.grid(row=1, column=1, pady=20, sticky=(tk.W, tk.E))
        
        # Configure options frame for centered radio buttons
        options_frame.grid_columnconfigure(0, weight=1)
        options_frame.grid_columnconfigure(1, weight=1)
        options_frame.grid_columnconfigure(2, weight=1)
        options_frame.grid_columnconfigure(3, weight=1)
        
        # Radio buttons for calculation options
        self.calc_option = tk.StringVar(value="qbin")
        ttk.Radiobutton(options_frame, text="QΣbin", variable=self.calc_option, 
                       value="qbin").grid(row=0, column=0, padx=15, pady=10)
        ttk.Radiobutton(options_frame, text="Qture", variable=self.calc_option, 
                       value="qture").grid(row=0, column=1, padx=15, pady=10)
        ttk.Radiobutton(options_frame, text="Qmult", variable=self.calc_option, 
                       value="qmult").grid(row=0, column=2, padx=15, pady=10)
        ttk.Radiobutton(options_frame, text="ΔT", variable=self.calc_option, 
                       value="delta_t").grid(row=0, column=3, padx=15, pady=10)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
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
        calculation_type = self.calc_option.get()
        
        # Validate composition
        if not composition:
            messagebox.showerror("Error", "Please select at least one element!")
            return
        
        # Check if Pandat data is loaded for advanced calculations
        if calculation_type in ['delta_t', 'qture', 'qmult', 'qbin'] and (self.pandat_p_data is None or self.pandat_ts_data is None):
            messagebox.showerror("Error", "Please import Pandat data first using 'Import > Pandat to ThermoQ'!")
            return
        
        # Composition is already in weight percent (wt%)
        wt_composition = composition
        
        # Validate composition sum equals 100%
        total_composition = sum(wt_composition.values())
        if abs(total_composition - 100.0) > 0.01:  # Allow small floating point errors
            messagebox.showerror("Error", f"Total composition must equal 100%! Current total: {total_composition:.2f}%")
            return
        
        # Perform calculation based on type
        try:
            if calculation_type == 'delta_t':
                result = self.calculate_delta_t(wt_composition)
            elif calculation_type == 'qture':
                result = self.calculate_qture(wt_composition)
            elif calculation_type == 'qmult':
                result = self.calculate_qmult(wt_composition)
            elif calculation_type == 'qbin':
                result = self.calculate_qbin(wt_composition)
            else:
                messagebox.showerror("Error", "Unknown calculation type!")
                return
            
            # Store result for display
            self.last_result = {
                'type': calculation_type,
                'composition': wt_composition,
                'result': result
            }
            
            # Show result
            messagebox.showinfo("Calculation Result", 
                f"Calculation Type: {calculation_type.upper()}\n"
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
        import_window.geometry("700x600")
        import_window.configure(bg='yellow')
        import_window.grab_set()  # Make window modal
        
        # Create main frame
        main_frame = ttk.Frame(import_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # P file selection (supports both .xls and .xlsx)
        p_frame = ttk.LabelFrame(main_frame, text="P File (Equilibrium Data)", padding="10")
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
        
        # Ts file selection (supports both .xls and .xlsx)
        ts_frame = ttk.LabelFrame(main_frame, text="Ts File (Solidus Temperature)", padding="10")
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
        
        # Status label
        status_label = ttk.Label(main_frame, text="Please select both files to proceed", foreground="red")
        status_label.pack(pady=10)
        
        # Import button
        def import_pandat_data():
            p_file = p_file_var.get()
            ts_file = ts_file_var.get()
            
            if not p_file or not ts_file:
                messagebox.showerror("Error", "Please select both P and Ts files!")
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

                # Load P.xls data (.xls -> xlrd)
                self.pandat_p_data = _read_excel_auto(p_file)
                # Load Ts.xlsx data (.xlsx -> openpyxl)
                self.pandat_ts_data = _read_excel_auto(ts_file)
                
                # Remove blank rows
                self.pandat_p_data = self.pandat_p_data.dropna(how='all')
                self.pandat_ts_data = self.pandat_ts_data.dropna(how='all')

                # Drop unit/meta rows where 'T' is non-numeric and coerce numerics
                def _clean_numeric(df):
                    if 'T' in df.columns:
                        t_num = pd.to_numeric(df['T'], errors='coerce')
                        df = df.loc[t_num.notna()].copy()
                        df['T'] = t_num.loc[t_num.notna()]
                    # Coerce common numeric columns
                    for col in df.columns:
                        col_str = str(col)
                        if any(s in col_str for s in ['w(', '-T//fs', 'w_S', 'w_L', '1/dwdT_L(']):
                            df[col] = pd.to_numeric(df[col], errors='ignore')
                    return df

                self.pandat_p_data = _clean_numeric(self.pandat_p_data)
                self.pandat_ts_data = _clean_numeric(self.pandat_ts_data)
                
                # Process 1/dwdT_L columns - divide by 100
                for col in self.pandat_p_data.columns:
                    if '1/dwdT_L(' in col and '@LIQUID)' in col:
                        self.pandat_p_data[col] = self.pandat_p_data[col] / 100
                
                # Extract available elements from w(*) columns with robust parsing
                self.available_elements = []
                for col in self.pandat_p_data.columns:
                    m = re.match(r"^w\(\s*([A-Za-z]{1,3})\s*\)$", str(col))
                    if m:
                        raw = m.group(1)
                        symbol = raw[:1].upper() + raw[1:].lower()
                        if symbol in PERIODIC_TABLE:
                            self.available_elements.append(symbol)
                # Deduplicate and sort
                self.available_elements = sorted(set(self.available_elements))
                
                # Update element selector to activate only available elements
                self.update_element_availability()
                
                status_label.config(text=f"Successfully loaded Pandat data! Recognized elements: {', '.join(self.available_elements) if self.available_elements else 'None'}", 
                                  foreground="green")
                
                messagebox.showinfo("Success", 
                    f"Pandat data loaded successfully!\n"
                    f"P file: {len(self.pandat_p_data)} rows\n"
                    f"Ts file: {len(self.pandat_ts_data)} rows\n"
                    f"Recognized elements (from w(*)): {', '.join(self.available_elements) if self.available_elements else 'None'}")
                
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
        tolerance = 0.05  # 0.05% tolerance for composition matching

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
    
    def calculate_qture(self, composition):
        """Calculate Qture from -T//fs column"""
        p_idx = self.find_matching_row(composition)
        return self.pandat_p_data.iloc[p_idx]['-T//fs']
    
    def calculate_qmult(self, composition):
        """Calculate Qmult for non-main elements"""
        p_idx = self.find_matching_row(composition)
        row = self.pandat_p_data.iloc[p_idx]

        # Determine main element: prefer the first added element, fallback to highest composition
        if getattr(self.element_selector, 'main_element', None):
            main_element = self.element_selector.main_element
        else:
            sorted_elements = sorted(composition.items(), key=lambda x: x[1], reverse=True)
            main_element = sorted_elements[0][0]

        # Sort elements but ensure main element is first
        sorted_elements = [(elem, comp) for elem, comp in composition.items()]
        sorted_elements.sort(key=lambda x: (0 if x[0] == main_element else 1, -x[1]))

        qmult = 0.0
        for element, comp in sorted_elements[1:]:  # Skip main element
            element_sym = element  # Use normalized symbol case

            # Get required columns
            dwdt_col = f'1/dwdT_L({element_sym}@LIQUID)'
            ws_wl_col = f'w_S({element_sym})/w_L({element_sym})'
            w_col = f'w({element_sym})'

            if all(col in self.pandat_p_data.columns for col in [dwdt_col, ws_wl_col, w_col]):
                dwdt_val = row[dwdt_col]
                ws_wl_val = row[ws_wl_col]
                w_val = comp / 100.0  # Convert percentage to fraction

                qmult += dwdt_val * (ws_wl_val - 1) * w_val

        return qmult
    
    def calculate_qbin(self, composition):
        """Calculate QΣbin from two hypothetical binary alloys"""
        # Determine main element: prefer the first added element, fallback to highest composition
        if getattr(self.element_selector, 'main_element', None):
            main_element = self.element_selector.main_element
        else:
            sorted_elements = sorted(composition.items(), key=lambda x: x[1], reverse=True)
            main_element = sorted_elements[0][0]

        # Sort elements but ensure main element is first
        sorted_elements = [(elem, comp) for elem, comp in composition.items()]
        sorted_elements.sort(key=lambda x: (0 if x[0] == main_element else 1, -x[1]))

        qbin = 0.0

        for element, comp in sorted_elements[1:]:  # Skip main element
            # Create binary alloy composition: main element + current element
            binary_comp = {
                main_element: 100.0 - comp,
                element: comp
            }

            # Find matching row for this binary alloy
            try:
                p_idx = self.find_matching_row(binary_comp)
                row = self.pandat_p_data.iloc[p_idx]

                element_sym = element  # Use normalized symbol case

                # Get required columns
                dwdt_col = f'1/dwdT_L({element_sym}@LIQUID)'
                ws_wl_col = f'w_S({element_sym})/w_L({element_sym})'
                w_col = f'w({element_sym})'

                if all(col in self.pandat_p_data.columns for col in [dwdt_col, ws_wl_col, w_col]):
                    dwdt_val = row[dwdt_col]
                    ws_wl_val = row[ws_wl_col]
                    w_val = row[w_col]
                    try:
                        wf = float(w_val)
                    except Exception:
                        continue
                    # Ensure fraction form
                    if wf > 1.0:
                        wf = wf / 100.0

                    qbin += dwdt_val * (ws_wl_val - 1) * wf

            except ValueError:
                # If exact binary composition not found, use interpolation or skip
                print(f"Warning: Binary composition not found for {main_element}-{element}")
                continue

        return qbin

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