# How to create a phishing training scenario

## Overview

This guide explains how to create a phishing training scenario using the Django admin panel.

## Prerequisites

Before you begin, make sure:

- The project is running.
- You have an account with access to the Django admin panel.

## Step 1: Open the Django admin panel

Open:

```text
http://127.0.0.1:8000/admin/
```

Sign in with an account that has access to the Django admin panel.

## Step 2 - Create a new scenario

Under the **Training** section, select **Scenarios**, then click **Add**.

Fill in the scenario details:

- Select a **Category**.
- Enter a **Title**.
- Add the phishing **Message**.
- Provide the scenario **Content**.
- Choose whether the scenario **Is phishing**.
- Select the **Difficulty**.
- Set the **Depth**.
- Choose the appropriate **Phase**.

Save the scenario.

## Step 3 - Add the scenario steps

Open **Scenarios step** from the **Training** section and create the steps associated with the new scenario.

## Step 4 - Test the scenario

Open the application, navigate to the scenario's category, and verify that the scenario appears in the category and behaves as expected.
