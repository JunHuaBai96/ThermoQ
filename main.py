import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import time
import pandas as pd
from periodic_table import PERIODIC_TABLE

class ElementSelector:
    def __init__(self, parent):
        self.parent = parent
        self.selected_elements = {}  # Dictionary to store selected elements and their compositions
        self.composition_unit = tk.StringVar(value="wt%")  # Default to weight percentage
        
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
        
        # Create composition unit selection
        ttk.Label(selection_frame, text="Unit:").grid(row=0, column=2, padx=5, pady=5)
        unit_frame = ttk.Frame(selection_frame)
        unit_frame.grid(row=0, column=3, padx=5, pady=5)
        ttk.Radiobutton(unit_frame, text="wt%", variable=self.composition_unit, 
                       value="wt%", command=self.update_composition_display).pack(side=tk.LEFT)
        ttk.Radiobutton(unit_frame, text="at%", variable=self.composition_unit, 
                       value="at%", command=self.update_composition_display).pack(side=tk.LEFT)
        
        # Create composition entry
        ttk.Label(selection_frame, text="Composition:").grid(row=0, column=4, padx=5, pady=5)
        self.composition_var = tk.StringVar()
        self.composition_entry = ttk.Entry(selection_frame, textvariable=self.composition_var, width=10)
        self.composition_entry.grid(row=0, column=5, padx=5, pady=5)
        
        # Add button
        ttk.Button(selection_frame, text="Add Element", 
                  command=self.add_element).grid(row=0, column=6, padx=5, pady=5)
        
    
    def create_selected_elements_display(self):
        # Create a frame for displaying selected elements
        display_frame = ttk.LabelFrame(self.frame, text="Selected Elements", padding="5")
        display_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Create treeview for displaying elements
        self.tree = ttk.Treeview(display_frame, columns=("Element", "Name", "Composition"), 
                                show="headings", height=5)
        self.tree.heading("Element", text="Element")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Composition", text="Composition")
        
        self.tree.column("Element", width=80)
        self.tree.column("Name", width=150)
        self.tree.column("Composition", width=100)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Add remove button
        ttk.Button(display_frame, text="Remove Selected", 
                  command=self.remove_element).grid(row=1, column=0, pady=5)
    
    def convert_composition(self, element, composition, from_unit, to_unit):
        if from_unit == to_unit:
            return composition
        
        if from_unit == "wt%" and to_unit == "at%":
            # Convert from weight % to atomic %
            total_weight = sum(comp * PERIODIC_TABLE[elem]['mass'] 
                             for elem, comp in self.selected_elements.items())
            atomic_mass = PERIODIC_TABLE[element]['mass']
            return (composition * atomic_mass) / total_weight * 100
        else:
            # Convert from atomic % to weight %
            total_atoms = sum(comp / PERIODIC_TABLE[elem]['mass'] 
                            for elem, comp in self.selected_elements.items())
            atomic_mass = PERIODIC_TABLE[element]['mass']
            return (composition / atomic_mass) / total_atoms * 100
    
    def update_composition_display(self):
        # Update the display of compositions when unit is changed
        current_unit = self.composition_unit.get()
        for item in self.tree.get_children():
            element = self.tree.item(item)['values'][0]
            composition = self.selected_elements[element]
            converted_composition = self.convert_composition(element, composition, 
                                                          "wt%" if current_unit == "at%" else "at%", 
                                                          current_unit)
            self.tree.item(item, values=(
                element,
                PERIODIC_TABLE[element]['name'],
                f"{converted_composition:.2f} {current_unit}"
            ))
    
    def add_element(self):
        element = self.element_var.get()
        try:
            composition = float(self.composition_var.get())
            if element in PERIODIC_TABLE and 0 <= composition <= 100:
                if element not in self.selected_elements:
                    # Store composition in wt% internally
                    if self.composition_unit.get() == "at%":
                        composition = self.convert_composition(element, composition, "at%", "wt%")
                    self.selected_elements[element] = composition
                    self.tree.insert("", "end", values=(
                        element,
                        PERIODIC_TABLE[element]['name'],
                        f"{composition:.2f} {self.composition_unit.get()}"
                    ))
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
            # Update remaining compositions
            self.update_composition_display()
    
    def get_composition(self):
        # Return composition in the currently selected unit
        current_unit = self.composition_unit.get()
        return {element: self.convert_composition(element, comp, "wt%", current_unit)
                for element, comp in self.selected_elements.items()}

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
        self.root.geometry("800x600")  # Increased height for element selection
        self.root.withdraw()  # Hide main window initially
        
        # Set yellow background for main window
        self.root.configure(bg='yellow')
        
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
        
        # Radio buttons for calculation options
        self.calc_option = tk.StringVar(value="qbin")
        ttk.Radiobutton(options_frame, text="QΣbin", variable=self.calc_option, 
                       value="qbin").grid(row=0, column=0, padx=20, pady=10)
        ttk.Radiobutton(options_frame, text="Qture", variable=self.calc_option, 
                       value="qture").grid(row=0, column=1, padx=20, pady=10)
        ttk.Radiobutton(options_frame, text="Qmult", variable=self.calc_option, 
                       value="qmult").grid(row=0, column=2, padx=20, pady=10)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Calculate and Results buttons
        ttk.Button(buttons_frame, text="Calculate", command=self.calculate).grid(row=0, column=0, padx=10)
        ttk.Button(buttons_frame, text="Show Results", command=self.show_results).grid(row=0, column=1, padx=10)

    def show(self):
        self.root.deiconify()

    def calculate(self):
        # Get the selected elements and their compositions
        composition = self.element_selector.get_composition()
        calculation_type = self.calc_option.get()
        
        # Here you can add the actual calculation logic
        print(f"Calculating with:")
        print(f"Composition: {composition}")
        print(f"Calculation type: {calculation_type}")

    def show_results(self):
        # Add results display logic here
        print("Showing calculation results...")
        
    def open_pandat_import(self):
        # Create a new window for Pandat import
        import_window = tk.Toplevel(self.root)
        import_window.title("Pandat to ThermoQ")
        import_window.geometry("500x400")
        import_window.configure(bg='yellow')
        import_window.grab_set()  # Make window modal
        
        # Create frame for import controls
        import_frame = ttk.LabelFrame(import_window, text="Import Pandat Excel File", padding="10")
        import_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File selection
        file_frame = ttk.Frame(import_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=file_path_var, width=50)
        file_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        def browse_file():
            file_path = filedialog.askopenfilename(
                title="Select Pandat Excel File",
                filetypes=[("Excel files", "*.xlsx *.xls")]
            )
            if file_path:
                file_path_var.set(file_path)
                preview_data(file_path)
        
        browse_button = ttk.Button(file_frame, text="Browse", command=browse_file)
        browse_button.pack(side=tk.RIGHT, padx=5)
        
        # Preview area
        preview_frame = ttk.LabelFrame(import_frame, text="Preview", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create treeview for displaying preview data
        preview_tree = ttk.Treeview(preview_frame, show="headings", height=6)  # 减小高度
        preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=preview_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        preview_tree.configure(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame = ttk.Frame(import_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def import_data():
            file_path = file_path_var.get()
            if not file_path:
                tk.messagebox.showerror("Error", "Please select a file first!")
                return
                
            try:
                # Import data from Excel file
                import pandas as pd
                df = pd.read_excel(file_path, engine='xlrd')
                
                # Check if required columns exist
                if 'Element' not in df.columns or 'Amount' not in df.columns:
                    # Try to find columns with similar names
                    element_col = None
                    amount_col = None
                    
                    for col in df.columns:
                        if 'element' in col.lower() or 'comp' in col.lower():
                            element_col = col
                        if 'amount' in col.lower() or 'wt' in col.lower() or 'at' in col.lower() or '%' in col.lower():
                            amount_col = col
                    
                    if element_col is None or amount_col is None:
                        tk.messagebox.showerror("Error", "Could not find Element and Amount columns in the Excel file!")
                        return
                    
                    # Use the identified columns
                    elements_data = df[[element_col, amount_col]]
                    elements_data.columns = ['Element', 'Amount']
                else:
                    elements_data = df[['Element', 'Amount']]
                
                # Clear existing elements
                for item in self.element_selector.tree.get_children():
                    self.element_selector.tree.delete(item)
                self.element_selector.selected_elements.clear()
                
                # Add imported elements
                for _, row in elements_data.iterrows():
                    element = row['Element'].strip()
                    amount = float(row['Amount'])
                    
                    if element in PERIODIC_TABLE and 0 <= amount <= 100:
                        self.element_selector.selected_elements[element] = amount
                        self.element_selector.tree.insert("", "end", values=(
                            element,
                            PERIODIC_TABLE[element]['name'],
                            f"{amount:.2f} {self.element_selector.composition_unit.get()}"
                        ))
                
                tk.messagebox.showinfo("Success", f"Successfully imported {len(elements_data)} elements!")
                import_window.destroy()
                
            except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to import data: {str(e)}")
        
        def preview_data(file_path):
            try:
                # Read Excel file
                import pandas as pd
                df = pd.read_excel(file_path)
                
                # Clear existing columns
                for col in preview_tree["columns"]:
                    preview_tree.heading(col, text="")
                preview_tree["columns"] = ()
                
                # Clear existing items
                for item in preview_tree.get_children():
                    preview_tree.delete(item)
                
                # Configure columns
                columns = list(df.columns)
                preview_tree["columns"] = columns
                
                # Set column headings
                for col in columns:
                    preview_tree.heading(col, text=col)
                    preview_tree.column(col, width=100)
                
                # Add data rows (limit to first 10 rows)
                for i, row in df.head(10).iterrows():
                    values = [row[col] for col in columns]
                    preview_tree.insert("", "end", values=values)
                    
            except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to preview data: {str(e)}")
        
        import_button = ttk.Button(button_frame, text="Import", command=import_data)
        import_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=import_window.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)

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