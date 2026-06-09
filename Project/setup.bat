@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" was not found.
  echo Install Python from https://www.python.org/downloads/ and enable the py launcher.
  exit /b 1
)

py -m pip install -r requirements.txt
