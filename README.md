# ThermoQ

## Description
ThermoQ is a powerful tool designed for extracting and analyzing thermodynamic data from TC databases. It provides a user-friendly graphical interface for calculating various Q-values including QΣbin, Qture, and Qmult, making it an essential tool for researchers and engineers working in chemical engineering, process optimization, and reaction analysis.

## Features
- Modern graphical user interface (GUI) for easy data processing
- Support for multiple calculation types:
  - QΣbin (Binary System Q-value)
  - Qture (Temperature-dependent Q-value)
  - Qmult (Multiple Component Q-value)
- File input/output functionality with support for text files
- Simple and intuitive calculation option selection
- Flexible input/output file path selection

## Installation
1. Ensure you have Python 3.x installed on your system
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Requirements
- Python 3.x
- tk==0.1.0

## Usage
1. Run the application:
```bash
python main.py
```

2. Using the GUI:
   - Click "Browse" to select your input file
   - Choose an output file location
   - Select the desired calculation type (QΣbin, Qture, or Qmult)
   - Click "Calculate" to process the data

## Documentation
The application provides a graphical interface with the following components:
- Input File Selection: Choose your source data file
- Output File Selection: Specify where to save the results
- Calculation Options: Select between QΣbin, Qture, and Qmult calculations
- Calculate Button: Process the data using selected options

## Contributing
We welcome contributions to ThermoQ! Please feel free to submit issues and pull requests.

## License
This project is licensed under the Mozilla Public License Version 2.0 - see the [LICENSE](LICENSE) file for details.

## Contact
For questions and support, please open an issue in the GitHub repository.

## Acknowledgments
- Contributors to the project
- The Python community
- The Tkinter GUI library team
