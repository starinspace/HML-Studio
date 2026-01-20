@echo off
chcp 65001 >nul
TITLE HeartMuLa Studio - AI Music Generator
echo ================================================
echo    HeartMuLa Studio - Music Generation GUI
echo ================================================
echo.
echo Activating conda environment 'heartlib'...
call conda activate heartlib
if %errorlevel% neq 0 (
    echo ERROR: Could not activate 'heartlib' environment.
    echo Please make sure Anaconda/Miniconda is installed
    echo and the 'heartlib' environment exists.
    pause
    exit /b 1
)
echo Environment activated successfully!
echo.
echo Starting HeartMuLa Studio GUI...
echo ================================================
echo.
python gui.py
if %errorlevel% neq 0 (
    echo.
    echo An error occurred while running the GUI.
    echo Please check that all dependencies are installed:
    echo    pip install -r requirements.txt
    pause
)
pause
