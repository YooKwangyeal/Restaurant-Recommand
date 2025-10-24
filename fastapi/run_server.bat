@echo off
echo Installing required packages...
pip install -r requirements.txt

echo.
echo Starting FastAPI server...
echo Server will be available at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.

python main.py