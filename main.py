import sqlite3
from datetime import datetime

def initialize_database():
    connection = sqlite3.connect("pokemon_tcg.db")
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            product_type TEXT NOT NULL,
            set_name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL', 'OPEN')),
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            unit_price REAL NOT NULL CHECK(unit_price >= 0),
            date TEXT NOT NULL,
            fees REAL DEFAULT 0.0,
            notes TEXT,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    connection.commit()
    connection.close()

def add_product():
    print("\n--- Add New Product to Catalog ---")
    name = input("Enter product name (e.g., 151 Booster Bundle): ").strip()
    product_type = input("Enter product type (e.g., Booster Bundle, ETB, Booster Box): ").strip()
    set_name = input("Enter set name (e.g., 151, Obsidian Flames): ").strip()

    if not name or not product_type or not set_name:
        print("Error: All fields are required.")
        return

    connection = sqlite3.connect("pokemon_tcg.db")
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("""
        INSERT INTO products (name, product_type, set_name)
        VALUES (?, ?, ?)
    """, (name, product_type, set_name))
    connection.commit()
    connection.close()
    print(f"Success: Added '{name}' to catalog!")

def get_products():
    connection = sqlite3.connect("pokemon_tcg.db")
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("SELECT product_id, name, product_type, set_name FROM products")
    rows = cursor.fetchall()
    connection.close()

    print("\n--- Product Catalog ---")
    if not rows:
        print("No products in the catalog yet.")
        return

    for row in rows:
        print(f"[{row[0]}] {row[3]} - {row[1]} ({row[2]})")

def add_transaction():
    print("\n--- Record Transaction ---")
    get_products()
    
    try:
        product_id = int(input("Enter Product ID: "))
        action = input("Enter action (BUY, SELL, OPEN): ").strip().upper()
        if action not in ('BUY', 'SELL', 'OPEN'):
            print("Invalid action. Must be BUY, SELL, or OPEN.")
            return

        quantity = int(input("Enter quantity: "))
        if quantity <= 0:
            print("Quantity must be greater than zero.")
            return

        unit_price = float(input("Enter unit price ($): "))
        if unit_price < 0:
            print("Price cannot be negative.")
            return

        date_input = input("Enter date YYYY-MM-DD (Press Enter for today): ").strip()
        date = date_input if date_input else datetime.today().strftime('%Y-%m-%d')

        fees = 0.0
        if action == 'SELL':
            fees_input = input("Enter platform/shipping fees ($) [Default 0.0]: ").strip()
            fees = float(fees_input) if fees_input else 0.0

        notes = input("Enter optional notes: ").strip()

        connection = sqlite3.connect("pokemon_tcg.db")
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("""
            INSERT INTO transactions (product_id, action, quantity, unit_price, date, fees, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_id, action, quantity, unit_price, date, fees, notes))
        connection.commit()
        connection.close()
        print(f"Success: Recorded {action} for {quantity} unit(s)!")

    except ValueError:
        print("Invalid input format. Please enter numbers for ID, quantity, and price.")
    except sqlite3.IntegrityError as e:
        print(f"Database error: Check if Product ID exists. Details: {e}")

def get_transactions():
    connection = sqlite3.connect("pokemon_tcg.db")
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("""
        SELECT 
            t.transaction_id, t.date, t.action, t.quantity, t.unit_price, 
            p.name, p.set_name, t.fees, t.notes
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        ORDER BY t.date DESC, t.transaction_id DESC
    """)
    rows = cursor.fetchall()
    connection.close()

    print("\n--- Transaction History ---")
    if not rows:
        print("No transactions recorded yet.")
        return

    for row in rows:
        trans_id, date, action, qty, price, name, set_name, fees, notes = row
        print(f"[{trans_id}] {date} | {action} {qty}x {set_name} - {name} @ ${price:.2f}/ea (Fees: ${fees:.2f})")
        if notes:
            print(f"    Note: {notes}")

def get_inventory():
    connection = sqlite3.connect("pokemon_tcg.db")
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.execute("""
        SELECT product_id, name, product_type, set_name, remaining_qty
        FROM (
            SELECT 
                p.product_id, 
                p.name, 
                p.product_type, 
                p.set_name,
                COALESCE(SUM(
                    CASE 
                        WHEN t.action = 'BUY' THEN t.quantity
                        WHEN t.action = 'SELL' THEN -t.quantity
                        WHEN t.action = 'OPEN' THEN -t.quantity
                        ELSE 0
                    END
                ), 0) AS remaining_qty
            FROM products p
            LEFT JOIN transactions t ON p.product_id = t.product_id
            GROUP BY p.product_id
        ) AS inventory_summary
        WHERE remaining_qty > 0
    """)
    
    rows = cursor.fetchall()
    connection.close()

    print("\n--- Current Active Sealed Inventory ---")
    if not rows:
        print("No products currently in stock.")
        return

    for row in rows:
        prod_id, name, prod_type, set_name, qty = row
        print(f"[{prod_id}] {set_name} - {name} ({prod_type}): {qty} units in stock")

def calculate_financials():
    connection = sqlite3.connect("pokemon_tcg.db")
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("""
        SELECT t.product_id, t.action, t.quantity, t.unit_price, t.fees, p.name
        FROM transactions t
        JOIN products p ON t.product_id = p.product_id
        ORDER BY t.product_id, t.date ASC, t.transaction_id ASC
    """)
    rows = cursor.fetchall()
    connection.close()

    if not rows:
        print("\nNo transactions found for financial reports.")
        return

    product_states = {}
    total_realized_profit = 0.0
    total_opening_cost = 0.0
    total_spent = 0.0
    total_received = 0.0

    for row in rows:
        p_id, action, qty, price, fees, name = row
        if p_id not in product_states:
            product_states[p_id] = {'qty': 0, 'total_cost': 0.0, 'name': name}

        state = product_states[p_id]

        if action == 'BUY':
            state['qty'] += qty
            state['total_cost'] += (qty * price)
            total_spent += (qty * price)
        elif action in ('SELL', 'OPEN'):
            current_avg_cost = (state['total_cost'] / state['qty']) if state['qty'] > 0 else 0.0
            
            if action == 'OPEN':
                opening_expense = qty * current_avg_cost
                total_opening_cost += opening_expense
            elif action == 'SELL':
                revenue = qty * price
                cogs = qty * current_avg_cost
                sale_profit = revenue - cogs - fees
                total_realized_profit += sale_profit
                total_received += (revenue - fees)

            state['qty'] -= qty
            state['total_cost'] -= (qty * current_avg_cost)
            if state['qty'] <= 0:
                state['qty'] = 0
                state['total_cost'] = 0.0

    net_cash_flow = total_received - total_spent

    print("\n================ FINANCIAL SUMMARY ================")
    print(f"Total Cash Spent (Purchases):  ${total_spent:.2f}")
    print(f"Total Cash Received (Sales):   ${total_received:.2f}")
    print(f"Net Cash Flow:                 ${net_cash_flow:.2f}")
    print("-" * 51)
    print(f"Total Opening Cost (History):  ${total_opening_cost:.2f}")
    print(f"Total Realized Profit (Sales): ${total_realized_profit:.2f}")
    print("===================================================")

def main_menu():
    initialize_database()
    while True:
        print("\n=== Pokémon TCG Sealed Tracker ===")
        print("1. View Product Catalog")
        print("2. Add New Product")
        print("3. View Current Inventory")
        print("4. Record Transaction (BUY, SELL, OPEN)")
        print("5. View Transaction History")
        print("6. View Financial Reports (Profit, Cash Flow, Openings)")
        print("7. Exit")
        
        choice = input("Enter your choice (1-7): ").strip()
        
        if choice == '1':
            get_products()
        elif choice == '2':
            add_product()
        elif choice == '3':
            get_inventory()
        elif choice == '4':
            add_transaction()
        elif choice == '5':
            get_transactions()
        elif choice == '6':
            calculate_financials()
        elif choice == '7':
            print("\nExiting tracker. Happy collecting!")
            break
        else:
            print("\nInvalid choice. Please enter a number between 1 and 7.")

if __name__ == "__main__":
    main_menu()