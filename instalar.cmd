@echo off
cd /d "%~dp0"
if not exist "dist\AlbionMercadoAmericas.exe" (
  echo Executavel nao encontrado em dist\AlbionMercadoAmericas.exe.
  echo Rode build_exe.cmd primeiro para gerar o programa.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "installer\install.ps1"
pause
