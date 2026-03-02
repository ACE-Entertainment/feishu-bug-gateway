# Contributing

## Development setup

1. `pip install -e .[dev]`
2. `cp config.example.py config.py`
3. Fill your local config values.

## Pull requests

- Keep changes focused and testable.
- Add/update tests for behavior changes.
- Run `pytest` before opening PR.

## Security

Do not commit secrets, `config.py`, or webhook/app credentials.
Report security issues privately to maintainers.
