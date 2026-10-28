-- ============================================================
-- InternHub sample data (OPTIONAL, safe to re-run)
-- Each row is inserted only if it is not already there, so nothing
-- existing is changed or duplicated. Requires 02_schema.sql first.
-- ============================================================
SET SERVEROUTPUT ON

DECLARE
  PROCEDURE add_company(p_name VARCHAR2, p_industry VARCHAR2, p_loc VARCHAR2, p_web VARCHAR2) IS
    n NUMBER; v NUMBER;
  BEGIN
    SELECT COUNT(*) INTO n FROM companies WHERE company_name = p_name;
    IF n = 0 THEN
      SELECT companies_seq.NEXTVAL INTO v FROM dual;
      INSERT INTO companies (company_id, company_name, industry, location, website)
      VALUES (v, p_name, p_industry, p_loc, p_web);
    END IF;
  END;

  PROCEDURE add_internship(p_company VARCHAR2, p_role VARCHAR2, p_cat VARCHAR2, p_desc VARCHAR2,
                           p_loc VARCHAR2, p_mode VARCHAR2, p_weeks NUMBER, p_stipend VARCHAR2,
                           p_elig VARCHAR2, p_open NUMBER, p_days_left NUMBER) IS
    n NUMBER; v NUMBER; cid NUMBER;
  BEGIN
    SELECT company_id INTO cid FROM companies WHERE company_name = p_company;
    SELECT COUNT(*) INTO n FROM internships WHERE company_id = cid AND role_title = p_role;
    IF n = 0 THEN
      SELECT internships_seq.NEXTVAL INTO v FROM dual;
      INSERT INTO internships (internship_id, company_id, role_title, category, description,
                               location, work_mode, duration_weeks, stipend, eligibility,
                               openings, deadline)
      VALUES (v, cid, p_role, p_cat, p_desc, p_loc, p_mode, p_weeks, p_stipend, p_elig,
              p_open, TRUNC(SYSDATE) + p_days_left);
    END IF;
  END;

  PROCEDURE add_student(p_name VARCHAR2, p_email VARCHAR2, p_phone VARCHAR2,
                        p_dept VARCHAR2, p_skills VARCHAR2) IS
    n NUMBER; v NUMBER;
  BEGIN
    SELECT COUNT(*) INTO n FROM students WHERE email = p_email;
    IF n = 0 THEN
      SELECT students_seq.NEXTVAL INTO v FROM dual;
      INSERT INTO students (student_id, full_name, email, phone, department, skills)
      VALUES (v, p_name, p_email, p_phone, p_dept, p_skills);
    END IF;
  END;

  PROCEDURE add_application(p_email VARCHAR2, p_company VARCHAR2, p_role VARCHAR2, p_status VARCHAR2) IS
    n NUMBER; v NUMBER; sid NUMBER; iid NUMBER;
  BEGIN
    SELECT student_id INTO sid FROM students WHERE email = p_email;
    SELECT i.internship_id INTO iid FROM internships i JOIN companies c ON c.company_id = i.company_id
     WHERE c.company_name = p_company AND i.role_title = p_role;
    SELECT COUNT(*) INTO n FROM applications WHERE student_id = sid AND internship_id = iid;
    IF n = 0 THEN
      SELECT applications_seq.NEXTVAL INTO v FROM dual;
      INSERT INTO applications (application_id, student_id, internship_id, status)
      VALUES (v, sid, iid, p_status);
    END IF;
  END;
BEGIN
  add_company('Infosys Labs',     'Information Technology', 'Bengaluru',  'https://example.com/infosys-labs');
  add_company('Tata Analytics',   'Data & Analytics',       'Hyderabad',  'https://example.com/tata-analytics');
  add_company('PixelCraft Studio','Design',                 'Chennai',    'https://example.com/pixelcraft');
  add_company('GreenGrid Energy', 'Engineering',            'Pune',       'https://example.com/greengrid');
  add_company('FinEdge Capital',  'Finance',                'Mumbai',     'https://example.com/finedge');
  add_company('BrightReach Media','Marketing',              'Remote',     'https://example.com/brightreach');

  add_internship('Infosys Labs', 'Python Backend Intern', 'Software',
    'Build and test REST APIs with Flask, write SQL queries and work with a mentor on a real product team.',
    'Bengaluru', 'Hybrid', 12, 'Rs 20,000 / month',
    'B.E/B.Tech CSE, IT or related; 2nd year or above; basic Python and SQL.', 3, 30);
  add_internship('Infosys Labs', 'Frontend Developer Intern', 'Software',
    'Create responsive user interfaces with HTML, CSS, JavaScript and Bootstrap.',
    'Bengaluru', 'Remote', 8, 'Rs 15,000 / month',
    'Any department; comfortable with HTML, CSS and JavaScript.', 4, 21);
  add_internship('Tata Analytics', 'Data Analyst Intern', 'Data Science',
    'Clean datasets, build dashboards and present insights to business teams.',
    'Hyderabad', 'Onsite', 12, 'Rs 18,000 / month',
    'CSE, IT, Statistics or Maths; SQL and Excel required; Python is a plus.', 2, 40);
  add_internship('PixelCraft Studio', 'UI/UX Design Intern', 'Design',
    'Design wireframes and prototypes, run small usability tests and refine designs.',
    'Chennai', 'Hybrid', 10, 'Rs 12,000 / month',
    'Any department; portfolio or sample designs preferred.', 2, 25);
  add_internship('GreenGrid Energy', 'Electrical Engineering Intern', 'Engineering',
    'Assist engineers with solar-plant monitoring, load calculations and site reports.',
    'Pune', 'Onsite', 16, 'Rs 14,000 / month',
    'EEE / ECE final or pre-final year; basic circuit knowledge.', 2, 35);
  add_internship('FinEdge Capital', 'Financial Research Intern', 'Finance',
    'Research companies, prepare Excel models and summarise market trends for the advisory team.',
    'Mumbai', 'Onsite', 8, 'Rs 16,000 / month',
    'Commerce, MBA, Economics or Maths; strong Excel skills.', 2, 28);
  add_internship('BrightReach Media', 'Social Media Marketing Intern', 'Marketing',
    'Plan content calendars, write posts and track engagement metrics across platforms.',
    'Remote', 'Remote', 6, 'Rs 8,000 / month',
    'Any department; good written English and creativity.', 5, 18);

  add_student('Ananya Reddy',  'ananya.reddy@example.com',  '9876543210', 'Computer Science', 'Python, SQL, Flask');
  add_student('Rahul Kumar',   'rahul.kumar@example.com',   '9123456780', 'Information Technology', 'JavaScript, React, HTML, CSS');
  add_student('Meera Nair',    'meera.nair@example.com',    '9012345678', 'Electronics', 'Circuit design, MATLAB');

  add_application('ananya.reddy@example.com', 'Infosys Labs',   'Python Backend Intern',  'PENDING');
  add_application('ananya.reddy@example.com', 'Tata Analytics', 'Data Analyst Intern',    'ACCEPTED');
  add_application('rahul.kumar@example.com',  'Infosys Labs',   'Frontend Developer Intern', 'PENDING');
  add_application('meera.nair@example.com',   'GreenGrid Energy','Electrical Engineering Intern', 'REJECTED');

  COMMIT;
  DBMS_OUTPUT.PUT_LINE('Sample data step finished (existing rows were left untouched).');
END;
/
