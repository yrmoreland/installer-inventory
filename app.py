from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

DATABASE = "inventory.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            minimum_quantity INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            installer_name TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            quantity_assigned INTEGER NOT NULL,
            date_assigned TEXT DEFAULT CURRENT_DATE,
            FOREIGN KEY (item_id) REFERENCES items (id)
        )
    """)

  conn.execute("""
    CREATE TABLE IF NOT EXISTS tool_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        installer_name TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        checked INTEGER DEFAULT 0,
        notes TEXT,
        check_date TEXT DEFAULT CURRENT_DATE
    )
""")

try:
    conn.execute("ALTER TABLE tool_checklist ADD COLUMN notes TEXT")
except sqlite3.OperationalError:
    pass
    
    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM items").fetchall()
    assignments = conn.execute("""
        SELECT assignments.id, assignments.installer_name, items.name, 
               assignments.quantity_assigned, assignments.date_assigned
        FROM assignments
        JOIN items ON assignments.item_id = items.id
        ORDER BY assignments.date_assigned DESC
    """).fetchall()
    conn.close()

    return render_template("index.html", items=items, assignments=assignments)


@app.route("/add", methods=["GET", "POST"])
def add_item():
    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        quantity = int(request.form["quantity"])
        minimum_quantity = int(request.form["minimum_quantity"])

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO items (name, category, quantity, minimum_quantity)
            VALUES (?, ?, ?, ?)
        """, (name, category, quantity, minimum_quantity))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add_item.html")


@app.route("/use/<int:item_id>", methods=["POST"])
def use_item(item_id):
    amount_used = int(request.form["amount_used"])

    conn = get_db_connection()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()

    if item and item["quantity"] >= amount_used:
        new_quantity = item["quantity"] - amount_used
        conn.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
        conn.commit()

    conn.close()
    return redirect("/")


@app.route("/restock/<int:item_id>", methods=["POST"])
def restock_item(item_id):
    amount_added = int(request.form["amount_added"])

    conn = get_db_connection()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()

    if item:
        new_quantity = item["quantity"] + amount_added
        conn.execute("UPDATE items SET quantity = ? WHERE id = ?", (new_quantity, item_id))
        conn.commit()

    conn.close()
    return redirect("/")


@app.route("/assign", methods=["GET", "POST"])
def assign_item():
    conn = get_db_connection()

    if request.method == "POST":
        installer_name = request.form["installer_name"]
        item_id = int(request.form["item_id"])
        quantity_assigned = int(request.form["quantity_assigned"])

        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()

        if item and item["quantity"] >= quantity_assigned:
            new_quantity = item["quantity"] - quantity_assigned

            conn.execute("""
                INSERT INTO assignments (installer_name, item_id, quantity_assigned)
                VALUES (?, ?, ?)
            """, (installer_name, item_id, quantity_assigned))

            conn.execute("""
                UPDATE items SET quantity = ? WHERE id = ?
            """, (new_quantity, item_id))

            conn.commit()

        conn.close()
        return redirect("/")

    items = conn.execute("SELECT * FROM items").fetchall()
    conn.close()

    return render_template("assign_item.html", items=items)


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/checklist", methods=["GET", "POST"])
def checklist():
    tools = [
        "Drill",
        "Impact Driver",
        "Batteries (4)",
        "Personal Batteries",
        "Hammer Drill",
        "Oscilating Tool",
        "Hand Saw",
        "Shop Saw",
        "Grinder",
        "Steamer",
        "Vaccum Cleaner",
        "Nail Gun"
    ]

   if request.method == "POST":
        installer_name = request.form["installer_name"]

        conn = get_db_connection()

        for tool in tools:
            field_name = tool.replace(" ", "_").lower()
            checked = 1 if f"{field_name}_present" in request.form else 0
            notes = request.form.get(f"{field_name}_notes", "")

            conn.execute("""
                INSERT INTO tool_checklist
                (installer_name, tool_name, checked, notes)
                VALUES (?, ?, ?, ?)
            """, (installer_name, tool, checked, notes))

        conn.commit()
        conn.close()

        return redirect("/checklist")

    conn = get_db_connection()
    checklist_history = conn.execute("""
        SELECT *
        FROM tool_checklist
        ORDER BY check_date DESC, installer_name, tool_name
    """).fetchall()
    conn.close()

    return render_template(
        "checklist.html",
        tools=tools,
        checklist_history=checklist_history
    )



create_tables()

if __name__ == "__main__":
    app.run(debug=True)
    
