@echo off
cd /d "%~dp0"
echo Installation des dependances (la premiere fois seulement, ca peut prendre quelques minutes)...
python -m pip install -q ultralytics opencv-python
echo.
echo Lancement du test YOLO (q pour quitter)
python yolo_test.py %*
pause
