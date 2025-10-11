@echo off
REM ========================================
REM MCP Mail Server - Windows Executable Builder
REM ========================================

echo ========================================
echo MCP Mail Query Server - Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Checking Python installation...
python --version
echo.

REM Install PyInstaller if not already installed
echo [2/5] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller
    pause
    exit /b 1
)
echo.

REM Install project dependencies
echo [3/5] Installing project dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Some dependencies may have failed to install
    echo This might cause issues in the built executable
)
echo.

REM Clean previous build
echo [4/5] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
echo Previous build cleaned
echo.

REM Build executable using spec file
echo [5/5] Building executable...
pyinstaller build_exe.spec
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)
echo.

echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\mcp_mail_server.exe
echo.
echo To run the server:
echo   HTTP mode:  dist\mcp_mail_server.exe --mode http --port 3000
echo   STDIO mode: dist\mcp_mail_server.exe --mode stdio
echo.
echo Press any key to exit...
pause >nul
