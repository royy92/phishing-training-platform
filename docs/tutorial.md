# Run the phishing awareness training platform

## Overview

This tutorial walks you through running the Phishing Awareness Training Platform for the first time. By the end, you will have the project running locally and will be able to explore the available phishing categories and training scenarios.

## Prerequisites

Before you begin, make sure you have:

- Git
- Python 3.11 or later
- pip

## Step 1 - Clone the repository

```bash
git clone https://github.com/royy92/phishing-training-platform.git
cd phishing-training-platform
```

## Step 2 - Install the project dependencies

Create and activate a virtual environment, then install the project dependencies.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 3 - Apply the database migrations

```bash
python manage.py migrate
```

## Step 4 - Load the example data

Load the example categories, scenarios, and scenario steps:

```bash
python manage.py loaddata sample_data_aligned.json
```


## Step 5 - Create an admin user

Create a superuser account so you can log in and manage the platform:

```bash
python manage.py createsuperuser
```

## Step 6 - Start the development server

```bash
python manage.py runserver
```

## Step 7 - Open the application

Open your browser and navigate to:

```text
http://127.0.0.1:8000/
```

## Step 8 - Explore the phishing categories

Browse the available phishing categories from the home page.

## Step 9 - Open a category and view its phishing scenarios

Select a category to view the avaliable phishing training scenarios and begin exploring the platform.
