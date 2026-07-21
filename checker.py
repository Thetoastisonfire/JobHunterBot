"""Thin wrapper so `python checker.py` behaves exactly as before.
All logic now lives in the job_alert_bot/ package."""
from Main_Code.main import run

if __name__ == "__main__":
    run()
