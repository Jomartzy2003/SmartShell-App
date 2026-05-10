from datetime import timezone
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from database import Base
from typing import Optional, List

class Rider(Base):
    __tablename__ = 'riders'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    mobile_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    place_in_binan_laguna: Mapped[str] = mapped_column(String)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Added relationship to link with Incidents
    incidents: Mapped[List["Incident"]] = relationship("Incident", back_populates="rider")
    emergency_contacts: Mapped[List["EmergencyContact"]] = relationship("EmergencyContact", back_populates="rider", cascade="all, delete-orphan")

class EmergencyContact(Base):
    __tablename__ = 'emergency_contacts'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rider_id: Mapped[int] = mapped_column(Integer, ForeignKey('riders.id'))
    name: Mapped[str] = mapped_column(String)
    phone_number: Mapped[str] = mapped_column(String)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    
    rider: Mapped["Rider"] = relationship("Rider", back_populates="emergency_contacts")

class Incident(Base):
    __tablename__ = 'incidents'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Linking the incident to a specific rider
    rider_id: Mapped[int] = mapped_column(Integer, ForeignKey('riders.id'))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))    
    location_lat: Mapped[str] = mapped_column(String)
    location_long: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")

    rider: Mapped["Rider"] = relationship("Rider", back_populates="incidents")