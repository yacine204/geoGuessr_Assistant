# GeoGuessr Location Assistant (still in progress)

Street-level image analysis pipeline that extracts geographic clues from images
(road signs, architecture, language) using YOLOv8, OCR, and OpenStreetMap
to infer country and region.

## Stack
- **end_logic** — YOLOv8 detection, OCR, Overpass/Nominatim queries
- **backend** — API serving end_logic results
- **frontend** — UI

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js (for frontend)

### Installation
```bash
# clone the repo
git clone https://github.com/yourusername/geoguessr_assistant.git
cd geoguessr_assistant

# create and activate venv
python -m venv .venv
source .venv/bin/activate        # linux/mac
.venv\Scripts\activate           # windows

# install dependencies
pip install -r requirements.txt
```

### Run
```bash
# backend
cd backend
uvicorn main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

## Model Weights
Download from [Google Drive](#) and place in `end_logic/weights/`. or just put ur desired model pt in the main and it'll be downloaded in the firt execution.
