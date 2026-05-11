#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 80)
print("DEBUGGING: Check all students in database")
print("=" * 80)

# Check raw students table
cur.execute("SELECT s.id, s.roll_no, s.name, s.prn, c.name as class_name FROM students s JOIN classes c ON s.class_id = c.id WHERE c.name = 'SY' ORDER BY s.roll_no")
students = cur.fetchall()
print(f"\nTotal SY students in DB: {len(students)}")
for s in students:
    print(f"  ID: {s['id']}, Roll: {s['roll_no']}, Name: {s['name']}, Class: {s['class_name']}, PRN: {s['prn']}")

# Check users table for student users
print("\n" + "=" * 80)
print("DEBUGGING: Check all student users in database")
print("=" * 80)
cur.execute("SELECT id, username, name, role FROM users WHERE role = 'student' ORDER BY username")
users = cur.fetchall()
print(f"\nTotal student users in DB: {len(users)}")
for u in users:
    print(f"  ID: {u['id']}, Username: {u['username']}, Name: {u['name']}, Role: {u['role']}")

# Check the join query
print("\n" + "=" * 80)
print("DEBUGGING: Check get_all_students() query result")
print("=" * 80)
cur.execute('''
    SELECT s.id, s.roll_no, s.prn, s.name, c.name as class_name, 
           COALESCE(u1.username, u2.username) as username
    FROM students s 
    JOIN classes c ON s.class_id = c.id 
    LEFT JOIN users u1 ON u1.username = s.roll_no AND u1.role = 'student'
    LEFT JOIN users u2 ON LOWER(TRIM(u2.name)) = LOWER(TRIM(s.name)) AND u2.role = 'student' AND u1.id IS NULL
    WHERE c.name = 'SY'
    ORDER BY c.name, s.roll_no
''')
result = cur.fetchall()
print(f"\nSY students from get_all_students() query: {len(result)}")
for r in result:
    print(f"  Roll: {r['roll_no']}, Name: {r['name']}, Username: {r['username']}, Class: {r['class_name']}")

# Check specific student
print("\n" + "=" * 80)
print("DEBUGGING: Check AMBIGAR SHIVANI BAPU")
print("=" * 80)
cur.execute("SELECT s.id, s.roll_no, s.name, s.prn, c.name as class_name FROM students s JOIN classes c ON s.class_id = c.id WHERE LOWER(TRIM(s.name)) LIKE '%ambigar%' OR LOWER(TRIM(s.name)) LIKE '%shivani%'")
specific = cur.fetchall()
print(f"\nResults for AMBIGAR SHIVANI BAPU: {len(specific)}")
for s in specific:
    print(f"  ID: {s['id']}, Roll: {s['roll_no']}, Name: {s['name']}, Class: {s['class_name']}, PRN: {s['prn']}")

cur.close()
conn.close()
