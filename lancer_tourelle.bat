@echo off
cd /d "%~dp0"
echo Installation des dependances (premiere fois seulement)...
python -m pip install -q ultralytics opencv-python pyserial
echo.
echo Interface : http://localhost:8082  (clic sur une personne = cible, Ctrl+C pour arreter)
start "" cmd /c "timeout /t 12 >nul & start http://localhost:8082"
python tracker_v2.py --source 0 --backend opencv --size 1280x720 %*
pause
