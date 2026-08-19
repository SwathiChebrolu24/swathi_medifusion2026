from sqlalchemy import inspect, text

from app.core.database import engine


MISSING_COLUMNS = {
    "users": {
        "specialty": "VARCHAR",
        "otp_created_at": "TIMESTAMP",
    },
    "patient_cases": {
        "severity_score": "FLOAT",
        "doctor_notes": "VARCHAR",
        "diagnosis": "VARCHAR",
        "reviewed_by_doctor": "BOOLEAN DEFAULT FALSE",
        "user_id": "INTEGER",
    },
}


def migrate_schema() -> None:
    inspector = inspect(engine)

    with engine.begin() as connection:
        for table_name, columns in MISSING_COLUMNS.items():
            if not inspector.has_table(table_name):
                continue

            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            for column_name, column_definition in columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ADD COLUMN {column_name} {column_definition}"
                        )
                    )
                    existing_columns.add(column_name)
