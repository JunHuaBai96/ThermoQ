import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import time
import re
import pandas as pd
import numpy as np
import subprocess
import webbrowser
import platform
from periodic_table import PERIODIC_TABLE

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
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C
    from scipy.interpolate import griddata
    SKLEARN_AVAILABLE = True
    SCIPY_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    SCIPY_AVAILABLE = False

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
        selection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=3, pady=3)
        
        # Create element dropdown
        ttk.Label(selection_frame, text="Element:").grid(row=0, column=0, padx=3, pady=3)
        self.element_var = tk.StringVar()
        self.element_dropdown = ttk.Combobox(selection_frame, textvariable=self.element_var, 
                                           values=sorted(PERIODIC_TABLE.keys()), width=10)
        self.element_dropdown.grid(row=0, column=1, padx=3, pady=3)
        
        # Create composition entry (always in wt%)
        ttk.Label(selection_frame, text="Composition (wt%):").grid(row=0, column=2, padx=3, pady=3)
        self.composition_var = tk.StringVar()
        self.composition_entry = ttk.Entry(selection_frame, textvariable=self.composition_var, width=10)
        self.composition_entry.grid(row=0, column=3, padx=3, pady=3)
        
        # Add button
        ttk.Button(selection_frame, text="Add Element", 
                  command=self.add_element).grid(row=0, column=4, padx=3, pady=3)

        # Hint: first added element is the main element
        self.main_hint_label = ttk.Label(self.frame, text="Hint: The first added element will be the main element", foreground="gray", wraplength=400)
        self.main_hint_label.grid(row=2, column=0, sticky='w', padx=3, pady=(0,3))
        
    
    def create_selected_elements_display(self):
        # Create a frame for displaying selected elements
        display_frame = ttk.LabelFrame(self.frame, text="Selected Elements", padding="5")
        display_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=3, pady=3)
        
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
                  command=self.remove_element).grid(row=1, column=0, pady=3)
    
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
                    self.sum_status_label.grid(row=3, column=0, sticky='w', padx=3, pady=(0,3))
                    
                    # Set main element if not set yet
                    if self.main_element is None:
                        self.main_element = element
                        # Hide hint label and show current main element label
                        if hasattr(self, 'main_hint_label'):
                            self.main_hint_label.destroy()
                        if hasattr(self, 'main_element_label'):
                            self.main_element_label.destroy()
                        self.main_element_label = ttk.Label(self.frame, text=f"Main element: {self.main_element}", foreground="blue", wraplength=400)
                        self.main_element_label.grid(row=2, column=0, sticky='w', padx=3, pady=(0,3))
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
        self.root.geometry("900x600")
        # Set a sensible minimum to prevent cramped UI
        self.root.minsize(800, 500)
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
        self.plot_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Plot", menu=self.plot_menu)
        self.plot_menu.add_command(label="Plot Phase Surfaces", command=self.open_phase_surface_plotter)
        self.plot_menu.add_command(label="Plot Q Values", command=self.open_q_value_plotter)
        self.plot_menu.add_command(label="Plot Liquidus Vectors", command=self.open_liquidus_vector_plotter)
        
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(label="Composition Converter (wt% ↔ at%)", command=self.open_composition_converter)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="Generate Thermo-calc Batch File", command=self.open_therocalc_generator)
        self.tools_menu.add_command(label="Extract Thermo-calc Results", command=self.open_exp_data_processor)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="Extract Pandat Results", command=self.open_extract_pandat_results)
        
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
        
        # Logo section
        try:
            logo_img = Image.open("images/Simplified logo.png")
            logo_size = (80, 80)  # Reduced logo size
            logo_img = logo_img.resize(logo_size, Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            
            logo_label = ttk.Label(main_frame, image=self.logo_photo)
            logo_label.grid(row=0, column=0, rowspan=2, padx=(0, 10), pady=5)
        except Exception as e:
            print(f"Error loading logo: {e}")
        
        # Create element selector
        self.element_selector = ElementSelector(main_frame)
        self.element_selector.frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
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
        
        # Perform calculations: Q, ΔT, ΔTs
        try:
            results = {}
            errors = []
            
            # 1. Calculate Q (from P.xlsx or P-S.xlsx)
            q_lever = None
            q_scheil = None
            
            # Q from P.xlsx (Lever/Equilibrium)
            try:
                p_idx = self.find_matching_row(wt_composition, self.pandat_p_data)
                if '-T//fw(@FCC_A1)' in self.pandat_p_data.columns:
                    q_lever = self.pandat_p_data.iloc[p_idx]['-T//fw(@FCC_A1)']
                    results['Q (Lever)'] = float(q_lever)
            except Exception as e:
                errors.append(f"Q (Lever) calculation failed: {str(e)}")
            
            # Q from P-S.xlsx (Scheil)
            if self.pandat_p_s_data is not None:
                try:
                    p_s_idx = self.find_matching_row(wt_composition, self.pandat_p_s_data)
                    if '-T//fw(@FCC_A1)' in self.pandat_p_s_data.columns:
                        q_scheil = self.pandat_p_s_data.iloc[p_s_idx]['-T//fw(@FCC_A1)']
                        results['Q (Scheil)'] = float(q_scheil)
                except Exception as e:
                    errors.append(f"Q (Scheil) calculation failed: {str(e)}")
            
            # 2. Calculate ΔT = T(P.xlsx) - T(Ts.xlsx)
            try:
                p_idx = self.find_matching_row(wt_composition, self.pandat_p_data)
                ts_idx = self.find_matching_row(wt_composition, self.pandat_ts_data)
                t_p = float(self.pandat_p_data.iloc[p_idx]['T'])
                t_ts = float(self.pandat_ts_data.iloc[ts_idx]['T'])
                delta_t = t_p - t_ts
                results['ΔT'] = delta_t
            except Exception as e:
                errors.append(f"ΔT calculation failed: {str(e)}")
            
            # 3. Calculate ΔTs = T(P-S.xlsx) - T(Ts-S.xlsx)
            if self.pandat_p_s_data is not None and self.pandat_ts_s_data is not None:
                try:
                    p_s_idx = self.find_matching_row(wt_composition, self.pandat_p_s_data)
                    ts_s_idx = self.find_matching_row(wt_composition, self.pandat_ts_s_data)
                    t_p_s = float(self.pandat_p_s_data.iloc[p_s_idx]['T'])
                    t_ts_s = float(self.pandat_ts_s_data.iloc[ts_s_idx]['T'])
                    delta_ts = t_p_s - t_ts_s
                    results['ΔTs'] = delta_ts
                except Exception as e:
                    errors.append(f"ΔTs calculation failed: {str(e)}")
            
            # Store result for display
            self.last_result = {
                'type': 'q_delta_t_delta_ts',
                'composition': wt_composition,
                'results': results
            }
            
            # Build result message
            result_msg = "Calculation Results:\n\n"
            result_msg += f"Composition: {', '.join([f'{elem}: {comp:.2f}wt%' for elem, comp in wt_composition.items()])}\n\n"
            
            if 'Q (Lever)' in results:
                result_msg += f"Q (Lever): {results['Q (Lever)']:.4f}\n"
            if 'Q (Scheil)' in results:
                result_msg += f"Q (Scheil): {results['Q (Scheil)']:.4f}\n"
            if 'ΔT' in results:
                result_msg += f"ΔT: {results['ΔT']:.4f}\n"
            if 'ΔTs' in results:
                result_msg += f"ΔTs: {results['ΔTs']:.4f}\n"
            
            # Show errors if any
            if errors:
                result_msg += "\nErrors:\n" + "\n".join(errors)
            
            # Show result
            if results:
                messagebox.showinfo("Calculation Result", result_msg)
            else:
                error_msg = "No results calculated.\n\nErrors:\n" + "\n".join(errors) if errors else "No results calculated. Please check your composition and data files."
                messagebox.showerror("Calculation Error", error_msg)
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("Calculation Error", f"Failed to calculate: {str(e)}\n\nDetails:\n{error_details}")

    def show_results(self):
        """Display calculation results in a window"""
        if not hasattr(self, 'last_result') or self.last_result is None:
            messagebox.showwarning("No Results", "Please calculate first before showing results!")
            return
        
        # Create results window
        results_window = tk.Toplevel(self.root)
        results_window.title("Calculation Results")
        results_window.geometry("600x500")
        
        # Create main frame
        main_frame = ttk.Frame(results_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Calculation Results", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Composition display
        composition = self.last_result.get('composition', {})
        comp_text = "Composition: " + ', '.join([f'{elem}: {comp:.2f}wt%' for elem, comp in composition.items()])
        comp_label = ttk.Label(main_frame, text=comp_text, font=('Arial', 10))
        comp_label.pack(pady=(0, 20))
        
        # Results display
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="15")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create scrollable text area for results
        text_frame = ttk.Frame(results_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        results_text = tk.Text(text_frame, height=15, width=60, wrap=tk.WORD, font=('Courier', 10))
        results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=results_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        results_text.configure(yscrollcommand=scrollbar.set)
        
        # Display results
        results = self.last_result.get('results', {})
        if results:
            results_text.insert("1.0", "Calculation Results:\n\n")
            
            if 'Q (Lever)' in results:
                results_text.insert(tk.END, f"Q (Lever): {results['Q (Lever)']:.6f}\n")
            else:
                results_text.insert(tk.END, "Q (Lever): Not available\n")
            
            if 'Q (Scheil)' in results:
                results_text.insert(tk.END, f"Q (Scheil): {results['Q (Scheil)']:.6f}\n")
            else:
                results_text.insert(tk.END, "Q (Scheil): Not available\n")
            
            if 'ΔT' in results:
                results_text.insert(tk.END, f"ΔT: {results['ΔT']:.6f}\n")
            else:
                results_text.insert(tk.END, "ΔT: Not available\n")
            
            if 'ΔTs' in results:
                results_text.insert(tk.END, f"ΔTs: {results['ΔTs']:.6f}\n")
            else:
                results_text.insert(tk.END, "ΔTs: Not available\n")
        else:
            results_text.insert("1.0", "No results available. Please run calculation first.")
        
        results_text.config(state=tk.DISABLED)  # Make read-only
        
        # Close button
        close_button = ttk.Button(main_frame, text="Close", command=results_window.destroy)
        close_button.pack(pady=10)
        
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
            
    def open_phase_surface_plotter(self):
        """Open phase surface plotter window (Liquidus/Solidus)"""
        plot_window = tk.Toplevel(self.root)
        plot_window.title("Plot Phase Surfaces (Liquidus/Solidus)")
        plot_window.geometry("800x700")
        plot_window.grab_set()

        main_frame = ttk.Frame(plot_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="Phase Surface Plotter", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 15))

        info_label = ttk.Label(
            main_frame,
            text=(
                "Plot solidus/liquidus surfaces using imported Pandat data.\n"
                "Equilibrium/Lever: Use P (liquidus T) and Ts (solidus T); Scheil: Use P-S and Ts-S."
            ),
            wraplength=700,
            justify='left'
        )
        info_label.pack(pady=(0, 10))

        controls = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        controls.pack(fill=tk.X, pady=10)

        dataset_var = tk.StringVar(value="Equilibrium")
        dataset_frame = ttk.Frame(controls)
        dataset_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dataset_frame, text="Dataset:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(dataset_frame, text="Equilibrium/Lever", variable=dataset_var, value="Equilibrium").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(dataset_frame, text="Scheil", variable=dataset_var, value="Scheil").pack(side=tk.LEFT, padx=5)

        surface_var = tk.StringVar(value="Liquidus")
        surface_frame = ttk.Frame(controls)
        surface_frame.pack(fill=tk.X, pady=5)
        ttk.Label(surface_frame, text="Type:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(surface_frame, text="Liquidus", variable=surface_var, value="Liquidus").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(surface_frame, text="Solidus", variable=surface_var, value="Solidus").pack(side=tk.LEFT, padx=5)

        elements_frame = ttk.Frame(controls)
        elements_frame.pack(fill=tk.X, pady=5)
        ttk.Label(elements_frame, text="X Element:").pack(side=tk.LEFT, padx=5)
        elem_x_var = tk.StringVar()
        elem_y_var = tk.StringVar()
        elem_values = self.available_elements if self.available_elements else sorted(PERIODIC_TABLE.keys())
        elem_x_combo = ttk.Combobox(elements_frame, textvariable=elem_x_var, values=elem_values, width=10)
        elem_x_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(elements_frame, text="Y Element:").pack(side=tk.LEFT, padx=15)
        elem_y_combo = ttk.Combobox(elements_frame, textvariable=elem_y_var, values=elem_values, width=10)
        elem_y_combo.pack(side=tk.LEFT, padx=5)

        viz_frame = ttk.Frame(controls)
        viz_frame.pack(fill=tk.X, pady=5)
        ttk.Label(viz_frame, text="Visualization:").pack(side=tk.LEFT, padx=5)
        viz_var = tk.StringVar(value="2D Heatmap")
        ttk.Radiobutton(viz_frame, text="2D Heatmap", variable=viz_var, value="2D Heatmap").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(viz_frame, text="3D Static", variable=viz_var, value="3D Static").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(viz_frame, text="3D Rotation GIF", variable=viz_var, value="3D Rotation GIF").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(viz_frame, text="Plotly 3D", variable=viz_var, value="Plotly 3D").pack(side=tk.LEFT, padx=5)

        output_frame = ttk.Frame(controls)
        output_frame.pack(fill=tk.X, pady=5)
        ttk.Label(output_frame, text="Output Prefix:").pack(side=tk.LEFT, padx=5)
        output_var = tk.StringVar(value="phase_surface")
        ttk.Entry(output_frame, textvariable=output_var, width=40).pack(side=tk.LEFT, padx=5)

        status_label = ttk.Label(main_frame, text="Ready to plot", foreground="blue")
        status_label.pack(pady=5)

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

        def run_plot():
            try:
                df = get_df()
                if df is None or len(df) == 0:
                    messagebox.showerror("Data Missing", "No data found. Please import P/Ts or P-S/Ts-S files via Import → Pandat to ThermoQ first.")
                    return

                ex = elem_x_var.get().strip()
                ey = elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror("Element Selection", "Please select X and Y elements first.")
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
                    messagebox.showerror("Column Not Found", 
                        f"Required columns not found in dataset.\n"
                        f"Looking for: {col_x_pattern}, {col_y_pattern}\n"
                        f"Available w(*) columns (first 10): {', '.join(available_cols) if available_cols else 'None'}")
                    return
                
                if col_t_found is None:
                    messagebox.showerror("Column Not Found", "Temperature column T not found in dataset.")
                    return

                x_vals = pd.to_numeric(df[col_x_found], errors='coerce')
                y_vals = pd.to_numeric(df[col_y_found], errors='coerce')
                t_vals = pd.to_numeric(df[col_t_found], errors='coerce')
                mask = x_vals.notna() & y_vals.notna() & t_vals.notna()
                x = x_vals.loc[mask].to_numpy()
                y = y_vals.loc[mask].to_numpy()
                z = t_vals.loc[mask].to_numpy()
                if len(x) == 0:
                    messagebox.showerror("No Data", "No valid data points after filtering.")
                    return

                prefix = output_var.get().strip() or "phase_surface"
                ds = dataset_var.get()
                sf = surface_var.get()
                base = f"{prefix}_{sf}_{ds}_{ex}_{ey}"
                label_z = f"{sf.lower()} line (K)" if sf in ("Liquidus", "Solidus") else "Temperature (K)"

                viz = viz_var.get()
                # Create smooth surface using Gaussian Process
                status_label.config(text="Creating smooth surface...", foreground="orange")
                plot_window.update()
                xi_grid, yi_grid, zi_grid = self.create_smooth_surface(x, y, z, grid_resolution=50)
                
                if xi_grid is None:
                    messagebox.showwarning("Smoothing Failed", "Could not create smooth surface. Using scatter plot instead. Please install scikit-learn and scipy for smooth surfaces.")
                    xi_grid, yi_grid, zi_grid = None, None, None
                
                if viz == "2D Heatmap":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror("Dependency Missing", "Matplotlib is not installed. Cannot generate 2D heatmap.")
                        return
                    plt.figure(figsize=(10, 8))
                    plt.xlabel(f"w({ex}) (%)")
                    plt.ylabel(f"w({ey}) (%)")
                    if xi_grid is not None:
                        # Use smooth surface
                        contour = plt.contourf(xi_grid, yi_grid, zi_grid, levels=50, cmap='hot', alpha=0.9)
                        plt.contour(xi_grid, yi_grid, zi_grid, levels=20, colors='black', alpha=0.3, linewidths=0.5)
                        plt.colorbar(contour, label=label_z)
                        # Overlay original data points
                        plt.scatter(x, y, c=z, cmap='hot', s=20, alpha=0.6, edgecolors='black', linewidths=0.5)
                    else:
                        # Fallback to scatter
                        scatter = plt.scatter(x, y, c=z, cmap='hot', s=50, alpha=0.8)
                        plt.colorbar(scatter, label=label_z)
                    plt.grid(True, linestyle='--', alpha=0.7)
                    out_path = f"{base}_Heatmap.png"
                    plt.savefig(out_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    status_label.config(text=f"Heatmap saved: {out_path}", foreground="green")
                    # Open the file
                    self.open_file_and_offer_save_as(out_path, plot_window)
                elif viz == "3D Static":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror("Dependency Missing", "Matplotlib is not installed. Cannot generate 3D image.")
                        return
                    fig = plt.figure(figsize=(12, 10))
                    ax = fig.add_subplot(111, projection='3d')
                    if xi_grid is not None:
                        # Use smooth surface
                        surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap='coolwarm', alpha=0.9, 
                                              linewidth=0, antialiased=True, shade=True)
                        # Overlay original data points
                        ax.scatter(x, y, z, c='black', s=10, alpha=0.5)
                        fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                    else:
                        # Fallback to scatter
                        sc3d = ax.scatter(x, y, z, c=z, cmap='coolwarm', s=30, alpha=0.8)
                        fig.colorbar(sc3d, shrink=0.5, aspect=5, label=label_z)
                    ax.set_xlabel(f"w({ex}) (%)")
                    ax.set_ylabel(f"w({ey}) (%)")
                    ax.set_zlabel(label_z)
                    out_path = f"{base}_3d.png"
                    plt.savefig(out_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    status_label.config(text=f"3D plot saved: {out_path}", foreground="green")
                    # Open the file
                    self.open_file_and_offer_save_as(out_path, plot_window)
                elif viz == "3D Rotation GIF":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror("Dependency Missing", "Matplotlib is not installed. Cannot generate GIF.")
                        return
                    fig = plt.figure(figsize=(12, 10))
                    ax = fig.add_subplot(111, projection='3d')
                    if xi_grid is not None:
                        # Use smooth surface
                        surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap='coolwarm', alpha=0.9, 
                                              linewidth=0, antialiased=True, shade=True)
                        # Overlay original data points
                        ax.scatter(x, y, z, c='black', s=10, alpha=0.5)
                        fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                    else:
                        # Fallback to scatter
                        sc3d = ax.scatter(x, y, z, c=z, cmap='coolwarm', s=30, alpha=0.8)
                        fig.colorbar(sc3d, shrink=0.5, aspect=5, label=label_z)
                    ax.set_xlabel(f"w({ex}) (%)")
                    ax.set_ylabel(f"w({ey}) (%)")
                    ax.set_zlabel(label_z)

                    def _rotate(angle):
                        ax.view_init(azim=angle)
                        return [ax]

                    ani = animation.FuncAnimation(fig, _rotate, frames=range(0, 360, 5), interval=50)
                    out_path = f"{base}_3d_rotation.gif"
                    ani.save(out_path, writer='pillow', fps=20, dpi=100)
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
                                          colorscale='Jet', opacity=0.9,
                                          colorbar=dict(title=label_z)),
                                go.Scatter3d(x=x, y=y, z=z, mode='markers',
                                           marker=dict(size=3, color='black', opacity=0.5))
                            ])
                        else:
                            # Fallback to scatter
                            fig_plotly = go.Figure(data=[go.Scatter3d(
                                x=x, y=y, z=z,
                                mode='markers',
                                marker=dict(size=3, color=z, colorscale='Jet', opacity=0.8,
                                            colorbar=dict(title=label_z))
                            )])
                        fig_plotly.update_layout(
                            scene=dict(
                                xaxis_title=f"w({ex}) (%)",
                                yaxis_title=f"w({ey}) (%)",
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
                            f.write('  marker: { size: 3, color: ' + str(z.tolist()) + ', colorscale: "Jet", opacity: 0.8, colorbar: {title: "' + label_z + '"} }\n')
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
                        status_label.config(text=f"Interactive 3D plot saved: {out_path}", foreground="green")
                        # Open the file
                        self.open_file_and_offer_save_as(out_path, plot_window)

            except Exception as e:
                messagebox.showerror("Plotting Failed", f"An error occurred: {str(e)}")

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=15)
        ttk.Button(buttons_frame, text="Plot", command=run_plot).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Close", command=plot_window.destroy).pack(side=tk.LEFT, padx=10)

    def create_smooth_surface(self, x, y, z, grid_resolution=50):
        """Create smooth surface using Gaussian Process Regression or interpolation"""
        if SKLEARN_AVAILABLE and len(x) >= 3:
            try:
                # Prepare training data
                X_train = np.column_stack([x, y])
                z_train = z
                
                # Create Gaussian Process Regressor
                # Increase parameter bounds to avoid convergence warnings
                # ConstantKernel: (lower, upper) for constant_value
                # RBF: (lower, upper) for length_scale (one per dimension)
                kernel = C(1.0, (1e-3, 1e5)) * RBF([1.0, 1.0], (1e-2, 1e4))
                gp = GaussianProcessRegressor(
                    kernel=kernel, 
                    n_restarts_optimizer=10, 
                    alpha=1e-6,  # Reduced alpha for better fitting
                    normalize_y=False  # Don't normalize y values
                )
                gp.fit(X_train, z_train)
                
                # Create grid for prediction
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
                
                # Predict on grid
                X_grid = np.column_stack([xi_grid.ravel(), yi_grid.ravel()])
                zi_grid = gp.predict(X_grid).reshape(xi_grid.shape)
                
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
                
                # Interpolate
                zi_grid = griddata((x, y), z, (xi_grid, yi_grid), method='cubic', fill_value=np.nan)
                
                # Fill NaN values with nearest neighbor interpolation
                if np.isnan(zi_grid).any():
                    zi_grid_filled = griddata((x, y), z, (xi_grid, yi_grid), method='nearest')
                    zi_grid = np.where(np.isnan(zi_grid), zi_grid_filled, zi_grid)
                
                return xi_grid, yi_grid, zi_grid
            except Exception:
                pass
        
        # Final fallback: return original data
        return None, None, None

    def open_file_and_offer_save_as(self, file_path, parent_window):
        """Open a file and offer save-as option when closing"""
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
            
            # Show a message box with save-as option
            result = messagebox.askyesnocancel(
                "File Opened",
                f"File has been opened:\n{file_path}\n\nWould you like to save it to a different location?",
                parent=parent_window
            )
            
            if result is True:  # Yes - save as
                self.save_file_as(file_path, parent_window)
            # If result is False (No) or None (Cancel), do nothing
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}", parent=parent_window)

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
                messagebox.showinfo("Success", f"File saved to:\n{save_path}", parent=parent_window)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}", parent=parent_window)

    def open_q_value_plotter(self):
        """Open Q value plotter window"""
        plot_window = tk.Toplevel(self.root)
        plot_window.title("Plot Q Values")
        plot_window.geometry("800x600")
        plot_window.grab_set()

        main_frame = ttk.Frame(plot_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="Q Value Plotter", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 15))

        info_label = ttk.Label(
            main_frame,
            text=(
                "Plot Q values (-T//fw(@FCC_A1)) using imported Pandat data.\n"
                "X-axis: w(MG), Y-axis: w(SI), Z-axis: Q value (-T//fw(@FCC_A1)).\n"
                "Equilibrium/Lever: Use P.xlsx; Scheil: Use P-S.xlsx."
            ),
            wraplength=700,
            justify='left'
        )
        info_label.pack(pady=(0, 10))

        controls = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        controls.pack(fill=tk.X, pady=10)

        dataset_var = tk.StringVar(value="Equilibrium")
        dataset_frame = ttk.Frame(controls)
        dataset_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dataset_frame, text="Dataset:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(dataset_frame, text="Equilibrium/Lever", variable=dataset_var, value="Equilibrium").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(dataset_frame, text="Scheil", variable=dataset_var, value="Scheil").pack(side=tk.LEFT, padx=5)

        viz_frame = ttk.Frame(controls)
        viz_frame.pack(fill=tk.X, pady=5)
        ttk.Label(viz_frame, text="Visualization:").pack(side=tk.LEFT, padx=5)
        viz_var = tk.StringVar(value="2D Heatmap")
        ttk.Radiobutton(viz_frame, text="2D Heatmap", variable=viz_var, value="2D Heatmap").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(viz_frame, text="3D Static", variable=viz_var, value="3D Static").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(viz_frame, text="3D Rotation GIF", variable=viz_var, value="3D Rotation GIF").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(viz_frame, text="Plotly 3D", variable=viz_var, value="Plotly 3D").pack(side=tk.LEFT, padx=5)

        output_frame = ttk.Frame(controls)
        output_frame.pack(fill=tk.X, pady=5)
        ttk.Label(output_frame, text="Output Prefix:").pack(side=tk.LEFT, padx=5)
        output_var = tk.StringVar(value="q_value")
        ttk.Entry(output_frame, textvariable=output_var, width=40).pack(side=tk.LEFT, padx=5)

        status_label = ttk.Label(main_frame, text="Ready to plot", foreground="blue")
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
                    messagebox.showerror("Data Missing", "No data found. Please import P.xlsx (Equilibrium) or P-S.xlsx (Scheil) via Import → Pandat to ThermoQ first.")
                    return

                # Fixed columns: X = w(MG), Y = w(SI), Z = -T//fw(@FCC_A1)
                col_x = "w(MG)"
                col_y = "w(SI)"
                col_q = "-T//fw(@FCC_A1)"
                
                # Try case-insensitive column matching
                col_x_found = None
                col_y_found = None
                col_q_found = None
                
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.upper()
                        if col_upper == "W(MG)":
                            col_x_found = col
                        elif col_upper == "W(SI)":
                            col_y_found = col
                        elif col_upper == "-T//FW(@FCC_A1)":
                            col_q_found = col
                
                if col_x_found is None or col_y_found is None or col_q_found is None:
                    available_cols = [str(c) for c in df.columns[:20]]
                    messagebox.showerror("Column Not Found", 
                        f"Required columns not found in dataset.\n"
                        f"Looking for: {col_x}, {col_y}, {col_q}\n"
                        f"Available columns (first 20): {', '.join(available_cols)}")
                    return

                x_vals = pd.to_numeric(df[col_x_found], errors='coerce')
                y_vals = pd.to_numeric(df[col_y_found], errors='coerce')
                q_vals = pd.to_numeric(df[col_q_found], errors='coerce')
                mask = x_vals.notna() & y_vals.notna() & q_vals.notna()
                x = x_vals.loc[mask].to_numpy()
                y = y_vals.loc[mask].to_numpy()
                z = q_vals.loc[mask].to_numpy()
                
                if len(x) == 0:
                    messagebox.showerror("No Data", "No valid data points after filtering.")
                    return

                prefix = output_var.get().strip() or "q_value"
                ds = dataset_var.get()
                base = f"{prefix}_{ds}"
                label_z = "Q Value (-T//fw(@FCC_A1))"

                # Create smooth surface using Gaussian Process
                status_label.config(text="Creating smooth surface...", foreground="orange")
                plot_window.update()
                xi_grid, yi_grid, zi_grid = self.create_smooth_surface(x, y, z, grid_resolution=50)
                
                if xi_grid is None:
                    messagebox.showwarning("Smoothing Failed", "Could not create smooth surface. Using scatter plot instead. Please install scikit-learn and scipy for smooth surfaces.")
                    xi_grid, yi_grid, zi_grid = None, None, None

                viz = viz_var.get()
                if viz == "2D Heatmap":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror("Dependency Missing", "Matplotlib is not installed. Cannot generate 2D heatmap.")
                        return
                    plt.figure(figsize=(10, 8))
                    plt.xlabel("w(MG) (%)")
                    plt.ylabel("w(SI) (%)")
                    if xi_grid is not None:
                        # Use smooth surface
                        contour = plt.contourf(xi_grid, yi_grid, zi_grid, levels=50, cmap='hot', alpha=0.9)
                        plt.contour(xi_grid, yi_grid, zi_grid, levels=20, colors='black', alpha=0.3, linewidths=0.5)
                        plt.colorbar(contour, label=label_z)
                        # Overlay original data points
                        plt.scatter(x, y, c=z, cmap='hot', s=20, alpha=0.6, edgecolors='black', linewidths=0.5)
                    else:
                        # Fallback to scatter
                        scatter = plt.scatter(x, y, c=z, cmap='hot', s=50, alpha=0.8)
                        plt.colorbar(scatter, label=label_z)
                    plt.grid(True, linestyle='--', alpha=0.7)
                    out_path = f"{base}_Heatmap.png"
                    plt.savefig(out_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    status_label.config(text=f"Heatmap saved: {out_path}", foreground="green")
                    # Open the file
                    self.open_file_and_offer_save_as(out_path, plot_window)
                elif viz == "3D Static":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror("Dependency Missing", "Matplotlib is not installed. Cannot generate 3D image.")
                        return
                    fig = plt.figure(figsize=(12, 10))
                    ax = fig.add_subplot(111, projection='3d')
                    if xi_grid is not None:
                        # Use smooth surface
                        surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap='coolwarm', alpha=0.9, 
                                              linewidth=0, antialiased=True, shade=True)
                        # Overlay original data points
                        ax.scatter(x, y, z, c='black', s=10, alpha=0.5)
                        fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                    else:
                        # Fallback to scatter
                        sc3d = ax.scatter(x, y, z, c=z, cmap='coolwarm', s=30, alpha=0.8)
                        fig.colorbar(sc3d, shrink=0.5, aspect=5, label=label_z)
                    ax.set_xlabel("w(MG) (%)")
                    ax.set_ylabel("w(SI) (%)")
                    ax.set_zlabel(label_z)
                    out_path = f"{base}_3d.png"
                    plt.savefig(out_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    status_label.config(text=f"3D plot saved: {out_path}", foreground="green")
                    # Open the file
                    self.open_file_and_offer_save_as(out_path, plot_window)
                elif viz == "3D Rotation GIF":
                    if not MATPLOTLIB_AVAILABLE:
                        messagebox.showerror("Dependency Missing", "Matplotlib is not installed. Cannot generate GIF.")
                        return
                    fig = plt.figure(figsize=(12, 10))
                    ax = fig.add_subplot(111, projection='3d')
                    if xi_grid is not None:
                        # Use smooth surface
                        surf = ax.plot_surface(xi_grid, yi_grid, zi_grid, cmap='coolwarm', alpha=0.9, 
                                              linewidth=0, antialiased=True, shade=True)
                        # Overlay original data points
                        ax.scatter(x, y, z, c='black', s=10, alpha=0.5)
                        fig.colorbar(surf, shrink=0.5, aspect=5, label=label_z)
                    else:
                        # Fallback to scatter
                        sc3d = ax.scatter(x, y, z, c=z, cmap='coolwarm', s=30, alpha=0.8)
                        fig.colorbar(sc3d, shrink=0.5, aspect=5, label=label_z)
                    ax.set_xlabel("w(MG) (%)")
                    ax.set_ylabel("w(SI) (%)")
                    ax.set_zlabel(label_z)

                    def _rotate(angle):
                        ax.view_init(azim=angle)
                        return [ax]

                    ani = animation.FuncAnimation(fig, _rotate, frames=range(0, 360, 5), interval=50)
                    out_path = f"{base}_3d_rotation.gif"
                    ani.save(out_path, writer='pillow', fps=20, dpi=100)
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
                                          colorscale='Jet', opacity=0.9,
                                          colorbar=dict(title=label_z)),
                                go.Scatter3d(x=x, y=y, z=z, mode='markers',
                                           marker=dict(size=3, color='black', opacity=0.5))
                            ])
                        else:
                            # Fallback to scatter
                            fig_plotly = go.Figure(data=[go.Scatter3d(
                                x=x, y=y, z=z,
                                mode='markers',
                                marker=dict(size=3, color=z, colorscale='Jet', opacity=0.8,
                                            colorbar=dict(title=label_z))
                            )])
                        fig_plotly.update_layout(
                            scene=dict(
                                xaxis_title="w(MG) (%)",
                                yaxis_title="w(SI) (%)",
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
                            f.write('    xaxis: {title: "w(MG) (%)"},\n')
                            f.write('    yaxis: {title: "w(SI) (%)"},\n')
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
                messagebox.showerror("Plotting Failed", f"An error occurred: {str(e)}\n\nDetails:\n{error_details}")

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=15)
        ttk.Button(buttons_frame, text="Plot", command=run_plot).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Close", command=plot_window.destroy).pack(side=tk.LEFT, padx=10)

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
    
    def find_matching_row(self, composition, data_df):
        """Find the row in the given Pandat data DataFrame that matches the given composition
        Matching is based on integer part only (e.g., 80.5 matches 80.8)
        Column names are case-insensitive (e.g., w(Al) matches w(AL))
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
        """Open Thermo-calc batch file generator tool"""
        generator_window = tk.Toplevel(self.root)
        generator_window.title("Generate Thermo-calc Batch File")
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
        title_label = ttk.Label(main_frame, text="Thermo-calc Batch File Generator", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Instructions
        info_label = ttk.Label(main_frame, 
            text="Generate Thermo-calc batch file (.tcm) by combining template files with element combinations",
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
            """Generate Thermo-calc batch file"""
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
        """Open Thermo-calc results extractor tool"""
        processor_window = tk.Toplevel(self.root)
        processor_window.title("Extract Thermo-calc Results")
        processor_window.geometry("800x600")
        processor_window.grab_set()  # Make window modal
        
        # Create main frame
        main_frame = ttk.Frame(processor_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Extract Thermo-calc Results", font=('Arial', 14, 'bold'))
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
    
    def open_extract_pandat_results(self):
        """Open Pandat results extractor tool"""
        extractor_window = tk.Toplevel(self.root)
        extractor_window.title("Extract Pandat Results")
        extractor_window.geometry("700x550")
        extractor_window.grab_set()  # Make window modal
        
        # Create main frame
        main_frame = ttk.Frame(extractor_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Extract Pandat Results", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Instructions
        info_label = ttk.Label(main_frame, 
            text="Extract data from CSV/DAT files to generate P.xlsx, Ts.xlsx, P-S.xlsx, and Ts-S.xlsx",
            wraplength=650, justify='center')
        info_label.pack(pady=(0, 20))
        
        # Lever folder selection
        lever_frame = ttk.LabelFrame(main_frame, text="Lever/Equilibrium Folder (All table_Lever)", padding="15")
        lever_frame.pack(fill=tk.X, pady=10)
        
        lever_folder_var = tk.StringVar()
        ttk.Entry(lever_frame, textvariable=lever_folder_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(lever_frame, text="Browse", 
                  command=lambda: lever_folder_var.set(filedialog.askdirectory(title="Select Lever Folder"))).pack(side=tk.RIGHT, padx=5)
        
        # Scheil folder selection
        scheil_frame = ttk.LabelFrame(main_frame, text="Scheil Folder (All table_Scheil)", padding="15")
        scheil_frame.pack(fill=tk.X, pady=10)
        
        scheil_folder_var = tk.StringVar()
        ttk.Entry(scheil_frame, textvariable=scheil_folder_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(scheil_frame, text="Browse", 
                  command=lambda: scheil_folder_var.set(filedialog.askdirectory(title="Select Scheil Folder"))).pack(side=tk.RIGHT, padx=5)
        
        # Output directory
        output_frame = ttk.LabelFrame(main_frame, text="Output Directory", padding="15")
        output_frame.pack(fill=tk.X, pady=10)
        
        output_dir_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=output_dir_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Browse", 
                  command=lambda: output_dir_var.set(filedialog.askdirectory(title="Select Output Directory"))).pack(side=tk.RIGHT, padx=5)
        
        # Status label
        status_label = ttk.Label(main_frame, text="Ready to extract", foreground="blue")
        status_label.pack(pady=10)
        
        def extract_results():
            """Extract results from CSV/DAT files"""
            try:
                lever_folder = lever_folder_var.get()
                scheil_folder = scheil_folder_var.get()
                output_dir = output_dir_var.get() or os.getcwd()
                
                if not lever_folder or not os.path.exists(lever_folder):
                    messagebox.showerror("Error", "Please select a valid Lever folder!")
                    return
                
                if not scheil_folder or not os.path.exists(scheil_folder):
                    messagebox.showerror("Error", "Please select a valid Scheil folder!")
                    return
                
                status_label.config(text="Processing files...", foreground="orange")
                extractor_window.update()
                
                # Process Lever files
                lever_csv_files = sorted([f for f in os.listdir(lever_folder) if f.endswith('.csv')])
                if not lever_csv_files:
                    messagebox.showerror("Error", "No CSV files found in Lever folder!")
                    return
                
                # Process each Lever CSV file for P.xlsx
                p_data_list = []
                for csv_file in lever_csv_files:
                    csv_path = os.path.join(lever_folder, csv_file)
                    df = pd.read_csv(csv_path, sep='\t', header=0, skiprows=[1])  # Skip unit row
                    
                    # Filter: fs < 0.000001, get row with max T
                    df['fs_num'] = pd.to_numeric(df['fs'], errors='coerce')
                    df['T_num'] = pd.to_numeric(df['T'], errors='coerce')
                    filtered = df[df['fs_num'] < 0.000001].copy()
                    
                    if not filtered.empty:
                        max_t_row = filtered.loc[filtered['T_num'].idxmax()]
                        p_data_list.append(max_t_row)
                
                # Extract columns for P.xlsx: T, w(*), w(*@*), fs, fw(@FCC_A1), dwdT_L(*@LIQUID), -T//fw(@FCC_A1)
                if p_data_list:
                    p_df = pd.DataFrame(p_data_list)
                    # Select required columns
                    p_cols = ['T', 'fs', 'fw(@FCC_A1)', '-T//fw(@FCC_A1)']
                    # Add w(*) columns (e.g., w(AL), w(MG), w(SI))
                    p_cols.extend([c for c in p_df.columns if re.match(r'^w\([A-Z]+\)$', c, re.IGNORECASE)])
                    # Add w(*@*) columns (LIQUID and FCC_A1) - e.g., w(AL@LIQUID), w(AL@FCC_A1)
                    p_cols.extend([c for c in p_df.columns if re.match(r'^w\([A-Z]+@(LIQUID|FCC_A1)\)$', c, re.IGNORECASE)])
                    # Add dwdT_L(*@LIQUID) columns (e.g., dwdT_L(AL@LIQUID))
                    p_cols.extend([c for c in p_df.columns if re.search(r'dwdT_L\([A-Z]+@LIQUID\)', c, re.IGNORECASE)])
                    
                    # Remove duplicates and keep only existing columns
                    p_cols = list(dict.fromkeys([c for c in p_cols if c in p_df.columns]))
                    p_output = p_df[p_cols].copy()
                    
                    p_output_path = os.path.join(output_dir, 'P.xlsx')
                    p_output.to_excel(p_output_path, index=False)
                    status_label.config(text=f"P.xlsx saved: {len(p_output)} rows", foreground="green")
                
                # Process each Lever CSV file for Ts.xlsx
                ts_data_list = []
                for csv_file in lever_csv_files:
                    csv_path = os.path.join(lever_folder, csv_file)
                    df = pd.read_csv(csv_path, sep='\t', header=0, skiprows=[1])
                    
                    df['fs_num'] = pd.to_numeric(df['fs'], errors='coerce')
                    df['T_num'] = pd.to_numeric(df['T'], errors='coerce')
                    
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
                
                # Extract columns for Ts.xlsx: T, w(*), fs
                if ts_data_list:
                    ts_df = pd.DataFrame(ts_data_list)
                    ts_cols = ['T', 'fs']
                    # Add w(*) columns (e.g., w(AL), w(MG), w(SI))
                    ts_cols.extend([c for c in ts_df.columns if re.match(r'^w\([A-Z]+\)$', c, re.IGNORECASE)])
                    # Remove duplicates and keep only existing columns
                    ts_cols = list(dict.fromkeys([c for c in ts_cols if c in ts_df.columns]))
                    ts_output = ts_df[ts_cols].copy()
                    
                    ts_output_path = os.path.join(output_dir, 'Ts.xlsx')
                    ts_output.to_excel(ts_output_path, index=False)
                    status_label.config(text=f"Ts.xlsx saved: {len(ts_output)} rows", foreground="green")
                
                # Process Scheil files (same logic as Lever)
                scheil_dat_files = sorted([f for f in os.listdir(scheil_folder) if f.endswith('.dat')])
                if scheil_dat_files:
                    # Process for P-S.xlsx
                    p_s_data_list = []
                    for dat_file in scheil_dat_files:
                        dat_path = os.path.join(scheil_folder, dat_file)
                        df = pd.read_csv(dat_path, sep='\t', header=0, skiprows=[1])
                        
                        df['fs_num'] = pd.to_numeric(df['fs'], errors='coerce')
                        df['T_num'] = pd.to_numeric(df['T'], errors='coerce')
                        filtered = df[df['fs_num'] < 0.000001].copy()
                        
                        if not filtered.empty:
                            max_t_row = filtered.loc[filtered['T_num'].idxmax()]
                            p_s_data_list.append(max_t_row)
                    
                    if p_s_data_list:
                        p_s_df = pd.DataFrame(p_s_data_list)
                        p_s_cols = ['T', 'fs', 'fw(@FCC_A1)', '-T//fw(@FCC_A1)']
                        # Add w(*) columns
                        p_s_cols.extend([c for c in p_s_df.columns if re.match(r'^w\([A-Z]+\)$', c, re.IGNORECASE)])
                        # Add w(*@*) columns
                        p_s_cols.extend([c for c in p_s_df.columns if re.match(r'^w\([A-Z]+@(LIQUID|FCC_A1)\)$', c, re.IGNORECASE)])
                        # Add dwdT_L(*@LIQUID) columns
                        p_s_cols.extend([c for c in p_s_df.columns if re.search(r'dwdT_L\([A-Z]+@LIQUID\)', c, re.IGNORECASE)])
                        # Remove duplicates and keep only existing columns
                        p_s_cols = list(dict.fromkeys([c for c in p_s_cols if c in p_s_df.columns]))
                        p_s_output = p_s_df[p_s_cols].copy()
                        
                        p_s_output_path = os.path.join(output_dir, 'P-S.xlsx')
                        p_s_output.to_excel(p_s_output_path, index=False)
                    
                    # Process for Ts-S.xlsx
                    ts_s_data_list = []
                    for dat_file in scheil_dat_files:
                        dat_path = os.path.join(scheil_folder, dat_file)
                        df = pd.read_csv(dat_path, sep='\t', header=0, skiprows=[1])
                        
                        df['fs_num'] = pd.to_numeric(df['fs'], errors='coerce')
                        df['T_num'] = pd.to_numeric(df['T'], errors='coerce')
                        
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
                        ts_s_cols = ['T', 'fs']
                        # Add w(*) columns
                        ts_s_cols.extend([c for c in ts_s_df.columns if re.match(r'^w\([A-Z]+\)$', c, re.IGNORECASE)])
                        # Remove duplicates and keep only existing columns
                        ts_s_cols = list(dict.fromkeys([c for c in ts_s_cols if c in ts_s_df.columns]))
                        ts_s_output = ts_s_df[ts_s_cols].copy()
                        
                        ts_s_output_path = os.path.join(output_dir, 'Ts-S.xlsx')
                        ts_s_output.to_excel(ts_s_output_path, index=False)
                
                status_label.config(
                    text=f"Success! Files saved to: {output_dir}\n"
                         f"P.xlsx: {len(p_data_list) if p_data_list else 0} rows\n"
                         f"Ts.xlsx: {len(ts_data_list) if ts_data_list else 0} rows\n"
                         f"P-S.xlsx: {len(p_s_data_list) if p_s_data_list else 0} rows\n"
                         f"Ts-S.xlsx: {len(ts_s_data_list) if ts_s_data_list else 0} rows",
                    foreground="green"
                )
                messagebox.showinfo("Success", 
                    f"Results extracted successfully!\n\n"
                    f"Output directory: {output_dir}\n\n"
                    f"P.xlsx: {len(p_data_list) if p_data_list else 0} rows\n"
                    f"Ts.xlsx: {len(ts_data_list) if ts_data_list else 0} rows\n"
                    f"P-S.xlsx: {len(p_s_data_list) if p_s_data_list else 0} rows\n"
                    f"Ts-S.xlsx: {len(ts_s_data_list) if ts_s_data_list else 0} rows")
                
            except Exception as e:
                status_label.config(text=f"Error: {str(e)}", foreground="red")
                messagebox.showerror("Error", f"Failed to extract results:\n{str(e)}")
                import traceback
                traceback.print_exc()
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="Extract Results", command=extract_results).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Close", command=extractor_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def open_liquidus_vector_plotter(self):
        """Open liquidus vector plotter tool"""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("Dependency Missing", "Matplotlib is not installed. Cannot generate vector plots.")
            return
        
        vector_window = tk.Toplevel(self.root)
        vector_window.title("Plot Liquidus Vectors")
        vector_window.geometry("800x750")
        vector_window.grab_set()  # Make window modal
        
        # Create main frame
        main_frame = ttk.Frame(vector_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Liquidus Vector Plotter", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Instructions
        info_label = ttk.Label(main_frame, 
            text="Plot quiver plots showing liquidus vectors from Excel data.\n"
                 "Requires columns: w(X), w(Y), 1/dwdT_L(X@LIQUID), 1/dwdT_L(Y@LIQUID)",
            wraplength=650, justify='center')
        info_label.pack(pady=(0, 20))
        
        # Excel file selection
        file_frame = ttk.LabelFrame(main_frame, text="Select Excel File", padding="15")
        file_frame.pack(fill=tk.X, pady=10)
        
        file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=file_var, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        def browse_excel_file():
            file_path = filedialog.askopenfilename(
                title="Select Excel File", 
                filetypes=[("Excel files", "*.xls *.xlsx"), ("All files", "*.*")]
            )
            if file_path:
                file_var.set(file_path)
                on_file_selected()  # Update element options immediately
        
        ttk.Button(file_frame, text="Browse", command=browse_excel_file).pack(side=tk.RIGHT, padx=5)
        
        # Element selection
        element_frame = ttk.LabelFrame(main_frame, text="Element Selection", padding="15")
        element_frame.pack(fill=tk.X, pady=10)
        
        # Store available elements from Excel file
        excel_elements = []
        
        def extract_elements_from_excel():
            """Extract available elements from selected Excel file"""
            excel_path = file_var.get()
            if not excel_path or not os.path.exists(excel_path):
                return []
            
            try:
                # Read Excel file to get column names
                df = pd.read_excel(excel_path, header=0, nrows=0)  # Only read header
                elements = []
                
                # Extract elements from w(*) columns
                for col in df.columns:
                    if isinstance(col, str):
                        col_upper = col.strip().upper()
                        # Match w(ELEMENT) pattern
                        match = re.match(r'^W\(([A-Z]+)\)$', col_upper)
                        if match:
                            element = match.group(1).capitalize()  # Convert to proper case (e.g., MG -> Mg)
                            if element in PERIODIC_TABLE and element not in elements:
                                elements.append(element)
                
                return sorted(elements)
            except Exception as e:
                return []
        
        def update_element_options():
            """Update element dropdown options based on Excel file"""
            elements = extract_elements_from_excel()
            if elements:
                excel_elements[:] = elements
                elem_x_combo['values'] = elements
                elem_y_combo['values'] = elements
                # Set default values if current values are not in the list
                if elem_x_var.get() not in elements and elements:
                    elem_x_var.set(elements[0])
                if elem_y_var.get() not in elements and len(elements) > 1:
                    elem_y_var.set(elements[1])
                elif elem_y_var.get() not in elements and elements:
                    elem_y_var.set(elements[0])
            else:
                # Fallback to all elements if no Excel file or extraction fails
                all_elements = sorted(PERIODIC_TABLE.keys())
                excel_elements[:] = all_elements
                elem_x_combo['values'] = all_elements
                elem_y_combo['values'] = all_elements
        
        ttk.Label(element_frame, text="X Element:").pack(side=tk.LEFT, padx=5)
        elem_x_var = tk.StringVar(value="")
        elem_x_combo = ttk.Combobox(element_frame, textvariable=elem_x_var, values=[], width=10, state="readonly")
        elem_x_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(element_frame, text="Y Element:").pack(side=tk.LEFT, padx=15)
        elem_y_var = tk.StringVar(value="")
        elem_y_combo = ttk.Combobox(element_frame, textvariable=elem_y_var, values=[], width=10, state="readonly")
        elem_y_combo.pack(side=tk.LEFT, padx=5)
        
        # Update element options when file is selected
        def on_file_selected():
            update_element_options()
            if excel_elements:
                status_label.config(text=f"Found {len(excel_elements)} elements: {', '.join(excel_elements)}", foreground="green")
            else:
                status_label.config(text="No elements found in Excel file. Using all elements.", foreground="orange")
        
        # Bind file selection to update elements
        file_var.trace_add("write", lambda *args: on_file_selected())
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="15")
        options_frame.pack(fill=tk.X, pady=10)
        
        clean_fill_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Clean and fill data before plotting", 
                       variable=clean_fill_var).pack(side=tk.LEFT, padx=5)
        
        # Output prefix
        output_frame = ttk.LabelFrame(main_frame, text="Output Prefix", padding="15")
        output_frame.pack(fill=tk.X, pady=10)
        
        output_var = tk.StringVar(value="liquid_vectors")
        ttk.Entry(output_frame, textvariable=output_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Status label
        status_label = ttk.Label(main_frame, text="Ready to plot", foreground="blue")
        status_label.pack(pady=10)
        
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
                excel_path = file_var.get()
                if not excel_path or not os.path.exists(excel_path):
                    messagebox.showerror("Error", "Please select a valid Excel file!")
                    return
                
                ex = elem_x_var.get().strip()
                ey = elem_y_var.get().strip()
                if not ex or not ey:
                    messagebox.showerror("Error", "Please select X and Y elements!")
                    return
                
                if ex not in PERIODIC_TABLE or ey not in PERIODIC_TABLE:
                    messagebox.showerror("Error", f"Invalid elements: {ex} or {ey}")
                    return
                
                status_label.config(text="Loading data...", foreground="orange")
                vector_window.update()
                
                # Load data
                df = pd.read_excel(excel_path, header=0)
                df = _standardize_columns(df)
                df = df.replace(r"^\s*$", np.nan, regex=True).dropna(how="all")
                
                # Clean and fill if requested
                if clean_fill_var.get():
                    status_label.config(text="Cleaning and filling data...", foreground="orange")
                    vector_window.update()
                    # This is a simplified version - full implementation would use process_excel_clean_fill logic
                    # For now, just do basic interpolation
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    df[numeric_cols] = df[numeric_cols].interpolate(method='linear', limit_direction='both')
                
                # Find required columns
                col_wx, col_wy, col_inv_x, col_inv_y = _find_required_columns(df, ex, ey)
                
                status_label.config(text="Processing data...", foreground="orange")
                vector_window.update()
                
                # Convert to numeric
                wx = pd.to_numeric(df[col_wx], errors="coerce")
                wy = pd.to_numeric(df[col_wy], errors="coerce")
                u = pd.to_numeric(df[col_inv_x], errors="coerce")
                v = pd.to_numeric(df[col_inv_y], errors="coerce")
                
                valid = ~(wx.isna() | wy.isna() | u.isna() | v.isna())
                wx, wy, u, v = wx[valid], wy[valid], u[valid], v[valid]
                
                if len(wx) == 0:
                    messagebox.showerror("Error", "No valid data points found after filtering!")
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
                
                prefix = output_var.get().strip() or "liquid_vectors"
                base_path = os.path.dirname(excel_path) or "."
                base_name = os.path.splitext(os.path.basename(excel_path))[0]
                
                status_label.config(text="Generating plots...", foreground="orange")
                vector_window.update()
                
                # Figure 1: U arrows (horizontal)
                fig1, ax1 = plt.subplots(figsize=(7, 6), dpi=140)
                x1 = np.clip(wx.values + dx.values, x_min, x_max)
                u_plot = x1 - wx.values
                ax1.quiver(wx.values, wy.values, u_plot, np.zeros_like(u_plot), 
                          angles="xy", scale_units="xy", scale=1, width=0.003, color="tab:blue")
                ax1.set_xlabel(col_wx)
                ax1.set_ylabel(col_wy)
                ax1.set_title(f"U arrows (scaled by ratio to min of 1/dwdT_L({ex}@LIQUID))")
                ax1.grid(True, ls=":", alpha=0.4)
                ax1.set_aspect("equal", adjustable="box")
                fig1.tight_layout()
                out1 = os.path.join(base_path, f"{prefix}_{ex}_horizontal.png")
                fig1.savefig(out1)
                plt.close(fig1)
                
                # Figure 2: V arrows (vertical)
                fig2, ax2 = plt.subplots(figsize=(7, 6), dpi=140)
                y1 = np.clip(wy.values + dy.values, y_min, y_max)
                v_plot = y1 - wy.values
                ax2.quiver(wx.values, wy.values, np.zeros_like(v_plot), v_plot, 
                          angles="xy", scale_units="xy", scale=1, width=0.003, color="tab:orange")
                ax2.set_xlabel(col_wx)
                ax2.set_ylabel(col_wy)
                ax2.set_title(f"V arrows (scaled by ratio to min of 1/dwdT_L({ey}@LIQUID))")
                ax2.grid(True, ls=":", alpha=0.4)
                ax2.set_aspect("equal", adjustable="box")
                fig2.tight_layout()
                out2 = os.path.join(base_path, f"{prefix}_{ey}_vertical.png")
                fig2.savefig(out2)
                plt.close(fig2)
                
                # Figure 3: Resultant Z vector
                fig3, ax3 = plt.subplots(figsize=(7, 6), dpi=140)
                z_dx = u_plot
                z_dy = v_plot
                ax3.quiver(wx.values, wy.values, z_dx, z_dy, 
                          angles="xy", scale_units="xy", scale=1, width=0.003, color="tab:green")
                ax3.set_xlabel(col_wx)
                ax3.set_ylabel(col_wy)
                ax3.set_title(f"Resultant Z = vector sum of U and V (scaled)")
                ax3.grid(True, ls=":", alpha=0.4)
                ax3.set_aspect("equal", adjustable="box")
                fig3.tight_layout()
                out3 = os.path.join(base_path, f"{prefix}_Z_resultant.png")
                fig3.savefig(out3)
                plt.close(fig3)
                
                status_label.config(
                    text=f"Success! Saved:\n{os.path.basename(out1)}\n{os.path.basename(out2)}\n{os.path.basename(out3)}",
                    foreground="green"
                )
                messagebox.showinfo("Success", 
                    f"Vector plots generated successfully!\n\n"
                    f"U horizontal: {out1}\n"
                    f"V vertical: {out2}\n"
                    f"Z resultant: {out3}")
                
            except Exception as e:
                status_label.config(text=f"Error: {str(e)}", foreground="red")
                messagebox.showerror("Error", f"Failed to generate vector plots:\n{str(e)}")
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="Plot Vectors", command=plot_vectors).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Close", command=vector_window.destroy).pack(side=tk.LEFT, padx=10)

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
