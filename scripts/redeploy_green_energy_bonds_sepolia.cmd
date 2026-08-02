@echo off
setlocal
cd /d "%~dp0.."

echo ====================================================
echo STARTING GREENBOND26 + ENERGYBOND26 REDEPLOY
echo ====================================================

call node_modules\.bin\hardhat.cmd --network sepolia run scripts\redeploy_green_energy_bonds_sepolia.js
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
    echo.
    echo REDEPLOY FAILED WITH EXIT CODE %EXIT_CODE%
    exit /b %EXIT_CODE%
)

echo.
echo REDEPLOY COMMAND COMPLETED SUCCESSFULLY
exit /b 0
