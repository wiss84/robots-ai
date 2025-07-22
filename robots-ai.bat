@echo off
echo Starting backend...

CALL "%USERPROFILE%\anaconda3\Scripts\activate.bat" cs_agent
start cmd /k "CALL %USERPROFILE%\anaconda3\Scripts\activate.bat cs_agent && cd %USERPROFILE%\Desktop\robots-ai\robots_backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug"


timeout /t 5
echo Starting frontend...

cd %USERPROFILE%\Desktop\robots-ai\robots_frontend
start cmd /k "npm run dev"

timeout /t 5
start "" "http://localhost:5173/"

