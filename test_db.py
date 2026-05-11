#!/usr/bin/env python3
"""Direct database diagnostic to identify the issue."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("="*80)
    print("1. CHECK CLASSES TABLE")
    print("="*80)
    cur.execute("SELECT id, name FROM classes ORDER BY id")
    classes = cur.fetchall()
    print(f"Classes in DB: {len(classes)}")
    for c in classes:
        print(f"  ID: {c['id']}, Name: {c['name']}")
    
    print("\n" + "="*80)
    print("2. CHECK SY STUDENTS IN DATABASE")
    print("="*80)
    cur.execute("""
        SELECT s.id, s.roll_no, s.name, s.prn, c.id as class_id, c.name as class_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE c.name = 'SY'
        ORDER BY s.roll_no
    """)
    sy_students = cur.fetchall()
    print(f"SY Students in DB: {len(sy_students)}")
    for s in sy_students:
        print(f"  ID: {s['id']}, Roll: {s['roll_no']}, Name: {s['name']}, Class_ID: {s['class_id']}, Class: {s['class_name']}")
    
    print("\n" + "="*80)
    print("3. CHECK STUDENT USERS IN DATABASE")
    print("="*80)
    cur.execute("SELECT id, username, name, role FROM users WHERE role = 'student' ORDER BY username")
    users = cur.fetchall()
    print(f"Student users in DB: {len(users)}")
    for u in users[:20]:  # Show first 20
        print(f"  ID: {u['id']}, Username: {u['username']}, Name: {u['name']}")
    if len(users) > 20:
        print(f"  ... and {len(users) - 20} more")
    
    print("\n" + "="*80)
    print("4. TEST THE get_all_students() QUERY")
    print("="*80)
    cur.execute('''
        SELECT s.id, s.roll_no, s.prn, s.name, c.id as class_id, c.name as class_name, 
               COALESCE(u_rollno.username, u_name.username) as username
        FROM students s 
        INNER JOIN classes c ON s.class_id = c.id 
        LEFT JOIN users u_rollno ON u_rollno.username = s.roll_no AND u_rollno.role = 'student'
        LEFT JOIN users u_name ON LOWER(TRIM(u_name.name)) = LOWER(TRIM(s.name)) AND u_name.role = 'student' AND u_rollno.id IS NULL
        ORDER BY c.name ASC, s.roll_no ASC
    ''')
    all_students = cur.fetchall()
    print(f"get_all_students() returns: {len(all_students)}")
    sy_from_query = [st for st in all_students if st['class_name'] == 'SY']
    print(f"SY students from query: {len(sy_from_query)}")
    for s in sy_from_query[:10]:  # Show first 10 SY students
        print(f"  Roll: {s['roll_no']}, Name: {s['name']}, Username: {s['username']}, Class: {s['class_name']}")
    if len(sy_from_query) > 10:
        print(f"  ... and {len(sy_from_query) - 10} more")
    
    print("\n" + "="*80)
    print("5. SEARCH FOR AMBIGAR SHIVANI BAPU")
    print("="*80)
    cur.execute("""
        SELECT s.id, s.roll_no, s.name, s.prn, c.id as class_id, c.name as class_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE LOWER(s.name) LIKE '%ambigar%' OR LOWER(s.name) LIKE '%shivani%'
    """)
    ambigar = cur.fetchall()
    print(f"AMBIGAR SHIVANI BAPU records: {len(ambigar)}")
    for s in ambigar:
        print(f"  ID: {s['id']}, Roll: {s['roll_no']}, Name: {s['name']}, Class_ID: {s['class_id']}, Class: {s['class_name']}")
        
        # Check if this student has a user
        cur.execute("""
            SELECT id, username, name FROM users 
            WHERE (username = %s OR LOWER(TRIM(name)) = LOWER(TRIM(%s))) AND role = 'student'
        """, (s['roll_no'], s['name']))
        user_match = cur.fetchone()
        if user_match:
            print(f"    → Has user: {user_match['username']} ({user_match['name']})")
        else:
            print(f"    → No user found")
    
    cur.close()
    conn.close()
    print("\n✅ Diagnostics complete")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
