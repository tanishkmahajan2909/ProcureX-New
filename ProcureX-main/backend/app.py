import os
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, jsonify, request
from flask_cors import CORS
from psycopg2 import sql
from psycopg2.errors import ForeignKeyViolation, UniqueViolation, CheckViolation

from db import db_cursor

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Only these database tables/columns can be used by the generic CRUD endpoints.
# Values are still passed as SQL parameters (%s) instead of being concatenated.
TABLES = {
    "corporation": {
        "pk": "company_id",
        "columns": {"company_name", "address", "gst_no"},
    },
    "department": {
        "pk": "department_id",
        "columns": {"company_id", "department_name"},
    },
    "role": {
        "pk": "role_id",
        "columns": {"role_name"},
    },
    "employee": {
        "pk": "employee_id",
        "columns": {"name", "email", "department_id", "role_id"},
    },
    "product": {
        "pk": "product_id",
        "columns": {"product_name", "category", "unit"},
    },
    "vendor": {
        "pk": "vendor_id",
        "columns": {"vendor_name", "email", "phone", "address", "gst_no"},
    },
    "purchase_request": {
        "pk": "pr_id",
        "columns": {"requestor_id", "department_id", "request_date", "approver_id", "approval_status"},
    },
    "purchase_request_item": {
        "pk": "pr_item_id",
        "columns": {"pr_id", "product_id", "quantity", "required_date"},
    },
    "rfq": {
        "pk": "rfq_id",
        "columns": {"pr_id", "procurement_officer_id", "issue_date", "due_date"},
    },
    "rfq_vendor": {
        "pk": None,
        "columns": {"rfq_id", "vendor_id"},
    },
    "quotation": {
        "pk": "quotation_id",
        "columns": {"rfq_id", "vendor_id", "quoted_price", "delivery_days", "submitted_date"},
    },
    "vendor_rating": {
        "pk": "rating_id",
        "columns": {"vendor_id", "rating_score", "rating_date"},
    },
    "purchase_order": {
        "pk": "po_id",
        "columns": {"quotation_id", "procurement_officer_id", "po_date", "total_amount", "po_status"},
    },
    "delivery": {
        "pk": "delivery_id",
        "columns": {"po_id", "delivery_date", "delivery_status"},
    },
    "quality_inspection": {
        "pk": "inspection_id",
        "columns": {"delivery_id", "inspector_id", "inspection_date", "result"},
    },
    "distribution": {
        "pk": "distribution_id",
        "columns": {"delivery_id", "department_id", "distributed_date", "received_by"},
    },
    "invoice": {
        "pk": "invoice_id",
        "columns": {"po_id", "vendor_id", "invoice_amount", "invoice_date", "verification_status"},
    },
    "payment": {
        "pk": "payment_id",
        "columns": {"invoice_id", "payment_date", "amount_paid", "payment_status"},
    },
}


def json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    return value


def rows(cursor):
    return json_safe([dict(row) for row in cursor.fetchall()])


def one(cursor):
    row = cursor.fetchone()
    return json_safe(dict(row)) if row else None


def validate_table(table):
    if table not in TABLES:
        raise ValueError(f"Table '{table}' is not allowed")
    return TABLES[table]


def validate_body(table, body):
    config = validate_table(table)
    if not isinstance(body, dict) or not body:
        raise ValueError("Request body must contain at least one field")
    unknown = set(body) - config["columns"]
    if unknown:
        raise ValueError(f"Invalid column(s) for {table}: {', '.join(sorted(unknown))}")
    return config


@app.get("/api/health")
def health():
    with db_cursor() as cur:
        cur.execute("SELECT current_database() AS database_name, version() AS version")
        info = one(cur)
    return jsonify({"ok": True, **info})


@app.get("/api/bootstrap")
def bootstrap():
    """Load the application data with normal PostgreSQL SELECT/JOIN queries."""
    data = {}
    with db_cursor() as cur:
        cur.execute("SELECT * FROM corporation ORDER BY company_id")
        data["corporations"] = rows(cur)

        cur.execute("""
            SELECT e.employee_id, e.name, e.email, e.department_id, e.role_id,
                   d.department_name, r.role_name
            FROM employee e
            JOIN department d ON d.department_id = e.department_id
            JOIN role r ON r.role_id = e.role_id
            ORDER BY e.employee_id
        """)
        employees = rows(cur)
        for e in employees:
            e["department"] = {"department_name": e.pop("department_name")}
            e["role"] = {"role_name": e.pop("role_name")}
        data["employees"] = employees

        cur.execute("SELECT department_id, department_name FROM department ORDER BY department_id")
        data["departments"] = rows(cur)

        cur.execute("SELECT role_id, role_name FROM role ORDER BY role_id")
        data["roles"] = rows(cur)

        cur.execute("SELECT product_id, product_name, category, unit FROM product ORDER BY product_id")
        data["products"] = rows(cur)

        cur.execute("SELECT vendor_id, vendor_name, email, phone, address, gst_no FROM vendor ORDER BY vendor_id")
        data["vendors"] = rows(cur)

        cur.execute("""
            SELECT vendor_id, rating_score, rating_date
            FROM vendor_rating
            ORDER BY rating_date DESC, rating_id DESC
        """)
        data["vendor_ratings"] = rows(cur)

        cur.execute("""
            SELECT pr.pr_id, pr.request_date, pr.approval_status,
                   req.name AS requestor_name,
                   app.name AS approver_name,
                   d.department_name
            FROM purchase_request pr
            JOIN employee req ON req.employee_id = pr.requestor_id
            LEFT JOIN employee app ON app.employee_id = pr.approver_id
            JOIN department d ON d.department_id = pr.department_id
            ORDER BY pr.request_date DESC, pr.pr_id DESC
        """)
        purchase_requests = rows(cur)
        for pr in purchase_requests:
            pr["requestor"] = {"name": pr.pop("requestor_name")}
            approver_name = pr.pop("approver_name")
            pr["approver"] = {"name": approver_name} if approver_name else None
            pr["department"] = {"department_name": pr.pop("department_name")}
        data["purchase_requests"] = purchase_requests

        cur.execute("""
            SELECT pri.pr_item_id, pri.pr_id, pri.quantity, pri.required_date,
                   p.product_name, p.unit
            FROM purchase_request_item pri
            JOIN product p ON p.product_id = pri.product_id
            ORDER BY pri.pr_item_id
        """)
        pr_items = rows(cur)
        for item in pr_items:
            item["product"] = {
                "product_name": item.pop("product_name"),
                "unit": item.pop("unit"),
            }
        data["purchase_request_items"] = pr_items

        cur.execute("""
            SELECT q.rfq_id, q.pr_id, q.issue_date, q.due_date, e.name AS officer_name
            FROM rfq q
            JOIN employee e ON e.employee_id = q.procurement_officer_id
            ORDER BY q.rfq_id
        """)
        rfqs = rows(cur)
        for q in rfqs:
            q["procurement_officer"] = {"name": q.pop("officer_name")}
        data["rfqs"] = rfqs

        cur.execute("SELECT rfq_id, vendor_id FROM rfq_vendor ORDER BY rfq_id, vendor_id")
        data["rfq_vendors"] = rows(cur)

        cur.execute("""
            SELECT q.quotation_id, q.rfq_id, q.quoted_price, q.delivery_days,
                   q.vendor_id, v.vendor_name
            FROM quotation q
            JOIN vendor v ON v.vendor_id = q.vendor_id
            ORDER BY q.quotation_id
        """)
        quotations = rows(cur)
        for q in quotations:
            q["vendor"] = {"vendor_name": q.pop("vendor_name")}
        data["quotations"] = quotations

        cur.execute("""
            SELECT po.po_id, po.po_date, po.total_amount, po.po_status,
                   v.vendor_name, e.name AS officer_name
            FROM purchase_order po
            JOIN quotation q ON q.quotation_id = po.quotation_id
            JOIN vendor v ON v.vendor_id = q.vendor_id
            JOIN employee e ON e.employee_id = po.procurement_officer_id
            ORDER BY po.po_date DESC, po.po_id DESC
        """)
        purchase_orders = rows(cur)
        for po in purchase_orders:
            po["quotation"] = {"vendor": {"vendor_name": po.pop("vendor_name")}}
            po["procurement_officer"] = {"name": po.pop("officer_name")}
        data["purchase_orders"] = purchase_orders

        cur.execute("""
            SELECT delivery_id, po_id, delivery_date, delivery_status
            FROM delivery
            ORDER BY delivery_date DESC NULLS LAST, delivery_id DESC
        """)
        data["deliveries"] = rows(cur)

        cur.execute("""
            SELECT qi.inspection_id, qi.delivery_id, qi.inspection_date, qi.result,
                   e.name AS inspector_name
            FROM quality_inspection qi
            JOIN employee e ON e.employee_id = qi.inspector_id
            ORDER BY qi.inspection_date DESC, qi.inspection_id DESC
        """)
        inspections = rows(cur)
        for i in inspections:
            i["inspector"] = {"name": i.pop("inspector_name")}
        data["inspections"] = inspections

        cur.execute("""
            SELECT dist.distribution_id, dist.delivery_id, dist.distributed_date,
                   d.department_name, e.name AS received_by_name
            FROM distribution dist
            JOIN department d ON d.department_id = dist.department_id
            JOIN employee e ON e.employee_id = dist.received_by
            ORDER BY dist.distributed_date DESC, dist.distribution_id DESC
        """)
        distributions = rows(cur)
        for d in distributions:
            d["department"] = {"department_name": d.pop("department_name")}
            d["received_by_emp"] = {"name": d.pop("received_by_name")}
        data["distributions"] = distributions

        cur.execute("""
            SELECT i.invoice_id, i.po_id, i.invoice_amount, i.verification_status,
                   v.vendor_name
            FROM invoice i
            JOIN vendor v ON v.vendor_id = i.vendor_id
            ORDER BY i.invoice_date DESC, i.invoice_id DESC
        """)
        invoices = rows(cur)
        for i in invoices:
            i["vendor"] = {"vendor_name": i.pop("vendor_name")}
        data["invoices"] = invoices

        cur.execute("""
            SELECT payment_id, invoice_id, amount_paid, payment_status
            FROM payment
            ORDER BY payment_date DESC NULLS LAST, payment_id DESC
        """)
        data["payments"] = rows(cur)

    return jsonify(data)


@app.delete("/api/purchase-requests/<int:pr_id>")
def delete_purchase_request(pr_id):
    """Explicit DELETE used by the Purchase Request button in React."""
    try:
        with db_cursor(commit=True) as cur:
            # This is the exact SQL your frontend-triggered API call executes.
            cur.execute(
                "DELETE FROM purchase_request WHERE pr_id = %s RETURNING *",
                (pr_id,),
            )
            deleted = one(cur)
        if not deleted:
            return jsonify({"error": "Purchase request not found"}), 404
        return jsonify({"deleted": deleted})
    except ForeignKeyViolation as e:
        return jsonify({"error": e.diag.message_primary or "Cannot delete because related records exist."}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/crud/<table>")
def insert_record(table):
    """INSERT endpoint used by React forms. This executes real SQL in PostgreSQL."""
    try:
        body = request.get_json(silent=True) or {}
        validate_body(table, body)
        columns = list(body.keys())
        values = [body[column] for column in columns]

        query = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING *").format(
            table=sql.Identifier(table),
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
            placeholders=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        )
        with db_cursor(commit=True) as cur:
            cur.execute(query, values)
            created = one(cur)
        return jsonify([created]), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except (ForeignKeyViolation, UniqueViolation, CheckViolation) as e:
        return jsonify({"error": e.diag.message_primary or str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.patch("/api/crud/<table>/<id_column>/<int:id_value>")
def update_record(table, id_column, id_value):
    """UPDATE endpoint. Example SQL: UPDATE purchase_request SET approval_status=%s WHERE pr_id=%s."""
    try:
        body = request.get_json(silent=True) or {}
        config = validate_body(table, body)
        if id_column != config["pk"]:
            raise ValueError(f"Invalid id column '{id_column}' for {table}")

        columns = list(body.keys())
        assignments = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(column), sql.Placeholder())
            for column in columns
        )
        query = sql.SQL("UPDATE {table} SET {assignments} WHERE {id_column} = %s RETURNING *").format(
            table=sql.Identifier(table),
            assignments=assignments,
            id_column=sql.Identifier(id_column),
        )
        values = [body[column] for column in columns] + [id_value]

        with db_cursor(commit=True) as cur:
            cur.execute(query, values)
            updated = one(cur)
        if not updated:
            return jsonify({"error": "Record not found"}), 404
        return jsonify([updated])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except (ForeignKeyViolation, UniqueViolation, CheckViolation) as e:
        return jsonify({"error": e.diag.message_primary or str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.delete("/api/crud/<table>/<id_column>/<int:id_value>")
def delete_record(table, id_column, id_value):
    """
    DELETE endpoint called by the React Delete button.

    For a purchase request with id 3, the executed SQL is equivalent to:
        DELETE FROM purchase_request WHERE pr_id = 3;
    """
    try:
        config = validate_table(table)
        if not config["pk"] or id_column != config["pk"]:
            raise ValueError(f"Invalid id column '{id_column}' for {table}")

        query = sql.SQL("DELETE FROM {table} WHERE {id_column} = %s RETURNING *").format(
            table=sql.Identifier(table),
            id_column=sql.Identifier(id_column),
        )
        with db_cursor(commit=True) as cur:
            cur.execute(query, (id_value,))
            deleted = one(cur)
        if not deleted:
            return jsonify({"error": "Record not found"}), 404
        return jsonify({"deleted": deleted})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ForeignKeyViolation as e:
        return jsonify({"error": e.diag.message_primary or "Cannot delete because related records exist."}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/vendor-ranking/<int:rfq_id>")
def vendor_ranking(rfq_id):
    """Run the project's 50% price + 20% delivery + 30% rating SQL query."""
    query = """
        WITH latest_rating AS (
            SELECT vendor_id, rating_score,
                   ROW_NUMBER() OVER (
                       PARTITION BY vendor_id
                       ORDER BY rating_date DESC, rating_id DESC
                   ) AS rn
            FROM vendor_rating
        ),
        quote_data AS (
            SELECT q.quotation_id, q.rfq_id, v.vendor_id, v.vendor_name,
                   q.quoted_price, q.delivery_days,
                   COALESCE(lr.rating_score, 0) AS rating_score
            FROM quotation q
            JOIN vendor v ON v.vendor_id = q.vendor_id
            LEFT JOIN latest_rating lr
              ON lr.vendor_id = v.vendor_id AND lr.rn = 1
            WHERE q.rfq_id = %s
        ),
        normalized AS (
            SELECT *,
                   1 - (quoted_price - MIN(quoted_price) OVER ()) /
                       NULLIF(MAX(quoted_price) OVER () - MIN(quoted_price) OVER (), 0) AS price_score,
                   1 - (delivery_days - MIN(delivery_days) OVER ()) /
                       NULLIF(MAX(delivery_days) OVER () - MIN(delivery_days) OVER (), 0) AS delivery_score,
                   rating_score / 5.0 AS rating_norm
            FROM quote_data
        )
        SELECT vendor_name, quoted_price, delivery_days, rating_score,
               ROUND(
                   (0.5 * COALESCE(price_score, 1)) +
                   (0.2 * COALESCE(delivery_score, 1)) +
                   (0.3 * rating_norm),
                   3
               ) AS final_score
        FROM normalized
        ORDER BY final_score DESC
    """
    with db_cursor() as cur:
        cur.execute(query, (rfq_id,))
        ranked = rows(cur)
    return jsonify(ranked)


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "API route not found"}), 404


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)
