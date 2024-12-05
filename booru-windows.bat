@echo off
IF NOT EXIST "venv" (
    REM Create and activate virtual environment
    python -m venv venv
    call venv\Scripts\activate

    REM Install requirements
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate.bat
)

REM Run Flask server
app.py
pause