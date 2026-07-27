# Contributing Guide

Thank you for your interest in contributing to the Phishing Awareness Training Platform!

Whether you are fixing a typo, improving the documentation, reporting a bug, or adding a new feature, your contributions are always welcome.

## Getting Started

### 1. Fork the repository

Fork [this repository](https://github.com/royy92/phishing-training-platform) to your GitHub account.

### 2. Clone your fork

```bash
git clone https://github.com/<your-username>/phishing-training-platform.git
cd phishing-training-platform
```

### 3. Create a new branch

Create a separate branch for every change.

```bash
git checkout -b feature-name
```

## Setting Up the Development Environment

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

Linux/macOS:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

Apply the database migrations:

```bash
python manage.py migrate
```

Load the sample data:

```bash
python manage.py loaddata sample_data_aligned.json
```

Create an administrator account:

```bash
python manage.py createsuperuser
```

Run the development server:

```bash
python manage.py runserver
```

Open your browser and navigate to:

```
http://127.0.0.1:8000/
```

## Running Tests

Before submitting a pull request, please make sure the project works correctly by running:

```bash
python manage.py test
```

If your changes introduce new functionality, please add or update tests where appropriate.

## Pull Request Guidelines

Before opening a [pull request](https://github.com/royy92/phishing-training-platform/pulls), please make sure to:

- Create a dedicated branch for your change.
- Use clear commit messages (for example: `docs:`, `feat:`, `fix:`, `refactor:`).
- Keep each pull request focused on a single change.
- Clearly describe what changed and why.

## Reporting Bugs

If you discover a bug, please open a GitHub Issue.

When reporting a bug, include:

- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Screenshots or logs (if applicable)

[Issues](https://github.com/royy92/phishing-training-platform/issues) can be opened here.

## Review Process

All pull requests are reviewed before being merged.

Please be open to feedback and update your pull request if changes are requested during the review process.

## Questions

If you have any questions or suggestions, feel free to open an Issue or submit a Pull Request.

Thank you for taking the time to contribute to the Phishing Awareness Training Platform!
