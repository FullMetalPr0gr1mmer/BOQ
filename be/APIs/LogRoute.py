from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from APIs.Core import get_db
from Models.Log import Log
from Schemas.LogSchema import LogCreate, LogOut

logRouter = APIRouter(tags=["Logs"])


@logRouter.post("/create-log", response_model=LogOut)
def create_log(log_data: LogCreate, db: Session = Depends(get_db)):
    """Create a new log entry."""
    new_log = Log(
        user=log_data.user,
        log=log_data.log,
        timestamp=datetime.utcnow()
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log


@logRouter.get("/get-logs", response_model=list[LogOut])
def get_all_logs(db: Session = Depends(get_db)):
    """Retrieve all log entries."""
    logs = db.query(Log).order_by(Log.timestamp.desc()).all()
    return logs
