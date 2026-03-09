"""
Follow-Up Automation Agent
5-step drip sequence over 21 days for each lead.
"""
import json
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings, COMPANY_PROFILE
from database.models import Lead, FollowUp, FollowUpStatus, OutreachChannel, Activity

client = AsyncOpenAI(api_key=settings.openai_api_key)


# -------------------------------------------------------
# Follow-Up Sequence Definition
# -------------------------------------------------------
FOLLOWUP_SEQUENCE = [
    {
        "step": 1,
        "day_offset": 1,
        "label": "Initial Outreach",
        "theme": "Introduction + free consultation offer",
        "tone": "warm and professional",
    },
    {
        "step": 2,
        "day_offset": 3,
        "label": "Quick Reminder",
        "theme": "Gentle follow-up, reiterate key benefit",
        "tone": "brief and friendly",
    },
    {
        "step": 3,
        "day_offset": 7,
        "label": "Portfolio Showcase",
        "theme": "Showcase past work, mention a relevant project type",
        "tone": "inspiring and proof-focused",
    },
    {
        "step": 4,
        "day_offset": 14,
        "label": "Free Site Inspection",
        "theme": "Strong offer: free no-obligation site inspection this week",
        "tone": "value-driven, urgent but not pushy",
    },
    {
        "step": 5,
        "day_offset": 21,
        "label": "Final Message",
        "theme": "Last check-in, leave door open, no pressure",
        "tone": "respectful, gracious, human",
    },
]


# -------------------------------------------------------
# Message Generator for Each Step
# -------------------------------------------------------
async def generate_followup_message(
    lead: Lead,
    step_config: dict,
    channel: OutreachChannel,
    previous_steps_sent: int,
) -> str:
    """Generate a follow-up message for a specific step"""

    prompt = f"""You are writing a follow-up message for Ahmad Al Zahidi Painting LLC.

Company: {json.dumps(COMPANY_PROFILE, indent=2)}

Lead: {lead.company_name} | Category: {lead.business_category} | Area: {lead.area or 'Dubai'}

Follow-up context:
- Step {step_config['step']} of 5: {step_config['label']}
- Day: {step_config['day_offset']} since first contact
- Theme: {step_config['theme']}
- Tone: {step_config['tone']}
- Channel: {channel.value}
- Previous messages sent: {previous_steps_sent}

Write the message. Requirements:
- Reference that this is a follow-up (naturally, not awkwardly)
- Stay on theme: {step_config['theme']}
- Tone: {step_config['tone']}
- {'Under 150 words for WhatsApp' if channel == OutreachChannel.WHATSAPP else 'Under 200 words for email'}
- End with a clear next step or question
- Do not be aggressive or pushy
- For step 5 (final), be gracious and leave the door open

Write only the message text, ready to send."""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[FollowUp] Generation error step {step_config['step']}: {e}")
        return _fallback_message(lead, step_config, channel)


def _fallback_message(lead: Lead, step: dict, channel: OutreachChannel) -> str:
    """Simple fallback messages if AI is unavailable"""
    fallbacks = {
        1: f"Hi! This is Ahmad Al Zahidi Painting LLC. We'd love to offer {lead.company_name} a free painting consultation. Can we connect?",
        2: f"Just a friendly follow-up from Ahmad Al Zahidi Painting LLC. We're offering a free site inspection for {lead.company_name} — interested?",
        3: f"We've recently completed beautiful projects for similar properties in Dubai. I'd love to share some ideas for {lead.company_name}. Shall we schedule a quick call?",
        4: f"Last chance for a FREE site inspection this week! Our team can visit {lead.company_name} at your convenience. No obligation. Just reply to book.",
        5: f"Hi, Ahmad Al Zahidi Painting LLC here. I'll wrap up my outreach now — but we're always here if {lead.company_name} needs painting services in the future. Wishing you all the best! 🎨",
    }
    return fallbacks.get(step["step"], "")


# -------------------------------------------------------
# Follow-Up Scheduler
# -------------------------------------------------------
class FollowUpAgent:

    async def schedule_sequence(
        self,
        lead: Lead,
        db: AsyncSession,
        channel: OutreachChannel = OutreachChannel.WHATSAPP,
        start_date: datetime = None,
    ) -> list[FollowUp]:
        """Schedule all 5 follow-up messages for a lead"""

        if start_date is None:
            start_date = datetime.utcnow()

        # Check if already scheduled
        existing = await db.execute(
            select(FollowUp).where(FollowUp.lead_id == lead.id)
        )
        if existing.scalars().first():
            logger.info(f"[FollowUp] Already scheduled for {lead.company_name}")
            return []

        follow_ups = []

        for step_config in FOLLOWUP_SEQUENCE:
            scheduled_at = start_date + timedelta(days=step_config["day_offset"])

            # Generate message
            message = await generate_followup_message(
                lead=lead,
                step_config=step_config,
                channel=channel,
                previous_steps_sent=step_config["step"] - 1,
            )

            fu = FollowUp(
                lead_id=lead.id,
                step=step_config["step"],
                day_offset=step_config["day_offset"],
                channel=channel,
                message_body=message,
                subject=f"Follow-up {step_config['step']}: {step_config['label']}" if channel == OutreachChannel.EMAIL else None,
                scheduled_at=scheduled_at,
                status=FollowUpStatus.PENDING,
            )
            db.add(fu)
            follow_ups.append(fu)

        await db.commit()
        logger.info(f"✅ Scheduled {len(follow_ups)} follow-ups for {lead.company_name}")
        return follow_ups

    async def process_due_followups(self, db: AsyncSession) -> int:
        """Send all follow-ups that are due now"""
        now = datetime.utcnow()

        result = await db.execute(
            select(FollowUp).where(
                FollowUp.status == FollowUpStatus.PENDING,
                FollowUp.scheduled_at <= now,
            ).limit(50)
        )
        due = result.scalars().all()

        sent_count = 0
        for fu in due:
            try:
                success = await self._send_followup(fu, db)
                if success:
                    fu.status = FollowUpStatus.SENT
                    fu.sent_at = now
                    sent_count += 1
                else:
                    fu.status = FollowUpStatus.FAILED
            except Exception as e:
                logger.error(f"[FollowUp] Send error: {e}")
                fu.status = FollowUpStatus.FAILED
                fu.error_message = str(e)

        await db.commit()
        logger.info(f"[FollowUp] Processed {sent_count}/{len(due)} due follow-ups")
        return sent_count

    async def _send_followup(self, fu: FollowUp, db: AsyncSession) -> bool:
        """Route follow-up to correct sender"""
        # Get lead
        lead = await db.get(Lead, fu.lead_id)
        if not lead:
            return False

        if fu.channel == OutreachChannel.WHATSAPP:
            return await self._send_whatsapp(lead, fu.message_body)
        elif fu.channel == OutreachChannel.EMAIL:
            return await self._send_email(lead, fu.subject or "Follow-up", fu.message_body)
        return False

    async def _send_whatsapp(self, lead: Lead, message: str) -> bool:
        """Send WhatsApp message via Twilio"""
        try:
            from twilio.rest import Client as TwilioClient
            twilio = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            to_number = lead.whatsapp or lead.phone
            if not to_number:
                return False

            twilio.messages.create(
                body=message,
                from_=settings.twilio_whatsapp_from,
                to=f"whatsapp:{to_number}",
            )
            logger.info(f"[WhatsApp] Sent to {lead.company_name} ({to_number})")
            return True
        except Exception as e:
            logger.error(f"[WhatsApp] Send error: {e}")
            return False

    async def _send_email(self, lead: Lead, subject: str, body: str) -> bool:
        """Send email via SMTP"""
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            if not lead.email:
                return False

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.email_from_name} <{settings.smtp_user}>"
            msg["To"] = lead.email
            msg.attach(MIMEText(body, "plain"))

            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                start_tls=True,
            )
            logger.info(f"[Email] Sent to {lead.company_name} ({lead.email})")
            return True
        except Exception as e:
            logger.error(f"[Email] Send error: {e}")
            return False
