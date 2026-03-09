"""
Property Opportunity Detection Agent
Uses AI to score each lead for painting need likelihood.
"""
import json
from openai import AsyncOpenAI
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings, COMPANY_PROFILE
from database.models import Lead, LeadStatus


client = AsyncOpenAI(api_key=settings.openai_api_key)


# -------------------------------------------------------
# Opportunity Signals (rule-based)
# -------------------------------------------------------
OPPORTUNITY_SIGNALS = {
    "hotel": {
        "label": "Hotel / Hospitality Property",
        "description": "Hotels regularly repaint every 3-5 years for guest experience",
        "score": 35,
    },
    "restaurant": {
        "label": "Restaurant / Cafe",
        "description": "F&B venues need frequent repaints to maintain ambiance",
        "score": 30,
    },
    "property management": {
        "label": "Property Management Company",
        "description": "Manages multiple buildings — potential for bulk contracts",
        "score": 40,
    },
    "real estate": {
        "label": "Real Estate Developer",
        "description": "Developers need painting for new builds and handovers",
        "score": 38,
    },
    "construction": {
        "label": "Construction Company",
        "description": "Active projects require painting as part of fit-out",
        "score": 35,
    },
    "villa": {
        "label": "Villa Community",
        "description": "Villa communities need exterior painting maintenance",
        "score": 33,
    },
    "facility management": {
        "label": "Facility Management",
        "description": "FM companies handle painting maintenance for buildings",
        "score": 42,
    },
    "maintenance": {
        "label": "Maintenance Company",
        "description": "Building maintenance includes periodic repainting",
        "score": 38,
    },
    "office": {
        "label": "Office Building",
        "description": "Corporate offices repaint during moves or refurb",
        "score": 28,
    },
    "school": {
        "label": "Educational Institution",
        "description": "Schools repaint during summer breaks",
        "score": 25,
    },
    "hospital": {
        "label": "Healthcare Facility",
        "description": "Medical facilities require specialized painting",
        "score": 30,
    },
    "warehouse": {
        "label": "Warehouse / Industrial",
        "description": "Industrial painting and floor coating opportunities",
        "score": 25,
    },
}


def detect_rule_based_signals(lead: Lead) -> tuple[list[dict], float]:
    """
    Detect opportunity signals using keyword matching.
    Returns: (signals, total_score)
    """
    text = " ".join([
        lead.company_name or "",
        lead.business_category or "",
        lead.address or "",
    ]).lower()

    signals = []
    total_score = 0

    for keyword, signal_data in OPPORTUNITY_SIGNALS.items():
        if keyword in text:
            signals.append({
                "signal": signal_data["label"],
                "reason": signal_data["description"],
                "score": signal_data["score"],
            })
            total_score += signal_data["score"]

    # Contact quality bonus
    if lead.email:
        total_score += 10
    if lead.phone:
        total_score += 8
    if lead.website:
        total_score += 5

    # Cap at 100
    total_score = min(total_score, 100)

    return signals, total_score


# -------------------------------------------------------
# AI-Powered Opportunity Analysis
# -------------------------------------------------------
async def ai_analyze_opportunity(lead: Lead) -> dict:
    """
    Use GPT-4o to deeper analyze the lead and provide:
    - opportunity score (0-100)
    - key signals
    - suggested approach
    - ideal message angle
    """

    prompt = f"""You are a business development expert for a Dubai painting company.

Company Profile:
{json.dumps(COMPANY_PROFILE, indent=2)}

Analyze this potential client and assess their painting service needs:

Lead Details:
- Company: {lead.company_name}
- Category: {lead.business_category}
- Location: {lead.address} {lead.area}
- Website: {lead.website}
- Source: {lead.lead_source}

Tasks:
1. Score the painting opportunity from 0-100 (100 = very likely needs painting now)
2. List 2-3 specific reasons this company might need painting services
3. Suggest the best outreach angle (what problem to highlight)
4. Recommend which service to lead with

Respond in JSON format:
{{
  "opportunity_score": <0-100>,
  "signals": ["signal 1", "signal 2"],
  "outreach_angle": "short description of best angle",
  "recommended_service": "e.g. Exterior Painting",
  "urgency": "low|medium|high",
  "notes": "any additional insight"
}}"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=500,
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        logger.error(f"[OpportunityAI] Error for {lead.company_name}: {e}")
        return {
            "opportunity_score": 50,
            "signals": [],
            "outreach_angle": "General painting services",
            "recommended_service": "Interior/Exterior Painting",
            "urgency": "medium",
            "notes": "AI analysis unavailable",
        }


# -------------------------------------------------------
# Orchestrator
# -------------------------------------------------------
class OpportunityDetectionAgent:

    async def score_lead(self, lead: Lead, use_ai: bool = True) -> Lead:
        """Score a single lead for painting opportunity"""

        # Rule-based scoring
        signals, rule_score = detect_rule_based_signals(lead)

        if use_ai and (lead.company_name or lead.business_category):
            # AI-enhanced scoring
            ai_result = await ai_analyze_opportunity(lead)
            ai_score = ai_result.get("opportunity_score", rule_score)

            # Blend: 40% rule-based, 60% AI
            final_score = (rule_score * 0.4) + (ai_score * 0.6)

            # Merge signals
            for sig in ai_result.get("signals", []):
                signals.append({"signal": sig, "reason": "", "score": 0})

            lead.ai_notes = (
                f"Outreach angle: {ai_result.get('outreach_angle', '')} | "
                f"Lead with: {ai_result.get('recommended_service', '')} | "
                f"Urgency: {ai_result.get('urgency', 'medium')}"
            )
        else:
            final_score = rule_score

        lead.opportunity_score = round(final_score, 1)
        lead.opportunity_signals = signals

        return lead

    async def score_all_new_leads(self, db: AsyncSession, use_ai: bool = True) -> int:
        """Score all unscored leads in the database"""
        result = await db.execute(
            select(Lead).where(
                Lead.opportunity_score == 0.0,
                Lead.status == LeadStatus.NEW
            ).limit(50)  # batch size
        )
        leads = result.scalars().all()

        scored = 0
        for lead in leads:
            try:
                lead = await self.score_lead(lead, use_ai=use_ai)
                scored += 1
                logger.info(
                    f"[Opportunity] {lead.company_name}: score={lead.opportunity_score}"
                )
            except Exception as e:
                logger.error(f"[Opportunity] Error scoring {lead.company_name}: {e}")

        await db.commit()
        logger.info(f"✅ Scored {scored} leads")
        return scored
