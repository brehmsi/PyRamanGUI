# PyRamanGUI - A general purpose Raman evaluation tool 
  - Author: Simon Brehm (Email: simon.brehm@physik.tu-freiberg.de) 
  - Coding language: Python 

# Description
Provides a general purpose tool for Raman spectra evaluation
  - structure similar to Origin 
  - use of spreadsheets and plotting windows
  - projects can be saved and loaded
  - general-purpose background fitting procedure
  - increased reproducibility of fitting processes 
  
A tutorial on how to use PyRamanGUI can be found here [Tutorial](doc/README.md)

# Requirements
PyRamanGUI requires:
  - [python](https://www.python.org/downloads/) >= 3.6
  
The following python packages have to be installed:
  - matplotlib
  - numpy
  - prettytable
  - pybaselines
  - PyQt5
  - rampy
  - scipy
  - sklearn

On **Linux** (Ubuntu, Debian) a package can be installed with following command:
```
pip install matplotlib numpy prettytable pybaselines pyqt5 pyside2 rampy scipy scikit-learn tabulate
```


On **Windows** with Anaconda:
Install [Anaconda](https://www.anaconda.com/products/distribution). Make sure to enable the 'Add Anaconda to the system 
PATH environment variable' box during installation. Otherwise, PyRamanGUI cannot find the python executable installed 
by Anaconda.

Open the Anaconda Command Prompt (CMD.exe Prompt)

Change the directory with the command
```
 cd\
```
Run as administrator
```
pip install --user matplotlib numpy prettytable pybaselines pyqt5 pyside2 rampy scipy scikit-learn tabulate
```

# Installation
## Linux
Open a terminal and go to the directory where you want to clone the files.
Run the following command. Git automatically creates a folder with the repository name and downloads the files there.
```
git clone https://gitlab.com/brehmsi/PyRamanGUI.git
```

Change directory to source files
```
cd pyramangui/src
```


Run PyRamanGUI
```
python3 pyramangui.py
```

## Windows


Copy the PyRamanGUI directory to a path you have chosen. To run PyRamanGUI, double-click the 'WindowsRun.bat' file

# License
This project is licensed under the Apache License 2.0   
See [LICENSE](LICENSE) for details.
