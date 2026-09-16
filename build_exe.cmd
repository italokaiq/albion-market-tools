@echo off
cd /d "%~dp0"
echo Instalando PyInstaller (se necessario)...
python -m pip install --quiet pyinstaller
if errorlevel 1 goto fail

echo Gerando AlbionMercadoAmericas.exe...
python -m PyInstaller --onefile --name AlbionMercadoAmericas --noconfirm ^
  --add-data "items.json;." ^
  --add-data "world.json;." ^
  --add-data "recipes.json;." ^
  --add-data "recipes_source.json;." ^
  --add-data "market_items.json;." ^
  --add-data "upgrade_costs.json;." ^
  --add-data "VERSION;." ^
  launcher.py
if errorlevel 1 goto fail

echo.
echo Pronto: dist\AlbionMercadoAmericas.exe
echo Copie esse arquivo para a pasta onde o programa vai rodar (ele cria
echo mercado.sqlite3, preferencias.json, historico.json etc. ao lado dele).
pause
exit /b 0

:fail
echo Falha ao gerar o executavel. Veja as mensagens acima.
pause
exit /b 1
