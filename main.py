from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="F&O Trading API")


# ---------- P&L Calculator ----------

class Position(BaseModel):
    entry_price: float
    current_price: float
    quantity: int
    position: str  # BUY or SELL


@app.get("/")
def home():
    return {"status": "F&O API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/pnl")
def calculate_pnl(position: Position):

    if position.position.upper() == "BUY":
        pnl = (position.current_price - position.entry_price) * position.quantity

    elif position.position.upper() == "SELL":
        pnl = (position.entry_price - position.current_price) * position.quantity

    else:
        return {
            "error": "Position must be BUY or SELL"
        }

    return {
        "position": position.position.upper(),
        "entry_price": position.entry_price,
        "current_price": position.current_price,
        "quantity": position.quantity,
        "pnl": round(pnl, 2)
    }


# ---------- Trading Signal ----------

class SignalData(BaseModel):
    price_change_percent: float
    oi_change_percent: float
    pcr: float
    volume_change_percent: float


@app.post("/signal")
def trading_signal(data: SignalData):

    score = 0

    # Price trend
    if data.price_change_percent > 0:
        score += 1
    elif data.price_change_percent < 0:
        score -= 1

    # OI confirmation
    if data.oi_change_percent > 0 and data.price_change_percent > 0:
        score += 1
    elif data.oi_change_percent > 0 and data.price_change_percent < 0:
        score -= 1

    # PCR
    if data.pcr > 1.2:
        score += 1
    elif data.pcr < 0.8:
        score -= 1

    # Volume
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
