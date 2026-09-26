@echo off
title AuthDoc - Identity Verification System
echo =====================================================================
echo  🛡️  AUTHDOC: BORDER SECURITY & IDENTITY VERIFICATION SYSTEM
echo =====================================================================
echo.
echo Installing / checking dependencies...
python -m pip install -r requirements.txt
echo.
echo Starting FastAPI application server...
echo Access the Interactive Dashboard at: http://localhost:8000
echo.
python main.py
pause
