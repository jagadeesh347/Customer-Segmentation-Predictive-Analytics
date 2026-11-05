
from flask import (
    Flask, render_template, send_file, request,
    make_response, redirect, url_for
)
import pandas as pd
import os
import subprocess
import sys
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

CSV_PATH = os.path.join(
    PROJECT_DIR, "analysis", "customer_segments.csv"
)



def calculate_churn_risk(recency, frequency, monetary):
    # Customer has no completed purchases
    if frequency is None or frequency <= 0:
        return {
            "churn_status": "New Customer",
            "churn_probability": None,
            "churn_prediction": 0
        }

    # Missing or invalid recency
    if recency is None or recency < 0:
        return {
            "churn_status": "Unclassified",
            "churn_probability": None,
            "churn_prediction": 0
        }

    # Recency score
    if recency <= 30:
        score = 5
    elif recency <= 60:
        score = 20
    elif recency <= 90:
        score = 35
    else:
        score = 50

    # Frequency score
    if frequency == 1:
        score += 10
    elif frequency <= 3:
        score += 5

    # Spending score
    if monetary < 500:
        score += 15
    elif monetary < 1500:
        score += 10
    else:
        score += 5

    score = min(score, 100)

    # Risk classification
    if score >= 70:
        status = "High Risk"
    elif score >= 40:
        status = "Medium Risk"
    else:
        status = "Low Risk"

    return {
        "churn_status": status,
        "churn_probability": score,
        "churn_prediction": int(score >= 70)
    }



def get_database_customers():
    from app.db import get_connection

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                c.customer_id,
                c.customer_code,
                c.signup_date,
                COALESCE(o.frequency, 0) AS frequency,
                COALESCE(o.monetary, 0) AS monetary,
                CASE
                    WHEN o.last_order_date IS NOT NULL
                    THEN DATEDIFF(
                        CURRENT_DATE, o.last_order_date
                    )
                    ELSE NULL
                END AS recency,
                cs.segment_label AS segment_name
            FROM customers c
            LEFT JOIN (
                SELECT
                    ord.customer_id,
                    COUNT(DISTINCT ord.order_id) AS frequency,
                    COALESCE(
                        SUM(oi.quantity * oi.unit_price), 0
                    ) AS monetary,
                    MAX(ord.order_date) AS last_order_date
                FROM orders ord
                LEFT JOIN order_items oi
                    ON oi.order_id = ord.order_id
                WHERE ord.order_status = 'Completed'
                GROUP BY ord.customer_id
            ) o ON o.customer_id = c.customer_id
            LEFT JOIN customer_segments cs
                ON cs.customer_id = c.customer_id
                AND cs.run_id = (
                    SELECT MAX(run_id) FROM segment_runs
                )
            ORDER BY c.customer_code
        """)

        rows = cursor.fetchall()

        segment_ids = {
            "Low-Activity Customers": 0,
            "Regular Customers": 1,
            "High-Value Customers": 2
        }

        for row in rows:
            if not row["segment_name"]:
                row["segment_name"] = "Not Yet Segmented"

            row["segment"] = segment_ids.get(
                row["segment_name"], -1
            )

            row.update(calculate_churn_risk(
                row["recency"],
                row["frequency"],
                row["monetary"]
            ))

        return rows

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def get_segment_recommendation(name):
    recommendations = {
        "High-Value Customers": (
            "Reward loyalty",
            "Offer exclusive benefits and personalized rewards "
            "to encourage repeat purchases."
        ),
        "Regular Customers": (
            "Increase engagement",
            "Use relevant product recommendations and loyalty "
            "points to encourage more purchases."
        ),
        "Low-Activity Customers": (
            "Re-engage customers",
            "Consider a personalized reminder or return offer."
        ),
        "Not Yet Segmented": (
            "Run segmentation",
            "Run customer segmentation to assign this customer "
            "to a group."
        )
    }

    return recommendations.get(
        name,
        (
            "Review segment",
            "Review customer behavior before choosing an action."
        )
    )


@app.route("/")
def home():
    try:
        customers = get_database_customers()
    except Exception as exc:
        print("Database error:", exc)
        customers = []

    for customer in customers:
        customer.setdefault("churn_status", "Unclassified")
        customer.setdefault("churn_probability", None)
        customer.setdefault("frequency", 0)
        customer.setdefault("monetary", 0)
        customer.setdefault("recency", -1)
        customer.setdefault("segment_name", "Not Yet Segmented")

    at_risk_customers = sum(
        c["churn_status"] == "High Risk" for c in customers
    )
    medium_risk_customers = sum(
        c["churn_status"] == "Medium Risk" for c in customers
    )
    active_customers = sum(
        c["churn_status"] == "Low Risk" for c in customers
    )
    new_customers = sum(
        c["churn_status"] == "New Customer" for c in customers
    )

    total_customers = len(customers)

    total_revenue = sum(
        float(c.get("monetary") or 0) for c in customers
    )
    average_spending = (
        total_revenue / total_customers if total_customers else 0
    )

    top_customer = max(
        customers,
        key=lambda c: float(c.get("monetary") or 0),
        default={}
    )
    top_customer_code = top_customer.get("customer_code", "N/A")
    top_customer_spending = float(
        top_customer.get("monetary") or 0
    )

    segments = {}
    segment_spending = {}
    segment_insights = []

    for customer in customers:
        name = customer.get("segment_name") or "Not Yet Segmented"
        segments[name] = segments.get(name, 0) + 1
        segment_spending[name] = (
            segment_spending.get(name, 0)
            + float(customer.get("monetary") or 0)
        )

    segment_names = {name: name for name in segments}
    total_segments = len(segments)
    largest_segment = (
        max(segments, key=segments.get) if segments else "N/A"
    )

    # Build segment recommendations for the dashboard.
    for name, count in segments.items():
        members = [
            c for c in customers if c["segment_name"] == name
        ]
        revenue = sum(float(c.get("monetary") or 0) for c in members)
        frequency_avg = (
            sum(c["frequency"] for c in members) / count
            if count else 0
        )
        recencies = [
            c["recency"] for c in members
            if c["recency"] is not None and c["recency"] >= 0
        ]
        recency_avg = (
            sum(recencies) / len(recencies) if recencies else 0
        )
        title, recommendation = get_segment_recommendation(name)

        segment_insights.append({
            "name": name,
            "count": count,
            "revenue": revenue,
            "average_spending": revenue / count if count else 0,
            "average_frequency": frequency_avg,
            "average_recency": recency_avg,
            "recommendation_title": title,
            "recommendation": recommendation
        })

    return render_template(
        "index.html",
        customers=customers,
        total_customers=total_customers,
        total_segments=total_segments,
        total_revenue=total_revenue,
        average_spending=average_spending,
        top_customer_code=top_customer_code,
        top_customer_spending=top_customer_spending,
        largest_segment=largest_segment,
        segments=segments,
        segment_names=segment_names,
        segment_spending=segment_spending,
        segment_insights=segment_insights,
        at_risk_customers=at_risk_customers,
        active_customers=active_customers,
        medium_risk_customers=medium_risk_customers,
        new_customers=new_customers,
        churn_model_available=False,
        churn_metrics=None
    )


@app.route("/download-report")
def download_report():
    if not os.path.exists(CSV_PATH):
        return "Report not found. Run customer segmentation first.", 404

    return send_file(
        CSV_PATH,
        as_attachment=True,
        download_name="customer_segmentation_report.csv",
        mimetype="text/csv"
    )


@app.route("/download-pdf")
def download_pdf():
    if not os.path.exists(CSV_PATH):
        return "Report not found. Run customer segmentation first.", 404

    df = pd.read_csv(CSV_PATH)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    content = [
        Paragraph("Customer Segmentation Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Customer Summary", styles["Heading2"]),
        Paragraph(f"Total customers: {len(df)}", styles["Normal"])
    ]

    if "monetary" in df.columns:
        total_spending = pd.to_numeric(
            df["monetary"], errors="coerce"
        ).fillna(0).sum()
        content.append(Paragraph(
            f"Total customer spending: {total_spending:.2f}",
            styles["Normal"]
        ))

    if "segment_name" in df.columns:
        content.extend([
            Spacer(1, 12),
            Paragraph("Segment Summary", styles["Heading2"])
        ])
        summary = (
            df.groupby("segment_name")
            .size()
            .reset_index(name="Customers")
        )
        data = [["Customer Segment", "Number of Customers"]]
        data.extend(summary.values.tolist())

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0),
             colors.HexColor("#243B53")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 6)
        ]))
        content.append(table)

    columns = [
        col for col in [
            "customer_code", "frequency", "monetary",
            "recency", "segment_name"
        ] if col in df.columns
    ]

    if columns:
        content.extend([
            Spacer(1, 16),
            Paragraph("Customer Details", styles["Heading2"])
        ])
        data = [columns]
        for _, row in df[columns].fillna("").iterrows():
            data.append([str(value) for value in row.tolist()])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0),
             colors.HexColor("#243B53")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 5)
        ]))
        content.append(table)

    doc.build(content)
    buffer.seek(0)

    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        'attachment; filename="customer_segmentation_report.pdf"'
    )
    return response


@app.route("/predict", methods=["GET", "POST"])
def predict():
    if request.method == "GET":
        return render_template(
            "predict.html",
            prediction=None,
            probability=None,
            recency=None,
            frequency=None,
            monetary=None
        )

    try:
        recency = int(request.form["recency"])
        frequency = int(request.form["frequency"])
        monetary = float(request.form["monetary"])

        if recency < 0 or frequency < 0 or monetary < 0:
            raise ValueError

        result = calculate_churn_risk(
            recency, frequency, monetary
        )

        return render_template(
            "predict.html",
            prediction=result["churn_status"],
            probability=result["churn_probability"],
            recency=recency,
            frequency=frequency,
            monetary=monetary
        )

    except (ValueError, TypeError):
        return "Please enter valid, non-negative numeric values.", 400


@app.route("/add-customer", methods=["GET", "POST"])
def add_customer():
    from app.db import get_connection
    from datetime import date

    message = None
    error = None

    if request.method == "POST":
        customer_code = request.form.get("customer_code", "").strip()
        signup_date = request.form.get("signup_date", "").strip()

        if not customer_code:
            error = "Customer code is required."
        else:
            connection = None
            cursor = None
            try:
                connection = get_connection()
                cursor = connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO customers (customer_code, signup_date)
                    VALUES (%s, %s)
                    """,
                    (customer_code, signup_date or None)
                )
                connection.commit()
                message = "Customer added successfully!"
            except Exception as exc:
                if connection is not None:
                    connection.rollback()
                print("Add customer error:", exc)
                error = (
                    "Could not add customer. Check that the customer "
                    "code is unique and the date is valid."
                )
            finally:
                if cursor is not None:
                    cursor.close()
                if connection is not None and connection.is_connected():
                    connection.close()

    return render_template(
        "add_customer.html",
        message=message,
        error=error,
        today=date.today().isoformat()
    )


@app.route("/delete-customer", methods=["POST"])
def delete_customer():
    from app.db import get_connection

    customer_id = request.form.get("customer_id", "").strip()
    if not customer_id.isdigit():
        return "Invalid customer ID.", 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        connection.start_transaction()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT customer_id FROM customers WHERE customer_id = %s",
            (int(customer_id),)
        )
        if cursor.fetchone() is None:
            connection.rollback()
            return "Customer not found.", 404

        cursor.execute("""
            DELETE oi FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.customer_id = %s
        """, (int(customer_id),))

        cursor.execute(
            "DELETE FROM orders WHERE customer_id = %s",
            (int(customer_id),)
        )
        cursor.execute(
            "DELETE FROM customer_segments WHERE customer_id = %s",
            (int(customer_id),)
        )
        cursor.execute(
            "DELETE FROM customers WHERE customer_id = %s",
            (int(customer_id),)
        )

        connection.commit()
        return redirect(url_for("home"))

    except Exception as exc:
        if connection is not None:
            connection.rollback()
        print("Delete customer error:", exc)
        return "Could not delete customer. No changes were committed.", 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/run-segmentation", methods=["POST"])
def run_segmentation():
    script_path = os.path.join(
        PROJECT_DIR, "analysis", "customer_segmentation.py"
    )

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            print("Segmentation error:", result.stderr)
            print("Segmentation output:", result.stdout)
            return "Segmentation failed. Check the VS Code terminal.", 500

        print(result.stdout)
        return redirect(url_for("home"))

    except subprocess.TimeoutExpired:
        return "Segmentation timed out. Please try again.", 500
    except Exception as exc:
        print("Segmentation error:", exc)
        return "Could not run segmentation. Check the VS Code terminal.", 500


@app.route("/add-purchase", methods=["GET", "POST"])
def add_purchase():
    from app.db import get_connection
    from datetime import date

    connection = None
    cursor = None
    message = None
    error = None
    customers_list = []

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if request.method == "POST":
            customer_id = request.form.get("customer_id", "")
            order_date = request.form.get("order_date", "")
            quantity = int(request.form.get("quantity", ""))
            unit_price = float(request.form.get("unit_price", ""))

            if not customer_id.isdigit():
                raise ValueError("Please select a valid customer.")
            if quantity <= 0 or unit_price < 0:
                raise ValueError(
                    "Quantity must be positive and price cannot be negative."
                )

            cursor.execute(
                "SELECT customer_id FROM customers WHERE customer_id = %s",
                (int(customer_id),)
            )
            if cursor.fetchone() is None:
                raise ValueError("Customer not found.")

            cursor.execute(
                """
                INSERT INTO orders (customer_id, order_date, order_status)
                VALUES (%s, %s, 'Completed')
                """,
                (int(customer_id), order_date or None)
            )
            order_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO order_items (order_id, quantity, unit_price)
                VALUES (%s, %s, %s)
                """,
                (order_id, quantity, unit_price)
            )

            connection.commit()
            message = "Purchase added successfully!"

        cursor.execute("""
            SELECT customer_id, customer_code
            FROM customers
            ORDER BY customer_code
        """)
        customers_list = cursor.fetchall()

    except (ValueError, TypeError) as exc:
        if connection is not None:
            connection.rollback()
        error = str(exc)

        if cursor is not None:
            cursor.execute("""
                SELECT customer_id, customer_code
                FROM customers
                ORDER BY customer_code
            """)
            customers_list = cursor.fetchall()

    except Exception as exc:
        if connection is not None:
            connection.rollback()
        print("Add purchase error:", exc)
        error = "Could not add purchase. Check the terminal for details."

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return render_template(
        "add_purchase.html",
        customers=customers_list,
        message=message,
        error=error,
        today=date.today().isoformat()
    )


if __name__ == "__main__":
    app.run(debug=True)
