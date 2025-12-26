import requests
from typing import Optional
from datetime import date

BASE_URL = "https://fintro-backend-883163069340.asia-south1.run.app"

def fetch_payments(
    org_id: int,
    start: Optional[date] = None,
    end: Optional[date] = None
):
    url = f"{BASE_URL}/payments/org/{org_id}"
    params = {}

    if start:
        params["from"] = start.isoformat()
    if end:
        params["to"] = end.isoformat()

    res = requests.get(url, params=params or None, timeout=10)
    res.raise_for_status()
    return res.json()["payments"]
