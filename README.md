# PyRamanGUI - A general purpose Raman analysis tool 
  - Author: Simon Brehm (Email: simon.brehm@physik.tu-freiberg.de) 
  - Coding language: Python 

# Description
Provides a general purpose tool for Raman spectra evaluation
  - constructed as graphical user interface (GUI)
  - use of spreadsheets, plots, and text windows
  - projects can be saved and loaded
  - offeres a variety of analysis methods like peak fitting, baseline correction, smoothing or cosmic spike removal
  
A tutorial on how to use PyRamanGUI can be found here [Tutorial](doc/README.md)

# Requirements
PyRamanGUI requires:
  - [python](https://www.python.org/downloads/) >= 3.10
  
The following python packages have to be installed:
  - matplotlib (3.7.0)
  - numpy (1.24.2)
  - prettytable (3.6.0)
  - pybaselines (1.0.0)
  - PyQt5 (5.15.9)
  - PySide2 (5.15.2.1)
  - rampy (0.4.9)
  - scipy (1.10.1)
  - sklearn (1.2.1)

It may also work with other versions, but it has been tested only with these.

On **Linux** (Ubuntu, Debian) a package can be installed with following command:
```
pip install matplotlib==3.7.0 numpy==1.24.2 prettytable==3.6.0 pybaselines==1.0.0 pyqt5==5.15.9 pyside2==5.15.2.1 rampy==0.4.9 scipy==1.10.1 scikit-learn==1.2.1 
```


On **Windows** with Anaconda:
Install [Anaconda](https://www.anaconda.com/products/distribution). 

Open the Anaconda Command Prompt (CMD.exe Prompt)

Run as administrator
```
pip install --user matplotlib==3.7.0 numpy==1.24.2 prettytable==3.6.0 pybaselines==1.0.0 pyqt5==5.15.9 pyside2==5.15.2.1 rampy==0.4.9 scipy==1.10.1 scikit-learn==1.2.1 
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
python3 PyRamanGUI.py
```

## Windows

Download the PyRamanGUI directory. To run PyRamanGUI, go in the directory src and double-click the 'WindowsRun.bat' file

Alternative: Open the Anaconda Command Prompt and run 
```
python my/path/src/PyRamanGUI.py
```

# License
This project is licensed under the Apache License 2.0   
See [LICENSE](LICENSE) for details.
