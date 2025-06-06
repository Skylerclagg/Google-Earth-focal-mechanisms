@echo off
TITLE Python Dependencies Installer for NDK to KML Converter

echo This script will install the Python libraries required for the NDK to KML converter.
echo.
echo Installing packages: tqdm, simplekml, obspy, matplotlib...
echo This may take a few minutes. Please wait.
echo.

rem This command calls pip to install all required libraries.
pip install tqdm simplekml obspy matplotlib

echo.
echo ====================================================================
echo.
echo Installation complete!
echo. 
echo If you saw any major errors (usually in RED text), please take a screenshot.
echo Otherwise, you can now close this window and proceed with running the main Python script.
echo.
echo ====================================================================
echo.
pause
