"""
InfluxDB API Endpoints for Querying Metrics
Add these to bridge_server.py
"""

from fastapi import HTTPException

@app.get("/influx/equity")
async def get_equity_history(hours: int = 24):
    """Get equity history for charting."""
    if influx_db and influx_db.connected:
        data = influx_db.query_equity_history(hours=hours)
        return {"data": data}
    else:
        raise HTTPException(status_code=503, detail="InfluxDB not available")

@app.get("/influx/trades")
async def get_recent_trades(limit: int = 50):
    """Get recent trade history from InfluxDB."""
    if influx_db and influx_db.connected:
        trades = influx_db.query_recent_trades(limit=limit)
        return {"trades": trades}
    else:
        raise HTTPException(status_code=503, detail="InfluxDB not available")

@app.get("/influx/status")
async def get_influx_status():
    """Check InfluxDB connection status."""
    if influx_db:
        return {
            "connected": influx_db.connected,
            "url": influx_db.url,
            "bucket": influx_db.bucket,
            "org": influx_db.org
        }
    else:
        return {"connected": False, "message": "InfluxDB not initialized"}
