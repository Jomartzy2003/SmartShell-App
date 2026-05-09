from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Rider(Base):
    __tablename__ = 'riders'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    mobile_number = Column(String, unique=True, index=True)
    place_in_binan_laguna = Column(String)
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String, nullable=True)

    # Added relationship to link with Incidents
    incidents = relationship("Incident", back_populates="rider")
    emergency_contacts = relationship("EmergencyContact", back_populates="rider", cascade="all, delete-orphan")

class EmergencyContact(Base):
    __tablename__ = 'emergency_contacts'
    
    id = Column(Integer, primary_key=True, index=True)
    rider_id = Column(Integer, ForeignKey('riders.id'))
    name = Column(String)
    phone_number = Column(String)
    priority = Column(Integer, default=1)
    
    rider = relationship("Rider", back_populates="emergency_contacts")

class Incident(Base):
    __tablename__ = 'incidents'
    
    id = Column(Integer, primary_key=True, index=True)
    # Linking the incident to a specific rider
    rider_id = Column(Integer, ForeignKey('riders.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    location_lat = Column(String)
    location_long = Column(String)
    status = Column(String, default="pending")

    rider = relationship("Rider", back_populates="incidents")