
import sqlite3

DB_NAME = "uzhavu.db"


def add_column_if_missing(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )


def create_database():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # 1. Farmers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            village TEXT,
            district TEXT
        )
    """)

    # 2. Farmer crop details
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            crop_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            quality TEXT,
            location TEXT,
            expected_price REAL,
            unit TEXT DEFAULT 'kg',
            FOREIGN KEY (farmer_id) REFERENCES farmers(id)
        )
    """)

    # 3. Markets
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS markets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_name TEXT NOT NULL UNIQUE,
            district TEXT NOT NULL
        )
    """)

    # 4. Sample market prices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_name TEXT NOT NULL,
            market_id INTEGER NOT NULL,
            price_per_kg REAL NOT NULL,
            FOREIGN KEY (market_id) REFERENCES markets(id),
            UNIQUE(crop_name, market_id)
        )
    """)

    # 5. Buyers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buyers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_name TEXT NOT NULL,
            crop_name TEXT NOT NULL,
            required_quantity REAL NOT NULL,
            quality TEXT,
            district TEXT,
            offered_price REAL NOT NULL,
            payment_terms TEXT,
            delivery_terms TEXT,
            UNIQUE(buyer_name, crop_name)
        )
    """)

    # 6. Farmer-buyer offers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            crop_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            price_per_kg REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            farmer_agreed INTEGER DEFAULT 0,
            buyer_agreed INTEGER DEFAULT 0,
            FOREIGN KEY (farmer_id) REFERENCES farmers(id),
            FOREIGN KEY (buyer_id) REFERENCES buyers(id)
        )
    """)

    # Safely add new columns to existing databases
    add_column_if_missing(cursor, "offers", "counter_price", "REAL")
    add_column_if_missing(
        cursor, "offers", "delivery_status", "TEXT DEFAULT 'Pending'"
    )
    add_column_if_missing(
        cursor, "offers", "payment_status", "TEXT DEFAULT 'Pending'"
    )

    # 7. Sample markets
    markets = [
        ("Coimbatore Central Market", "Coimbatore"),
        ("Pollachi Market", "Coimbatore"),
        ("Erode Agricultural Market", "Erode"),
        ("Tiruppur Market", "Tiruppur"),
        ("Salem Agricultural Market", "Salem"),
        ("Madurai Market", "Madurai"),
        ("Dindigul Market", "Dindigul"),
        ("Trichy Market", "Tiruchirappalli"),
    ]

    for market_name, district in markets:
        cursor.execute("""
            INSERT OR IGNORE INTO markets (market_name, district)
            VALUES (?, ?)
        """, (market_name, district))

    # 8. Sample prices - demo values in rupees per kg
    price_data = {
        "Rice": [
            ("Coimbatore Central Market", 35),
            ("Pollachi Market", 36),
            ("Erode Agricultural Market", 38),
            ("Tiruppur Market", 34),
            ("Salem Agricultural Market", 37),
            ("Madurai Market", 36),
            ("Dindigul Market", 35),
            ("Trichy Market", 39),
        ],
        "Tomato": [
            ("Coimbatore Central Market", 25),
            ("Pollachi Market", 27),
            ("Erode Agricultural Market", 28),
            ("Tiruppur Market", 24),
            ("Salem Agricultural Market", 23),
            ("Madurai Market", 26),
            ("Dindigul Market", 24),
            ("Trichy Market", 29),
        ],
        "Onion": [
            ("Coimbatore Central Market", 30),
            ("Pollachi Market", 31),
            ("Erode Agricultural Market", 32),
            ("Tiruppur Market", 28),
            ("Salem Agricultural Market", 29),
            ("Madurai Market", 33),
            ("Dindigul Market", 30),
            ("Trichy Market", 31),
        ],
        "Groundnut": [
            ("Coimbatore Central Market", 54),
            ("Pollachi Market", 55),
            ("Erode Agricultural Market", 56),
            ("Tiruppur Market", 52),
            ("Salem Agricultural Market", 53),
            ("Madurai Market", 57),
            ("Dindigul Market", 54),
            ("Trichy Market", 55),
        ],
        "Banana": [
            ("Coimbatore Central Market", 22),
            ("Pollachi Market", 23),
            ("Erode Agricultural Market", 24),
            ("Tiruppur Market", 21),
            ("Salem Agricultural Market", 22),
            ("Madurai Market", 25),
            ("Dindigul Market", 24),
            ("Trichy Market", 23),
        ],
    }

    for crop_name, market_list in price_data.items():
        for market_name, price in market_list:
            cursor.execute(
                "SELECT id FROM markets WHERE market_name = ?",
                (market_name,)
            )
            market = cursor.fetchone()

            if market:
                cursor.execute("""
                    INSERT OR IGNORE INTO market_prices
                    (crop_name, market_id, price_per_kg)
                    VALUES (?, ?, ?)
                """, (crop_name, market[0], price))

    # 9. Ten buyers for each crop = 50 unique sample buyers
    districts = [
        "Coimbatore", "Erode", "Salem", "Tiruppur", "Madurai",
        "Dindigul", "Tiruchirappalli", "Coimbatore", "Erode", "Salem"
    ]

    payment_options = [
        "Immediate payment",
        "Within 2 days",
        "Within 3 days",
        "Within 5 days",
        "On delivery",
    ]

    delivery_options = [
        "Buyer pickup",
        "Farmer delivery",
        "Buyer pickup",
        "Farmer delivery",
        "Negotiable",
    ]

    crop_settings = {
        "Rice": {
            "base_price": 34,
            "qualities": ["Standard", "Premium"],
            "base_quantity": 300,
        },
        "Tomato": {
            "base_price": 24,
            "qualities": ["Fresh", "Premium"],
            "base_quantity": 200,
        },
        "Onion": {
            "base_price": 29,
            "qualities": ["Standard", "Premium"],
            "base_quantity": 250,
        },
        "Groundnut": {
            "base_price": 52,
            "qualities": ["Standard", "Premium"],
            "base_quantity": 400,
        },
        "Banana": {
            "base_price": 21,
            "qualities": ["Standard", "Fresh"],
            "base_quantity": 200,
        },
    }

    buyer_prefixes = [
        "Kongu Traders",
        "Green Valley Buyers",
        "Farm Direct Buyers",
        "Fresh Harvest Traders",
        "Golden Field Buyers",
        "Agri Connect Traders",
        "Regional Wholesale Buyers",
        "Quality Crop Buyers",
        "Village Market Traders",
        "Southern Farm Buyers",
    ]

    for crop_name, settings in crop_settings.items():
        for i in range(10):
            buyer_name = f"{buyer_prefixes[i]} - {crop_name}"
            district = districts[i]
            quality = settings["qualities"][i % 2]
            quantity = settings["base_quantity"] + (i * 100)
            price = settings["base_price"] + (i % 5) + (i // 5)

            cursor.execute("""
                INSERT OR IGNORE INTO buyers
                (buyer_name, crop_name, required_quantity, quality,
                 district, offered_price, payment_terms, delivery_terms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                buyer_name,
                crop_name,
                quantity,
                quality,
                district,
                price,
                payment_options[i % len(payment_options)],
                delivery_options[i % len(delivery_options)],
            ))

    conn.commit()

    # Print sample data counts for verification
    buyer_count = cursor.execute(
        "SELECT COUNT(*) FROM buyers"
    ).fetchone()[0]

    market_count = cursor.execute(
        "SELECT COUNT(*) FROM markets"
    ).fetchone()[0]

    price_count = cursor.execute(
        "SELECT COUNT(*) FROM market_prices"
    ).fetchone()[0]

    conn.close()

    print("Uzhavu Paathai database created successfully!")
    print(f"Markets: {market_count}")
    print(f"Sample market prices: {price_count}")
    print(f"Total sample buyers: {buyer_count}")


if __name__ == "__main__":
    create_database()
