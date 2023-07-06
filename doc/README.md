PyRamanGUI
===================

# Table of Content
1. [Introduction](#introduction)
2. [Requirements and Installation](#requirements-and-installation)
   1. [Linux](#linux)
   2. [Windows](#windows)
3. [The Interface](#the-interface)
   1. [Main Window](#main-window)
   2. [Spreadsheet](#spreadsheet-img-srcpicsiconspreadsheetpng-alticon-of-spreadsheet-height20)
   3. [Text Window](#text-window-img-srcpicsicontextwindowpng-alticon-of-textwindow-height20)
   4. [Plot Window](#plot-window-img-alticon-of-plotwindow-height20-srcpicsiconplotwindowpng)

# Introduction

PyRamanGUI is a free and open-source tool to process Raman spectra. 
The source code is written in Python, the GUI is based on PyQt5.
    
# Requirements and Installation
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

## Linux
On **Linux** (Ubuntu, Debian) the packages can be installed with following command:
```
pip install matplotlib==3.7.0 numpy==1.24.2 prettytable==3.6.0 pybaselines==1.0.0 pyqt5==5.15.9 pyside2==5.15.2.1 rampy==0.4.9 scipy==1.10.1 scikit-learn==1.2.1 
```
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
On **Windows** with Anaconda:
Install [Anaconda](https://www.anaconda.com/products/distribution). 

Open the Anaconda Command Prompt (CMD.exe Prompt)

Run as administrator
```
pip install --user matplotlib==3.7.0 numpy==1.24.2 prettytable==3.6.0 pybaselines==1.0.0 pyqt5==5.15.9 pyside2==5.15.2.1 rampy==0.4.9 scipy==1.10.1 scikit-learn==1.2.1 
```


Download the PyRamanGUI directory. To run PyRamanGUI, go in the directory src and double-click the 'WindowsRun.bat' file

Alternative: Open the Anaconda Command Prompt and run 
```
python my/path/src/PyRamanGUI.py
```

# The Interface

## Main window
The structure of the PyRamanGUI is remotely based on OriginLab. 
The GUI consists of three main parts, which are framed in the
following picture; a menu bar at the top, a side tree at the 
left, and a workspace containing the open subwindows.

<img src="pics/Example_Mainwindow.png" alt="Main window" width="400"/>

### Workspace
The workspace contains the windows. There are three different kinds of windows,
[Spreadsheet <img src="pics/Icon_spreadsheet.png" alt="Icon of Spreadsheet" height="15"/>](#spreadsheet), 
[Plotwindow <img src="pics/Icon_plotwindow.png" alt="Icon of Plotwindow" height="15"/>](#plot-window),
[Textwindow <img src="pics/Icon_textwindow.png" alt="Icon of Textwindow" height="15"/>](#text-window).
They are explained in more detail in later sections.

### Side bar
The side bar contains the project structure. 
The subwindows are organized in folders, so the workspace only
shows the subwindows of the selected folder. You can switch between 
folders by double-clicking at another folder at the side tree or by 
changing the tab of the workspace.

### Menu bar
The menu bar of the main window contains the drop-down menus "File", "Edit" and "Tools". 
In addition to the main window menu bar, each subwindow has its own menu bar

### Open and Save a PyRamanGUI Project
A project can be saved and reloaded via the menu item "File". The projects are 
saved as JSON-file, which all got the file-ending .jrmn.
A project can also be saved with the shortcut "CTRL+S".

<img src="pics/Open_Save_Project.PNG" width="200"/>

### Open a new Window or Folder in the Project
There are two ways to open a new folder or window. 
The first one is to use the menu bar item "File" ->; "New" and the second one is to 
right-click on the side tree. 
The new window then opens in the opened folder.


##  Spreadsheet <img src="pics/Icon_spreadsheet.png" alt="Icon of Spreadsheet" height="20"/>
<img src="pics/Example_Table.PNG" width="200"/>

The spreadsheet contains the data in a table, which can either be loaded ("File"
&rarr; "Load Data") or filled in manually.\
A new column can be added with "Edit" &rarr; "New Column".
\
The header of the table consists of a column title and 5 rows 
("Name", "Axis", "Unit", "Comments", "F(x)").
\
By right-clicking on the column title, a drop-down menu is opened.

### How to work with a Spreadsheet
#### Load data
Open a spreadsheet and click "File"->"Load Data" in the menu bar. In the open data 
import menu, you can select the path to the file to load and other basic 
import options.

<img src="pics/LoadData.png" width="200"/>

#### Plot data
In order to plot the loaded data, there have to be at least two columns. Each column 
can be of the type "X", "Y" or "Yerr". To plot data, select one or several column 
with the type "Y".
The data can be plotted over the drop-down menu or the menu bar at the top. 
As x-values, automatically the associated columned with type "X" (the closest column 
to the left) is selected.

### Functionalities
There are further functionalities, which can be used in the Spreadsheet. They can be 
found over the menubar or by right-click on the column header. These functionalities 
include:
- Move a column one to the right, one to the left or to the end/ beginning of the 
spreadsheet
- Delete a column
- Change the type of column
- Flip a column
- Convert units: if values in the selected column are in units of wavenumbers, 
they can be converted to a wavelength and vice versa.
- Resample: create a new x-axis for selected "Y" columns
- Principal component analysis (PCA)
- Non-negative matrix factorization (NMF)

The resampling, PCA and NMF are explained later in more detail.

#### Resampling new x-axis

#### PCA and NMF

## Text Window <img src="pics/Icon_textwindow.png" alt="Icon of Textwindow" height="20"/>
<img src="pics/Example_TextWindow.PNG" width="200"/>

The text window offers an opportunity to take notes and document a project.
The text can be saved into a .txt file or loaded from one.

##  Plot Window <img alt="Icon of Plotwindow" height="20" src="pics/Icon_plotwindow.png"/>
<img src="pics/Example_PlotWindow.PNG" width="200"/>

The plot window is the most complex of the three windows.

### Toolbar
<img src="pics/PlotWindow_toolbar.png" width="200"/>

The first five tools help with navigation:

- house: restore original view
- left arrow: undo view
- right arrow: redo view
- arrow cross:
  - left click + mouse movement: move plot
  - right click + mouse movement: scaling
- magnifier: zoom in

- The slide controller button opens a dialogue window to adjust the spacing 
at the left, right, bottom, and top of the plot.
- The indented arrow button opens a dialogue with the figure options, e.g., 
for renaming the labels, changing colors, repositioning the legend.
- The disc button allows for saving a picture of the plot as an image file 
(.png, .jpg., .eps, .pdf, ...)


### Sidebar

<img src="pics/PlotWindow_sidebar.PNG" height="80"/> 

- The first symbol (mouse cursor) plots a movable vertical line in the spectrum, 
which can be used, e.g., to compare peak positions. The vertical line disappears
if the symbol on the sidebar is clicked again or the right mouse button is pressed.
- With the second and third symbol (upwards arrows), the shown spectra can be scaled 
or shifted with respect to the y-axis.
- The fourth symbol (narrow arrow) allows for drawing lines and arrows in the spectrum.
These lines and arrows can be edited later via an option dialogue, which opens 
with a right mouse click.
- The fifth symbol (upper-case T) creates a text field in the spectrum. The text
can be changed by double-clicking and the style can be adjusted by a right mouse click
on the inserted text.

### Functionalities

#### Delete single data point

#### Remove cosmic spike

#### Set new limits

#### Normalization

#### Add up or subtract two spectra

#### Baseline correction

#### Smoothing

#### Peak Fitting
There are two peak fitting options. The quick fit and via the Fit Dialog.

For both first a dialog opens, which ask for the dataset, which should be fitted? \
Then two red lines appear. By dragging them to the wanted position, the 
fit region can be chosen. \

<img src="pics/Fit_Dialog.png" width="300"/>

The fitdialog consists of a menubar, four buttons:
- Add Function: add fit function 
- Remove Function: remove fit function 
- Apply: Plot functions spectrum with given parameter 
- Fit: Fit parameters to selected spectrum 

and a table: \
In the left column a fit function can be selected:
- Lorentzian
- Gaussian
- Breit-Wigner-Fano
- Voigtian
- Pseudo-Voigtian

The other columns are used to enter values for the fit parameters, 
the lower and the upper boundary limit.




