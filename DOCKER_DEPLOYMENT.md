# FRC Scouting System - Docker Deployment Guide

## Quick Start

### Prerequisites
- Docker and Docker Compose installed on your homeserver
- Ports 80, 8000, and 8501 available

### Deployment

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd scoutification
   ```

2. **Start the services:**
   ```bash
   docker compose up -d
   ```

3. **Access the applications:**
   - **Scouting App (index.html):** http://your-server/
   - **Pit Scouting (pit.html):** http://your-server/pit.html
   - **QR Scanner (scanner.html):** http://your-server/scanner.html
   - **Dashboard:** http://your-server:8501
   - **API:** http://your-server:8000

### Architecture

The system consists of three Docker services:

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Frontend   │  │   Backend    │  │  Dashboard   │  │
│  │   (Nginx)    │  │  (FastAPI)   │  │ (Streamlit)  │  │
│  │   Port 80    │  │  Port 8000   │  │  Port 8501   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                 │                  │           │
│         └─────────────────┴──────────────────┘           │
│                           │                              │
│                    ┌──────▼──────┐                       │
│                    │   Volume    │                       │
│                    │  scout-db   │                       │
│                    │  (SQLite)   │                       │
│                    └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

#### Service Details

**Frontend (Nginx):**
- Serves static HTML files: index.html, pit.html, scanner.html
- Proxies API requests to the backend
- Port: 80

**Backend (FastAPI):**
- RESTful API with `/api/submit` endpoint
- Handles match and pit data submissions
- SQLite database stored in shared volume
- Port: 8000

**Dashboard (Streamlit):**
- Data visualization and analysis
- Pick list formulation
- Team analysis
- Match predictor
- Port: 8501

### Usage Workflow

1. **Scouting Tablets/Phones:**
   - Open http://your-server/ or http://your-server/pit.html
   - Fill out forms
   - Generate QR codes

2. **Scanner Station:**
   - Open http://your-server/scanner.html on a device with a camera
   - Point camera at QR codes
   - Data automatically saves to database

3. **Analysis:**
   - Open http://your-server:8501
   - View team statistics
   - Create pick lists
   - Predict match outcomes

### Docker Commands

**View logs:**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f dashboard
docker compose logs -f frontend
```

**Restart services:**
```bash
# All services
docker compose restart

# Specific service
docker compose restart backend
```

**Stop services:**
```bash
docker compose down
```

**Stop and remove volumes (⚠️ deletes database):**
```bash
docker compose down -v
```

**Rebuild containers:**
```bash
docker compose up -d --build
```

### Data Backup

The database is stored in a Docker volume named `scout-db`. To backup:

```bash
# Create backup directory
mkdir -p backups

# Copy database from container
docker run --rm \
  -v scout-db:/data \
  -v $(pwd)/backups:/backup \
  alpine cp /data/scouting_data.db /backup/scouting_data_$(date +%Y%m%d_%H%M%S).db
```

### Data Restore

```bash
# Restore from backup
docker run --rm \
  -v scout-db:/data \
  -v $(pwd)/backups:/backup \
  alpine cp /backup/your_backup.db /data/scouting_data.db
```

### Troubleshooting

**Services won't start:**
```bash
# Check if ports are in use
sudo netstat -tulpn | grep -E ':(80|8000|8501)'

# View detailed logs
docker compose logs
```

**Database issues:**
```bash
# Access database directly
docker run --rm -it \
  -v scout-db:/data \
  alpine sh

# Inside container:
ls -la /data/
```

**Clear cache and rebuild:**
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Network Configuration

For external access (from other devices on your network):

1. Find your server's IP address:
   ```bash
   ip addr show
   ```

2. Access from other devices:
   - Scouting: http://SERVER_IP/
   - Scanner: http://SERVER_IP/scanner.html
   - Dashboard: http://SERVER_IP:8501

### Security Notes

**IMPORTANT: This setup is designed for local/homelab deployment. For production:**

1. **Configure CORS properly** in `api.py`:
   ```python
   allow_origins=["http://your-server.com", "https://your-server.com"]
   ```

2. **Use HTTPS** with SSL/TLS certificates (Let's Encrypt recommended)

3. **Download html5-qrcode locally** instead of using CDN:
   ```bash
   wget https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js
   # Update scanner.html to use local copy
   ```

4. **Add authentication** for the dashboard (Streamlit supports basic auth)

5. **Firewall rules** - restrict access to trusted networks only

6. **Regular backups** - automate database backups

7. **Update dependencies** - keep Docker images and Python packages current

### Customization

**Change ports:** Edit `docker compose.yml`
```yaml
ports:
  - "8080:80"  # Frontend on port 8080
  - "9000:8000"  # Backend on port 9000
  - "9501:8501"  # Dashboard on port 9501
```

**Update database location:** Edit environment variables
```yaml
environment:
  - DB_PATH=/data/custom_db.db
```

### Migration from Local Setup

If you have an existing `scouting_data.db`:

1. Copy to the Docker volume:
   ```bash
   docker volume create scout-db
   docker run --rm \
     -v scout-db:/data \
     -v $(pwd):/backup \
     alpine cp /backup/scouting_data.db /data/scouting_data.db
   ```

2. Start services:
   ```bash
   docker compose up -d
   ```

### Development

To make changes and test:

1. Edit source files
2. Rebuild and restart:
   ```bash
   docker compose up -d --build
   ```

### Support

For issues or questions:
- Check logs: `docker compose logs`
- Verify containers are running: `docker compose ps`
- Check API health: `curl http://localhost:8000/`
