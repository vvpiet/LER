import os
import psycopg2
from psycopg2.extras import RealDictCursor
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
            total_absent INTEGER
        );
    ''')
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