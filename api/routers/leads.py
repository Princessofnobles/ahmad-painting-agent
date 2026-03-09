"""
Leads API Router — CRUD for lead management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database.session import get_db
from database.models import Lead, LeadStatus, LeadSource, OutreachChannel

router = APIRouter()


# -------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------
class LeadCreate(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    address: Optional[str] = None
    area: Optional[str] = None
    business_category: Optional[str] = None
    lead_source: Optional[LeadSource] = LeadSource.MANUAL


class LeadUpdate(BaseModel):
    status: Optional[LeadStatus] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    area: Optional[str] = None
    response_notes: Optional[str] = None
    outreach_channel: Optional[OutreachChannel] = None


class LeadResponse(BaseModel):
    id: int
    company_name: str
    contact_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    area: Optional[str]
    business_category: Optional[str]
    lead_source: Optional[str]
    status: str
    opportunity_score: float
    opportunity_signals: Optional[list]
    ai_notes: Optional[str]
    response_received: bool
    last_contacted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------
# Routes
# -------------------------------------------------------
@router.get("/", response_model=dict)
async def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    min_score: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Lead)

    if status:
        query = query.where(Lead.status == status)
    if source:
        query = query.where(Lead.lead_source == source)
    if search:
        query = query.where(
            or_(
                Lead.company_name.ilike(f"%{search}%"),
                Lead.contact_name.ilike(f"%{search}%"),
                Lead.area.ilike(f"%{search}%"),
            )
        )
    if min_score is not None:
        query = query.where(Lead.opportunity_score >= min_score)

    # Count total
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Paginate and order by score
    query = query.order_by(Lead.opportunity_score.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    leads = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "leads": [
            {
                "id": l.id,
                "company_name": l.company_name,
                "contact_name": l.contact_name,
                "phone": l.phone,
                "email": l.email,
                "area": l.area,
                "business_category": l.business_category,
                "lead_source": l.lead_source,
                "status": l.status,
                "opportunity_score": l.opportunity_score,
                "response_received": l.response_received,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ],
    }


@router.post("/", status_code=201)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead = Lead(**data.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return {"id": lead.id, "message": "Lead created successfully"}


@router.get("/{lead_id}")
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/{lead_id}")
async def update_lead(lead_id: int, data: LeadUpdate, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(lead, field, value)

    await db.commit()
    return {"message": "Lead updated"}


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    await db.commit()
    return {"message": "Lead deleted"}


@router.get("/{lead_id}/messages")
async def get_lead_messages(lead_id: int, db: AsyncSession = Depends(get_db)):
    from database.models import OutreachMessage
    result = await db.execute(
        select(OutreachMessage).where(OutreachMessage.lead_id == lead_id)
    )
    messages = result.scalars().all()
    return {
        "lead_id": lead_id,
        "messages": [
            {
                "id": m.id,
                "channel": m.channel,
                "subject": m.subject,
                "body": m.body,
                "sent": m.sent,
                "sent_at": m.sent_at,
                "created_at": m.created_at,
            }
            for m in messages
        ],
    }


@router.get("/{lead_id}/followups")
async def get_lead_followups(lead_id: int, db: AsyncSession = Depends(get_db)):
    from database.models import FollowUp
    result = await db.execute(
        select(FollowUp).where(FollowUp.lead_id == lead_id).order_by(FollowUp.step)
    )
    followups = result.scalars().all()
    return {
        "lead_id": lead_id,
        "followups": [
            {
                "id": f.id,
                "step": f.step,
                "day_offset": f.day_offset,
                "channel": f.channel,
                "message_body": f.message_body,
                "scheduled_at": f.scheduled_at,
                "status": f.status,
                "sent_at": f.sent_at,
            }
            for f in followups
        ],
    }
