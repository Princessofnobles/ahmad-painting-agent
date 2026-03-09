"""
Database models for Ahmad Al Zahidi Painting AI Agent System
"""
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, Enum, ForeignKey, JSON
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime
import enum


class Base(AsyncAttrs, DeclarativeBase):
    pass


# -------------------------------------------------------
# Enums
# -------------------------------------------------------
class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    CONSULTATION_BOOKED = "consultation_booked"
    QUOTED = "quoted"
    WON = "won"
    LOST = "lost"
    UNRESPONSIVE = "unresponsive"


class OutreachChannel(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    LINKEDIN = "linkedin"
    PHONE = "phone"


class LeadSource(str, enum.Enum):
    GOOGLE_MAPS = "google_maps"
    LINKEDIN = "linkedin"
    PROPERTY_DIRECTORY = "property_directory"
    BUSINESS_DIRECTORY = "business_directory"
    REFERRAL = "referral"
    MANUAL = "manual"
    SEO_SCAN = "seo_scan"


class FollowUpStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


# -------------------------------------------------------
# Lead Model
# -------------------------------------------------------
class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    # Basic Info
    company_name = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    contact_title = Column(String(255), nullable=True)

    # Contact Details
    phone = Column(String(50), nullable=True)
    whatsapp = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)

    # Location
    address = Column(Text, nullable=True)
    area = Column(String(100), nullable=True)  # e.g. JBR, Downtown, DIFC
    city = Column(String(50), default="Dubai")
    google_maps_url = Column(String(500), nullable=True)

    # Classification
    business_category = Column(String(100), nullable=True)
    lead_source = Column(Enum(LeadSource), default=LeadSource.MANUAL)
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW)

    # AI Scoring
    opportunity_score = Column(Float, default=0.0)  # 0-100
    opportunity_signals = Column(JSON, default=list)  # list of detected signals
    ai_notes = Column(Text, nullable=True)

    # Outreach
    outreach_channel = Column(Enum(OutreachChannel), nullable=True)
    last_contacted_at = Column(DateTime, nullable=True)
    response_received = Column(Boolean, default=False)
    response_notes = Column(Text, nullable=True)

    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    raw_data = Column(JSON, nullable=True)  # store original scraped data

    # Relationships
    outreach_messages = relationship("OutreachMessage", back_populates="lead", cascade="all, delete-orphan")
    follow_ups = relationship("FollowUp", back_populates="lead", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead {self.company_name} [{self.status}]>"


# -------------------------------------------------------
# Outreach Message
# -------------------------------------------------------
class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)

    channel = Column(Enum(OutreachChannel), nullable=False)
    subject = Column(String(500), nullable=True)  # for email
    body = Column(Text, nullable=False)

    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    opened = Column(Boolean, default=False)
    replied = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="outreach_messages")


# -------------------------------------------------------
# Follow-Up Sequence
# -------------------------------------------------------
class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)

    step = Column(Integer, nullable=False)        # 1-5
    day_offset = Column(Integer, nullable=False)  # 1, 3, 7, 14, 21
    channel = Column(Enum(OutreachChannel), nullable=False)
    message_body = Column(Text, nullable=False)
    subject = Column(String(500), nullable=True)

    scheduled_at = Column(DateTime, nullable=False)
    status = Column(Enum(FollowUpStatus), default=FollowUpStatus.PENDING)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="follow_ups")


# -------------------------------------------------------
# Activity Log
# -------------------------------------------------------
class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)

    action = Column(String(100), nullable=False)  # e.g. "email_sent", "wa_replied"
    description = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="activities")


# -------------------------------------------------------
# Scrape Job Tracking
# -------------------------------------------------------
class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)  # google_maps, linkedin, etc.
    query = Column(String(500), nullable=False)
    status = Column(String(50), default="pending")  # pending, running, done, failed
    leads_found = Column(Integer, default=0)
    leads_new = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
