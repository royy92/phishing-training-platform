# Project reference

## Overview

This reference provides an overview of the main components of the Phishing Awareness Training Platform.

## Main models

### Category

Groups phishing training scenarios into categories such as **General**, **Students**, and **IT**.

### Scenario

Represents a phishing training scenario. Each scenario belongs to a category and stores information such as the title, message, content, difficulty, and phase.

### `ScenarioStep`

Represents a single step within a phishing training scenario and defines the order of the scenario flow.

### Step

Stores the content associated with a scenario step.

## Project structure

```text
training/
├── admin.py
├── models.py
├── urls.py
├── views.py
├── templates/
└── migrations/
```

## Admin interface

The Django admin panel provides access to the following project resources:

- Categories
- Scenarios
- Scenario steps
