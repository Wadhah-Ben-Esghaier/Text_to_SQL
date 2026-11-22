import argparse
import sqlite3
import sys
from contextlib import closing, contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from cli_display import format_ast, format_results
from parser import ParserError, parse_sql


DATABASE_PATH = ROOT / 'data' / 'Chinook_Sqlite.sqlite'


@contextmanager
def open_read_only(database_path: Path):
    uri = database_path.resolve().as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.execute('PRAGMA query_only = ON')
        yield connection


@contextmanager
def query_cursor(sql: str):
    parse_sql(sql)
    with open_read_only(DATABASE_PATH) as connection:
        with closing(connection.execute(sql)) as cursor:
            yield cursor


def run_query(sql: str):
    with query_cursor(sql) as cursor:
        return cursor.fetchall()


def main() -> int:
    cli = argparse.ArgumentParser(description='Parse SQL or run it on the Chinook database.')
    cli.add_argument('command', choices=('parse', 'run'))
    cli.add_argument('sql', help='a single SQL query')
    cli.add_argument('--pretty', action='store_true', help='format output for a live demonstration')
    args = cli.parse_args()

    try:
        if args.command == 'parse':
            query = parse_sql(args.sql)
            print(format_ast(query) if args.pretty else query)
        elif args.pretty:
            with query_cursor(args.sql) as cursor:
                headers = [column[0] for column in cursor.description]
                print(format_results(headers, cursor.fetchall()))
        else:
            for row in run_query(args.sql):
                print('\t'.join('NULL' if value is None else str(value) for value in row))
    except (ParserError, ValueError) as error:
        label = 'Refused' if args.command == 'run' else type(error).__name__
        if args.pretty:
            if args.command == 'run':
                label = 'Requête refusée avant exécution'
            else:
                label = 'Erreur de syntaxe' if isinstance(error, ParserError) else 'Erreur lexicale'
            print(label, file=sys.stderr)
            if isinstance(error, ParserError):
                source_line = args.sql.split('\n')[error.line - 1].rstrip('\r')
                prefix = source_line[:error.column - 1].expandtabs(4)
                print(source_line.expandtabs(4), file=sys.stderr)
                print(' ' * len(prefix) + '^', file=sys.stderr)
            print(error, file=sys.stderr)
        else:
            print(f'{label}: {error}', file=sys.stderr)
        return 1
    except sqlite3.Error as error:
        label = 'Erreur SQLite' if args.pretty else 'SQLite error'
        print(f'{label}: {error}', file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
