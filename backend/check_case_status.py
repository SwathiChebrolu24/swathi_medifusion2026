import sqlite3

conn = sqlite3.connect('medifusion.db')
cursor = conn.cursor()

print("=== Cases assigned to doctor (ID=2, username='shiva') ===\n")
cursor.execute("""
    SELECT id, status, reviewed_by_doctor, test_ordered, test_status, 
           assigned_doctor_id, doctor_notes, diagnosis
    FROM patient_cases 
    WHERE assigned_doctor_id = 2
    ORDER BY id DESC
    LIMIT 10
""")

rows = cursor.fetchall()
for row in rows:
    print(f"Case ID: {row[0]}")
    print(f"  Status: {row[1]}")
    print(f"  Reviewed: {row[2]}")
    print(f"  Test Ordered: {row[3]}")
    print(f"  Test Status: {row[4]}")
    print(f"  Doctor Notes: {row[6][:50] if row[6] else 'None'}...")
    print(f"  Diagnosis: {row[7]}")
    print()

conn.close()
