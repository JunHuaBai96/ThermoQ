import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import os
import time

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
            
            # Create and pack splash image label
            splash_label = tk.Label(self.splash_root, image=self.splash_photo, bg='black')
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
        self.root.geometry("800x400")  # Increased width for logo
        self.root.withdraw()  # Hide main window initially
        
        # Set window icon
        try:
            icon_path = "images/Simplified logo.png"
            icon_image = Image.open(icon_path)
            # Convert to .ico format for window icon
            icon_photo = ImageTk.PhotoImage(icon_image)
            self.root.iconphoto(True, icon_photo)
            # Keep a reference to prevent garbage collection
            self.icon_photo = icon_photo
        except Exception as e:
            print(f"Error loading window icon: {e}")
        
        # Configure grid weights for better layout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame grid weights
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Logo section
        try:
            # Load and resize logo
            logo_img = Image.open("images/Simplified logo.png")
            logo_size = (100, 100)  # Set desired size
            logo_img = logo_img.resize(logo_size, Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            
            # Create and place logo label
            logo_label = ttk.Label(main_frame, image=self.logo_photo)
            logo_label.grid(row=0, column=0, rowspan=2, padx=(0, 20), pady=10)
        except Exception as e:
            print(f"Error loading logo: {e}")
        
        # Right side frame for input and options
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.grid_columnconfigure(1, weight=1)
        
        # Input file section
        ttk.Label(right_frame, text="Input File:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.input_path = tk.StringVar()
        input_entry = ttk.Entry(right_frame, textvariable=self.input_path, width=50)
        input_entry.grid(row=0, column=1, padx=10, pady=10, sticky=(tk.W, tk.E))
        ttk.Button(right_frame, text="Browse", command=self.browse_input).grid(row=0, column=2, padx=(5, 0), pady=10)
        
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
        self.root.deiconify()  # Show the main window

    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filename:
            self.input_path.set(filename)

    def calculate(self):
        # Get the selected values
        input_file = self.input_path.get()
        calculation_type = self.calc_option.get()
        
        # Here you can add the actual calculation logic
        print(f"Calculating with:")
        print(f"Input file: {input_file}")
        print(f"Calculation type: {calculation_type}")

    def show_results(self):
        # Add results display logic here
        print("Showing calculation results...")

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