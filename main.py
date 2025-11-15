import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import requests

app = FastAPI(title="Currency Converter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


def fetch_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """Fetch FX rate using exchangerate.host with graceful fallback.
    Returns rate or None if unavailable.
    """
    try:
        url = f"https://api.exchangerate.host/latest?base={from_currency.upper()}&symbols={to_currency.upper()}"
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            rate = data.get("rates", {}).get(to_currency.upper())
            if isinstance(rate, (int, float)):
                return float(rate)
    except Exception:
        pass
    return None

@app.get("/api/convert")
def convert_currency(
    amount: float = Query(..., gt=0, description="Amount to convert"),
    from_currency: str = Query("OMR", min_length=3, max_length=3, description="Source currency (e.g., OMR)"),
    to_currency: str = Query("USD", min_length=3, max_length=3, description="Target currency (e.g., USD)"),
):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    rate = fetch_rate(from_currency, to_currency)
    source = "live"

    # Fallback: common OMR→USD approximate rate if live fetch fails
    if rate is None and from_currency == "OMR" and to_currency == "USD":
        rate = 2.597
        source = "fallback"

    if rate is None:
        return {
            "success": False,
            "message": "Unable to retrieve exchange rate right now.",
            "from": from_currency,
            "to": to_currency,
        }

    result = amount * rate
    return {
        "success": True,
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
        "rate": rate,
        "result": result,
        "source": source,
    }


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
