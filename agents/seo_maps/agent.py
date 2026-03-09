"""
Local SEO & Google Maps Lead Agent
Identifies businesses in Dubai that visually need painting services.
"""
import json
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from database.models import LeadSource

# Queries specifically targeting businesses likely to need exterior refresh
SEO_MAPS_QUERIES = [
    "hotel Dubai old building",
    "restaurant Dubai",
    "villa community Dubai maintenance",
    "apartment building Dubai older",
    "shopping mall Dubai",
    "office building Dubai",
    "school Dubai",
    "hospital Dubai",
    "mosque Dubai",
    "warehouse Al Quoz Dubai",
    "factory Jebel Ali Dubai",
    "showroom Dubai",
    "petrol station Dubai",
    "supermarket Dubai",
    "gym fitness center Dubai",
]

# Categories with high painting frequency
HIGH_VALUE_CATEGORIES = [
    "hotel", "motel", "resort", "inn",
    "restaurant", "cafe", "bakery", "canteen",
    "property management", "real estate", "developer",
    "school", "nursery", "academy",
    "hospital", "clinic", "pharmacy",
    "warehouse", "factory", "workshop",
    "mall", "shopping center", "showroom",
    "office", "corporate", "business center",
]


class SEOMapsAgent:
    """
    Google Maps scraper focused on identifying businesses
    that visually appear to need painting services.
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        self.api_key = settings.serpapi_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def search_maps(self, query: str) -> list[dict]:
        params = {
            "engine": "google_maps",
            "q": query,
            "location": "Dubai, UAE",
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

        return data.get("local_results", [])

    def calculate_visual_opportunity_score(self, result: dict) -> tuple[float, list[str]]:
        """
        Estimate visual painting need from available data signals.
        Returns (score, signals)
        """
        score = 0.0
        signals = []

        # Rating analysis: lower ratings sometimes indicate property maintenance issues
        rating = result.get("rating", 5.0)
        if rating and rating < 3.5:
            score += 10
            signals.append("Below average rating — may indicate maintenance issues")

        # Review count: established businesses with many reviews = larger property
        reviews = result.get("reviews", 0)
        if reviews > 100:
            score += 15
            signals.append(f"Established business ({reviews}+ reviews) — regular maintenance likely needed")

        # Business type scoring
        biz_type = (result.get("type", "") or "").lower()
        for category in HIGH_VALUE_CATEGORIES:
            if category in biz_type:
                score += 25
                signals.append(f"High-value category: {biz_type}")
                break

        # Presence of hours (open business = active property)
        if result.get("hours"):
            score += 5

        # Check for keywords in reviews/snippets that suggest painting need
        snippet = (result.get("description", "") or "").lower()
        paint_signals = [
            ("old", 10, "Business described as 'old'"),
            ("dated", 12, "Described as 'dated'"),
            ("needs renovation", 20, "Reviews mention renovation need"),
            ("worn", 15, "Property described as worn"),
            ("refresh", 15, "Interior refresh mentioned"),
        ]
        for keyword, pts, label in paint_signals:
            if keyword in snippet:
                score += pts
                signals.append(label)

        return min(score, 100), signals

    def parse_result(self, result: dict) -> dict:
        """Parse SerpAPI result for SEO leads"""
        score, signals = self.calculate_visual_opportunity_score(result)

        # Extract area
        address = result.get("address", "")
        area = ""
        for known in ["JBR", "JLT", "DIFC", "Downtown", "Business Bay", "Deira",
                      "Bur Dubai", "Jumeirah", "Al Barsha", "Mirdif", "Marina",
                      "Palm", "Al Quoz", "Karama", "Satwa", "Jebel Ali"]:
            if known.lower() in address.lower():
                area = known
                break

        return {
            "company_name": result.get("title", ""),
            "phone": result.get("phone", ""),
            "website": result.get("website", ""),
            "address": address,
            "area": area,
            "business_category": result.get("type", ""),
            "google_maps_url": result.get("link", ""),
            "lead_source": LeadSource.SEO_SCAN,
            "opportunity_score": score,
            "opportunity_signals": signals,
            "raw_data": result,
        }

    async def run(self, queries: list[str] = None) -> list[dict]:
        """Run SEO maps scan and return leads above threshold"""
        queries = queries or SEO_MAPS_QUERIES
        all_leads = []
        seen = set()

        for query in queries:
            try:
                results = await self.search_maps(query)
                for r in results:
                    name = r.get("title", "").strip()
                    if not name or name in seen:
                        continue
                    seen.add(name)

                    lead = self.parse_result(r)
                    # Only include leads with meaningful opportunity score
                    if lead["opportunity_score"] >= 20:
                        all_leads.append(lead)

                import asyncio
                await asyncio.sleep(1.5)

            except Exception as e:
                logger.error(f"[SEOMaps] Error for '{query}': {e}")

        # Sort by opportunity score descending
        all_leads.sort(key=lambda x: x["opportunity_score"], reverse=True)
        logger.info(f"[SEOMaps] Found {len(all_leads)} opportunity leads")
        return all_leads
