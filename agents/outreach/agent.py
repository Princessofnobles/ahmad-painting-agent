"""
Personalized Outreach Generator Agent
Creates customized WhatsApp, Email, and LinkedIn messages for each lead.
"""
import json
import google.generativeai as genai
from loguru import logger
from datetime import datetime

from config.settings import settings, COMPANY_PROFILE
from database.models import Lead, OutreachMessage, OutreachChannel

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")


# -------------------------------------------------------
# Message Templates (fallback if AI is unavailable)
# -------------------------------------------------------
WHATSAPP_TEMPLATE = """Hello {contact_name}! 👋

I'm reaching out from *Ahmad Al Zahidi Painting LLC* — a trusted painting company serving Dubai for over 20 years.

We specialize in {service_type} for {business_type} like {company_name}, and we'd love to show you what we can do.

✅ Premium quality paints — Dubai climate resistant
✅ 2-year painting warranty on all projects
✅ Minimal disruption to your operations
✅ Free site consultation and color advice

Would you be open to a free inspection of your property? I can arrange a visit at your convenience.

Best regards,
Ahmad Al Zahidi Painting LLC 🎨
📞 {company_phone}"""

EMAIL_TEMPLATE = """Subject: Enhance Your Property's Appeal — Free Painting Consultation for {company_name}

Dear {contact_name},

I hope this message finds you well.

My name is Ahmad, and I'm reaching out from Ahmad Al Zahidi Painting LLC — Dubai's trusted painting specialists with over 20 years of experience in residential and commercial projects.

I noticed that {company_name} {opportunity_note}, and I believe we can help refresh and protect your property with our premium painting services.

**Why Dubai businesses and property managers choose us:**
• 20+ years serving Dubai's residential and commercial properties
• Dubai climate-resistant paints that withstand harsh summers
• Minimal disruption — we work around your schedule
• 2-year warranty on all painting projects
• Free color consultation and site inspection

**Our services include:**
Interior & Exterior Painting | Villa & Apartment Painting | Commercial & Industrial Painting | Surface Preparation & Priming

I'd love to schedule a free no-obligation site inspection at {company_name}. This will allow us to provide a detailed proposal tailored to your specific needs.

Would you be available for a brief call this week? I can also arrange a site visit at your convenience.

Thank you for your time, and I look forward to hearing from you.

Warm regards,

Ahmad Al Zahidi
Ahmad Al Zahidi Painting LLC
📞 {company_phone}
📧 {company_email}
🌐 {company_website}
📍 Dubai, UAE"""

LINKEDIN_TEMPLATE = """Hi {contact_name},

I came across {company_name} and was impressed by your work in {business_type} across Dubai.

I'm reaching out from Ahmad Al Zahidi Painting LLC — we've been serving Dubai's property sector for 20+ years, working with property managers, developers, and facility teams to maintain and enhance their properties.

We specialize in {service_type} with:
✅ Climate-resistant premium paints
✅ Minimal operational disruption
✅ 2-year warranty

Would you be open to a quick call to explore how we might support your properties?

Best,
Ahmad Al Zahidi Painting LLC"""


# -------------------------------------------------------
# AI Message Generator
# -------------------------------------------------------
async def generate_whatsapp_message(lead: Lead) -> str:
    """Generate personalized WhatsApp message for a lead"""

    prompt = f"""You are writing a WhatsApp message for Ahmad Al Zahidi Painting LLC, a Dubai painting company.

Company: {json.dumps(COMPANY_PROFILE, indent=2)}

Lead to contact:
- Company: {lead.company_name}
- Category: {lead.business_category}
- Area: {lead.area or lead.city}
- AI Notes: {lead.ai_notes or ''}
- Opportunity Signals: {json.dumps(lead.opportunity_signals or [], indent=2)}

Write a friendly, professional WhatsApp message that:
1. Opens with a warm greeting
2. Briefly introduces Ahmad Al Zahidi Painting LLC
3. References something specific about their business type
4. Highlights 2-3 key benefits relevant to them
5. Offers a free site inspection
6. Ends with a clear call-to-action
7. Includes emojis appropriately (not excessive)
8. Is under 200 words
9. Is in English (UAE business standard)

Do NOT use placeholders. Write the complete ready-to-send message."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"[Outreach] WhatsApp gen error: {e}")
        return WHATSAPP_TEMPLATE.format(
            contact_name=lead.contact_name or "there",
            company_name=lead.company_name,
            service_type="interior and exterior painting",
            business_type=lead.business_category or "business",
            company_phone=settings.company_phone,
        )


async def generate_email_message(lead: Lead) -> tuple[str, str]:
    """Generate personalized email subject and body"""

    prompt = f"""You are writing a sales email for Ahmad Al Zahidi Painting LLC, a Dubai painting company.

Company: {json.dumps(COMPANY_PROFILE, indent=2)}

Lead to contact:
- Company: {lead.company_name}
- Category: {lead.business_category}
- Area: {lead.area or lead.city}
- AI Notes: {lead.ai_notes or ''}

Write a professional, personalized email that:
1. Has a compelling subject line (not generic)
2. Opens by referencing their specific business type
3. Explains a relevant pain point they likely have
4. Presents Ahmad Al Zahidi's solution
5. Lists 3-4 specific benefits
6. Offers a free no-obligation consultation
7. Has a clear single call-to-action
8. Is under 250 words
9. Has proper professional sign-off

Respond in JSON:
{{
  "subject": "email subject line",
  "body": "full email body"
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        return result.get("subject", ""), result.get("body", "")
    except Exception as e:
        logger.error(f"[Outreach] Email gen error: {e}")
        subject = f"Premium Painting Services for {lead.company_name} — Free Consultation"
        body = EMAIL_TEMPLATE.format(
            contact_name=lead.contact_name or "Sir/Madam",
            company_name=lead.company_name,
            opportunity_note="may benefit from professional painting services",
            company_phone=settings.company_phone,
            company_email=settings.company_email,
            company_website=settings.company_website,
        )
        return subject, body


async def generate_linkedin_message(lead: Lead) -> str:
    """Generate personalized LinkedIn connection message"""

    prompt = f"""Write a short LinkedIn connection/message for Ahmad Al Zahidi Painting LLC to send to a potential client.

Company context: {json.dumps(COMPANY_PROFILE, indent=2)}

Recipient:
- Company: {lead.company_name}
- Category: {lead.business_category}
- Area: {lead.area}

Requirements:
- Under 300 characters for connection request note, OR
- Under 150 words for InMail
- Professional but personable
- Specific to their industry
- Clear value proposition
- No spam feel

Write the message (InMail format)."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"[Outreach] LinkedIn gen error: {e}")
        return LINKEDIN_TEMPLATE.format(
            contact_name=lead.contact_name or "there",
            company_name=lead.company_name,
            business_type=lead.business_category or "your sector",
            service_type="commercial and residential painting",
        )


# -------------------------------------------------------
# Outreach Orchestrator
# -------------------------------------------------------
class OutreachGeneratorAgent:

    async def generate_for_lead(
        self,
        lead: Lead,
        channels: list[OutreachChannel] = None,
    ) -> list[OutreachMessage]:
        """Generate outreach messages for a lead across channels"""

        if channels is None:
            # Select channels based on available contact info
            channels = []
            if lead.whatsapp or lead.phone:
                channels.append(OutreachChannel.WHATSAPP)
            if lead.email:
                channels.append(OutreachChannel.EMAIL)
            if lead.linkedin_url:
                channels.append(OutreachChannel.LINKEDIN)
            if not channels:
                channels = [OutreachChannel.WHATSAPP]  # default

        messages = []

        for channel in channels:
            try:
                if channel == OutreachChannel.WHATSAPP:
                    body = await generate_whatsapp_message(lead)
                    msg = OutreachMessage(
                        lead_id=lead.id,
                        channel=channel,
                        body=body,
                    )

                elif channel == OutreachChannel.EMAIL:
                    subject, body = await generate_email_message(lead)
                    msg = OutreachMessage(
                        lead_id=lead.id,
                        channel=channel,
                        subject=subject,
                        body=body,
                    )

                elif channel == OutreachChannel.LINKEDIN:
                    body = await generate_linkedin_message(lead)
                    msg = OutreachMessage(
                        lead_id=lead.id,
                        channel=channel,
                        body=body,
                    )
                else:
                    continue

                messages.append(msg)
                logger.info(
                    f"[Outreach] Generated {channel.value} message for {lead.company_name}"
                )

            except Exception as e:
                logger.error(
                    f"[Outreach] Failed to generate {channel.value} for {lead.company_name}: {e}"
                )

        return messages
