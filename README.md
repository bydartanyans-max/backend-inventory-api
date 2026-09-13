# Backend Inventory API

A portfolio-ready RESTful inventory management API built with **Python, Flask and SQLite**. It demonstrates product CRUD, stock movements, validation, low-stock monitoring and persistent storage.

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

- Python 3
- Flask 3
- SQLite
- REST/JSON

## Portfolio focus

This project is intended to demonstrate backend/API fundamentals: routing, validation, relational persistence, business rules, error handling and maintainable REST design.
