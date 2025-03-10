import tkinter as tk
from tkinter import ttk, filedialog
import os

class ThermoQGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ThermoQ")
        self.root.geometry("600x400")
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input file section
        ttk.Label(main_frame, text="Input File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_path = tk.StringVar()
        input_entry = ttk.Entry(main_frame, textvariable=self.input_path, width=50)
        input_entry.grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_input).grid(row=0, column=2)
        
        # Output file section
        ttk.Label(main_frame, text="Output File:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_path = tk.StringVar()
        output_entry = ttk.Entry(main_frame, textvariable=self.output_path, width=50)
        output_entry.grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output).grid(row=1, column=2)
        
        # Calculation options frame
        options_frame = ttk.LabelFrame(main_frame, text="Calculation Options", padding="10")
        options_frame.grid(row=2, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E))
        
        # Radio buttons for calculation options
        self.calc_option = tk.StringVar(value="qbin")
        ttk.Radiobutton(options_frame, text="QΣbin", variable=self.calc_option, 
                       value="qbin").grid(row=0, column=0, padx=20)
        ttk.Radiobutton(options_frame, text="Qture", variable=self.calc_option, 
                       value="qture").grid(row=0, column=1, padx=20)
        ttk.Radiobutton(options_frame, text="Qmult", variable=self.calc_option, 
                       value="qmult").grid(row=0, column=2, padx=20)
        
        # Calculate button
        ttk.Button(main_frame, text="Calculate", command=self.calculate).grid(row=3, column=1, pady=20)

    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filename:
            self.input_path.set(filename)

    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="Select Output File",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            defaultextension=".txt"
        )
        if filename:
            self.output_path.set(filename)

    def calculate(self):
        # Get the selected values
        input_file = self.input_path.get()
        output_file = self.output_path.get()
        calculation_type = self.calc_option.get()
        
        # Here you can add the actual calculation logic
        print(f"Calculating with:")
        print(f"Input file: {input_file}")
        print(f"Output file: {output_file}")
        print(f"Calculation type: {calculation_type}")

def main():
    root = tk.Tk()
    app = ThermoQGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 