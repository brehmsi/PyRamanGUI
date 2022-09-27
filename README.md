# PyRamanGui - A general purpose Raman evaluation tool 
  - Author: Simon Brehm (Email: simon.brehm@physik.tu-freiberg.de) 
  - Coding language: Python 

# Description
Provides a general purpose tool for Raman spectra evaluation
  - structure similar to Origin 
  - use of spreadsheets and plotting windows
  - projects can be saved and loaded
  - general-purpose background fitting procedure
  - increased reproducibility of fitting processes 
  
A tutorial on how to use PyRamanGui can be found here [Tutorial](doc/README.md)

# Installation
## Linux
Copy the PyRamanGui directory to a path you have chosen. 
Run 'python3 .../src/PyRamanGui.py'

## Windows
Install [Anaconda](https://www.anaconda.com/products/distribution). Make sure to enable the 'Add Anaconda to the system 
PATH environment variable' box during installation. Otherwise, PyRamanGui can't find the python executable installed 
by Anaconda.

Copy the PyRamanGui directory to a path you have chosen. To run PyRamanGui double-click the 'WindowsRun.bat' file

# Requirements
PyRamanGui requires:
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
  - sympy

On **Linux** (Ubuntu, Debian) a package can be installed with following command:
```
sudo apt-get install matplotlib numpy prettytable pybaselines PyQt5 rampy scipy scikit-learn sympy
```


On **Windows** with Anaconda:

Open Anaconda. Click on 'Environments' ond the left sidebar. Select 'Not installed' in the drop-down menu
Check all the boxes for the needed packages and click 'Apply'.

# License
This project is licensed under the Apache License 2.0   
See [LICENSE](LICENSE) for details.
