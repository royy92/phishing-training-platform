# 0001. Use Django for the phishing training platform

## Status 

Accepted, 2026-07-04

## Context

The project aims to provide a phishing awareness training platform where users can complete interactive scenarios and improve their ability to recognize phishing attacks.
The application requires user authentication, database support, an administrative interface for managing training content, and a maintainable project structure. 
The team is small, with limited development time and limited hardware resources.
The project also needs a framework that supports rapid development without implementing common web features from scratch.

## Decision

Use Django as the web framework for the phishing training platform.

## Consequences

+ Django provides a built-in admin interface for managing training content.
 + Built-in authentication reduces the amount of custom code.
 + Django reduces development time by providing built-in authentication, an admin interface, and database migrations.
 + Django provides a clear and maintainable project structure.
 - Contributors should have basic Django knowledge to work on the project.
 - New features should follow Django's project structure and conventions.
