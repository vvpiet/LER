import streamlit as st
import pandas as pd
import database
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
    if st.button("Login", key="login_button"):
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

# Admin page
def admin_page():
    st.title("Admin Dashboard")
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Upload Students", "Manage Subjects", "Assign Faculty", "Download Attendance", "Download Engagement", "Create Users", "Manage Students"])
    
    with tab1:
        st.header("Upload Student List")
        uploaded_file = st.file_uploader("Upload CSV (roll_no, name, class_name)", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            if st.button("Upload", key="upload_students"):
                conn = get_db_connection()
                cur = conn.cursor()
                for _, row in df.iterrows():
                    # Get class_id
                    cur.execute("SELECT id FROM classes WHERE name = %s", (row['class_name'],))
                    class_id = cur.fetchone()[0]
                    cur.execute("INSERT INTO students (roll_no, name, class_id) VALUES (%s, %s, %s) ON CONFLICT (roll_no) DO NOTHING",
                                (row['roll_no'], row['name'], class_id))
                    # Create user
                    cur.execute("INSERT INTO users (username, password_hash, role, name, email) VALUES (%s, %s, 'student', %s, '') ON CONFLICT (username) DO NOTHING",
                                (row['roll_no'], hash_password('student123'), row['name']))
                conn.commit()
                cur.close()
                conn.close()
                st.success("Students uploaded")
    
    with tab2:
        st.header("Add Subjects to Classes")
        class_name = st.selectbox("Class", ["SY", "TY", "B.Tech"], key="admin_add_subject_class")
        subject_name = st.text_input("Subject Name")
        if st.button("Add Subject", key="add_subject"):
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
        if not faculty_names:
            st.warning("No faculty available to assign subjects")
        else:
            faculty_dict = {f['name']: f['id'] for f in faculty}
            selected_faculty = st.selectbox("Faculty", faculty_names, key="admin_assign_faculty")
            faculty_id = faculty_dict[selected_faculty]
            
            # List subjects
            cur.execute("SELECT s.id, s.name, c.name as class_name FROM subjects s JOIN classes c ON s.class_id = c.id")
            subjects = cur.fetchall()
            subject_options = [f"{s['name']} ({s['class_name']})" for s in subjects]
            if not subject_options:
                st.warning("No subjects available")
            else:
                subject_dict = {f"{s['name']} ({s['class_name']})": s['id'] for s in subjects}
                selected_subject = st.selectbox("Subject", subject_options, key="admin_assign_subject")
                subject_id = subject_dict[selected_subject]
                
                if st.button("Assign", key="assign_subject"):
                    cur.execute("INSERT INTO faculty_subjects (faculty_id, subject_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (faculty_id, subject_id))
                    conn.commit()
                    st.success("Assigned")
        cur.close()
        conn.close()
    
    with tab4:
        st.header("Download Monthly Attendance")
        month = st.selectbox("Month", list(range(1,13)), key="admin_attendance_month")
        year = st.number_input("Year", value=2023)
        if st.button("Download", key="download_attendance"):
            # Query attendance
            conn = get_db_connection()
            df = pd.read_sql(f"SELECT s.roll_no, s.name, c.name as class, sub.name as subject, a.date, a.time, a.present FROM attendance a JOIN students s ON a.student_id = s.id JOIN subjects sub ON a.subject_id = sub.id JOIN classes c ON s.class_id = c.id WHERE EXTRACT(MONTH FROM a.date) = {month} AND EXTRACT(YEAR FROM a.date) = {year}", conn)
            conn.close()
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", csv, "attendance.csv", key="download_att_csv")
    
    with tab5:
        st.header("Download Lecture Engagement")
        period = st.selectbox("Period", ["Weekly", "Monthly"])
        if period == "Weekly":
            week_start = st.date_input("Week Start")
            # Calculate week end
            week_end = week_start + pd.Timedelta(days=6)
        else:
            month = st.selectbox("Month", list(range(1,13)), key="admin_engagement_month")
            year = st.number_input("Year", value=2023)
        if st.button("Download", key="download_engagement"):
            conn = get_db_connection()
            if period == "Weekly":
                df = pd.read_sql("SELECT le.date, u.name as faculty, s.name as subject, le.topic_covered, le.lecture_number, le.syllabus_percent, le.total_present, le.total_absent, array_to_string(le.absent_roll_numbers, ', ') as absent_roll_numbers FROM lecture_engagement le JOIN users u ON le.faculty_id = u.id JOIN subjects s ON le.subject_id = s.id WHERE le.date BETWEEN %s AND %s", conn, params=(week_start, week_end))
            else:
                df = pd.read_sql(f"SELECT le.date, u.name as faculty, s.name as subject, le.topic_covered, le.lecture_number, le.syllabus_percent, le.total_present, le.total_absent, array_to_string(le.absent_roll_numbers, ', ') as absent_roll_numbers FROM lecture_engagement le JOIN users u ON le.faculty_id = u.id JOIN subjects s ON le.subject_id = s.id WHERE EXTRACT(MONTH FROM le.date) = {month} AND EXTRACT(YEAR FROM le.date) = {year}", conn)
            conn.close()
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", csv, "engagement.csv", key="download_eng_csv")
    
    with tab6:
        st.header("Create Users")
        role = st.selectbox("Role", ["faculty", "student"], key="admin_create_user_role")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        name = st.text_input("Name")
        email = st.text_input("Email")
        if role == "student":
            class_name = st.selectbox("Class", ["SY", "TY", "B.Tech"], key="admin_create_user_class")
        if st.button("Create", key="create_user"):
            if role == "student":
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT id FROM classes WHERE name = %s", (class_name,))
                class_id = cur.fetchone()[0]
                cur.execute("INSERT INTO students (roll_no, name, class_id) VALUES (%s, %s, %s) ON CONFLICT (roll_no) DO NOTHING",
                            (username, name, class_id))
                conn.commit()
                cur.close()
                conn.close()
            create_user(username, password, role, name, email)
            st.success("User created")
    
    with tab7:
        st.header("Manage Students")
        students = get_all_students()
        if not students:
            st.warning("No students found")
        else:
            st.subheader("Student List")
            for student in students:
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
                with col1:
                    st.write(student['roll_no'])
                with col2:
                    st.write(student['name'])
                with col3:
                    st.write(student['class_name'])
                with col4:
                    if st.button("Edit", key=f"edit_student_{student['id']}"):
                        st.session_state.edit_student_id = student['id']
                with col5:
                    if st.button("Delete", key=f"delete_student_{student['id']}"):
                        st.session_state.delete_student_id = student['id']
            
            if 'edit_student_id' in st.session_state:
                st.divider()
                st.subheader("Edit Student")
                student = next((s for s in students if s['id'] == st.session_state.edit_student_id), None)
                if student:
                    new_roll_no = st.text_input("Roll No", value=student['roll_no'], key="edit_roll_no")
                    new_name = st.text_input("Name", value=student['name'], key="edit_name")
                    new_class = st.selectbox("Class", ["SY", "TY", "B.Tech"], index=["SY", "TY", "B.Tech"].index(student['class_name']), key="edit_class")
                    if st.button("Save Changes", key="save_student_changes"):
                        update_student(st.session_state.edit_student_id, new_roll_no, new_name, new_class)
                        del st.session_state.edit_student_id
                        st.success("Student updated")
                        st.rerun()
            
            if 'delete_student_id' in st.session_state:
                st.divider()
                st.warning("Are you sure you want to delete this student? All related attendance records will be deleted.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Confirm Delete", key="confirm_delete_student"):
                        delete_student(st.session_state.delete_student_id)
                        del st.session_state.delete_student_id
                        st.success("Student deleted")
                        st.rerun()
                with col2:
                    if st.button("Cancel", key="cancel_delete_student"):
                        del st.session_state.delete_student_id
                        st.rerun()

# Faculty page
def faculty_page():
    st.title("Faculty Dashboard")
    user = st.session_state.user
    tab1, tab2, tab3, tab4 = st.tabs(["Mark Attendance", "Lecture Engagement", "Upload Resources", "View Resources"])
    
    with tab1:
        st.header("Mark Attendance")
        # Get assigned subjects
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT s.id, s.name, c.name as class_name FROM subjects s JOIN faculty_subjects fs ON s.id = fs.subject_id JOIN classes c ON s.class_id = c.id WHERE fs.faculty_id = %s", (user['id'],))
        subjects = cur.fetchall()
        subject_options = [f"{s['name']} ({s['class_name']})" for s in subjects]
        if not subject_options:
            st.warning("No subjects assigned to you")
        else:
            subject_dict = {f"{s['name']} ({s['class_name']})": s['id'] for s in subjects}
            selected_subject = st.selectbox("Subject", subject_options, key="faculty_att_subject")
            subject_id = subject_dict[selected_subject]
            
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
            
            if st.button("Submit Attendance", key="submit_attendance"):
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
        if not subject_options:
            st.warning("No subjects assigned to you")
        else:
            subject_dict = {f"{s['name']} ({s['class_name']})": s['id'] for s in subjects}
            selected_subject = st.selectbox("Subject", subject_options, key="eng_subject")
            subject_id = subject_dict[selected_subject]
            
            date = st.date_input("Date", key="eng_date")
            topic = st.text_area("Topic Covered")
            lecture_num = st.number_input("Lecture Number", min_value=1)
            syllabus_pct = st.number_input("% Syllabus Covered", min_value=0.0, max_value=100.0)
            
            # Get attendance records for that date, subject, faculty
            cur.execute("SELECT st.roll_no, a.present FROM attendance a JOIN students st ON a.student_id = st.id WHERE a.subject_id = %s AND a.faculty_id = %s AND a.date = %s ORDER BY st.roll_no", (subject_id, user['id'], date))
            att_records = cur.fetchall()
            total_students = len(att_records)
            present = sum(1 for a in att_records if a['present'])
            absent = total_students - present
            absent_roll_numbers = [a['roll_no'] for a in att_records if not a['present']]
            
            st.write(f"Total Students: {total_students}, Present: {present}, Absent: {absent}")
            st.info(f"Absent Students: {', '.join(absent_roll_numbers) if absent_roll_numbers else 'None'}")
            
            if st.button("Submit Engagement", key="submit_engagement"):
                cur.execute("INSERT INTO lecture_engagement (faculty_id, subject_id, date, topic_covered, lecture_number, syllabus_percent, total_present, total_absent, absent_roll_numbers) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (user['id'], subject_id, date, topic, lecture_num, syllabus_pct, present, absent, absent_roll_numbers))
                conn.commit()
                st.success("Submitted")
        cur.close()
        conn.close()
    
    with tab3:
        st.header("Upload Resources (Assignments & Notes)")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT s.id, s.name, c.name as class_name FROM subjects s JOIN faculty_subjects fs ON s.id = fs.subject_id JOIN classes c ON s.class_id = c.id WHERE fs.faculty_id = %s", (user['id'],))
        subjects = cur.fetchall()
        cur.close()
        conn.close()
        
        subject_options = [f"{s['name']} ({s['class_name']})" for s in subjects]
        if not subject_options:
            st.warning("No subjects assigned to you")
        else:
            subject_dict = {f"{s['name']} ({s['class_name']})": s['id'] for s in subjects}
            selected_subject = st.selectbox("Subject", subject_options, key="upload_subject")
            subject_id = subject_dict[selected_subject]
            
            resource_type = st.selectbox("Resource Type", ["Assignment", "Notes", "Other"], key="resource_type")
            uploaded_file = st.file_uploader("Choose file", key="resource_file")
            
            if uploaded_file and st.button("Upload", key="upload_resource"):
                file_data = uploaded_file.read()
                database.upload_resource(user['id'], subject_id, uploaded_file.name, file_data, resource_type)
                st.success(f"{resource_type} uploaded successfully")
                st.rerun()
    
    with tab4:
        st.header("Your Resources")
        try:
            resources = database.get_faculty_resources(user['id'])
        except Exception as e:
            st.error(f"Error loading resources: {str(e)}")
            resources = []
        
        if not resources:
            st.info("No resources uploaded yet")
        else:
            for resource in resources:
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
                with col1:
                    st.write(resource['file_name'])
                with col2:
                    st.write(resource['resource_type'])
                with col3:
                    st.write(resource.get('subject_name', 'N/A'))
                with col4:
                    st.write(resource['uploaded_date'])
                with col5:
                    if st.button("Delete", key=f"delete_resource_{resource['id']}"):
                        database.delete_resource(resource['id'])
                        st.success("Resource deleted")
                        st.rerun()

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