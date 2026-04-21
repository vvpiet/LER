# Technical Implementation Details

## Files Modified

### 1. database.py
**Changes Made:**
- Modified `create_tables()` function:
  - Added `absent_roll_numbers TEXT[]` column to `lecture_engagement` table
  - Added new `faculty_resources` table with BYTEA column for binary file storage

- Added new functions:
  - `upload_resource(faculty_id, subject_id, file_name, file_data, resource_type)`
  - `get_faculty_resources(faculty_id, subject_id=None)`
  - `delete_resource(resource_id)`
  - `get_resource_file(resource_id)`
  - `get_all_students()`
  - `update_student(student_id, roll_no, name, class_name)`
  - `delete_student(student_id)` - with cascade delete of attendance records

### 2. app.py
**Changes Made:**

#### Admin Dashboard:
- Updated tab count: 6 tabs → 7 tabs
- Added Tab 7: "Manage Students"
  - Display student list with Roll No, Name, Class
  - Edit functionality with form for updating student details
  - Delete functionality with confirmation dialog
  - Cascade delete of attendance records

- Enhanced Tab 5: "Download Engagement"
  - Modified SQL queries to include `array_to_string(le.absent_roll_numbers, ', ')` 
  - Exports absent_roll_numbers as CSV column

#### Faculty Dashboard:
- Updated tab count: 2 tabs → 4 tabs
- Enhanced Tab 2: "Lecture Engagement"
  - Changed from counting absent to retrieving actual attendance records
  - Join with attendance and students tables to get roll numbers
  - Display absent student list before submission
  - Store absent_roll_numbers array in database

- Added Tab 3: "Upload Resources"
  - Subject selection
  - Resource type dropdown (Assignment/Notes/Other)
  - File uploader
  - Stores file as binary in database

- Added Tab 4: "View Resources"
  - Display all faculty resources
  - Show file details: name, type, subject, upload date
  - Delete button for each resource

---

## Database Schema Changes

### New Column in Existing Table
**lecture_engagement table:**
```sql
absent_roll_numbers TEXT[]  -- Array of student roll numbers who were absent
```

### New Table
**faculty_resources table:**
```sql
CREATE TABLE faculty_resources (
    id SERIAL PRIMARY KEY,
    faculty_id INTEGER REFERENCES users(id),
    subject_id INTEGER REFERENCES subjects(id),
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_data BYTEA NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## SQL Queries Updated/Added

### Lecture Engagement Query (Modified)
**Before:**
```sql
SELECT COUNT(*) as total, SUM(CASE WHEN present THEN 1 ELSE 0 END) as present 
FROM attendance 
WHERE subject_id = %s AND faculty_id = %s AND date = %s
```

**After:**
```sql
SELECT st.roll_no, a.present 
FROM attendance a 
JOIN students st ON a.student_id = st.id 
WHERE a.subject_id = %s AND a.faculty_id = %s AND a.date = %s 
ORDER BY st.roll_no
```

### Download Engagement Query (Enhanced)
**Before:**
```sql
SELECT le.date, u.name as faculty, s.name as subject, le.topic_covered, 
       le.lecture_number, le.syllabus_percent, le.total_present, le.total_absent 
FROM lecture_engagement le ...
```

**After:**
```sql
SELECT le.date, u.name as faculty, s.name as subject, le.topic_covered, 
       le.lecture_number, le.syllabus_percent, le.total_present, le.total_absent, 
       array_to_string(le.absent_roll_numbers, ', ') as absent_roll_numbers 
FROM lecture_engagement le ...
```

### Student Management Queries (New)
```sql
-- Get all students
SELECT s.id, s.roll_no, s.name, c.name as class_name 
FROM students s 
JOIN classes c ON s.class_id = c.id 
ORDER BY s.roll_no

-- Update student
UPDATE students 
SET roll_no = %s, name = %s, class_id = %s 
WHERE id = %s

-- Delete student (cascade)
DELETE FROM attendance WHERE student_id = %s
DELETE FROM students WHERE id = %s
```

### Faculty Resources Queries (New)
```sql
-- Upload resource
INSERT INTO faculty_resources 
(faculty_id, subject_id, file_name, file_data, resource_type, file_type) 
VALUES (%s, %s, %s, %s, %s, %s)

-- Get resources
SELECT id, file_name, resource_type, uploaded_date, s.name as subject_name 
FROM faculty_resources fr 
JOIN subjects s ON fr.subject_id = s.id 
WHERE faculty_id = %s 
ORDER BY uploaded_date DESC

-- Delete resource
DELETE FROM faculty_resources WHERE id = %s

-- Get file data
SELECT file_name, file_data, file_type 
FROM faculty_resources 
WHERE id = %s
```

---

## Streamlit Session State Management

### New Session State Keys Used:
- `edit_student_id` - Track which student is being edited
- `delete_student_id` - Track which student deletion is pending

### Existing Session State:
- `db_init` - Database initialization flag
- `user` - Current logged-in user

---

## Data Flow Diagrams

### Lecture Engagement Flow:
```
Faculty selects date & subject
         ↓
System queries attendance table
         ↓
Retrieves all students + attendance status
         ↓
Calculates absent students
         ↓
Displays absent roll numbers
         ↓
Faculty submits with topic & lecture details
         ↓
Stores absent_roll_numbers array in lecture_engagement table
```

### Faculty Resource Upload Flow:
```
Faculty selects subject & resource type
         ↓
File uploaded via Streamlit uploader
         ↓
File converted to binary data
         ↓
Stored in faculty_resources table (BYTEA column)
         ↓
Metadata saved: filename, type, upload_date
         ↓
Appears in "View Resources" tab
```

### Student Management Flow:
```
Admin views student list
         ↓
Can edit: Roll No, Name, Class
         ↓
Changes committed to students table
         ↓
Or delete student:
  - Confirmation dialog
  - Cascade delete attendance records
  - Remove from students table
```

---

## Error Handling

### Implemented Safeguards:
1. **Student Deletion:** Confirmation dialog prevents accidental deletion
2. **File Upload:** Error handling for file reading
3. **Database Operations:** Try-except blocks for constraint violations
4. **Cascade Delete:** Attendance records removed before student deletion

---

## Performance Considerations

### Database Queries:
- Indexed on: `subject_id`, `faculty_id`, `date` for fast attendance queries
- Array operations in PostgreSQL (native support)
- Timestamp indexing for date-range queries

### File Storage:
- BYTEA storage in PostgreSQL handles binary efficiently
- No external file system overhead
- Metadata tracking enables quick searches

---

## Security Notes

1. **Binary File Storage:** Files stored directly in database (no path traversal risks)
2. **SQL Injection:** All queries use parameterized statements
3. **Authentication:** Faculty/Admin roles verify resource ownership
4. **Cascade Delete:** Only admin can trigger (no accidental data loss from users)

---

## Backward Compatibility

- ✅ Existing attendance data preserved
- ✅ Existing student records preserved
- ✅ Existing lecture_engagement records work (absent_roll_numbers defaults to NULL)
- ✅ Faculty_resources table separate (no conflicts)
- ✅ All new features are additive

---

## Dependencies

### Required Python Packages:
- streamlit (existing)
- pandas (existing)
- psycopg2-binary (existing)
- bcrypt (existing)
- python-dotenv (existing)

### Database:
- PostgreSQL 10+ (NeonDB supported)
- BYTEA support for file storage
- Array type support for roll numbers

---

## Testing Recommendations

### Unit Tests Needed:
- File upload/download functions
- Student CRUD operations
- Cascade delete verification
- Absent student calculation

### Integration Tests:
- Complete workflow: attendance → engagement → download
- Multi-file upload/delete
- Student edit persistence
- CSV export with absent roll numbers

### Manual Testing:
- Upload various file types
- Verify database storage
- Test cascade delete
- Check CSV export formatting

---

## Future Enhancements

Potential additions:
- Download/view faculty resources (currently upload/delete only)
- Batch student import with update capability
- Engagement report analytics
- Student export to CSV
- Resource sharing between faculty
- File size limits/validation

---

## Deployment Checklist

- [ ] `.env` file configured with DATABASE_URL
- [ ] PostgreSQL/NeonDB credentials valid
- [ ] Database migrations applied (tables created)
- [ ] Python packages installed from requirements.txt
- [ ] Streamlit app tested locally
- [ ] All three features verified working
- [ ] CSV export tested
- [ ] Admin/Faculty workflows tested
