"""
Dashboard API Router — analytics and stats for the CRM dashboard
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from database.session import get_db
from database.models import Lead, LeadStatus, LeadSource, FollowUp, FollowUpStatus, Activity

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Main stats for the dashboard overview"""

    # Lead counts by status
    status_counts = {}
    for status in LeadStatus:
        count = (await db.execute(
            select(func.count(Lead.id)).where(Lead.status == status)
        )).scalar()
        status_counts[status.value] = count

    # Total leads
    total = (await db.execute(select(func.count(Lead.id)))).scalar()

    # Leads with responses
    responses = (await db.execute(
        select(func.count(Lead.id)).where(Lead.response_received == True)
    )).scalar()

    # Average opportunity score
    avg_score = (await db.execute(
        select(func.avg(Lead.opportunity_score))
    )).scalar() or 0

    # Leads by source
    source_result = await db.execute(
        select(Lead.lead_source, func.count(Lead.id))
        .group_by(Lead.lead_source)
    )
    leads_by_source = {str(row[0]): row[1] for row in source_result}

    # Top areas
    area_result = await db.execute(
        select(Lead.area, func.count(Lead.id))
        .where(Lead.area != None, Lead.area != "")
        .group_by(Lead.area)
        .order_by(func.count(Lead.id).desc())
        .limit(10)
    )
    top_areas = [{"area": row[0], "count": row[1]} for row in area_result]

    # Follow-up stats
    total_followups = (await db.execute(select(func.count(FollowUp.id)))).scalar()
    sent_followups = (await db.execute(
        select(func.count(FollowUp.id)).where(FollowUp.status == FollowUpStatus.SENT)
    )).scalar()
    pending_followups = (await db.execute(
        select(func.count(FollowUp.id)).where(FollowUp.status == FollowUpStatus.PENDING)
    )).scalar()

    # Leads added this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_this_week = (await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= week_ago)
    )).scalar()

    # Recent activity
    recent_activity = await db.execute(
        select(Activity).order_by(Activity.created_at.desc()).limit(10)
    )
    activities = recent_activity.scalars().all()

    return {
        "overview": {
            "total_leads": total,
            "new_leads": status_counts.get("new", 0),
            "contacted": status_counts.get("contacted", 0),
            "interested": status_counts.get("interested", 0),
            "consultation_booked": status_counts.get("consultation_booked", 0),
            "won": status_counts.get("won", 0),
            "lost": status_counts.get("lost", 0),
            "response_rate": round((responses / total * 100) if total > 0 else 0, 1),
            "avg_opportunity_score": round(float(avg_score), 1),
            "new_this_week": new_this_week,
        },
        "by_source": leads_by_source,
        "top_areas": top_areas,
        "followups": {
            "total": total_followups,
            "sent": sent_followups,
            "pending": pending_followups,
        },
        "recent_activity": [
            {
                "action": a.action,
                "description": a.description,
                "created_at": a.created_at.isoformat(),
            }
            for a in activities
        ],
    }


@router.get("/top-leads")
async def get_top_leads(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get highest-scored leads"""
    result = await db.execute(
        select(Lead)
        .where(Lead.status.in_(["new", "contacted"]))
        .order_by(Lead.opportunity_score.desc())
        .limit(limit)
    )
    leads = result.scalars().all()
    return {
        "leads": [
            {
                "id": l.id,
                "company_name": l.company_name,
                "area": l.area,
                "business_category": l.business_category,
                "opportunity_score": l.opportunity_score,
                "status": l.status,
                "phone": l.phone,
                "ai_notes": l.ai_notes,
            }
            for l in leads
        ]
    }
