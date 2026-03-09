"""
Agents API Router — trigger and monitor AI agents
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db

router = APIRouter()


@router.post("/discover")
async def run_lead_discovery(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger the Lead Discovery Agent"""
    from agents.lead_discovery.agent import LeadDiscoveryOrchestrator
    orchestrator = LeadDiscoveryOrchestrator()
    background_tasks.add_task(orchestrator.run)
    return {"status": "started", "message": "Lead discovery running in background"}


@router.post("/score-leads")
async def run_opportunity_scoring(
    use_ai: bool = True,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """Trigger Opportunity Detection Agent to score unscored leads"""
    from agents.opportunity_detection.agent import OpportunityDetectionAgent
    agent = OpportunityDetectionAgent()
    background_tasks.add_task(agent.score_all_new_leads, db, use_ai)
    return {"status": "started", "message": "Scoring leads in background"}


@router.post("/generate-outreach/{lead_id}")
async def generate_outreach_for_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Generate personalized outreach messages for a specific lead"""
    from agents.outreach.agent import OutreachGeneratorAgent
    from database.models import Lead

    lead = await db.get(Lead, lead_id)
    if not lead:
        return {"error": "Lead not found"}

    agent = OutreachGeneratorAgent()
    messages = await agent.generate_for_lead(lead)

    for msg in messages:
        db.add(msg)
    await db.commit()

    return {
        "lead_id": lead_id,
        "messages_generated": len(messages),
        "channels": [m.channel for m in messages],
    }


@router.post("/schedule-followup/{lead_id}")
async def schedule_followup(
    lead_id: int,
    channel: str = "whatsapp",
    db: AsyncSession = Depends(get_db),
):
    """Schedule 5-step follow-up sequence for a lead"""
    from agents.followup.agent import FollowUpAgent
    from database.models import Lead, OutreachChannel

    lead = await db.get(Lead, lead_id)
    if not lead:
        return {"error": "Lead not found"}

    ch = OutreachChannel(channel)
    agent = FollowUpAgent()
    followups = await agent.schedule_sequence(lead, db, channel=ch)

    return {
        "lead_id": lead_id,
        "followups_scheduled": len(followups),
        "steps": [f.step for f in followups],
    }


@router.post("/process-followups")
async def process_due_followups(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Send all due follow-up messages"""
    from agents.followup.agent import FollowUpAgent
    agent = FollowUpAgent()
    background_tasks.add_task(agent.process_due_followups, db)
    return {"status": "started", "message": "Processing due follow-ups"}


@router.post("/seo-scan")
async def run_seo_scan(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Run Google Maps SEO scan for new leads"""
    from agents.seo_maps.agent import SEOMapsAgent
    from agents.lead_discovery.normalizer import normalize_lead
    from database.models import Lead
    from sqlalchemy import select

    async def _run():
        agent = SEOMapsAgent()
        raw_leads = await agent.run()
        new_count = 0
        async with db:
            for raw in raw_leads:
                normalized = normalize_lead(raw)
                if not normalized.get("company_name"):
                    continue
                result = await db.execute(
                    select(Lead).where(Lead.company_name == normalized["company_name"])
                )
                if result.scalar_one_or_none():
                    continue
                lead = Lead(**normalized)
                lead.opportunity_score = raw.get("opportunity_score", 0)
                lead.opportunity_signals = raw.get("opportunity_signals", [])
                db.add(lead)
                new_count += 1
            await db.commit()
        return new_count

    background_tasks.add_task(_run)
    return {"status": "started", "message": "SEO Maps scan running in background"}


@router.get("/status")
async def agent_status():
    """Get current agent system status"""
    from database.session import AsyncSessionLocal
    from database.models import Lead, ScrapeJob, FollowUp, FollowUpStatus
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        total_leads = (await db.execute(select(func.count(Lead.id)))).scalar()
        new_leads = (await db.execute(
            select(func.count(Lead.id)).where(Lead.status == "new")
        )).scalar()
        pending_followups = (await db.execute(
            select(func.count(FollowUp.id)).where(FollowUp.status == FollowUpStatus.PENDING)
        )).scalar()
        last_job = (await db.execute(
            select(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(1)
        )).scalar_one_or_none()

    return {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "pending_followups": pending_followups,
        "last_scrape_job": {
            "source": last_job.source if last_job else None,
            "status": last_job.status if last_job else None,
            "leads_found": last_job.leads_found if last_job else 0,
            "completed_at": last_job.completed_at if last_job else None,
        },
    }
