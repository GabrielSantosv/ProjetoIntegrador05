"""Small connection test for the PostgreSQL database."""
from database import get_connection


def main() -> None:
    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT version();")
        version = cursor.fetchone()

        print("Conectado ao PostgreSQL!")
        print(version[0] if version else "Versão não retornada")

        cursor.close()
        connection.close()
    except Exception as exc:
        print("Erro ao conectar no PostgreSQL:")
        print(exc)


if __name__ == "__main__":
    main()