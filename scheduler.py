import os
import time
import schedule
from main import run_ingestion_cycle
from services.logging_service import log_event

def job():
    log_event("SCHEDULER", "Starting automated news ingestion cycle...")
    try:
        run_ingestion_cycle()
        log_event("SCHEDULER", "Automated news ingestion cycle completed successfully.")
    except Exception as e:
        log_event("SCHEDULER_ERROR", f"Error during automated ingestion: {str(e)}", level="ERROR")

def main():
    log_event("SCHEDULER_START", "Starting background scheduler. Ingestion will run every 30 minutes.")
    
    # Run once immediately on startup
    job()
    
    # Schedule to run every 30 minutes
    schedule.every(30).minutes.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
