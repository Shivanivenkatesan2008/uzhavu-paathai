
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from database import create_database
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "uzhavu_paathai_demo_secret")
create_database()

def get_db():
    conn = sqlite3.connect("uzhavu.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# HOME
@app.route("/")
def home():
    return render_template("index.html")


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        village = request.form.get("village", "").strip()
        district = request.form.get("district", "").strip()

        if not name or not mobile or not password:
            flash("Please fill all required fields.")
        elif not mobile.isdigit() or len(mobile) != 10:
            flash("Enter a valid 10-digit mobile number.")
        elif len(password) < 6:
            flash("Password must have at least 6 characters.")
        else:
            conn = get_db()
            try:
                conn.execute(
                    """INSERT INTO farmers
                    (name, mobile, password, village, district)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        name, mobile, generate_password_hash(password),
                        village, district
                    )
                )
                conn.commit()
                flash("Registration successful! Please log in.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("This mobile number is already registered.")
            finally:
                conn.close()

    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        farmer = conn.execute(
            "SELECT * FROM farmers WHERE mobile = ?", (mobile,)
        ).fetchone()
        conn.close()

        if farmer and check_password_hash(farmer["password"], password):
            session["farmer_id"] = farmer["id"]
            session["farmer_name"] = farmer["name"]
            return redirect(url_for("dashboard"))

        flash("Invalid mobile number or password.")

    return render_template("login.html")


# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        farmer_name=session["farmer_name"]
    )


# CROP DETAILS
@app.route("/crops", methods=["GET", "POST"])
def crops():
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    if request.method == "POST":
        crop_name = request.form.get("crop_name", "").strip()
        quality = request.form.get("quality", "").strip()
        location = request.form.get("location", "").strip()
        unit = request.form.get("unit", "kg")
        quantity = request.form.get("quantity", "").strip()
        expected_price = request.form.get("expected_price", "").strip()

        try:
            if not crop_name or not quantity:
                flash("Enter crop name and quantity.")
            elif float(quantity) <= 0:
                flash("Quantity must be greater than zero.")
            elif expected_price and float(expected_price) < 0:
                flash("Expected price cannot be negative.")
            else:
                conn.execute(
                    """INSERT INTO crops
                    (farmer_id, crop_name, quantity, quality, location,
                     expected_price, unit)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        session["farmer_id"], crop_name, float(quantity),
                        quality, location,
                        float(expected_price) if expected_price else None,
                        unit
                    )
                )
                conn.commit()
                flash("Crop saved successfully!")

        except ValueError:
            flash("Enter valid numbers for quantity and price.")

    crop_list = conn.execute(
        """SELECT * FROM crops
        WHERE farmer_id = ?
        ORDER BY id DESC""",
        (session["farmer_id"],)
    ).fetchall()

    conn.close()
    return render_template("crops.html", crop_list=crop_list)


# MARKET PRICE COMPARISON
@app.route("/markets")
def markets():
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    crop_name = request.args.get("crop", "").strip()
    conn = get_db()

    if crop_name:
        prices = conn.execute(
            """SELECT mp.crop_name, m.market_name, m.district,
                      mp.price_per_kg
               FROM market_prices mp
               JOIN markets m ON m.id = mp.market_id
               WHERE lower(mp.crop_name) = lower(?)
               ORDER BY mp.price_per_kg DESC""",
            (crop_name,)
        ).fetchall()
    else:
        prices = conn.execute(
            """SELECT mp.crop_name, m.market_name, m.district,
                      mp.price_per_kg
               FROM market_prices mp
               JOIN markets m ON m.id = mp.market_id
               ORDER BY mp.crop_name, mp.price_per_kg DESC"""
        ).fetchall()

    conn.close()

    return render_template(
        "market_prices.html",
        prices=prices,
        selected_crop=crop_name
    )


# PRICE DISCOVERY
@app.route("/price-discovery", methods=["GET", "POST"])
def price_discovery():
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    result = None

    if request.method == "POST":
        try:
            quantity = float(request.form.get("quantity", "0"))
            price = float(request.form.get("price", "0"))
            transport = float(request.form.get("transport", "0"))
            storage = float(request.form.get("storage", "0"))
            other = float(request.form.get("other", "0"))

            if quantity <= 0 or min(price, transport, storage, other) < 0:
                raise ValueError

            total = quantity * price
            expenses = transport + storage + other

            result = {
                "total": total,
                "expenses": expenses,
                "net": total - expenses
            }

        except ValueError:
            flash("Enter a valid quantity, price and non-negative expenses.")

    return render_template("price_discovery.html", result=result)


# BUYER LIST
@app.route("/buyers")
def buyers():
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    crop_name = request.args.get("crop", "").strip()
    conn = get_db()

    if crop_name:
        buyer_list = conn.execute(
            """SELECT * FROM buyers
               WHERE lower(crop_name) = lower(?)
               ORDER BY offered_price DESC""",
            (crop_name,)
        ).fetchall()
    else:
        buyer_list = conn.execute(
            """SELECT * FROM buyers
               ORDER BY crop_name, offered_price DESC"""
        ).fetchall()

    conn.close()

    return render_template(
        "buyers.html",
        buyers=buyer_list,
        selected_crop=crop_name
    )


# FARMER SENDS AN OFFER
@app.route("/offers", methods=["GET", "POST"])
def offers():
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    if request.method == "POST":
        try:
            buyer_id = int(request.form.get("buyer_id", "0"))
            crop_name = request.form.get("crop_name", "").strip()
            quantity = float(request.form.get("quantity", "0"))
            price = float(request.form.get("price", "0"))

            buyer = conn.execute(
                "SELECT * FROM buyers WHERE id = ?", (buyer_id,)
            ).fetchone()

            if not buyer or crop_name.lower() != buyer["crop_name"].lower():
                flash("Please select a valid buyer and matching crop.")
            elif quantity <= 0 or price <= 0:
                flash("Quantity and offer price must be greater than zero.")
            elif quantity > buyer["required_quantity"]:
                flash("Quantity exceeds the buyer's required quantity.")
            else:
                conn.execute(
                    """INSERT INTO offers
                    (farmer_id, buyer_id, crop_name, quantity,
                     price_per_kg, status, farmer_agreed, buyer_agreed)
                    VALUES (?, ?, ?, ?, ?, 'Pending', 1, 0)""",
                    (
                        session["farmer_id"], buyer_id, crop_name,
                        quantity, price
                    )
                )
                conn.commit()
                flash("Offer sent! Waiting for buyer response.")

        except (ValueError, TypeError):
            flash("Enter valid offer details.")

    offer_list = conn.execute(
        """SELECT o.*, b.buyer_name
           FROM offers o
           JOIN buyers b ON b.id = o.buyer_id
           WHERE o.farmer_id = ?
           ORDER BY o.id DESC""",
        (session["farmer_id"],)
    ).fetchall()

    buyer_list = conn.execute(
        "SELECT * FROM buyers ORDER BY crop_name, buyer_name"
    ).fetchall()

    conn.close()

    return render_template(
        "offers.html",
        offers=offer_list,
        buyers=buyer_list
    )


# DEMO BUYER ACCEPTS OR MAKES A COUNTER-OFFER
@app.route("/offers/<int:offer_id>/buyer-response", methods=["POST"])
def buyer_response(offer_id):
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    action = request.form.get("action", "")
    conn = get_db()

    offer = conn.execute(
        """SELECT * FROM offers
           WHERE id = ? AND farmer_id = ?""",
        (offer_id, session["farmer_id"])
    ).fetchone()

    if not offer:
        conn.close()
        flash("Offer not found.")
        return redirect(url_for("offers"))

    if offer["status"] != "Pending":
        conn.close()
        flash("This offer has already been responded to.")
        return redirect(url_for("offers"))

    if action == "accept":
        conn.execute(
            """UPDATE offers
               SET buyer_agreed = 1,
                   status = 'Linkage Confirmed'
               WHERE id = ? AND farmer_id = ? AND status = 'Pending'""",
            (offer_id, session["farmer_id"])
        )
        flash("Demo buyer accepted! Linkage confirmed.")

    elif action == "counter":
        try:
            counter_price = float(
                request.form.get("counter_price", "0")
            )

            if counter_price <= 0:
                raise ValueError

            conn.execute(
                """UPDATE offers
                   SET counter_price = ?,
                       buyer_agreed = 1,
                       farmer_agreed = 0,
                       status = 'Counter Offer'
                   WHERE id = ? AND farmer_id = ?
                     AND status = 'Pending'""",
                (counter_price, offer_id, session["farmer_id"])
            )
            flash("Buyer counter-offer sent. Waiting for farmer decision.")

        except ValueError:
            flash("Enter a valid counter-offer price.")

    else:
        flash("Invalid buyer action.")

    conn.commit()
    conn.close()

    return redirect(url_for("offers"))


# FARMER ACCEPTS OR REJECTS A COUNTER-OFFER
@app.route("/offers/<int:offer_id>/respond", methods=["POST"])
def respond_offer(offer_id):
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    action = request.form.get("action", "")
    conn = get_db()

    offer = conn.execute(
        """SELECT * FROM offers
           WHERE id = ? AND farmer_id = ?""",
        (offer_id, session["farmer_id"])
    ).fetchone()

    if not offer:
        conn.close()
        flash("Offer not found.")
        return redirect(url_for("offers"))

    if action == "accept" and offer["status"] == "Counter Offer":
        if offer["counter_price"] is None:
            flash("Counter-offer price is missing.")
        else:
            conn.execute(
                """UPDATE offers
                   SET price_per_kg = counter_price,
                       farmer_agreed = 1,
                       buyer_agreed = 1,
                       status = 'Linkage Confirmed'
                   WHERE id = ? AND farmer_id = ?
                     AND status = 'Counter Offer'""",
                (offer_id, session["farmer_id"])
            )
            flash("You accepted the counter-offer. Linkage confirmed.")

    elif action == "reject" and offer["status"] in (
        "Pending", "Counter Offer"
    ):
        conn.execute(
            """UPDATE offers
               SET status = 'Rejected'
               WHERE id = ? AND farmer_id = ?""",
            (offer_id, session["farmer_id"])
        )
        flash("Offer rejected.")

    else:
        flash("This offer cannot be updated with that action.")

    conn.commit()
    conn.close()

    return redirect(url_for("offers"))


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
