# Contribution Guidelines

We welcome contributions to CipherBrief!

## Development Setup

1. Fork the repository
2. Clone your fork locally
3. Set up the virtual environment: `python -m venv venv && source venv/bin/activate`
4. Install dependencies: `make install`
5. Create `.env` based on `.env.example`

## Code Style

- We use `black` for code formatting. Run `make lint` before submitting a PR.
- Add type hints to all new functions.
- Write unit tests for new logic in `tests/`. Run tests via `make test`.

## Pull Request Process

1. Create a feature branch (`git checkout -b feature/your-feature`)
2. Commit your changes (`git commit -m 'Add some feature'`)
3. Push to the branch (`git push origin feature/your-feature`)
4. Open a Pull Request targeting the `main` branch.
