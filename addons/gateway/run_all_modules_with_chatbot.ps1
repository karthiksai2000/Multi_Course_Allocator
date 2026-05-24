$ErrorActionPreference = "Stop"

Write-Host "Starting existing modules and chatbot sidecars..."

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\..\backend'; python backend_api.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\..\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\lifeskill_chatbot_service'; pip install -r requirements.txt; python main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\dept_chatbot_app'; pip install -r requirements.txt; streamlit run streamlit_chat.py --server.port 8511 --server.headless=true"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\dual_chatbot_app'; pip install -r requirements.txt; streamlit run streamlit_chat.py --server.port 8512 --server.headless=true"

Write-Host "Started. URLs:"
Write-Host "- Existing Frontend: http://localhost:5173"
Write-Host "- Existing LifeSkill API: http://localhost:8000"
Write-Host "- New LifeSkill Chatbot API: http://localhost:8010"
Write-Host "- New Single Course Chatbot UI: http://localhost:8511"
Write-Host "- New Dual Course Chatbot UI: http://localhost:8512"
