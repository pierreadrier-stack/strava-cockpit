@echo off
echo ================================================
echo   Running Cockpit - Installation des dependances
echo ================================================
echo.

REM Verifier si Python est accessible
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas trouve dans le PATH.
    echo.
    echo Installe Python depuis https://www.python.org/downloads/
    echo IMPORTANT : Coche "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python detecte :
python --version
echo.

echo Installation des bibliotheques...
pip install streamlit pandas plotly numpy

echo.
echo ================================================
echo   Installation terminee !
echo   Lance maintenant : lancer_app.bat
echo ================================================
pause
