# Backend Inventory API

A portfolio-ready RESTful inventory management API built with **Python, Flask and SQLite**. It demonstrates product CRUD, stock movements, validation, low-stock monitoring, persistent storage, automated tests and CI.

## What this project demonstrates

This project is designed to show practical backend engineering skills that are useful in real business applications: inventory control, validation, transactional updates, REST API design and automated verification.

## Features

- Product CRUD endpoints
- Unique SKU validation
- Persistent SQLite database
- Stock-in, stock-out and stock-adjustment operations
- Stock movement history
- Protection against negative stock
- Per-product low-stock thresholds
- Search and low-stock filtering
- Dedicated low-stock endpoint
- Health-check endpoint
- Environment-based configuration
- Automated API tests with `pytest`
- GitHub Actions CI on pushes and pull requests

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/api/products` | List products |
| POST | `/api/products` | Create a product |
| GET | `/api/products/<id>` | Get one product |
| PUT | `/api/products/<id>` | Update product metadata |
| DELETE | `/api/products/<id>` | Delete product |
| POST | `/api/products/<id>/stock` | Record a stock movement |
| GET | `/api/products/<id>/movements` | Product movement history |
| GET | `/api/low-stock` | Products at/below threshold |

Optional product filters:

```text
GET /api/products?q=keyboard
GET /api/products?low_stock=1
```

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

The API runs by default at `http://127.0.0.1:5003`.

## Run tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The test suite verifies health checks, product creation, stock operations, low-stock behavior, duplicate SKU handling and protection against negative stock.

## Continuous integration

The repository includes a GitHub Actions workflow that automatically runs the test suite on pushes to `main` and on pull requests.

## Example: create a product

```bash
curl -X POST http://127.0.0.1:5003/api/products \
  -H "Content-Type: application/json" \
  -d '{"sku":"KB-001","name":"Mechanical Keyboard","price":79.90,"stock":12,"low_stock_threshold":4}'
```

## Example: stock out

```bash
curl -X POST http://127.0.0.1:5003/api/products/1/stock \
  -H "Content-Type: application/json" \
  -d '{"type":"out","quantity":2,"note":"Customer order #1001"}'
```

## Technology

`Python 3` · `Flask 3` · `SQLite` · `REST/JSON` · `pytest` · `GitHub Actions`

## Portfolio focus

This project demonstrates backend/API fundamentals: routing, validation, relational persistence, business rules, error handling, testability and maintainable REST design.

## Production improvements

For a production deployment I would typically add PostgreSQL, schema migrations, authentication/authorization, rate limiting, structured logging, Docker, API documentation and deployment monitoring.
