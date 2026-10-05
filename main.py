import os
from datetime import date
import requests

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="F&O Trading API")

UPSTOX_TOKEN = os.getenv("UPSTOX_TOKEN")
UPSTOX_BASE = "https://api.upstox.com/v2"


# ---------- Basic ----------

@app.get("/")
def home():
    return {
        "status": "F&O API is running",
        "data_provider": "Upstox"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ---------- Helper ----------

def upstox_get(endpoint, params=None):
    if not UPSTOX_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="UPSTOX_TOKEN is not configured"
        )

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {UPSTOX_TOKEN}"
    }

    response = requests.get(
        f"{UPSTOX_BASE}{endpoint}",
        headers=headers,
        params=params,
        timeout=15
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


# ---------- Option Contracts ----------

@app.get("/option-contracts")
def option_contracts(
    index: str = "NIFTY",
    expiry: str | None = None
):
    instruments = {
        "NIFTY": "NSE_INDEX|Nifty 50",
        "BANKNIFTY": "NSE_INDEX|Nifty Bank"
    }

    if index.upper() not in instruments:
        raise HTTPException(
            status_code=400,
            detail="Use NIFTY or BANKNIFTY"
        )

    params = {
        "instrument_key": instruments[index.upper()]
    }

    if expiry:
        params["expiry_date"] = expiry

    return upstox_get("/option/contract", params)


# ---------- Option Chain ----------

@app.get("/option-chain")
def option_chain(
    index: str = "NIFTY",
    expiry: str | None = None
):
    instruments = {
        "NIFTY": "NSE_INDEX|Nifty 50",
        "BANKNIFTY": "NSE_INDEX|Nifty Bank"
    }

    if index.upper() not in instruments:
        raise HTTPException(
            status_code=400,
            detail="Use NIFTY or BANKNIFTY"
        )

    if not expiry:
        raise HTTPException(
            status_code=400,
            detail="Please provide expiry in YYYY-MM-DD format"
        )

    params = {
        "instrument_key": instruments[index.upper()],
        "expiry_date": expiry
    }

    return upstox_get("/option/chain", params)


# ---------- P&L ----------

class Position(BaseModel):
    entry_price: float
    current_price: float
    quantity: int
    position: str


@app.post("/pnl")
def calculate_pnl(position: Position):

    side = position.position.upper()

    if side == "BUY":
        pnl = (
            position.current_price - position.entry_price
        ) * position.quantity

    elif side == "SELL":
        pnl = (
            position.entry_price - position.current_price
        ) * position.quantity

    else:
        raise HTTPException(
            status_code=400,
            detail="Position must be BUY or SELL"
        )

    return {
        "position": side,
        "entry_price": position.entry_price,
        "current_price": position.current_price,
        "quantity": position.quantity,
        "pnl": round(pnl, 2)
    }


# ---------- Signal ----------

class SignalData(BaseModel):
    price_change_percent: float
    oi_change_percent: float
    pcr: float
    volume_change_percent: float


@app.post("/signal")
def trading_signal(data: SignalData):

    score = 0

    if data.price_change_percent > 0:
        score += 1
    elif data.price_change_percent < 0:
        score -= 1

    if data.oi_change_percent > 0:
        if data.price_change_percent > 0:
            score += 1
        elif data.price_change_percent < 0:
            score -= 1

    if data.pcr > 1.2:
        score += 1
    elif data.pcr < 0.8:
        score -= 1

    if data.volume_change_percent > 20:
        score += 1

    if score >= 3:
        signal = "STRONG BUY"
    elif score >= 1:
        signal = "BUY"
    elif score <= -3:
        signal = "STRONG SELL"
    elif score <= -1:
        signal = "SELL"
    else:
        signal = "NEUTRAL"

    return {
        "signal": signal,
        "score": score
    }
