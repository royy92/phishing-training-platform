phishing training platform (Django)


Phishing scenario training app featuring multiple scenarios, login/registration support, and interactive reporting dashboard.

# Requermint 
- Python 3.11+
- Django 5.x
- Tailwind CSS

# Run
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

