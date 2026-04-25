import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import Binary
from psycopg2 import Binary
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# Database connection
def get_db_connection():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn

# Create tables
def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            email VARCHAR(100)
        );
        CREATE TABLE IF NOT EXISTS classes (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS subjects (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            class_id INTEGER REFERENCES classes(id)
        );
        CREATE TABLE IF NOT EXISTS faculty_subjects (
            faculty_id INTEGER REFERENCES users(id),
            subject_id INTEGER REFERENCES subjects(id),
            PRIMARY KEY (faculty_id, subject_id)
        );
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            roll_no VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            class_id INTEGER REFERENCES classes(id)
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(id),
            subject_id INTEGER REFERENCES subjects(id),
            faculty_id INTEGER REFERENCES users(id),
            date DATE NOT NULL,
            time TIME NOT NULL,
            present BOOLEAN NOT NULL
        );
        CREATE TABLE IF NOT EXISTS lecture_engagement (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER REFERENCES users(id),
            subject_id INTEGER REFERENCES subjects(id),
            date DATE NOT NULL,
            topic_covered TEXT,
            lecture_number INTEGER,
            syllabus_percent DECIMAL(5,2),
            total_present INTEGER,
            total_absent INTEGER,
            absent_roll_numbers TEXT[]
        );
        CREATE TABLE IF NOT EXISTS faculty_resources (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER REFERENCES users(id),
            subject_id INTEGER REFERENCES subjects(id),
            file_name VARCHAR(255) NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            file_data BYTEA NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS resources (
            id SERIAL PRIMARY KEY,
            faculty_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            file_name VARCHAR(255) NOT NULL,
            file_data BYTEA NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()


def ensure_schema():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("ALTER TABLE lecture_engagement ADD COLUMN IF NOT EXISTS absent_roll_numbers TEXT[]")
    conn.commit()
    cur.close()
    conn.close()

# User functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_user(username, password, role, name, email):
    conn = get_db_connection()
    cur = conn.cursor()
    hashed = hash_password(password)
    cur.execute('INSERT INTO users (username, password_hash, role, name, email) VALUES (%s, %s, %s, %s, %s)',
                (username, hashed, role, name, email))
    conn.commit()
    cur.close()
    conn.close()

def authenticate_user(username, password):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user and check_password(password, user['password_hash']):
        return user
    return None

# Other functions will be added as needed

# Faculty resource functions
def upload_resource(faculty_id, subject_id, file_name, file_data, resource_type):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO resources (faculty_id, subject_id, file_name, file_data, resource_type) VALUES (%s, %s, %s, %s, %s)",
        (faculty_id, subject_id, file_name, file_data, resource_type)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_faculty_resources(faculty_id, subject_id=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if subject_id:
            cur.execute('SELECT id, file_name, resource_type, uploaded_date FROM faculty_resources WHERE faculty_id = %s AND subject_id = %s ORDER BY uploaded_date DESC',
                        (faculty_id, subject_id))
        else:
            cur.execute('SELECT id, file_name, resource_type, uploaded_date, s.name as subject_name FROM faculty_resources fr LEFT JOIN subjects s ON fr.subject_id = s.id WHERE fr.faculty_id = %s ORDER BY fr.uploaded_date DESC',
                        (faculty_id,))
        resources = cur.fetchall()
        cur.close()
        conn.close()
        return resources if resources else []
    except Exception as e:
        print(f"Error getting faculty resources: {e}")
        return []


def store_lecture_engagement(faculty_id, subject_id, date, topic_covered, lecture_number, syllabus_percent, total_present, total_absent, absent_roll_numbers):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO lecture_engagement (faculty_id, subject_id, date, topic_covered, lecture_number, syllabus_percent, total_present, total_absent, absent_roll_numbers) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (faculty_id, subject_id, date, topic_covered, lecture_number, syllabus_percent, total_present, total_absent, absent_roll_numbers))
    conn.commit()
    cur.close()
    conn.close()


def get_student_resources(roll_no):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT r.id, r.file_name, r.resource_type, s.name as subject_name, r.uploaded_date, r.file_data "
        "FROM resources r "
        "JOIN subjects s ON r.subject_id = s.id "
        "JOIN students st ON st.class_id = s.class_id "
        "WHERE st.roll_no = %s "
        "ORDER BY r.uploaded_date DESC",
        (roll_no,)
    )
    resources = cur.fetchall()
    cur.close()
    conn.close()
    return resources if resources else []


def delete_resource(resource_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM faculty_resources WHERE id = %s', (resource_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_resource_file(resource_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT file_name, file_data, file_type FROM faculty_resources WHERE id = %s', (resource_id,))
    resource = cur.fetchone()
    cur.close()
    conn.close()
    return resource

# Student management functions
def get_all_students():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT s.id, s.roll_no, s.name, c.name as class_name FROM students s JOIN classes c ON s.class_id = c.id ORDER BY s.roll_no')
    students = cur.fetchall()
    cur.close()
    conn.close()
    return students

def update_student(student_id, roll_no, name, class_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM classes WHERE name = %s', (class_name,))
    class_id = cur.fetchone()[0]
    cur.execute('UPDATE students SET roll_no = %s, name = %s, class_id = %s WHERE id = %s',
                (roll_no, name, class_id, student_id))
    conn.commit()
    cur.close()
    conn.close()

def delete_student(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # Delete attendance records first (cascade)
    cur.execute('DELETE FROM attendance WHERE student_id = %s', (student_id,))
    # Delete student
    cur.execute('DELETE FROM students WHERE id = %s', (student_id,))
    conn.commit()
    cur.close()
    conn.close()