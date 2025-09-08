phishing training platform (Django)


Phishing scenario training app featuring multiple scenarios, login/registration support, (EN/AR), and interactive reporting dashboard.

# Requermint 
- Python 3.11+
- Django 5.x
- SQLite/PostgreSQL
- Node (اختياري لدمج Tailwind/Build)

# Run
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

#Translate
python manage.py makemessages -l ar
python manage.py compilemessages
