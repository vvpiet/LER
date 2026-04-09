import streamlit as st
import pandas as pd
from database import *
import os

# Set page config
st.set_page_config(page_title="Lecture Engagement Register", layout="wide")

# Initialize database
if 'db_init' not in st.session_state:
    create_tables()
    # Insert initial classes
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO classes (name) VALUES ('SY'), ('TY'), ('B.Tech') ON CONFLICT (name) DO NOTHING")
    # Create default admin
    try:
        create_user('admin', 'admin123', 'admin', 'Administrator', 'admin@example.com')
    except:
        pass
    conn.commit()
    cur.close()
    conn.close()
    st.session_state.db_init = True

# Login function
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = authenticate_user(username, password)
        if user:
            st.session_state.user = user
            st.success("Logged in successfully")
            st.rerun()
        else:
            st.error("Invalid credentials")

# Logout
def logout():
    if 'user' in st.session_state:
        del st.session_state.user
    st.rerun()

# Main app
if 'user' not in st.session_state:
    login()
else:
    user = st.session_state.user
    st.sidebar.title(f"Welcome, {user['name']}")
    st.sidebar.button("Logout", on_click=logout)
    
    if user['role'] == 'admin':
        admin_page()
    elif user['role'] == 'faculty':
        faculty_page()
    elif user['role'] == 'student':
        student_page()

# Admin page
def admin_page():
    st.title("Admin Dashboard")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Upload Students", "Manage Subjects", "Assign Faculty", "Download Attendance", "Download Engagement"])
    
    with tab1:
        st.header("Upload Student List")
        uploaded_file = st.file_uploader("Upload CSV (roll_no, name, class_name)", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            if st.button("Upload"):
                conn = get_db_connection()
                cur = conn.cursor()
                for _, row in df.iterrows():
                    # Get class_id
                    cur.execute("SELECT id FROM classes WHERE name = %s", (row['class_name'],))
                    class_id = cur.fetchone()[0]
                    cur.execute("INSERT INTO students (roll_no, name, class_id) VALUES (%s, %s, %s) ON CONFLICT (roll_no) DO NOTHING",
                                (row['roll_no'], row['name'], class_id))
                conn.commit()
                cur.close()
                conn.close()
                st.success("Students uploaded")
    
    with tab2:
        st.header("Add Subjects to Classes")
        class_name = st.selectbox("Class", ["SY", "TY", "B.Tech"])
        subject_name = st.text_input("Subject Name")
        if st.button("Add Subject"):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM classes WHERE name = %s", (class_name,))
            class_id = cur.fetchone()[0]
            cur.execute("INSERT INTO subjects (name, class_id) VALUES (%s, %s)", (subject_name, class_id))
            conn.commit()
            cur.close()
            conn.close()
            st.success("Subject added")
    
    with tab3:
        st.header("Assign Subjects to Faculty")
        # List faculty
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name FROM users WHERE role = 'faculty'")
        faculty = cur.fetchall()
        faculty_names = [f['name'] for f in faculty]
        selected_faculty = st.selectbox("Faculty", faculty_names)
        faculty_id = next(f['id'] for f in faculty if f['name'] == selected_faculty)
        
        # List subjects
        cur.execute("SELECT s.id, s.name, c.name as class_name FROM subjects s JOIN classes c ON s.class_id = c.id")
        subjects = cur.fetchall()
        subject_options = [f"{s['name']} ({s['class_name']})" for s in subjects]
        selected_subject = st.selectbox("Subject", subject_options)
        subject_id = next(s['id'] for s in subjects if f"{s['name']} ({s['class_name']})" == selected_subject)
        
        if st.button("Assign"):
            cur.execute("INSERT INTO faculty_subjects (faculty_id, subject_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (faculty_id, subject_id))
            conn.commit()
            st.success("Assigned")
        cur.close()
        conn.close()
    
    with tab4:
        st.header("Download Monthly Attendance")
        month = st.selectbox("Month", list(range(1,13)))
        year = st.number_input("Year", value=2023)
        if st.button("Download"):
            # Query attendance
            conn = get_db_connection()
            df = pd.read_sql(f"SELECT s.roll_no, s.name, c.name as class, sub.name as subject, a.date, a.time, a.present FROM attendance a JOIN students s ON a.student_id = s.id JOIN subjects sub ON a.subject_id = sub.id JOIN classes c ON s.class_id = c.id WHERE EXTRACT(MONTH FROM a.date) = {month} AND EXTRACT(YEAR FROM a.date) = {year}", conn)
            conn.close()
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", csv, "attendance.csv")
    
    with tab5:
        st.header("Download Lecture Engagement")
        period = st.selectbox("Period", ["Weekly", "Monthly"])
        if period == "Weekly":
            week_start = st.date_input("Week Start")
            # Calculate week end
            week_end = week_start + pd.Timedelta(days=6)
        else:
            month = st.selectbox("Month", list(range(1,13)))
            year = st.number_input("Year", value=2023)
        if st.button("Download"):
            conn = get_db_connection()
            if period == "Weekly":
                df = pd.read_sql("SELECT le.date, u.name as faculty, s.name as subject, le.topic_covered, le.lecture_number, le.syllabus_percent, le.total_present, le.total_absent FROM lecture_engagement le JOIN users u ON le.faculty_id = u.id JOIN subjects s ON le.subject_id = s.id WHERE le.date BETWEEN %s AND %s", conn, params=(week_start, week_end))
            else:
                df = pd.read_sql(f"SELECT le.date, u.name as faculty, s.name as subject, le.topic_covered, le.lecture_number, le.syllabus_percent, le.total_present, le.total_absent FROM lecture_engagement le JOIN users u ON le.faculty_id = u.id JOIN subjects s ON le.subject_id = s.id WHERE EXTRACT(MONTH FROM le.date) = {month} AND EXTRACT(YEAR FROM le.date) = {year}", conn)
            conn.close()
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", csv, "engagement.csv")

# Faculty page
def faculty_page():
    st.title("Faculty Dashboard")
    user = st.session_state.user
    tab1, tab2 = st.tabs(["Mark Attendance", "Lecture Engagement"])
    
    with tab1:
        st.header("Mark Attendance")
        # Get assigned subjects
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT s.id, s.name, c.name as class_name FROM subjects s JOIN faculty_subjects fs ON s.id = fs.subject_id JOIN classes c ON s.class_id = c.id WHERE fs.faculty_id = %s", (user['id'],))
        subjects = cur.fetchall()
        subject_options = [f"{s['name']} ({s['class_name']})" for s in subjects]
        selected_subject = st.selectbox("Subject", subject_options)
        subject_id = next(s['id'] for s in subjects if f"{s['name']} ({s['class_name']})" == selected_subject)
        
        date = st.date_input("Date")
        time = st.time_input("Time")
        
        # Get students for the class
        cur.execute("SELECT st.id, st.roll_no, st.name FROM students st JOIN subjects sub ON st.class_id = sub.class_id WHERE sub.id = %s", (subject_id,))
        students = cur.fetchall()
        cur.close()
        conn.close()
        
        attendance = {}
        for student in students:
            attendance[student['id']] = st.checkbox(f"{student['roll_no']} - {student['name']}", key=f"att_{student['id']}")
        
        if st.button("Submit Attendance"):
            conn = get_db_connection()
            cur = conn.cursor()
            for student_id, present in attendance.items():
                cur.execute("INSERT INTO attendance (student_id, subject_id, faculty_id, date, time, present) VALUES (%s, %s, %s, %s, %s, %s)",
                            (student_id, subject_id, user['id'], date, time, present))
            conn.commit()
            cur.close()
            conn.close()
            st.success("Attendance marked")
    
    with tab2:
        st.header("Lecture Engagement Register")
        # Similar to above, select subject, date
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT s.id, s.name, c.name as class_name FROM subjects s JOIN faculty_subjects fs ON s.id = fs.subject_id JOIN classes c ON s.class_id = c.id WHERE fs.faculty_id = %s", (user['id'],))
        subjects = cur.fetchall()
        subject_options = [f"{s['name']} ({s['class_name']})" for s in subjects]
        selected_subject = st.selectbox("Subject", subject_options, key="eng_subject")
        subject_id = next(s['id'] for s in subjects if f"{s['name']} ({s['class_name']})" == selected_subject)
        
        date = st.date_input("Date", key="eng_date")
        topic = st.text_area("Topic Covered")
        lecture_num = st.number_input("Lecture Number", min_value=1)
        syllabus_pct = st.number_input("% Syllabus Covered", min_value=0.0, max_value=100.0)
        
        # Get attendance counts for that date, subject, faculty
        cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN present THEN 1 ELSE 0 END) as present FROM attendance WHERE subject_id = %s AND faculty_id = %s AND date = %s", (subject_id, user['id'], date))
        att = cur.fetchone()
        total_students = att['total']
        present = att['present'] or 0
        absent = total_students - present
        
        st.write(f"Total Students: {total_students}, Present: {present}, Absent: {absent}")
        
        if st.button("Submit Engagement"):
            cur.execute("INSERT INTO lecture_engagement (faculty_id, subject_id, date, topic_covered, lecture_number, syllabus_percent, total_present, total_absent) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (user['id'], subject_id, date, topic, lecture_num, syllabus_pct, present, absent))
            conn.commit()
            st.success("Submitted")
        cur.close()
        conn.close()

# Student page
def student_page():
    st.title("Student Dashboard")
    user = st.session_state.user
    # Assume student is linked, but for simplicity, show attendance for all
    # In reality, need to link user to student
    # For now, placeholder
    st.header("Your Attendance")
    # Query attendance for the student
    # But since no link, perhaps by username or something
    # Let's assume username is roll_no
    conn = get_db_connection()
    df = pd.read_sql("SELECT sub.name as subject, a.date, a.time, a.present FROM attendance a JOIN subjects sub ON a.subject_id = sub.id WHERE a.student_id = (SELECT id FROM students WHERE roll_no = %s)", conn, params=(user['username'],))
    conn.close()
    st.dataframe(df)