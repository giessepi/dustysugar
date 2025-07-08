import sqlite3

with open("export.sql", "w", encoding="utf-8") as f:
    for line in sqlite3.connect("db.sqlite3").iterdump():
        f.write(f"{line}\n")

print("✅ export.sql created from db.sqlite3")
