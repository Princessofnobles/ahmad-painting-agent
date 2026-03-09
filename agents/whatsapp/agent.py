"""
WhatsApp Lead Handling Agent
Processes inbound WhatsApp/email replies and suggests responses.
"""
import json
import google.generativeai as genai
from loguru import logger
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings, COMPANY_PROFILE
from database.models import Lead, LeadStatus, Activity

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")


# -------------------------------------------------------
# Intent Detection
# -------------------------------------------------------
INTENT_PROMPTS = {
    "interested": ["interested", "tell me more", "yes", "sure", "when", "price", "quote", "how much", "available", "call me"],
    "not_interested": ["no", "not interested", "don't need", "already have", "remove", "unsubscribe", "stop"],
    "scheduling": ["tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "morning", "afternoon", "evening", "time", "meet", "visit", "inspection"],
    "asking_price": ["price", "cost", "how much", "rate", "quote", "estimate", "budget"],
    "asking_portfolio": ["portfolio", "previous work", "examples", "photos", "projects done"],
}


def detect_intent(message: str) -> str:
    """Simple keyword-based intent detection"""
    message_lower = message.lower()
    for intent, keywords in INTENT_PROMPTS.items():
        if any(kw in message_lower for kw in keywords):
            return intent
    return "general_inquiry"


async def ai_analyze_reply(lead: Lead, inbound_message: str) -> dict:
    """Use AI to analyze an inbound reply and suggest the best response"""

    prompt = f"""You are a sales assistant for Ahmad Al Zahidi Painting LLC (Dubai painting company).

Company context: {json.dumps(COMPANY_PROFILE, indent=2)}

Lead info:
- Company: {lead.company_name}
- Category: {lead.business_category}
- Area: {lead.area or 'Dubai'}
- Current status: {lead.status}

The lead just replied with this message:
"{inbound_message}"

Analyze the reply and provide:
1. intent: what does the lead want? (interested/not_interested/scheduling/asking_price/asking_portfolio/general_inquiry)
2. sentiment: positive/neutral/negative
3. suggested_reply: a natural, helpful reply message (WhatsApp format, under 150 words)
4. recommended_action: what should the sales team do? (e.g., call immediately, book site visit, send portfolio, remove from list)
5. urgency: low/medium/high
6. update_status: what status to update the lead to?

Respond in JSON:
{{
  "intent": "...",
  "sentiment": "...",
  "suggested_reply": "...",
  "recommended_action": "...",
  "urgency": "...",
  "update_status": "..."
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        logger.error(f"[WhatsApp Handler] AI error: {e}")
        intent = detect_intent(inbound_message)
        return {
            "intent": intent,
            "sentiment": "neutral",
            "suggested_reply": _fallback_reply(intent, lead),
            "recommended_action": "Review and respond manually",
            "urgency": "medium",
            "update_status": "contacted",
        }


def _fallback_reply(intent: str, lead: Lead) -> str:
    replies = {
        "interested": (
            f"Thank you for your interest! 😊 We'd love to visit {lead.company_name} for a free site inspection. "
            f"Could you share a convenient time — morning or afternoon? We're flexible and can work around your schedule."
        ),
        "scheduling": (
            f"Perfect! We can arrange a visit to {lead.company_name}. "
            f"Could you confirm the address and your preferred time? Our team will be there!"
        ),
        "asking_price": (
            f"Great question! Our pricing depends on the area and surface type. "
            f"The easiest way to get an accurate quote is a free site visit — no obligation. "
            f"Can we arrange one this week?"
        ),
        "asking_portfolio": (
            f"We'd be happy to share our project portfolio! We've worked on villas, apartments, hotels, and offices across Dubai. "
            f"Shall I send you some photos? And we can arrange a free inspection too."
        ),
        "not_interested": (
            f"Absolutely, no problem at all! We'll keep your details for future reference. "
            f"Wishing {lead.company_name} all the best. Feel free to reach out anytime. 🙏"
        ),
        "general_inquiry": (
            f"Thank you for getting back to us! How can we help {lead.company_name}? "
            f"We offer a full range of painting services and would love to assist."
        ),
    }
    return replies.get(intent, replies["general_inquiry"])


# -------------------------------------------------------
# Consultation Booking Assistant
# -------------------------------------------------------
async def generate_booking_message(lead: Lead, preferred_time: str = "") -> str:
    """Generate a consultation booking confirmation message"""

    prompt = f"""Write a WhatsApp message from Ahmad Al Zahidi Painting LLC confirming a free site inspection booking.

Lead: {lead.company_name} | Area: {lead.area or 'Dubai'}
Preferred time: {preferred_time or 'to be confirmed'}

The message should:
- Confirm the booking enthusiastically
- Ask for the exact address if not known
- Mention what to expect (quick 30-min visit, photos, free quote)
- Provide the company phone number for any changes
- Be warm and professional
- Under 120 words

Company phone: {settings.company_phone}"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"[WhatsApp] Booking message error: {e}")
        return (
            f"Great news! We've booked your free site inspection 🎉\n\n"
            f"Our team will visit {lead.company_name} {preferred_time or 'at the agreed time'}.\n\n"
            f"Please confirm your full address. The inspection takes about 30 minutes — "
            f"we'll assess the surfaces and provide a detailed quote. No obligation!\n\n"
            f"Any changes? Call us: {settings.company_phone}\n\nSee you soon! 🎨"
        )


# -------------------------------------------------------
# Inbound Message Handler
# -------------------------------------------------------
class WhatsAppHandlerAgent:

    async def handle_inbound(
        self,
        lead_id: int,
        message: str,
        db: AsyncSession,
    ) -> dict:
        """Process an inbound message from a lead"""

        lead = await db.get(Lead, lead_id)
        if not lead:
            return {"error": "Lead not found"}

        # AI analysis
        analysis = await ai_analyze_reply(lead, message)

        # Update lead status
        status_map = {
            "interested": LeadStatus.INTERESTED,
            "scheduling": LeadStatus.CONSULTATION_BOOKED,
            "not_interested": LeadStatus.LOST,
        }
        new_status = status_map.get(
            analysis.get("intent", ""),
            LeadStatus.CONTACTED
        )
        lead.status = new_status
        lead.response_received = True
        lead.response_notes = f"Reply: {message[:200]}"

        # Log activity
        activity = Activity(
            lead_id=lead.id,
            action="whatsapp_reply_received",
            description=f"Lead replied: {message[:100]}",
            metadata=analysis,
        )
        db.add(activity)
        await db.commit()

        return {
            "lead_id": lead_id,
            "lead_name": lead.company_name,
            "intent": analysis.get("intent"),
            "sentiment": analysis.get("sentiment"),
            "suggested_reply": analysis.get("suggested_reply"),
            "recommended_action": analysis.get("recommended_action"),
            "urgency": analysis.get("urgency"),
            "status_updated_to": new_status,
        }

    async def handle_webhook(self, payload: dict, db: AsyncSession) -> dict:
        """
        Handle Twilio WhatsApp webhook payload.
        Maps inbound message to the correct lead.
        """
        from_number = payload.get("From", "").replace("whatsapp:", "")
        message_body = payload.get("Body", "")

        if not from_number or not message_body:
            return {"status": "ignored", "reason": "empty payload"}

        # Find lead by phone number
        result = await db.execute(
            select(Lead).where(
                (Lead.whatsapp == from_number) | (Lead.phone == from_number)
            )
        )
        lead = result.scalar_one_or_none()

        if not lead:
            logger.warning(f"[WhatsApp] No lead found for {from_number}")
            return {"status": "no_lead_found", "from": from_number}

        return await self.handle_inbound(lead.id, message_body, db)
