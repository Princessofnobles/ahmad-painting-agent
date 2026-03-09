# Deployment Guide — Ahmad Al Zahidi Painting AI Agent System

## Local Development (Cursor / VS Code)

### 1. Prerequisites
- Python 3.11+
- pip
- Git

### 2. Setup

```bash
# Clone the project and enter directory
cd ahmad-painting-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for scraping)
playwright install chromium

# Copy and configure environment
cp .env.example .env
# Now edit .env with your actual API keys
```

### 3. Configure API Keys

Edit `.env`:

| Key | Where to Get |
|-----|-------------|
| `OPENAI_API_KEY` | https://platform.openai.com |
| `SERPAPI_KEY` | https://serpapi.com (free tier: 100 searches/month) |
| `TWILIO_*` | https://twilio.com (WhatsApp sandbox for testing) |
| `SMTP_*` | Gmail App Password: myaccount.google.com → Security → App Passwords |

### 4. Initialize Database

```bash
python scripts/init_db.py --seed     # creates DB + adds 5 sample leads
```

### 5. Run the Server

```bash
uvicorn api.main:app --reload --port 8000
```

Open: http://localhost:8000

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/leads/ | List all leads (paginated) |
| POST | /api/leads/ | Create lead manually |
| GET | /api/leads/{id} | Get lead details |
| PUT | /api/leads/{id} | Update lead |
| DELETE | /api/leads/{id} | Delete lead |
| GET | /api/leads/{id}/messages | View outreach messages |
| GET | /api/leads/{id}/followups | View follow-up sequence |
| POST | /api/agents/discover | Run lead discovery |
| POST | /api/agents/score-leads | Score all new leads |
| POST | /api/agents/generate-outreach/{id} | Generate outreach for lead |
| POST | /api/agents/schedule-followup/{id} | Schedule follow-up sequence |
| POST | /api/agents/seo-scan | Run SEO Maps scan |
| POST | /api/agents/process-followups | Send due follow-ups |
| GET | /api/agents/status | Agent system status |
| GET | /api/dashboard/stats | Dashboard analytics |
| GET | /api/dashboard/top-leads | Top-scored leads |
| POST | /api/outreach/generate-all | Generate for all top leads |
| POST | /webhooks/whatsapp | Twilio WhatsApp webhook |

---

## WhatsApp Setup (Twilio)

1. Create Twilio account at https://twilio.com
2. Enable WhatsApp Sandbox
3. Get your WhatsApp sandbox number
4. Set webhook URL to: `https://yourdomain.com/webhooks/whatsapp`
5. Update `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxx
   TWILIO_AUTH_TOKEN=xxxx
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```

---

## Production Deployment (Ubuntu VPS)

```bash
# Install system deps
sudo apt update && sudo apt install python3.11 python3-pip nginx certbot

# Clone project
git clone <your-repo> /opt/ahmad-painting
cd /opt/ahmad-painting

# Setup
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps

# Environment
cp .env.example .env
# Edit .env with production values
# Change DATABASE_URL to PostgreSQL for production

# Initialize DB
python scripts/init_db.py

# Create systemd service
sudo nano /etc/systemd/system/ahmad-painting.service
```

**Systemd service file:**
```ini
[Unit]
Description=Ahmad Al Zahidi Painting AI Agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ahmad-painting
Environment=PATH=/opt/ahmad-painting/venv/bin
ExecStart=/opt/ahmad-painting/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable ahmad-painting
sudo systemctl start ahmad-painting

# Nginx config
sudo nano /etc/nginx/sites-available/ahmad-painting
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo certbot --nginx -d yourdomain.com
sudo systemctl restart nginx
```

---

## Scheduled Agent Runs

Agents run automatically via APScheduler:
- **8:00 AM UAE daily** — Lead Discovery
- **8:30 AM UAE daily** — Opportunity Scoring  
- **9:00 AM UAE daily** — Follow-Up Processing
- **Monday 10:00 AM UAE** — SEO Maps Scan

To change schedules, edit `api/scheduler.py`.

---

## SerpAPI Free Tier

The free SerpAPI plan gives **100 searches/month**.
- Each discovery run uses ~15-20 queries
- Recommended: run discovery 3-4x per month
- For daily use, upgrade to paid plan (~$50/month)

Alternatively, implement Playwright-based scraping to avoid API costs.

---

## Cost Estimate (Monthly)

| Service | Cost |
|---------|------|
| VPS (DigitalOcean) | ~$12/month |
| OpenAI API (GPT-4o) | ~$5-20/month |
| SerpAPI (Basic) | $50/month |
| Twilio WhatsApp | ~$0.005/message |
| Gmail SMTP | Free |
| **Total** | **~$70-90/month** |

For a painting company generating even 1-2 new clients per month, ROI is very high.
