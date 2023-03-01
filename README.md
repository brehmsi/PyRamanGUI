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
  - matplotlib (3.5.3)
  - numpy (1.12.3)
  - prettytable (3.3.0)
  - pybaselines (0.8.0)
  - PyQt5 (5.15.7)
  - rampy (0.4.9)
  - scipy (1.10.0)
  - sklearn (1.0.2)

It may also work with other versions, but it has been tested only with these.

On **Linux** (Ubuntu, Debian) a package can be installed with following command:
```
pip install matplotlib==3.5.3 numpy==1.12.1 prettytable==3.3.0 pybaselines==0.8.0 pyqt5==5.15.7 pyside2 rampy==0.4.9 scipy==1.10.0 scikit-learn==1.0.2 
```


On **Windows** with Anaconda:
Install [Anaconda](https://www.anaconda.com/products/distribution). 

Open the Anaconda Command Prompt (CMD.exe Prompt)

Run as administrator
```
pip install --user matplotlib==3.5.3 numpy==1.12.1 prettytable==3.3.0 pybaselines==0.8.0 pyqt5==5.15.7 pyside2 rampy==0.4.9 scipy==1.10.0 scikit-learn==1.0.2 
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

# License
This project is licensed under the Apache License 2.0   
See [LICENSE](LICENSE) for details.
