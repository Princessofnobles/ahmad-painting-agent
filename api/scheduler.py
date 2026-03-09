"""
Task Scheduler — runs agents on a schedule
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

scheduler = AsyncIOScheduler()


async def daily_lead_discovery():
    """Run every morning at 8am Dubai time"""
    logger.info("⏰ Scheduled: Lead Discovery")
    from agents.lead_discovery.agent import LeadDiscoveryOrchestrator
    orchestrator = LeadDiscoveryOrchestrator()
    result = await orchestrator.run()
    logger.info(f"[Scheduler] Discovery done: {result}")


async def daily_opportunity_scoring():
    """Score new leads at 8:30am"""
    logger.info("⏰ Scheduled: Opportunity Scoring")
    from agents.opportunity_detection.agent import OpportunityDetectionAgent
    from database.session import AsyncSessionLocal
    agent = OpportunityDetectionAgent()
    async with AsyncSessionLocal() as db:
        scored = await agent.score_all_new_leads(db, use_ai=True)
    logger.info(f"[Scheduler] Scored {scored} leads")


async def daily_followup_processing():
    """Process due follow-ups at 9am"""
    logger.info("⏰ Scheduled: Follow-Up Processing")
    from agents.followup.agent import FollowUpAgent
    from database.session import AsyncSessionLocal
    agent = FollowUpAgent()
    async with AsyncSessionLocal() as db:
        sent = await agent.process_due_followups(db)
    logger.info(f"[Scheduler] Sent {sent} follow-ups")


async def weekly_seo_scan():
    """Weekly Google Maps SEO scan on Monday at 10am"""
    logger.info("⏰ Scheduled: SEO Maps Scan")
    from agents.seo_maps.agent import SEOMapsAgent
    agent = SEOMapsAgent()
    leads = await agent.run()
    logger.info(f"[Scheduler] SEO scan found {len(leads)} opportunity leads")


def start_scheduler():
    """Register all scheduled tasks"""
    # Daily at 8:00 AM UAE time (UTC+4 → UTC 4am)
    scheduler.add_job(
        daily_lead_discovery,
        CronTrigger(hour=4, minute=0),  # 8am UAE
        id="lead_discovery",
        replace_existing=True,
    )

    # Daily at 8:30 AM UAE
    scheduler.add_job(
        daily_opportunity_scoring,
        CronTrigger(hour=4, minute=30),
        id="opportunity_scoring",
        replace_existing=True,
    )

    # Daily at 9:00 AM UAE
    scheduler.add_job(
        daily_followup_processing,
        CronTrigger(hour=5, minute=0),
        id="followup_processing",
        replace_existing=True,
    )

    # Weekly Monday 10am UAE
    scheduler.add_job(
        weekly_seo_scan,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        id="seo_scan",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("✅ Scheduler started — 4 jobs registered")
