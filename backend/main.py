from datetime import timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import json
import random
from typing import List
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import Session, Mapped, mapped_column
from datetime import datetime
from pydantic import BaseModel

from database import SessionLocal, engine
import database
import models
import twilio_service

app = FastAPI(title="SmartShell API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.get("/")
def serve_dashboard():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


class RegisterRequest(BaseModel):
    name: str
    mobile_number: str
    place: str

class ContactCreate(BaseModel):
    name: str
    phone_number: str
    priority: int = 1

class HardwareCrashRequest(BaseModel):
    rider_id: int
    latitude: float
    longitude: float

class VerifyRequest(BaseModel):
    mobile_number: str
    code: str

class LoginRequest(BaseModel):
    mobile_number: str

class Accident(database.Base):
    __tablename__ = "accidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rider_name: Mapped[str] = mapped_column(String)
    latitude: Mapped[float] = mapped_column(Float) 
    longitude: Mapped[float] = mapped_column(Float) 
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
# Create DB schema
try:
    if os.path.exists("./smartshell.db"):
        os.remove("./smartshell.db")
    database.Base.metadata.create_all(bind=database.engine)
except Exception as e:
    print("Warning: Database creation failed -", e)

class AccidentAlert(BaseModel):
    rider_name: str
    latitude: float
    longitude: float

@app.post("/register")
def register_rider(req: RegisterRequest, db: Session = Depends(database.get_db)):
    rider = db.query(models.Rider).filter(models.Rider.mobile_number == req.mobile_number).first()
    if rider:
        raise HTTPException(status_code=400, detail="Mobile number already registered")
    
    code = str(random.randint(1000, 9999))
    new_rider = models.Rider(
        name=req.name,
        mobile_number=req.mobile_number,
        place_in_binan_laguna=req.place,
        is_verified=False,
        verification_code=code
    )
    db.add(new_rider)
    db.commit()
    
    
    twilio_service.dispatch_sms(req.mobile_number, f"Your SmartShell verification code is {code}")
    return {"message": "Verification code sent."}

@app.post("/verify")
def verify_rider(req: VerifyRequest, db: Session = Depends(database.get_db)):
    rider = db.query(models.Rider).filter(models.Rider.mobile_number == req.mobile_number).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    if rider.verification_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid code")
    
    rider.is_verified = True
    rider.verification_code = None
    db.commit()
    return {"message": "Verification successful."}

@app.post("/login")
def login_rider(req: LoginRequest, db: Session = Depends(database.get_db)):
    rider = db.query(models.Rider).filter(models.Rider.mobile_number == req.mobile_number).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found. Please register.")
    
    code = str(random.randint(1000, 9999))
    rider.verification_code = code
    db.commit()
    
    twilio_service.dispatch_sms(req.mobile_number, f"Your SmartShell login code is {code}")
    return {"message": "Login code sent."}

@app.post("/login_verify")
def verify_login(req: VerifyRequest, db: Session = Depends(database.get_db)):
    rider = db.query(models.Rider).filter(models.Rider.mobile_number == req.mobile_number).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    if rider.verification_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid code")
    
    rider.verification_code = None
    db.commit()
    
    return {
        "message": "Login successful.",
        "rider": {
            "id": rider.id,
            "name": rider.name,
            "mobile_number": rider.mobile_number,
            "place": rider.place_in_binan_laguna
        }
    }

@app.post("/alert")
async def create_alert(data: AccidentAlert, db: Session = Depends(get_db)):
    new_accident = Accident(
        rider_name=data.rider_name,
        latitude=data.latitude,
        longitude=data.longitude
    )
    db.add(new_accident)
    db.commit()
    db.refresh(new_accident)
    
    return {"status": "success", "message": "Location received", "id": new_accident.id}

class ConnectionManager:
    def __init__(self):
        self.active_riders: List[WebSocket] = []
        self.dashboard_connections: List[WebSocket] = []

    async def connect_rider(self, websocket: WebSocket):
        await websocket.accept()
        self.active_riders.append(websocket)

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.append(websocket)

    def disconnect_rider(self, websocket: WebSocket):
        if websocket in self.active_riders:
            self.active_riders.remove(websocket)

    def disconnect_dashboard(self, websocket: WebSocket):
        if websocket in self.dashboard_connections:
            self.dashboard_connections.remove(websocket)

    async def broadcast_to_riders(self, message: str):
        for connection in self.active_riders:
            await connection.send_text(message)
            
    async def broadcast_to_dashboards(self, message: str):
        for connection in self.dashboard_connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                self.disconnect_dashboard(connection)

manager = ConnectionManager()

active_crashes = {}

async def crash_countdown_task(rider_id: int, contacts: List[models.EmergencyContact], lat: float, lng: float):
    for _ in range(10):
        if active_crashes.get(rider_id, False):
            print(f"Crash for rider {rider_id} was cancelled in background task.")
            return
        await asyncio.sleep(1)
        
    print(f"Countdown finished for rider {rider_id}. Triggering alerts to {len(contacts)} contacts...")
    for contact in contacts:
        message = f"EMERGENCY: Rider {rider_id} has crashed! View exact location on Map: https://www.google.com/maps?q={lat},{lng}"
        print(f"MOCK SMS: {message}")
        try:
            twilio_service.dispatch_sms(contact.phone_number, message)
        except Exception as e:
            print(f"SMS failed to {contact.phone_number}: {e}")
            
    await manager.broadcast_to_dashboards(json.dumps({"event": "ALERT_DISPATCHED", "rider_id": rider_id, "lat": lat, "lng": lng}))

@app.post("/hardware_crash")
async def trigger_hardware_crash(req: HardwareCrashRequest, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    rider = db.query(models.Rider).filter(models.Rider.id == req.rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
        
    contacts = db.query(models.EmergencyContact).filter(models.EmergencyContact.rider_id == req.rider_id).all()
    
    active_crashes[req.rider_id] = False
    
    await manager.broadcast_to_riders(json.dumps({"event": "CRASH_DETECTED", "rider_id": req.rider_id}))
    await manager.broadcast_to_dashboards(json.dumps({"event": "CRASH_DETECTED", "rider_id": req.rider_id}))
    
    background_tasks.add_task(crash_countdown_task, rider.id, contacts, req.latitude, req.longitude)
    
    return {"status": "Crash initiated and broadcasted"}

@app.get("/contacts/{rider_id}")
def get_contacts(rider_id: int, db: Session = Depends(database.get_db)):
    contacts = db.query(models.EmergencyContact).filter(models.EmergencyContact.rider_id == rider_id).all()
    return [{"id": c.id, "name": c.name, "phone_number": c.phone_number, "priority": c.priority} for c in contacts]

@app.post("/contacts/{rider_id}")
def add_contact(rider_id: int, req: ContactCreate, db: Session = Depends(database.get_db)):
    new_contact = models.EmergencyContact(
        rider_id=rider_id,
        name=req.name,
        phone_number=req.phone_number,
        priority=req.priority
    )
    db.add(new_contact)
    db.commit()
    return {"id": new_contact.id, "name": new_contact.name, "phone_number": new_contact.phone_number, "priority": new_contact.priority}

@app.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(database.get_db)):
    contact = db.query(models.EmergencyContact).filter(models.EmergencyContact.id == contact_id).first()
    if contact:
        db.delete(contact)
        db.commit()
    return {"status": "deleted"}

@app.websocket("/ws/rider")
async def websocket_rider(websocket: WebSocket):
    await manager.connect_rider(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload.get("event") == "CANCELLED":
                # Cancellation logic from voice command "CANCEL" or "I AM OKAY"
                rider_id = payload.get("rider_id")
                if rider_id:
                    active_crashes[rider_id] = True
                print(f"Crash event cancelled by rider {rider_id} voice command/tap.")
                await manager.broadcast_to_dashboards(json.dumps({"event": "RESOLVED", "rider_id": rider_id}))
                
    except WebSocketDisconnect:
        manager.disconnect_rider(websocket)
    except Exception as e:
        manager.disconnect_rider(websocket)
        print(f"Rider WS error: {e}")

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await manager.connect_dashboard(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)

@app.get("/health")
def health_check():
    return {"status": "ok"}
