"""Webhooks Router — for Twilio WhatsApp inbound"""
from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db

router = APIRouter()


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(default=""),
    Body: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Twilio WhatsApp inbound webhook"""
    from agents.whatsapp.agent import WhatsAppHandlerAgent
    agent = WhatsAppHandlerAgent()
    payload = {"From": From, "Body": Body}
    result = await agent.handle_webhook(payload, db)

    # Return TwiML response
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>{result.get('suggested_reply', 'Thank you for your message! We will get back to you shortly.')}</Message>
</Response>"""
    from fastapi.responses import Response
    return Response(content=twiml, media_type="application/xml")


@router.post("/whatsapp/analyze")
async def analyze_whatsapp_reply(
    lead_id: int,
    message: str,
    db: AsyncSession = Depends(get_db),
):
    """Manually analyze a WhatsApp reply for a lead"""
    from agents.whatsapp.agent import WhatsAppHandlerAgent
    agent = WhatsAppHandlerAgent()
    return await agent.handle_inbound(lead_id, message, db)
