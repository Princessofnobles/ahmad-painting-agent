"""
Initialize the database and optionally seed sample data.
Run: python scripts/init_db.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.session import init_db, AsyncSessionLocal
from database.models import Lead, LeadSource, LeadStatus
from loguru import logger


SAMPLE_LEADS = [
    {
        "company_name": "Emirates Properties LLC",
        "contact_name": "Mohammed Al Farsi",
        "contact_title": "Property Manager",
        "phone": "+971501234567",
        "whatsapp": "+971501234567",
        "email": "info@emiratesproperties.ae",
        "website": "https://emiratesproperties.ae",
        "address": "Business Bay, Dubai",
        "area": "Business Bay",
        "business_category": "Property Management",
        "lead_source": LeadSource.MANUAL,
        "opportunity_score": 82.0,
        "ai_notes": "Manages 20+ residential buildings in Business Bay. Likely needs annual painting maintenance contracts.",
    },
    {
        "company_name": "Jumeirah Villa Community",
        "phone": "+971504567890",
        "address": "Jumeirah 3, Dubai",
        "area": "Jumeirah",
        "business_category": "Villa Community",
        "lead_source": LeadSource.GOOGLE_MAPS,
        "opportunity_score": 75.0,
        "ai_notes": "Villa community with exterior painting needs. Dubai sun causes paint degradation every 3-4 years.",
    },
    {
        "company_name": "Grand Rotana Hotel Dubai",
        "phone": "+971567891234",
        "email": "maintenance@grandrotana.ae",
        "address": "Dubai Marina, Dubai",
        "area": "Dubai Marina",
        "business_category": "Hotel",
        "lead_source": LeadSource.GOOGLE_MAPS,
        "opportunity_score": 88.0,
        "ai_notes": "5-star hotel. Hotels repaint every 3-5 years for guest experience. High-value contract potential.",
    },
    {
        "company_name": "Al Barsha Office Complex",
        "website": "https://albarshaofficex.ae",
        "address": "Al Barsha 1, Dubai",
        "area": "Al Barsha",
        "business_category": "Commercial Office Building",
        "lead_source": LeadSource.SEO_SCAN,
        "opportunity_score": 65.0,
    },
    {
        "company_name": "Deira Textile Trading LLC",
        "phone": "+971523456789",
        "address": "Deira, Dubai",
        "area": "Deira",
        "business_category": "Commercial / Warehouse",
        "lead_source": LeadSource.GOOGLE_MAPS,
        "opportunity_score": 55.0,
    },
]


async def seed_sample_data():
    async with AsyncSessionLocal() as db:
        for lead_data in SAMPLE_LEADS:
            lead = Lead(**lead_data)
            db.add(lead)
        await db.commit()
        logger.info(f"✅ Seeded {len(SAMPLE_LEADS)} sample leads")


async def main():
    logger.info("Initializing database...")
    await init_db()

    if "--seed" in sys.argv or "--with-samples" in sys.argv:
        logger.info("Seeding sample data...")
        await seed_sample_data()

    logger.info("✅ Done! Run: uvicorn api.main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
