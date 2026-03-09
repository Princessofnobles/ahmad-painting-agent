"""Outreach Router"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db

router = APIRouter()


@router.post("/generate-all")
async def generate_outreach_for_top_leads(
    limit: int = 20,
    min_score: float = 40.0,
    db: AsyncSession = Depends(get_db),
):
    """Generate outreach messages for top-scored leads"""
    from sqlalchemy import select
    from database.models import Lead, LeadStatus, OutreachMessage
    from agents.outreach.agent import OutreachGeneratorAgent

    result = await db.execute(
        select(Lead).where(
            Lead.opportunity_score >= min_score,
            Lead.status == LeadStatus.NEW,
        ).order_by(Lead.opportunity_score.desc()).limit(limit)
    )
    leads = result.scalars().all()

    agent = OutreachGeneratorAgent()
    total_generated = 0

    for lead in leads:
        # Check if messages already exist
        existing = await db.execute(
            select(OutreachMessage).where(OutreachMessage.lead_id == lead.id)
        )
        if existing.scalars().first():
            continue

        messages = await agent.generate_for_lead(lead)
        for msg in messages:
            db.add(msg)
        total_generated += len(messages)

    await db.commit()

    return {
        "leads_processed": len(leads),
        "messages_generated": total_generated,
    }
