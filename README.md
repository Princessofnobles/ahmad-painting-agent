# Ahmad Al Zahidi Painting LLC — AI Client Acquisition Agent

An AI-powered lead generation and outreach automation system for a Dubai-based painting company.

## Overview

This system automatically discovers potential clients in Dubai, detects painting opportunities, generates personalized outreach, and manages follow-ups — all from a single dashboard.

## Modules

| Module | Description |
|--------|-------------|
| **Lead Discovery Agent** | Scrapes Google Maps, LinkedIn, directories for Dubai leads |
| **Opportunity Detection Agent** | AI signals for who needs painting now |
| **Outreach Generator** | Personalized WhatsApp, Email, LinkedIn messages |
| **SEO & Maps Agent** | Finds businesses with visual exterior issues |
| **Follow-Up Automation** | 5-step drip sequence over 21 days |
| **CRM Dashboard** | Full lead management UI |
| **WhatsApp Handler** | AI response suggestions for inbound replies |

## Quick Start

```bash
# 1. Clone / open in Cursor
cd ahmad-painting-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Initialize database
python scripts/init_db.py

# 6. Run the server
uvicorn api.main:app --reload --port 8000

# 7. Open dashboard
# Visit http://localhost:8000
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: SQLite (dev) → PostgreSQL (prod)
- **AI**: OpenAI GPT-4o via API
- **Scraping**: Playwright, BeautifulSoup, SerpAPI
- **Scheduling**: APScheduler
- **Frontend**: Vanilla HTML/CSS/JS dashboard

## Project Structure

```
ahmad-painting-agent/
├── agents/
│   ├── lead_discovery/       # Find potential clients
│   ├── opportunity_detection/ # AI scoring & signals
│   ├── outreach/             # Message generation
│   ├── seo_maps/             # Google Maps agent
│   ├── followup/             # Drip sequences
│   └── whatsapp/             # Inbound handler
├── api/
│   ├── main.py               # FastAPI app entry
│   └── routers/              # API route handlers
├── dashboard/                # Frontend UI
├── database/                 # Models & migrations
├── templates/                # Outreach message templates
├── config/                   # Settings & constants
├── scripts/                  # CLI utilities
└── docs/                     # Guides & architecture
```

## License

Private — Ahmad Al Zahidi Painting LLC
# ahmad-painting-agent
