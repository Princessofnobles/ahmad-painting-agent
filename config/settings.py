"""
Central configuration for Ahmad Al Zahidi Painting AI Agent System
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", env="OPENAI_MODEL")

    # SerpAPI
    serpapi_key: str = Field("", env="SERPAPI_KEY")

    # Email
    smtp_host: str = Field("smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_user: str = Field("", env="SMTP_USER")
    smtp_password: str = Field("", env="SMTP_PASSWORD")
    email_from_name: str = Field("Ahmad Al Zahidi Painting LLC", env="EMAIL_FROM_NAME")

    # WhatsApp
    whatsapp_provider: str = Field("twilio", env="WHATSAPP_PROVIDER")
    twilio_account_sid: str = Field("", env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field("", env="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str = Field("", env="TWILIO_WHATSAPP_FROM")

    # Database
    database_url: str = Field(
        "sqlite+aiosqlite:///./data/ahmad_painting.db",
        env="DATABASE_URL"
    )

    # App
    app_secret_key: str = Field("changeme-secret-key", env="APP_SECRET_KEY")
    app_host: str = Field("0.0.0.0", env="APP_HOST")
    app_port: int = Field(8000, env="APP_PORT")
    debug: bool = Field(True, env="DEBUG")

    # Company
    company_name: str = Field("Ahmad Al Zahidi Painting LLC", env="COMPANY_NAME")
    company_phone: str = Field("+971 XX XXX XXXX", env="COMPANY_PHONE")
    company_email: str = Field("info@ahmadpainting.ae", env="COMPANY_EMAIL")
    company_website: str = Field("https://ahmadpainting.ae", env="COMPANY_WEBSITE")
    company_location: str = Field("Dubai, UAE", env="COMPANY_LOCATION")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


# -------------------------------------------------------
# Company Profile (used by AI agents for context)
# -------------------------------------------------------
COMPANY_PROFILE = {
    "name": "Ahmad Al Zahidi Painting LLC",
    "experience_years": 20,
    "location": "Dubai, UAE",
    "services": [
        "Interior Painting",
        "Exterior Painting",
        "Villa Painting",
        "Apartment Painting",
        "Commercial Painting",
        "Industrial Painting",
        "Surface Preparation & Priming",
        "Color Consultation",
    ],
    "usp": [
        "20+ years of experience in Dubai",
        "Dubai climate-resistant premium paints",
        "Minimal disruption to businesses and residents",
        "2-year painting warranty on all projects",
        "Free site consultation and color advice",
        "Serving residential and commercial properties across Dubai",
    ],
    "target_clients": [
        "Property management companies",
        "Real estate developers",
        "Villa owners",
        "Apartment building managers",
        "Hotels and hospitality",
        "Restaurants and cafes",
        "Office buildings",
        "Construction companies",
        "Facility management companies",
    ],
}

# -------------------------------------------------------
# Dubai Search Targets
# -------------------------------------------------------
DUBAI_SEARCH_QUERIES = [
    "property management company Dubai",
    "real estate developer Dubai",
    "villa community management Dubai",
    "apartment building manager Dubai",
    "hotel facility management Dubai",
    "restaurant owner Dubai",
    "office building manager Dubai",
    "construction company Dubai",
    "facility management company Dubai",
    "building maintenance company Dubai",
    "residential community Dubai",
    "commercial property Dubai",
    "strata management Dubai",
    "hospitality management Dubai",
]

# Lead scoring weights
LEAD_SCORE_WEIGHTS = {
    "has_email": 20,
    "has_phone": 15,
    "has_website": 10,
    "high_opportunity_signal": 30,
    "decision_maker_contact": 25,
}
