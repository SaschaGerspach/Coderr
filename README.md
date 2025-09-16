# Coderr – Backend API (Django + DRF)

Backend for **Coderr**: Businesses publish offers, customers order them, businesses receive reviews, and user profiles include all basic data plus an avatar (upload via the same `file` field). Authentication is handled via token auth.  

---

##  Features

- **Auth**
  - Registration & login with token authentication
  - Automatic profile creation on registration (`type: customer | business`)

- **Profiles**
  - GET/PATCH own profile (`/api/profile/{user_id}/`)
  - Lazy-create: PATCH creates a profile if it doesn’t exist yet
  - Endpoints for listing business and customer profiles
  - Avatar upload: JPEG/PNG/WEBP (max 5MB) via the same `file` field

- **Offers**
  - Businesses can create offers with exactly 3 details (basic / standard / premium)
  - Filtering: `creator_id`, `min_price`, `max_delivery_time`
  - Search in title/description
  - Sorting: `updated_at`, `min_price`

- **Orders**
  - Customers can place orders from offers
  - Businesses can update order status (in_progress → completed/cancelled)
  - Staff can delete orders
  - Count endpoints for open and completed orders

- **Reviews**
  - Customers can review businesses (max 1 review per pair)
  - Filtering & sorting by `updated_at` or `rating`

- **Admin**
  - Customized lists/columns (IDs, profile type, etc.) for better overview

---

##  Tech Stack

- Python 3.12+
- Django 5.2.5
- Django REST Framework
- Token authentication (`rest_framework.authtoken`)
- CORS (frontend integration)
- SQLite (development DB)
- Pillow (image uploads)

---

##  Quickstart (Development)

```bash
# 1. Virtual environment
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Create guest accounts (if not already existing)
python manage.py create_guest_users

# 5. Start development server
python manage.py runserver
