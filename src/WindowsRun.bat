set mypath=%cd%
cd ..\..
where /q pyw
IF ERRORLEVEL 1 (
    ECHO 'pyw' is missing, try 'pythonw'
    where /q pythonw
    IF ERRORLEVEL 1 (
        ECHO 'pythonw' also missing. Abort.
    ) ELSE (
       start pythonw "%mypath%"\PyRamanGui.py
    )
) ELSE (
    start pyw "%mypath%"\PyRamanGui.py
)
