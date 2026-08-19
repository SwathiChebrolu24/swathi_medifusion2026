import logging

from sqlalchemy import inspect, text

from app.core.database import engine

logger = logging.getLogger(__name__)


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

    for table_name, columns in MISSING_COLUMNS.items():
        if not inspector.has_table(table_name):
            continue

        existing_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        for column_name, column_definition in columns.items():
            if column_name in existing_columns:
                continue

            try:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ADD COLUMN {column_name} {column_definition}"
                        )
                    )
                existing_columns.add(column_name)
                logger.info("Added missing database column %s.%s", table_name, column_name)
            except Exception:
                logger.exception(
                    "Could not add required database column %s.%s",
                    table_name,
                    column_name,
                )
                raise
