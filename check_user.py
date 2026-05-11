#!/usr/bin/env python3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

print("Checking for AMBIGAR SHIVANI BAPU user...")
cur.execute("""
    SELECT id, username, name, role FROM users 
    WHERE LOWER(name) LIKE '%ambigar%' OR LOWER(name) LIKE '%shivani%'
""")
users = cur.fetchall()
print(f"Found {len(users)} user(s)")
for u in users:
    print(f"  ID: {u['id']}, Username: {u['username']}, Name: {u['name']}, Role: {u['role']}")

cur.close()
conn.close()
