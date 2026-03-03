import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

def run():
    # Asegurar que src está en PYTHONPATH para el backend
    os.environ["PYTHONPATH"] = os.path.join(ROOT, "src")
    
    # 1. Levantar Backend (FastAPI)
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "atlas.server:build_app",
         "--host", "127.0.0.1", "--port", "8001", "--reload"],
        cwd=ROOT
    )
    
    # 2. Levantar Frontend (Vite)
    subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=os.path.join(ROOT, "src", "atlas", "frontend"),
        shell=True
    )

if __name__ == "__main__":
    print("🚀 TEAM ATLAS: Iniciando sistema (Backend: 8001, Frontend: Vite)...")
    run()