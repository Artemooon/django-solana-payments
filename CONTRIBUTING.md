# Contributing to Django Solana Payments

Thanks for your interest in contributing.

This project is still evolving, so the main goal is to keep contributions practical, easy to review, and aligned with the core payment flow.

## What Contributions Are Welcome

Good contributions include:

- bug fixes
- tests for existing behavior
- documentation improvements
- small focused features that improve the payment flow
- example project improvements
- developer experience improvements

Please avoid very large refactors or broad API changes without opening an issue first.

## Before You Start

If you want to:

- report a bug: open an issue with steps to reproduce, expected behavior, actual behavior, environment details, and relevant logs or screenshots
- propose a feature: open an issue first and explain the use case, expected API, and tradeoffs
- send a pull request: keep it focused and explain why the change is needed

## Project Direction

The current direction of the project is:

- reliable Solana payment verification
- a clean Django integration story
- optional DRF support without forcing DRF on every user
- clear extension points through services, callbacks, and signals
- strong documentation and a usable demo project

When in doubt, prefer simple and predictable behavior over adding more abstraction.

## Local Setup

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/Artemooon/django-solana-payments.git
cd django-solana-payments
python -m venv .venv
source .venv/bin/activate
```

Install the project with development dependencies:

```bash
pip install -e ".[dev,docs,drf]"
```

## Running Tests

Run the test suite from the repository root:

```bash
pytest
```

If you are working on a focused area, it is fine to run a subset first:

```bash
pytest django_solana_payments/tests/test_verify_transaction_service.py
```

## Pull Request Guidelines

Please try to keep pull requests small and reviewable.

A good pull request usually includes:

- a clear description of the problem
- a clear summary of the solution
- tests for behavior changes when applicable
- documentation updates when user-facing behavior changes

If your change affects the public API, signals, callbacks, settings, example project, or installation flow, update the docs in the same pull request.

## Coding Expectations

Some practical expectations for contributions:

- keep backward compatibility in mind
- avoid unrelated formatting-only changes
- do not remove existing behavior without explaining why
- prefer explicit service-layer changes over hidden side effects
- add or update tests when fixing bugs

## Communication

The best way to discuss contributions is through GitHub issues and pull requests.

Please open an issue before starting major work. That avoids duplicate effort and makes review much faster.

## New Contributors

Documentation fixes, examples, tests, and small bug fixes are all useful contributions.

If you are new to the project, those are excellent places to start.
