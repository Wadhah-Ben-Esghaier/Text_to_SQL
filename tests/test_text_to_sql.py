import shutil
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent / 'src'))

from Lexer import tokenize
from parser import ParserError, parse_sql
from sql_ast import ColumnRef, Comparison, SelectItem, SelectQuery, TableRef
from t2s import DATABASE_PATH, open_read_only, run_query


FRANCE_QUERY = "SELECT FirstName FROM Customer WHERE Country = 'France' LIMIT 3"
DELETE_QUERY = 'DELETE FROM Customer'


class LexerTests(unittest.TestCase):
    def test_strings_and_escaped_apostrophe(self):
        cases = [("'France'", 'France'), ("'l''été'", "l'été"), ("''", '')]
        for sql, expected_value in cases:
            with self.subTest(sql=sql):
                self.assertEqual(tokenize(sql)[0], ('STRING', expected_value, 1, 1))

    def test_numbers(self):
        for number in ['42', '10.5', '-10.5', '-42']:
            with self.subTest(number=number):
                self.assertEqual(tokenize(number)[0], ('NUMBER', number, 1, 1))

    def test_operators_and_positions(self):
        self.assertEqual(
            tokenize('<= <> >='),
            [('OPERATOR', '<=', 1, 1), ('OPERATOR', '<>', 1, 4),
             ('OPERATOR', '>=', 1, 7), ('EOF', '', 1, 9)],
        )

    def test_keyword_and_identifier_with_digit_on_next_line(self):
        self.assertEqual(
            tokenize('select\n  T1'),
            [('KEYWORD', 'select', 1, 1), ('IDENTIFIER', 'T1', 2, 3),
             ('EOF', '', 2, 5)],
        )

    def test_reports_lexical_errors_with_position(self):
        for sql, message in [("'unfinished", 'Unterminated string'), ('@', 'Unexpected character')]:
            with self.subTest(sql=sql):
                with self.assertRaisesRegex(ValueError, message + r'.*line 1, column 1'):
                    tokenize(sql)


class ParserTests(unittest.TestCase):
    def test_accepts_16_valid_queries(self):
        queries = [
            'SELECT CustomerId FROM Customer',
            'SELECT c.CustomerId, c.FirstName FROM Customer AS c',
            'SELECT c.CustomerId FROM Customer c',
            'SELECT COUNT(*) FROM Invoice',
            'SELECT COUNT(InvoiceId) AS total FROM Invoice',
            'SELECT SUM(Total) AS revenue FROM Invoice',
            'SELECT CustomerId FROM Customer WHERE CustomerId = 42',
            'SELECT Total FROM Invoice WHERE Total >= -10.5',
            "SELECT FirstName FROM Customer WHERE FirstName = 'O''Brien'",
            'SELECT CustomerId FROM Customer WHERE Company IS NULL',
            "SELECT CustomerId FROM Customer WHERE Company IS NOT NULL AND Country <> 'France'",
            'SELECT c.CustomerId, i.InvoiceId FROM Customer c INNER JOIN Invoice i '
            'ON c.CustomerId = i.CustomerId',
            'SELECT Country, City, COUNT(*) AS total FROM Customer GROUP BY Country, City',
            'SELECT CustomerId FROM Customer GROUP BY CustomerId HAVING COUNT(*) > 2',
            'SELECT FirstName FROM Customer ORDER BY FirstName DESC, CustomerId ASC LIMIT 10;',
            'SELECT e.EmployeeId FROM Employee e INNER JOIN Employee boss '
            'ON e.ReportsTo = boss.EmployeeId',
        ]
        for sql in queries:
            with self.subTest(sql=sql):
                self.assertIsInstance(parse_sql(sql), SelectQuery)

    def test_rejects_5_invalid_queries_at_the_offending_token(self):
        cases = [
            ('SELECT FROM Customer', 'FROM', 8, 'identifier'),
            ('SELECT CustomerId, FROM Customer', 'FROM', 20, 'identifier'),
            ('SELECT c.CustomerId FROM Customer c INNER JOIN Invoice i '
             'WHERE c.CustomerId = i.CustomerId', 'WHERE', 58, 'keyword ON'),
            ('SELECT CustomerId FROM Customer WHERE CustomerId =', '', 51, 'number or a string'),
            ('SELECT CustomerId FROM Customer LIMIT 2.5', '2.5', 39, 'non-negative integer'),
        ]
        for sql, token_value, column, message in cases:
            with self.subTest(sql=sql):
                with self.assertRaisesRegex(ParserError, message) as caught:
                    parse_sql(sql)
                error = caught.exception
                self.assertEqual((error.line, error.column), (1, column))
                self.assertEqual(error.token[1], token_value)

    def test_builds_the_expected_ast(self):
        self.assertEqual(
            parse_sql(FRANCE_QUERY),
            SelectQuery(
                select_items=[SelectItem(ColumnRef('FirstName'))],
                from_table=TableRef('Customer'),
                where=[Comparison(ColumnRef('Country'), '=', 'France')],
                limit=3,
            ),
        )

    def test_rejects_delete(self):
        with self.assertRaisesRegex(ParserError, 'SELECT.*DELETE'):
            parse_sql(DELETE_QUERY)


class ExecutionTests(unittest.TestCase):
    def test_runs_a_select_on_chinook(self):
        self.assertEqual(run_query(FRANCE_QUERY), [('Camille',), ('Dominique',), ('Marc',)])

    def test_refusal_precedes_opening_sqlite(self):
        with patch('t2s.open_read_only') as connect:
            with self.assertRaises(ParserError):
                run_query(DELETE_QUERY)
            connect.assert_not_called()

    def test_connection_itself_refuses_delete(self):
        with TemporaryDirectory() as directory:
            copy_path = Path(directory) / 'Chinook copy.sqlite'
            shutil.copyfile(DATABASE_PATH, copy_path)
            with open_read_only(copy_path) as connection:
                self.assertEqual(connection.execute('PRAGMA query_only').fetchone(), (1,))
                with self.assertRaisesRegex(sqlite3.OperationalError, 'readonly'):
                    connection.execute(DELETE_QUERY)

                # Isolate the effect of mode=ro from PRAGMA query_only.
                connection.execute('PRAGMA query_only = OFF')
                self.assertEqual(connection.execute('PRAGMA query_only').fetchone(), (0,))
                with self.assertRaisesRegex(sqlite3.OperationalError, 'readonly'):
                    connection.execute(DELETE_QUERY)


class CLITests(unittest.TestCase):
    def run_cli(self, command, sql, *options):
        return subprocess.run(
            [sys.executable, '-X', 'utf8', str(TESTS_DIR / 't2s.py'), command, sql, *options],
            cwd=TESTS_DIR,
            capture_output=True,
            encoding='utf-8',
        )

    def test_parse_prints_ast(self):
        sql = 'SELECT FirstName, LastName FROM Customer LIMIT 5'
        result = self.run_cli('parse', sql)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('SelectQuery('))
        self.assertIn('limit=5', result.stdout)
        self.assertEqual(result.stderr, '')

        result = self.run_cli('parse', sql, '--pretty')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            'Arbre syntaxique (AST)',
            '  SELECT     FirstName, LastName',
            '  FROM       Customer',
            '  LIMIT      5',
        ])

    def test_parse_reports_syntax_error(self):
        result = self.run_cli('parse', 'SELECT FROM Customer')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('ParserError:', result.stderr)
        self.assertIn('line 1, column 8', result.stderr)

        result = self.run_cli('parse', 'SELECT\n\tFROM Customer', '--pretty')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr.splitlines()[:3], [
            'Erreur de syntaxe', '    FROM Customer', '    ^',
        ])
        self.assertIn('line 2, column 2', result.stderr)

    def test_run_prints_rows(self):
        result = self.run_cli('run', FRANCE_QUERY)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['Camille', 'Dominique', 'Marc'])

        result = self.run_cli('run', FRANCE_QUERY, '--pretty')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            'Résultat Chinook (3 lignes)', 'FirstName', '---------', 'Camille', 'Dominique', 'Marc',
        ])

        result = self.run_cli('run', 'SELECT FirstName AS Name, Company FROM Customer LIMIT 0', '--pretty')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['Résultat Chinook (0 ligne)', 'Name | Company', '-----+--------'])

    def test_run_refuses_delete(self):
        result = self.run_cli('run', DELETE_QUERY)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('Refused:', result.stderr)

        result = self.run_cli('run', DELETE_QUERY, '--pretty')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr.splitlines()[:3], ['Requête refusée avant exécution', DELETE_QUERY, '^'])

    def test_run_reports_sqlite_errors(self):
        result = self.run_cli('run', 'SELECT Name FROM UnknownTable')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('SQLite error: no such table: UnknownTable', result.stderr)
