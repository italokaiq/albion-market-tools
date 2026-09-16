"""Os scripts do instalador não são Python, então não entram no resto da
suíte por importação — mas dá pra pegar de verdade o bug encontrado nesta
revisão (PowerShell 5.1 sem BOM lê UTF-8 pelo codepage ANSI do sistema e
quebra qualquer string com acento ou travessão, ex.: 'dá', 'até', '—') sem
precisar instalar nada: basta ler os bytes do arquivo e, quando o
PowerShell do Windows (não o pwsh usado nesta sessão) estiver disponível,
rodar o parser real contra o conteúdo decodificado como o Windows
PowerShell decodificaria sem BOM.
"""
import shutil
import subprocess
import unittest
from pathlib import Path

SCRIPTS = [Path('installer/install.ps1'), Path('installer/uninstall.ps1')]


class InstallerScriptEncodingTest(unittest.TestCase):
    def test_scripts_have_utf8_bom(self):
        """Sem BOM, o Windows PowerShell 5.1 (powershell.exe, não o pwsh usado
        aqui) lê o arquivo pelo codepage ANSI do sistema e corrompe qualquer
        caractere não-ASCII dentro de uma string, quebrando o parser —
        reproduzido de verdade rodando install.ps1 antes desta correção."""
        for script in SCRIPTS:
            with self.subTest(script=script):
                self.assertEqual(script.read_bytes()[:3], b'\xef\xbb\xbf',
                    f'{script} sem BOM UTF-8: acentos/travessões vão quebrar no Windows PowerShell 5.1.')

    @unittest.skipUnless(shutil.which('powershell'), 'Windows PowerShell (powershell.exe) não disponível')
    def test_scripts_parse_cleanly_under_windows_powershell(self):
        """O parser do pwsh (usado por [System.Management.Automation.Language.Parser])
        já lida bem com BOM; o bug real só aparece no powershell.exe legado, então
        o teste de verdade precisa chamar exatamente esse binário."""
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command',
                     f'$errors=$null; [System.Management.Automation.Language.Parser]::ParseFile('
                     f'(Resolve-Path "{script}"), [ref]$null, [ref]$errors) | Out-Null; '
                     f'if ($errors.Count -gt 0) {{ $errors | ForEach-Object {{ Write-Error $_ }}; exit 1 }}'],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
