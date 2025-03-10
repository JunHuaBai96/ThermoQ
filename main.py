import tkinter as tk
from tkinter import ttk, filedialog
import os

class ThermoQGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ThermoQ")
        self.root.geometry("600x350")  # Adjusted height
        
        # Configure grid weights for better layout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")  # Increased padding
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame grid weights
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Input file section
        ttk.Label(main_frame, text="Input File:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.input_path = tk.StringVar()
        input_entry = ttk.Entry(main_frame, textvariable=self.input_path, width=50)
        input_entry.grid(row=0, column=1, padx=10, pady=10, sticky=(tk.W, tk.E))
        ttk.Button(main_frame, text="Browse", command=self.browse_input).grid(row=0, column=2, padx=(5, 0), pady=10)
        
        # Calculation options frame
        options_frame = ttk.LabelFrame(main_frame, text="Calculation Options", padding="15")
        options_frame.grid(row=1, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E))
        
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
        buttons_frame.grid(row=2, column=0, columnspan=3, pady=20)
        
        # Calculate and Results buttons
        ttk.Button(buttons_frame, text="Calculate", command=self.calculate).grid(row=0, column=0, padx=10)
        ttk.Button(buttons_frame, text="Show Results", command=self.show_results).grid(row=0, column=1, padx=10)

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
    root = tk.Tk()
    app = ThermoQGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 