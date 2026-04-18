@echo off
cd /d "C:\Users\saya\Desktop\Daily"

:: 絵文字などUnicode文字を含む予定があってもクラッシュしないようにUTF-8を強制
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

"C:\Python313\python.exe" main.py >> logs\run.log 2>&1

