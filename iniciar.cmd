@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 goto try_py
python launcher.py
if errorlevel 1 pause
exit /b
:try_py
where py >nul 2>nul
if errorlevel 1 goto missing
py -3 launcher.py
if errorlevel 1 pause
exit /b
:missing
echo Instale Python 3.12 ou superior, com Tkinter e a opcao Add Python to PATH.
pause
