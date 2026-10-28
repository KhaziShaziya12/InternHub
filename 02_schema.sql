-- ============================================================
-- InternHub schema for Oracle Database 10g XE
-- SAFE TO RE-RUN: every table and sequence is created ONLY if it
-- does not already exist. Nothing is dropped, altered or deleted.
-- Uses only 10g-compatible syntax (sequences, no IDENTITY columns).
--
-- Run as the INTERNHUB user:
--   SQL> SET SERVEROUTPUT ON
--   SQL> @sql\02_schema.sql
-- or:  python setup_db.py
-- ============================================================
SET SERVEROUTPUT ON

DECLARE
  PROCEDURE make_seq(p_name VARCHAR2) IS
    n NUMBER;
  BEGIN
    SELECT COUNT(*) INTO n FROM user_sequences WHERE sequence_name = p_name;
    IF n = 0 THEN
      EXECUTE IMMEDIATE 'CREATE SEQUENCE ' || p_name || ' START WITH 1 INCREMENT BY 1 NOCACHE';
      DBMS_OUTPUT.PUT_LINE('Created sequence ' || p_name);
    ELSE
      DBMS_OUTPUT.PUT_LINE('Sequence exists, skipped: ' || p_name);
    END IF;
  END;

  PROCEDURE make_table(p_name VARCHAR2, p_ddl VARCHAR2) IS
    n NUMBER;
  BEGIN
    SELECT COUNT(*) INTO n FROM user_tables WHERE table_name = p_name;
    IF n = 0 THEN
      EXECUTE IMMEDIATE p_ddl;
      DBMS_OUTPUT.PUT_LINE('Created table ' || p_name);
    ELSE
      DBMS_OUTPUT.PUT_LINE('Table exists, skipped: ' || p_name);
    END IF;
  END;
BEGIN
  make_seq('COMPANIES_SEQ');
  make_seq('STUDENTS_SEQ');
  make_seq('INTERNSHIPS_SEQ');
  make_seq('APPLICATIONS_SEQ');

  make_table('COMPANIES', q'[
    CREATE TABLE companies (
      company_id    NUMBER         NOT NULL,
      company_name  VARCHAR2(100)  NOT NULL,
      industry      VARCHAR2(60),
      location      VARCHAR2(100),
      website       VARCHAR2(200),
      created_at    DATE           DEFAULT SYSDATE,
      CONSTRAINT companies_pk PRIMARY KEY (company_id),
      CONSTRAINT companies_name_uq UNIQUE (company_name)
    )]');

  make_table('STUDENTS', q'[
    CREATE TABLE students (
      student_id   NUMBER         NOT NULL,
      full_name    VARCHAR2(100)  NOT NULL,
      email        VARCHAR2(120)  NOT NULL,
      phone        VARCHAR2(20)   NOT NULL,
      department   VARCHAR2(80)   NOT NULL,
      skills       VARCHAR2(500),
      created_at   DATE           DEFAULT SYSDATE,
      CONSTRAINT students_pk PRIMARY KEY (student_id),
      CONSTRAINT students_email_uq UNIQUE (email)
    )]');

  make_table('INTERNSHIPS', q'[
    CREATE TABLE internships (
      internship_id   NUMBER         NOT NULL,
      company_id      NUMBER         NOT NULL,
      role_title      VARCHAR2(100)  NOT NULL,
      category        VARCHAR2(40)   NOT NULL,
      description     VARCHAR2(2000),
      location        VARCHAR2(100),
      work_mode       VARCHAR2(10)   DEFAULT 'Onsite',
      duration_weeks  NUMBER(3),
      stipend         VARCHAR2(40),
      eligibility     VARCHAR2(500),
      openings        NUMBER(4)      DEFAULT 1,
      deadline        DATE,
      created_at      DATE           DEFAULT SYSDATE,
      CONSTRAINT internships_pk PRIMARY KEY (internship_id),
      CONSTRAINT internships_company_fk FOREIGN KEY (company_id)
        REFERENCES companies (company_id),
      CONSTRAINT internships_mode_ck CHECK (work_mode IN ('Onsite','Remote','Hybrid'))
    )]');

  make_table('APPLICATIONS', q'[
    CREATE TABLE applications (
      application_id  NUMBER        NOT NULL,
      student_id      NUMBER        NOT NULL,
      internship_id   NUMBER        NOT NULL,
      status          VARCHAR2(10)  DEFAULT 'PENDING' NOT NULL,
      applied_on      DATE          DEFAULT SYSDATE,
      updated_on      DATE,
      CONSTRAINT applications_pk PRIMARY KEY (application_id),
      CONSTRAINT applications_student_fk FOREIGN KEY (student_id)
        REFERENCES students (student_id) ON DELETE CASCADE,
      CONSTRAINT applications_internship_fk FOREIGN KEY (internship_id)
        REFERENCES internships (internship_id) ON DELETE CASCADE,
      CONSTRAINT applications_status_ck CHECK (status IN ('PENDING','ACCEPTED','REJECTED')),
      CONSTRAINT applications_once_uq UNIQUE (student_id, internship_id)
    )]');
END;
/
