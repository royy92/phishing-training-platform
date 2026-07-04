[![CI](https://github.com/royy92/phishing-training-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/royy92/phishing-training-platform/actions/workflows/ci.yml)

# Phishing Training Platform (Django)

Phishing scenario training app featuring multiple scenarios, login/registration support, and an interactive reporting dashboard.

## Documentation

📖 View the project documentation:

https://royy92.github.io/phishing-training-platform/

## Requirements

- Python 3.11+
- Django 4.x
- Tailwind CSS

## Run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
