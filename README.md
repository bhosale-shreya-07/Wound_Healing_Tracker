# SmartHeal – Wound Healing Tracker (Digital Image Processing)

```
smartheal/
├── backend/    Flask + OpenCV + MySQL
└── frontend/   React (Vite) + Chart.js
```

## Run the backend
1. Install MySQL and create the database: `CREATE DATABASE smartheal;`
2. In `backend/`:
   ```
   python -m venv venv
   source venv/bin/activate          # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   export DATABASE_URL="mysql+pymysql://root:YOUR_PASSWORD@localhost/smartheal"
   export JWT_SECRET="long-random-string"
   python app.py                     # http://localhost:5000
   ```
   (Windows PowerShell: `$env:DATABASE_URL="..."`)

## Run the frontend
```
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

## Image-processing techniques (backend/cv/)
| Technique | File | Purpose |
|---|---|---|
| Gaussian filtering | pipeline.py | Remove camera noise and skin texture before clustering |
| HSV conversion | pipeline.py | Separate colour from brightness; hue mapped to (S·cosH, S·sinH) |
| K-Means (k=3) | pipeline.py | Split pixels into wound / skin / shadow clusters |
| Contour detection | pipeline.py | Wound boundary, area and perimeter |
| Image subtraction | compare.py | Healed vs new wound pixels between two dates |

Extras: gray-world + CLAHE lighting normalisation, ORB+RANSAC alignment, 2-click ruler calibration, manual polygon correction.

## Disclaimer
SmartHeal measures visible wound-region size in photographs. It cannot diagnose infection or confirm healing.
