from sqlalchemy import create_engine, inspect, text

from app.services.donation_reasons import upgrade_donation_reason_schema


def test_upgrade_legacy_donation_reason_table_preserves_reasons():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE donation_reasons (
                code VARCHAR(30) PRIMARY KEY,
                label VARCHAR(120) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_system BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            text(
                """
                INSERT INTO donation_reasons (code, label, is_active, is_system)
                VALUES (:code, :label, :is_active, :is_system)
                """
            ),
            [
                {
                    "code": "custom_community",
                    "label": "Community Support",
                    "is_active": True,
                    "is_system": False,
                },
                {
                    "code": "monthly_donation",
                    "label": "Monthly Donation",
                    "is_active": True,
                    "is_system": True,
                },
            ],
        )

    upgrade_donation_reason_schema(engine)

    assert "id" in {column["name"] for column in inspect(engine).get_columns("donation_reasons")}
    with engine.connect() as connection:
        reasons = connection.execute(
            text(
                """
                SELECT id, code, label, is_active, is_system
                FROM donation_reasons
                ORDER BY id
                """
            )
        ).all()
    assert [(row.code, row.label, row.is_active, row.is_system) for row in reasons] == [
        ("custom_community", "Community Support", 1, 0),
        ("monthly_donation", "Monthly Donation", 1, 1),
    ]
    engine.dispose()
