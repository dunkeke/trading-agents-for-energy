@echo off
setlocal
cd /d "%~dp0streamlit_app"
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
python -m streamlit run offline_app.py --server.address 127.0.0.1 --server.port 8501
