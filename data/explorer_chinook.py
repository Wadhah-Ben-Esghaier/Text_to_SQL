import sqlite3
from contextlib import closing
from pathlib import Path


def main() -> None:
    database_path = Path(__file__).resolve().with_name('Chinook_Sqlite.sqlite')
    database_uri = database_path.as_uri() + '?mode=ro'

    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        print('Tables de Chinook')
        tables = connection.execute("SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name")
        for (name,) in tables:
            print(f'- {name}')

        print('\nSchéma de la table Customer')
        (schema,) = connection.execute(
            "SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = 'Customer'"
        ).fetchone()
        print(schema)


if __name__ == '__main__':
    main()
