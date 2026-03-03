$repo = "C:\Users\gdgar\MisProyectosVSCode\TEAM_ATLAS"

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd `"$repo`"; .\venv\Scripts\Activate.ps1; python -m pip install -U pip; pip install -r requirements.txt; python -m uvicorn atlas.api.main:app --reload --host 127.0.0.1 --port 8001 --app-dir src"
)

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd `"$repo\src\atlas\frontend`"; npm install; npm run dev -- --host 127.0.0.1 --port 3000"
)