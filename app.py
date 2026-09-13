from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, jsonify, request

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("INVENTORY_DB", BASE_DIR / "inventory.db"))
LOW_STOCK_DEFAULT = int(os.getenv("LOW_STOCK_THRESHOLD", "5"))

app = Flask(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            low_stock_threshold INTEGER NOT NULL DEFAULT 5 CHECK(low_stock_threshold >= 0),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL CHECK(movement_type IN ('in', 'out', 'adjustment')),
            quantity INTEGER NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
        """
    )
    db.commit()


def product_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "sku": row["sku"],
        "name": row["name"],
        "price": row["price"],
        "stock": row["stock"],
        "low_stock_threshold": row["low_stock_threshold"],
        "is_low_stock": row["stock"] <= row["low_stock_threshold"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_product_or_none(product_id: int):
    return get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()


def parse_json(required_fields=()):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify(error="JSON body is required"), 400)
    missing = [field for field in required_fields if field not in data]
    if missing:
        return None, (jsonify(error=f"Missing field(s): {', '.join(missing)}"), 400)
    return data, None


@app.get("/health")
def health():
    return jsonify(status="ok", service="backend-inventory-api")


@app.get("/api/products")
def list_products():
    search = request.args.get("q", "").strip()
    low_stock = request.args.get("low_stock") == "1"
    sql = "SELECT * FROM products"
    params = []
    where = []

    if search:
        where.append("(name LIKE ? OR sku LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term])
    if low_stock:
        where.append("stock <= low_stock_threshold")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC"

    rows = get_db().execute(sql, params).fetchall()
    return jsonify([product_to_dict(row) for row in rows])


@app.post("/api/products")
def create_product():
    data, error = parse_json(("sku", "name", "price"))
    if error:
        return error
    try:
        sku = str(data["sku"]).strip()
        name = str(data["name"]).strip()
        price = float(data["price"])
        stock = int(data.get("stock", 0))
        threshold = int(data.get("low_stock_threshold", LOW_STOCK_DEFAULT))
        if not sku or not name or price < 0 or stock < 0 or threshold < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(error="Invalid product data"), 400

    now = utc_now()
    db = get_db()
    try:
        cursor = db.execute(
            """
            INSERT INTO products (sku, name, price, stock, low_stock_threshold, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (sku, name, price, stock, threshold, now, now),
        )
        product_id = cursor.lastrowid
        if stock:
            db.execute(
                """
                INSERT INTO stock_movements (product_id, movement_type, quantity, note, created_at)
                VALUES (?, 'adjustment', ?, 'Initial stock', ?)
                """,
                (product_id, stock, now),
            )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="SKU already exists"), 409

    return jsonify(product_to_dict(get_product_or_none(product_id))), 201


@app.get("/api/products/<int:product_id>")
def get_product(product_id: int):
    product = get_product_or_none(product_id)
    if product is None:
        return jsonify(error="Product not found"), 404
    return jsonify(product_to_dict(product))


@app.put("/api/products/<int:product_id>")
def update_product(product_id: int):
    current = get_product_or_none(product_id)
    if current is None:
        return jsonify(error="Product not found"), 404
    data, error = parse_json()
    if error:
        return error

    try:
        sku = str(data.get("sku", current["sku"])).strip()
        name = str(data.get("name", current["name"])).strip()
        price = float(data.get("price", current["price"]))
        threshold = int(data.get("low_stock_threshold", current["low_stock_threshold"]))
        if not sku or not name or price < 0 or threshold < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(error="Invalid product data"), 400

    db = get_db()
    try:
        db.execute(
            """
            UPDATE products
            SET sku = ?, name = ?, price = ?, low_stock_threshold = ?, updated_at = ?
            WHERE id = ?
            """,
            (sku, name, price, threshold, utc_now(), product_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="SKU already exists"), 409
    return jsonify(product_to_dict(get_product_or_none(product_id)))


@app.delete("/api/products/<int:product_id>")
def delete_product(product_id: int):
    if get_product_or_none(product_id) is None:
        return jsonify(error="Product not found"), 404
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    return "", 204


@app.post("/api/products/<int:product_id>/stock")
def change_stock(product_id: int):
    product = get_product_or_none(product_id)
    if product is None:
        return jsonify(error="Product not found"), 404

    data, error = parse_json(("type", "quantity"))
    if error:
        return error
    movement_type = str(data["type"]).lower().strip()
    try:
        quantity = int(data["quantity"])
    except (TypeError, ValueError):
        return jsonify(error="Quantity must be an integer"), 400

    if movement_type not in {"in", "out", "adjustment"}:
        return jsonify(error="type must be in, out, or adjustment"), 400
    if quantity < 0:
        return jsonify(error="Quantity must be non-negative"), 400

    current_stock = product["stock"]
    if movement_type == "in":
        new_stock = current_stock + quantity
        recorded_quantity = quantity
    elif movement_type == "out":
        if quantity > current_stock:
            return jsonify(error="Insufficient stock"), 409
        new_stock = current_stock - quantity
        recorded_quantity = -quantity
    else:
        new_stock = quantity
        recorded_quantity = quantity - current_stock

    now = utc_now()
    db = get_db()
    db.execute(
        "UPDATE products SET stock = ?, updated_at = ? WHERE id = ?",
        (new_stock, now, product_id),
    )
    db.execute(
        """
        INSERT INTO stock_movements (product_id, movement_type, quantity, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (product_id, movement_type, recorded_quantity, data.get("note"), now),
    )
    db.commit()
    return jsonify(product_to_dict(get_product_or_none(product_id)))


@app.get("/api/products/<int:product_id>/movements")
def list_movements(product_id: int):
    if get_product_or_none(product_id) is None:
        return jsonify(error="Product not found"), 404
    rows = get_db().execute(
        "SELECT * FROM stock_movements WHERE product_id = ? ORDER BY id DESC",
        (product_id,),
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/low-stock")
def low_stock():
    rows = get_db().execute(
        "SELECT * FROM products WHERE stock <= low_stock_threshold ORDER BY stock ASC, name ASC"
    ).fetchall()
    return jsonify([product_to_dict(row) for row in rows])


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5003")))
