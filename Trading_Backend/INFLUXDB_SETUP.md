# InfluxDB Setup Guide for Spidy

## Option 1: Docker (Recommended)

### Install Docker Desktop for Windows:
1. Download from https://www.docker.com/products/docker-desktop/
2. Install and restart computer
3. Start Docker Desktop

### Run InfluxDB Container:
```powershell
docker run -d -p 8086:8086 `
  -v influxdb-data:/var/lib/influxdb2 `
  --name spidy-influxdb `
  influxdb:2.7
```

### Initial Setup:
1. Open browser: http://localhost:8086
2. Setup wizard:
   - Username: `admin`
   - Password: (choose secure password)
   - Organization: `spidy`
   - Bucket: `trading_metrics`
   - Click "Configure"
3. Copy the generated token (looks like: `abc123xyz...`)
4. Add token to `.env` file:
   ```
   INFLUXDB_TOKEN=your_token_here
   ```

---

## Option 2: Windows Native Install

### Download & Install:
1. Download from https://portal.influxdata.com/downloads/
2. Extract to `C:\influxdb`
3. Run in PowerShell:
   ```powershell
   cd C:\influxdb
   .\influxd.exe
   ```
4. Follow browser setup at http://localhost:8086 (same as Docker)

---

## Verify Installation

Test connection:
```powershell
cd Trading_Backend
python influxdb_manager.py
```

Expected output:
```
Testing InfluxDB Connection...
✅ InfluxDB Connected: http://localhost:8086
✅ InfluxDB Ready
✅ Test data written
✅ Queried 1 trades
```

---

## Integration with Spidy

InfluxDB will automatically start when `bridge_server.py` launches.

If InfluxDB is NOT running, the system gracefully continues without metrics logging.

---

## Grafana Dashboard (Optional)

For visualization:
```powershell
docker run -d -p 3001:3000 `
  --name spidy-grafana `
  grafana/grafana
```

Access: http://localhost:3001 (admin/admin)

Add InfluxDB data source:
- URL: http://host.docker.internal:8086
- Organization: spidy
- Token: (paste from .env)
- Bucket: trading_metrics

---

## Troubleshooting

**Port 8086 already in use:**
```powershell
docker stop spidy-influxdb
docker rm spidy-influxdb
```

**Can't connect:**
- Check Docker Desktop is running
- Firewall: Allow port 8086
- Test: `curl http://localhost:8086/health`
