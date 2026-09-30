# Campus Lost & Found — with AI Image Matching

Full-stack app: Flask REST API + SQLite (SQLAlchemy) + CLIP embeddings for
visual similarity matching between "lost" and "found" item reports.

## Features
- Upload lost/found items with photo, auto-computes a CLIP embedding
- **Auto-matching on upload** — checks for strong matches the moment a report is submitted, no manual click needed
- **Email alerts** (SMTP) sent automatically when a strong match is found, if the reporter left an email as contact info
- **Text search** across title/description/category/location (in addition to image matching)
- **QR claim slips** — generates a scannable QR code per confirmed match pair, with a server-side verification endpoint, so a lost-and-found desk can confirm a claim is genuine instead of relying on someone's word
- Filter by lost/found, mark items resolved, delete items

## How the matching works
1. Every uploaded image is passed through a pretrained CLIP model
   (`clip-ViT-B-32` via `sentence-transformers`), producing a 512-dim
   embedding that captures the image's visual/semantic content.
2. The embedding is stored in SQLite as a JSON array (simple + good enough
   for a project of this scale — no vector DB needed).
3. When someone clicks "Find Matches" on a lost item, the backend fetches
   all unresolved *found* items, computes cosine similarity between
   embeddings, and returns the top matches above a similarity threshold.

## Project structure
```
lost-found-app/
├── backend/
│   ├── app.py           # Flask routes (API)
│   ├── models.py        # SQLAlchemy Item model
│   ├── embedding.py      # CLIP embedding + similarity logic
│   ├── requirements.txt
│   └── uploads/          # uploaded images (auto-created)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js            # vanilla JS calling the Flask API
└── README.md
```

## Building the folder structure from scratch

If you're starting with nothing, here's every command to set it up (Mac/Linux —
Windows notes are inline):

```bash
mkdir lost-found-app
cd lost-found-app
mkdir backend frontend
mkdir backend/uploads

cd backend
touch app.py models.py embedding.py notifications.py qr_utils.py requirements.txt .env.example
cd ..

cd frontend
touch index.html style.css app.js
cd ..
```

At this point your structure looks like:
```
lost-found-app/
├── backend/
│   ├── app.py
│   ├── models.py
│   ├── embedding.py
│   ├── notifications.py
│   ├── qr_utils.py
│   ├── requirements.txt
│   ├── .env.example
│   └── uploads/            (starts empty — images land here at runtime)
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

Now paste the corresponding code (from this conversation, or the zip already shared) into each file.

## Setup and run (needs internet the first time, to download the CLIP model)

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
First run downloads the CLIP model (~350MB) — needs internet once, then it's
cached locally. The API runs on `http://127.0.0.1:5000` and auto-creates
`lost_found.db` (SQLite) on first run.

**Optional — enable email alerts:**
```bash
cp .env.example .env
```
Edit `.env` and set `MAIL_ENABLED=true`, your Gmail address, and a
Gmail App Password (myaccount.google.com/apppasswords — not your real password).
Without this, the app runs fine — auto-match emails just won't send.

### 2. Frontend
Open `frontend/index.html` directly in a browser, or serve it:
```bash
cd frontend
python -m http.server 5500
```
Then visit `http://127.0.0.1:5500`.

### 3. Verify it's working
- Visit `http://127.0.0.1:5000/api/health` → should return `{"status": "ok"}`
- Submit a "found" report with a photo
- Submit a "lost" report with a visually similar photo → "possible matches found" should pop up immediately (auto-match feature)

## API Endpoints
| Method | Route                          | Purpose                              |
|--------|----------------------------------|---------------------------------------|
| POST   | `/api/items`                   | Create a lost/found report (multipart form + image) |
| GET    | `/api/items?status=lost`       | List items, optional filters |
| GET    | `/api/items/<id>`              | Get one item |
| GET    | `/api/items/<id>/matches`      | Get top visual matches (opposite status) |
| PATCH  | `/api/items/<id>/resolve`      | Mark item as resolved/claimed |
| DELETE | `/api/items/<id>`              | Delete an item |

## Ideas to extend (good for interview talking points)
- Swap SQLite similarity search for FAISS once item count grows (mention you understand the scaling limit of brute-force cosine search).
- Add text-based matching too — combine CLIP image embedding with a text embedding of title+description for a hybrid score.
- Add JWT auth so only the reporter can mark their item resolved.
- Deploy: Flask on Render/Railway, frontend on Vercel/Netlify, images in S3 instead of local disk.
- Add email/SMS notification when a match crosses a similarity threshold.

## Talking points for interviews
- **Why CLIP over classic CV (ORB/SIFT)?** CLIP embeds semantic meaning (a "black backpack" from any angle/lighting still clusters near other black backpacks), not just pixel-level features — more robust for casual, unposed photos.
- **Why cosine similarity over Euclidean distance?** CLIP embeddings are typically compared by direction, not magnitude — cosine similarity is the standard choice and is scale-invariant.
- **Why not a vector DB here?** At student-project scale (hundreds of items), brute-force cosine comparison in Python is simpler and fast enough; explaining you'd swap to FAISS/pgvector at scale shows systems thinking.
