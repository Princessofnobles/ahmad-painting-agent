"""
Normalize raw scraped data into Lead model fields
"""
import re
from database.models import LeadSource


def normalize_phone(phone: str) -> str:
    """Clean and normalize phone number to international format"""
    if not phone:
        return ""
    # Remove everything except digits and +
    cleaned = re.sub(r"[^\d+]", "", phone)
    # UAE numbers
    if cleaned.startswith("0") and len(cleaned) == 10:
        cleaned = "+971" + cleaned[1:]
    elif cleaned.startswith("971") and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def normalize_email(email: str) -> str:
    if not email:
        return ""
    email = email.strip().lower()
    if re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return email
    return ""


def normalize_website(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url and not url.startswith("http"):
        url = "https://" + url
    return url


def normalize_lead(raw: dict) -> dict:
    """Convert raw scraped dict into clean Lead fields"""
    return {
        "company_name": raw.get("company_name", "").strip(),
        "contact_name": raw.get("contact_name", ""),
        "contact_title": raw.get("contact_title", ""),
        "phone": normalize_phone(raw.get("phone", "")),
        "whatsapp": normalize_phone(raw.get("phone", "")),  # assume same initially
        "email": normalize_email(raw.get("email", "")),
        "website": normalize_website(raw.get("website", "")),
        "linkedin_url": raw.get("linkedin_url", ""),
        "address": raw.get("address", ""),
        "area": raw.get("area", ""),
        "city": "Dubai",
        "google_maps_url": raw.get("google_maps_url", ""),
        "business_category": raw.get("business_category", ""),
        "lead_source": raw.get("lead_source", LeadSource.MANUAL),
        "raw_data": raw.get("raw_data", raw),
    }
