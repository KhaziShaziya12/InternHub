-- ============================================================
-- InternHub: READ-ONLY inspection of the existing INTERNHUB schema
-- Run as INTERNHUB in SQL*Plus / "Run SQL Command Line" / SQL Developer.
-- Nothing here changes data.
-- ============================================================

-- Tables you already have
SELECT table_name FROM user_tables ORDER BY table_name;

-- Columns of every table
SELECT table_name, column_id, column_name, data_type, data_length, nullable
FROM   user_tab_columns
ORDER  BY table_name, column_id;

-- Constraints (primary keys, foreign keys, unique, check)
SELECT table_name, constraint_name, constraint_type, search_condition
FROM   user_constraints
ORDER  BY table_name, constraint_type;

-- Sequences and triggers
SELECT sequence_name, last_number FROM user_sequences ORDER BY sequence_name;
SELECT trigger_name, table_name, status FROM user_triggers ORDER BY table_name;

-- Row counts for the four tables InternHub uses (errors if a table is missing)
SELECT 'COMPANIES'    AS tbl, COUNT(*) AS rows_found FROM companies
UNION ALL SELECT 'STUDENTS',     COUNT(*) FROM students
UNION ALL SELECT 'INTERNSHIPS',  COUNT(*) FROM internships
UNION ALL SELECT 'APPLICATIONS', COUNT(*) FROM applications;
