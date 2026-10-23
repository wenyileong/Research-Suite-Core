@echo off
rem Build ResearchSuite.exe locally on Windows (Python 3.11 or later with tkinter, as from python.org).
rem The same steps run on GitHub's Windows runners: see .github\workflows\build-windows.yml.
setlocal
cd /d "%~dp0"

python -m pip install --upgrade "pyinstaller>=6.10,<7" "pytest>=8" || goto :error
python -m pytest -q || goto :error
pyinstaller --noconfirm --clean packaging\research_suite.spec --distpath dist --workpath build || goto :error

if not exist release mkdir release
copy /y dist\ResearchSuite.exe release\ >nul || goto :error
copy /y packaging\READ_ME_FIRST.txt release\ >nul || goto :error
copy /y LICENSE release\LICENSE.txt >nul || goto :error
python packaging\third_party_notices.py release\THIRD_PARTY_NOTICES.txt || goto :error

echo.
echo Built release\ResearchSuite.exe
exit /b 0

:error
echo.
echo Build failed.
exit /b 1
