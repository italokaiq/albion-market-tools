@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 goto try_py
python launcher.py --diagnostico
pause
exit /b
:try_py
py -3 launcher.py --diagnostico
pause
