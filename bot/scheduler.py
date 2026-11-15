import logging
from apscheduler.schedulers.background import BackgroundScheduler
from services.news_service import get_today_high_impact_news
from services.market_data import get_market_prices
from config import settings

logger = logging.getLogger(__name__)

def job_morning_brief():
    """Task that runs daily at 11:00 AM PKT for Morning Briefing."""
    news = get_today_high_impact_news()
    prices = get_market_prices()
    
    brief = (
        "Good morning! Here's your EUR/USD briefing for today.\n"
        f"Bias: Neutral (Waiting for London open)\n"
        f"DXY: {prices['DXY']} | US10Y: {prices['US10Y']}%\n"
        "Scheduled News Today:\n"
    )
    for event in news:
        brief += f"- {event['time_pkt']}: {event['event']} ({event['impact']} Impact)\n"
        
    logger.info("Morning Brief Triggered:\n" + brief)
    # Note: To push this to Telegram, you can wire a bot application instance here.

def start_scheduler() -> BackgroundScheduler:
    """Start the background scheduler in the configured timezone."""
    scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)
    # Schedule the morning brief at 11:00 AM PKT daily.
    scheduler.add_job(job_morning_brief, "cron", hour=11, minute=0)
    scheduler.start()
    logger.info("APScheduler started successfully in %s timezone.", settings.TIMEZONE)
    return scheduler
    