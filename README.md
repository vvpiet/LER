# Lecture Engagement Register

A Streamlit application for managing lecture engagement with PostgreSQL database.

## Setup

1. Create a NeonDB database and get the connection string.

2. Set environment variable `DATABASE_URL` to your NeonDB connection string.

   You can create a `.env` file in the root directory with:

   ```
   DATABASE_URL=postgresql://user:pass@host/db
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Run the app:

   ```
   streamlit run app.py
   ```

   Or use the VS Code task "Run Streamlit App"

## Features

- **Admin**: 
  - Upload student list via CSV
  - Add subjects to classes
  - Assign subjects to faculty
  - Download monthly attendance reports
  - Download weekly/monthly lecture engagement reports
  - Create faculty and student users

- **Faculty**:
  - View assigned subjects
  - Mark attendance for students in their subjects
  - Fill lecture engagement register with attendance counts

- **Student**:
  - View their attendance records

## Default Credentials

- Admin: username `admin`, password `admin123`
- Students: username is roll_no, password `student123` (created when uploading students)
- Faculty: Created by admin

## Database Schema

- users: User accounts with roles
- classes: SY, TY, B.Tech
- subjects: Subjects linked to classes
- faculty_subjects: Assignments
- students: Student details
- attendance: Attendance records
- lecture_engagement: Lecture details with attendance counts