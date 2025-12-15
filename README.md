# FRC Scouting System

A complete, offline-capable scouting system for FIRST Robotics Competition (FRC) teams. This system allows scouts to collect match data on tablets/phones and transfer it via QR codes or web-based scanning to a central database.

## System Overview

### Deployment Options

**Option 1: Docker (Recommended for Homeservers)**
- **Frontend**: Nginx serving HTML/CSS/JS PWA
- **Backend**: FastAPI RESTful API
- **Scanner**: Web-based QR scanner (html5-qrcode)
- **Dashboard**: Streamlit analytics dashboard
- See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for details

**Option 2: Local (Original)**
- **Frontend**: PWA with QR code generation
- **Backend**: Python/OpenCV desktop scanner
- **Dashboard**: Streamlit analytics
- See instructions below

### Key Features
- **Multiple Deployment Options** - Docker or local
- **Web-Based Scanner** - No desktop software needed
- **100% Offline** - No internet required (after initial setup)
- **Dark Mode UI** - Battery-efficient high-contrast design
- **Configurable Fields** - Easy to customize for different seasons
- **Local Backup** - Data saved to localStorage
- **QR Code Transfer** - Reliable data transmission
- **SQLite Database** - Persistent storage with SQL queries
- **RESTful API** - Modern web architecture

## Quick Start

### Docker Deployment (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd scoutification

# Start all services
docker compose up -d

# Access the system
# - Scouting App: http://localhost/
# - QR Scanner: http://localhost/scanner.html
# - Dashboard: http://localhost:8501
# - API: http://localhost:8000
```

**Full Docker documentation:** [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

### Local Deployment (Original)

## Requirements (Local Deployment)

### Frontend (Scouting App)
- Any modern web browser (Chrome, Firefox, Safari, Edge)
- No installation needed - just open `index.html`

### Backend Scanner Options

**Option A: Web-based (New)**
- Modern browser with camera support
- No additional software needed
- Open `scanner.html` in a browser

**Option B: Desktop Scanner (Original)**
- Python 3.7 or higher
- Required Python packages:
  ```bash
  pip install opencv-python pyzbar numpy pillow
  ```
- Webcam or camera device

### Additional Requirements for pyzbar
On some systems, you may need to install the `zbar` library:

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install libzbar0
```

**macOS:**
```bash
brew install zbar
```

**Windows:**
- Usually works out of the box with `pip install pyzbar`
- If issues occur, download zbar DLL from: http://zbar.sourceforge.net/

## Quick Start

### 1. Setup the Frontend (Scouting App)

#### Option A: Local File Access
Simply open `index.html` in your web browser:
```bash
# Navigate to the project directory
cd scoutification

# Open in browser (example for different OS)
# Linux:
xdg-open index.html
# macOS:
open index.html
# Windows:
start index.html
```

#### Option B: Local Web Server (Recommended for PWA features)
```bash
# Using Python 3
python3 -m http.server 8000

# Or using Python 2
python -m SimpleHTTPServer 8000

# Then open browser to:
# http://localhost:8000
```

### 2. Setup the Backend

#### Option A: Web-Based Scanner (New - No Installation Required)

1. Start a local web server (or use Docker):
   ```bash
   python3 -m http.server 8000
   ```

2. Open `http://localhost:8000/scanner.html` in a browser with a camera

3. Point the camera at QR codes - they'll be automatically scanned and sent to the API

**Note:** For the web scanner to work, you need the FastAPI backend running:
```bash
# Install dependencies
pip install fastapi uvicorn

# Run the API
DB_PATH=scouting_data.db python3 api.py
```

#### Option B: Desktop Scanner (Original - OpenCV)

1. Install Dependencies
   ```bash
   pip install opencv-python pyzbar numpy pillow
   ```

2. Initialize Database (Optional - auto-created on first run)
   ```bash
   sqlite3 scouting_data.db < schema.sql
   ```

3. Run the Scanner
   ```bash
   python3 scanner.py
   ```

The desktop scanner will:
- Initialize the database
- Open your webcam
- Wait for QR codes to scan

## 📱 Usage Guide

### Scouting Workflow

#### Step 1: Scout Fills Out Form
1. Open `index.html` on a tablet/phone
2. Fill in match information:
   - Match Number
   - Team Number
   - Alliance (Red/Blue)
   - Scouter Name
3. Record performance during the match:
   - Autonomous period data
   - Teleoperated period data
   - Endgame/climbing data
   - Defense and driver ratings
   - Notes

#### Step 2: Generate QR Code
1. Click "Generate QR Code" button
2. Form data is validated
3. QR code is displayed on screen
4. Data is saved to localStorage as backup

#### Step 3: Scan QR Code

**Web-Based Scanner (Recommended):**
1. Open `scanner.html` on a device with a camera
2. Allow camera permissions when prompted
3. Point the camera at the QR code on the tablet/phone
4. Scanner automatically:
   - Detects and decodes QR code
   - Flashes green on success
   - Sends data to API
   - Shows "Success: Match X, Team Y" notification
   - Resumes scanning immediately

**Desktop Scanner (Original):**
1. Run `scanner.py` on the master computer
2. Point the webcam at the QR code on the tablet/phone
3. Scanner automatically:
   - Detects and decodes QR code
   - Validates data structure
   - Saves to SQLite database
   - Shows green border around QR code on success

#### Step 4: Repeat
1. Click "New Entry" on the scouting app
2. Form resets for next match
3. Previous entries are preserved in history

## Customization

### Modifying Scouting Fields

Edit `config.js` to add, remove, or modify fields:

```javascript
const CONFIG = {
  fields: [
    {
      id: "field_name",           // Database column name
      label: "Field Label",       // Display name
      type: "counter",            // counter, checkbox, dropdown, text, number, textarea
      required: true,             // Whether field is required
      category: "category_name",  // Grouping category
      options: ["Option1", "Option2"] // For dropdowns only
    }
    // ... more fields
  ],
  
  categories: {
    category_name: "Category Display Name"
  }
};
```

**Important:** If you modify fields, you must also update:
1. `scanner.py` - Update `expected_keys` and database save logic
2. `schema.sql` - Update table schema

### Field Types

- **counter**: Large +/- buttons for counting (e.g., balls scored)
- **checkbox**: Yes/No boolean value
- **dropdown**: Select from predefined options
- **number**: Numeric input field
- **text**: Short text input
- **textarea**: Multi-line text input

## Data Analysis

### Accessing the Database

The data is stored in `scouting_data.db` SQLite file. You can query it using:

**SQLite Command Line:**
```bash
sqlite3 scouting_data.db

# Example queries:
SELECT * FROM scouting_data;
SELECT * FROM scouting_summary;
SELECT team_number, AVG(auto_total_balls) FROM scouting_summary GROUP BY team_number;
```

**Python:**
```python
import sqlite3
conn = sqlite3.connect('scouting_data.db')
df = pd.read_sql_query("SELECT * FROM scouting_summary", conn)
```

**Excel/Google Sheets:**
- Use a SQLite viewer/exporter
- Or export to CSV:
```bash
sqlite3 -header -csv scouting_data.db "SELECT * FROM scouting_data;" > data.csv
```

### Scanner Statistics

While the scanner is running:
- Press `s` to show statistics
- Press `q` to quit

### Resolving Duplicate Entries

If the same match data gets scanned multiple times, you can resolve conflicts using the conflict resolution tool:

```bash
python3 resolve_conflicts.py
```

This tool will:
1. Load the database and identify duplicate entries (same match number, team number, and alliance)
2. Display conflicting records side-by-side with differences highlighted
3. Prompt you to choose how to resolve each conflict:
   - **Keep (1)**: Keep the first record, delete the second
   - **Keep (2)**: Keep the second record, delete the first
   - **Average (A)**: Calculate the mean of all numeric fields and merge string fields
4. Update the database with your chosen resolution

**Note:** The tool requires pandas. Install it with:
```bash
pip install pandas
```

## 🗂️ File Structure

```
scoutification/
├── index.html                   # Main scouting interface
├── pit.html                     # Pit scouting interface
├── scanner.html                 # Web-based QR scanner (NEW)
├── app.js                       # Frontend application logic
├── config.js                    # Field configuration
├── qrcode.min.js                # QR code generation library
├── manifest.json                # PWA manifest
│
├── api.py                       # FastAPI backend (NEW)
├── scanner.py                   # Desktop QR scanner (original)
├── dashboard.py                 # Streamlit analytics dashboard
├── resolve_conflicts.py         # Conflict resolution tool
│
├── docker-compose.yml           # Docker orchestration (NEW)
├── Dockerfile.backend           # Backend container config (NEW)
├── Dockerfile.dashboard         # Dashboard container config (NEW)
├── nginx.conf                   # Nginx web server config (NEW)
├── requirements-backend.txt     # Backend Python deps (NEW)
├── requirements-dashboard.txt   # Dashboard Python deps (NEW)
│
├── schema.sql                   # Database schema
├── README.md                    # This file
├── DOCKER_DEPLOYMENT.md         # Docker deployment guide (NEW)
│
├── test_*.py                    # Unit tests
└── scouting_data.db             # SQLite database (created on first run)
```

## Data Backup

### Automatic Backups
- Frontend: Data saved to browser localStorage
- Backend: All data stored in `scouting_data.db`

### Manual Backup
```bash
# Backup database
cp scouting_data.db scouting_data_backup_$(date +%Y%m%d).db

# Or use SQLite backup command
sqlite3 scouting_data.db ".backup scouting_data_backup.db"
```

## Troubleshooting

### Frontend Issues

**QR Code not generating:**
- Check browser console for errors
- Ensure all required fields are filled
- Try refreshing the page

**Form not saving:**
- Check if localStorage is enabled
- Clear browser cache and reload

### Backend Issues

**Webcam not opening:**
```bash
# Test webcam
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Success' if cap.isOpened() else 'Failed')"
```

**pyzbar not working:**
- Ensure zbar library is installed (see Requirements)
- Try reinstalling: `pip uninstall pyzbar && pip install pyzbar`

**QR code not detected:**
- Ensure good lighting
- Hold QR code steady
- Increase QR code size on display
- Clean camera lens

**Database errors:**
- Check file permissions
- Ensure `scouting_data.db` is not locked by another program
- Try deleting database and letting it recreate

## Notes

- The system uses FRC 2022 Rapid React game fields as examples
- Customize `config.js` for your specific season/game
- QR codes can store approximately 2-3 KB of data
- For best results, use tablets with 7" or larger screens
- Recommended: 1 tablet per 6 scouts, 1 master station per event

## Contributing

To add new features or fix bugs:
1. Modify the appropriate files
2. Test thoroughly with sample data
3. Update this README if needed

## License

This project is intended for FRC teams and educational use.

## Credits

Built for FRC teams to make scouting easier and more reliable.

---

**Good luck with your scouting!**
