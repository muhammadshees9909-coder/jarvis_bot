from datetime import datetime

def get_today_high_impact_news() -> list:
    """
    Fetches today's high and medium impact economic events related to USD and EUR.
    Filters out low-impact events.
    """
    # Mock filtered economic calendar data for USD/EUR
    events = [
        {
            "time_pkt": "12:30 AM PKT",
            "currency": "USD",
            "event": "Non-Farm Payrolls (NFP)",
            "impact": "High",
            "forecast": "180K",
            "previous": "140K"
        },
        {
            "time_pkt": "05:15 AM PKT",
            "currency": "USD",
            "event": "ISM Manufacturing PMI",
            "impact": "High",
            "forecast": "52.5",
            "previous": "51.8"
        },
        {
            "time_pkt": "09:00 AM PKT",
            "currency": "EUR",
            "event": "Eurozone CPI (Harmonized)",
            "impact": "Medium",
            "forecast": "+0.5%",
            "previous": "+0.2%"
        },
        {
            "time_pkt": "12:30 PM PKT",
            "currency": "USD",
            "event": "FOMC Rate Decision",
            "impact": "High",
            "forecast": "+5.25% to 5.50%",
            "previous": "+5.25% to 5.50%"
        },
        {
            "time_pkt": "02:00 PM PKT",
            "currency": "USD",
            "event": "ADP Non-Farm Employment Change",
            "impact": "Medium",
            "forecast": "130K",
            "previous": "140K"
        },
        {
            "time_pkt": "04:00 PM PKT",
            "currency": "EUR",
            "event": "Eurozone Retail Sales M/M",
            "impact": "Medium",
            "forecast": "+0.2%",
            "previous": "-0.1%"
        }
    ]

    # Ensure only Medium or High impact are returned
    filtered_events = [e for e in events if e["impact"] in ["High", "Medium"]]
    return filtered_events

def get_news_events() -> list:
    """Return the latest high-impact USD/EUR economic events (wrapped API)."""
    return get_today_high_impact_news()
