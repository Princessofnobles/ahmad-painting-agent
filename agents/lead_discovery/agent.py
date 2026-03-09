"""
Lead Discovery Agent
Finds potential painting clients in Dubai from multiple sources.
"""
import asyncio
import httpx
from typing import Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings, DUBAI_SEARCH_QUERIES
from database.models import Lead, LeadSource, ScrapeJob
from database.session import AsyncSessionLocal
from agents.lead_discovery.normalizer import normalize_lead


# -------------------------------------------------------
# Google Maps / SerpAPI Scraper
# -------------------------------------------------------
class GoogleMapsLeadAgent:
    """
    Uses SerpAPI to scrape Google Maps for businesses in Dubai.
    Each result is normalized into a Lead record.
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        self.api_key = settings.serpapi_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def search(self, query: str, location: str = "Dubai, UAE") -> list[dict]:
        params = {
            "engine": "google_maps",
            "q": query,
            "location": location,
            "api_key": self.api_key,
            "hl": "en",
            "gl": "ae",
            "type": "search",
            "num": 20,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("local_results", [])
        logger.info(f"[GoogleMaps] '{query}' → {len(results)} results")
        return results

    def parse_result(self, result: dict) -> dict:
        """Parse a SerpAPI Google Maps result into lead fields"""
        return {
            "company_name": result.get("title", ""),
            "phone": result.get("phone", ""),
            "website": result.get("website", ""),
            "address": result.get("address", ""),
            "area": self._extract_area(result.get("address", "")),
            "business_category": result.get("type", ""),
            "google_maps_url": result.get("link", ""),
            "lead_source": LeadSource.GOOGLE_MAPS,
            "raw_data": result,
        }

    def _extract_area(self, address: str) -> str:
        """Try to extract Dubai area from address string"""
        known_areas = [
            "Downtown", "JBR", "JLT", "DIFC", "Business Bay", "Deira",
            "Bur Dubai", "Jumeirah", "Al Barsha", "Mirdif", "Dubai Marina",
            "Palm Jumeirah", "Discovery Gardens", "Sports City", "Silicon Oasis",
            "Al Quoz", "Karama", "Satwa", "Rashidiya", "Muhaisnah",
        ]
        for area in known_areas:
            if area.lower() in address.lower():
                return area
        return ""

    async def run(self, queries: Optional[list[str]] = None) -> list[dict]:
        """Run discovery across all queries and return raw leads"""
        queries = queries or DUBAI_SEARCH_QUERIES
        all_leads = []

        for query in queries:
            try:
                results = await self.search(query)
                for r in results:
                    lead = self.parse_result(r)
                    if lead["company_name"]:
                        all_leads.append(lead)
                await asyncio.sleep(1)  # be polite
            except Exception as e:
                logger.error(f"[GoogleMaps] Error for query '{query}': {e}")

        logger.info(f"[GoogleMaps] Total raw leads: {len(all_leads)}")
        return all_leads


# -------------------------------------------------------
# Property Directory Scraper (Dubai-specific)
# -------------------------------------------------------
class PropertyDirectoryAgent:
    """
    Scrapes Dubai property management directories.
    Target sites: Bayut, Dubizzle, Property Finder, RERA directories.
    """

    SOURCES = [
        {
            "name": "Bayut Property Management",
            "url": "https://www.bayut.com/property-management/dubai/",
        },
        {
            "name": "Dubizzle Business",
            "url": "https://uae.dubizzle.com/business-industrial/",
        },
    ]

    async def scrape_source(self, source: dict) -> list[dict]:
        """
        Placeholder scraper — in production, use Playwright for JS-rendered pages.
        Returns sample structure for development.
        """
        logger.info(f"[PropertyDirectory] Scraping: {source['name']}")
        # TODO: implement Playwright scraping per site
        # Example:
        # async with async_playwright() as p:
        #     browser = await p.chromium.launch()
        #     page = await browser.new_page()
        #     await page.goto(source["url"])
        #     ...
        return []

    async def run(self) -> list[dict]:
        all_leads = []
        for source in self.SOURCES:
            try:
                leads = await self.scrape_source(source)
                all_leads.extend(leads)
            except Exception as e:
                logger.error(f"[PropertyDirectory] Error: {e}")
        return all_leads


# -------------------------------------------------------
# LinkedIn Company Agent
# -------------------------------------------------------
class LinkedInLeadAgent:
    """
    Uses LinkedIn search (via SerpAPI Google search on LinkedIn) to find
    property management and real estate companies in Dubai.
    """

    LINKEDIN_QUERIES = [
        "site:linkedin.com/company property management Dubai",
        "site:linkedin.com/company real estate developer Dubai",
        "site:linkedin.com/company hotel management Dubai",
        "site:linkedin.com/company facility management Dubai",
        "site:linkedin.com/company construction Dubai",
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def search_linkedin(self, query: str) -> list[dict]:
        params = {
            "engine": "google",
            "q": query,
            "location": "Dubai, UAE",
            "api_key": settings.serpapi_key,
            "num": 10,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("organic_results", [])
        leads = []
        for r in results:
            if "linkedin.com/company" in r.get("link", ""):
                leads.append({
                    "company_name": r.get("title", "").replace(" | LinkedIn", "").strip(),
                    "linkedin_url": r.get("link", ""),
                    "website": "",
                    "lead_source": LeadSource.LINKEDIN,
                    "business_category": "LinkedIn Company",
                    "raw_data": r,
                })
        return leads

    async def run(self) -> list[dict]:
        all_leads = []
        for query in self.LINKEDIN_QUERIES:
            try:
                leads = await self.search_linkedin(query)
                all_leads.extend(leads)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"[LinkedIn] Error: {e}")
        logger.info(f"[LinkedIn] Found {len(all_leads)} companies")
        return all_leads


# -------------------------------------------------------
# Main Lead Discovery Orchestrator
# -------------------------------------------------------
class LeadDiscoveryOrchestrator:
    """
    Runs all discovery agents, deduplicates, saves to DB.
    """

    def __init__(self):
        self.google_maps = GoogleMapsLeadAgent()
        self.property_dir = PropertyDirectoryAgent()
        self.linkedin = LinkedInLeadAgent()

    async def run(self) -> dict:
        logger.info("🚀 Starting Lead Discovery Run")

        # Track job
        async with AsyncSessionLocal() as db:
            job = ScrapeJob(
                source="all",
                query="full_discovery_run",
                status="running",
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            job_id = job.id

        all_raw = []

        # Run agents
        try:
            maps_leads = await self.google_maps.run()
            all_raw.extend(maps_leads)
        except Exception as e:
            logger.error(f"Google Maps agent failed: {e}")

        try:
            linkedin_leads = await self.linkedin.run()
            all_raw.extend(linkedin_leads)
        except Exception as e:
            logger.error(f"LinkedIn agent failed: {e}")

        # Deduplicate by company name
        seen = set()
        unique_leads = []
        for lead in all_raw:
            key = lead.get("company_name", "").lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique_leads.append(lead)

        logger.info(f"[Discovery] {len(unique_leads)} unique leads after dedup")

        # Save to DB
        new_count = await self._save_leads(unique_leads)

        # Update job
        async with AsyncSessionLocal() as db:
            job = await db.get(ScrapeJob, job_id)
            job.status = "done"
            job.leads_found = len(unique_leads)
            job.leads_new = new_count
            from datetime import datetime
            job.completed_at = datetime.utcnow()
            await db.commit()

        logger.info(f"✅ Discovery complete. {new_count} new leads saved.")
        return {"leads_found": len(unique_leads), "new_leads": new_count}

    async def _save_leads(self, raw_leads: list[dict]) -> int:
        """Save leads to DB, skip duplicates"""
        from sqlalchemy import select
        new_count = 0

        async with AsyncSessionLocal() as db:
            for raw in raw_leads:
                normalized = normalize_lead(raw)
                if not normalized.get("company_name"):
                    continue

                # Check duplicate
                result = await db.execute(
                    select(Lead).where(Lead.company_name == normalized["company_name"])
                )
                existing = result.scalar_one_or_none()
                if existing:
                    continue

                lead = Lead(**normalized)
                db.add(lead)
                new_count += 1

            await db.commit()

        return new_count
