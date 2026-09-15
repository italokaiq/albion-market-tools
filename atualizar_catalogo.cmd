@echo off
cd /d "%~dp0"
echo Verificando e baixando atualizacoes dos catalogos publicos (ao-bin-dumps)...
echo Isso roda a partir do codigo-fonte; se voce usa o .exe, rode build_exe.cmd
echo de novo depois para gerar uma versao atualizada dele.
echo.
python catalog_updater.py
echo.
pause
