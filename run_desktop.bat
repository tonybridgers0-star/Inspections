@echo off
cd /d %~dp0

if not exist backend\.venv (
  py -3.11 -m venv backend\.venv
)

call backend\.venv\Scripts\activate
pip install -r backend\requirements.txt
pip install -r desktop\requirements.txt

python desktop\launcher.py
