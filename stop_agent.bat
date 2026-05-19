@echo off
echo 텔레그램 인사이트 에이전트를 종료합니다...
taskkill /IM pythonw.exe /F
taskkill /IM python.exe /FI "WINDOWTITLE eq 텔레그램 인사이트*" /F
echo 종료 완료!
pause
