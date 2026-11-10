# Expense Tracker (Django REST Framework + PostgreSQL)

## Setup (Windows)
1. Create a PostgreSQL database named `expense_tracker` (pgAdmin > Databases > Create).
2. `python -m venv venv` then `venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. `set DB_PASSWORD=your_postgres_password`
5. `python manage.py migrate`
6. `python manage.py createsuperuser`
7. `python manage.py runserver` and open http://127.0.0.1:8000/admin
