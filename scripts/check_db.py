import mysql.connector

conns_tried = [
    {"user": "root", "password": "", "database": "db_apotek_sehat"},
    {"user": "app_apotek", "password": "PasswordApotek123!", "database": "db_apotek_sehat"},
]
for c in conns_tried:
    try:
        conn = mysql.connector.connect(host="localhost", **c)
        cur = conn.cursor(dictionary=True)
        cur.execute("SHOW TABLES")
        tables = [list(t.values())[0] for t in cur.fetchall()]
        print("Connected as:", c["user"])
        print("Tables:", tables)
        if "pengguna" in tables:
            cur.execute("DESCRIBE pengguna")
            cols = cur.fetchall()
            print("Columns:", [col["Field"] for col in cols])
            cur.execute("SELECT * FROM pengguna LIMIT 3")
            print("Rows:", cur.fetchall())
        conn.close()
        break
    except Exception as e:
        print("Failed:", e)
