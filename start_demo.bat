@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" goto :have_venv

echo [INFO] venv not found, creating virtualenv (requires Python 3.12)...
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 goto :make_with_py
python -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>&1
if not errorlevel 1 goto :make_with_python

echo [ERROR] Python 3.12 is required but was not found, or the default python is not 3.12.x.
echo Please install Python 3.12 and make sure "py -3.12" works, then run this script again.
pause
exit /b 1

:make_with_py
py -3.12 -m venv venv
goto :after_create

:make_with_python
python -m venv venv
goto :after_create

:after_create
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] failed to create venv with Python 3.12.
    pause
    exit /b 1
)
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -e ".[ui]"
if errorlevel 1 (
    echo [ERROR] dependency install failed.
    pause
    exit /b 1
)

:have_venv
set CIPM_MOCK=1
set CIPM_RUNTIME=local

echo Starting CIPM-MAS frontend and backend...
start "CIPM-MAS Demo" cmd /c "venv\Scripts\python.exe ops\start_dev.py"
timeout /t 4 >nul
start "" "http://127.0.0.1:8501"

echo.
echo Dashboard: http://127.0.0.1:8501
echo API docs:  http://127.0.0.1:8000/docs
echo.
echo Keep the "CIPM-MAS Demo" console window open while using the system.
exit /b 0