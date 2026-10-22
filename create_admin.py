from getpass import getpass
from werkzeug.security import generate_password_hash

from database import create_tables, get_connection


def main():
    create_tables()

    name = input("Enter admin name: ").strip()
    email = input("Enter admin email: ").strip().lower()
    password = getpass("Enter admin password: ")

    if not name or not email or len(password) < 8:
        print("Enter valid details and a password of at least 8 characters.")
        return

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO employees (name, email, password, role)
            VALUES (?, ?, ?, 'admin')
            """,
            (
                name,
                email,
                generate_password_hash(password)
            )
        )

        connection.commit()

        print("Admin account created successfully!")

    except Exception as error:
        print("Could not create admin account:", error)

    finally:
        connection.close()


if __name__ == "__main__":
    main()