Nutramigo — Macro & Calorie Coach

Track meals, hit your macro targets, and get smart suggestions to stay on plan.
Live demo: https://nutramigo.onrender.com

<!-- Optional badges ![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white) ![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7?logo=render&logoColor=white) -->
✨ Features

Beautiful dashboard

Daily totals, goal progress, color-coded badges (green/amber/red)

7-day calories chart, macro pie chart

Goals

Set/adjust daily calories + per-macro targets

(Optional) smart target coach: suggests a modest deficit/surplus from TDEE

Quick logging

Search OpenFoodFacts and add with one click

Favorites with per-100g macros + default grams

Recent foods section

Copy yesterday’s meals

CSV export

AI assistant

“Coach” page that suggests meals/snacks based on what you still need

Responsive UI

Looks great on desktop and mobile

Dark mode toggle (remembers your preference)

Auth

Clean login/signup pages, Django auth, CSRF & session security

Production-ready basics

Static files via WhiteNoise

Deployable to Render (free tier)

📸 Screenshots

Add images in the repo and link them here.

Dashboard
<!-- screenshot: /docs/img/dashboard.png -->
<img width="1768" height="778" alt="image" src="https://github.com/user-attachments/assets/b6e07052-0757-400f-ab4a-dc745cb5f6e1" />


Coach
<!-- screenshot: /docs/img/coach.png -->
<img width="1919" height="919" alt="image" src="https://github.com/user-attachments/assets/dbe45b1f-f80e-48da-9744-b34da0781428" />


Login
<!-- screenshot: /docs/img/login.png -->
<img width="1907" height="1002" alt="image" src="https://github.com/user-attachments/assets/f1d5dd63-505a-4eb1-9780-ff2e78b77621" />


🧱 Tech Stack

Backend: Django 5.x, Django ORM

Frontend: Bootstrap 5, Chart.js

Database: SQLite (dev) / PostgreSQL (production)

Deploy: Render (Web Service + PostgreSQL)

Other: WhiteNoise (static files), OpenFoodFacts search

🚀 Live Demo

App: https://nutramigo.onrender.com

Free tier note: cold starts may take a few seconds.

🧭 Project Structure (simplified)
calorie_counter/
├─ calorie_counter/
│  ├─ settings.py        # env-driven config
│  ├─ urls.py
│  ├─ wsgi.py
├─ tracker/
│  ├─ models.py          # Meal, Goal, FavoriteFood
│  ├─ views.py           # dashboard, coach, APIs
│  ├─ templates/tracker/ # pages & partials
│  ├─ static/tracker/    # styles, scripts
├─ requirements.txt
├─ manage.py
├─ .env.example

🧪 API Endpoints (selected)
Method	Path	Purpose
GET	/	Dashboard
GET	/ai/	Coach page
POST	/ai/suggest/	Get meal suggestions (JSON)
GET	/food-search/?q=	OpenFoodFacts search (JSON)
POST	/quick-add/	Log a food by grams/macros
POST	/favorites/<id>/quick/	Log a favorite food
GET	/export-csv/	Export CSV (date or date-range)
POST	/copy-yesterday/	Copy all of yesterday’s meals
GET	/accounts/login/	Login
GET	/accounts/logout/	Logout
🛠️ Getting Started (Local)
1) Clone & create a virtualenv
git clone https://github.com/<your-username>/nutramigo.git
cd nutramigo
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

2) Configure environment

Copy the example and fill values as needed:

cp .env.example .env


.env.example (what it should roughly contain):

DEBUG=True
SECRET_KEY=dev-unsafe-change-me

# For local dev only:
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

# Optional: if using Postgres locally
# DATABASE_URL=postgresql://user:pass@localhost:5432/nutramigo


If DATABASE_URL is omitted, SQLite is used by default.

3) Migrate & run
python manage.py migrate
python manage.py createsuperuser  # optional
python manage.py runserver


Open http://127.0.0.1:8000
