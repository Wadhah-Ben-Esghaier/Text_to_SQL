"""Part A: the workshop references and the limits of the extended grammar."""

import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent / 'src'))

from cli_display import format_ast
from parser import ParserError, parse_sql
from sql_ast import Aggregate, ColumnRef, SelectQuery
from t2s import run_query


# Copied from the 12 reference queries in docs/atelier-architecture.html.
REFERENCE_QUERIES = (
    'SELECT COUNT(*) FROM Customer',
    'SELECT Name FROM Genre',
    "SELECT FirstName, LastName FROM Customer WHERE Country = 'France'",
    'SELECT Name, Milliseconds FROM Track ORDER BY Milliseconds DESC LIMIT 5',
    'SELECT BillingCountry, COUNT(*) AS n FROM Invoice '
    'GROUP BY BillingCountry ORDER BY n DESC',
    'SELECT a.Title FROM Album a JOIN Artist ar ON a.ArtistId = ar.ArtistId '
    "WHERE ar.Name = 'AC/DC'",
    'SELECT t.Name FROM Track t JOIN Genre g ON t.GenreId = g.GenreId '
    "WHERE g.Name = 'Jazz' AND t.Milliseconds > 400000",
    'SELECT e.FirstName, e.LastName FROM Customer c JOIN Employee e '
    'ON c.SupportRepId = e.EmployeeId WHERE c.CustomerId = 1',
    'SELECT c.FirstName, c.LastName, SUM(i.Total) AS total FROM Customer c '
    'JOIN Invoice i ON i.CustomerId = c.CustomerId '
    'GROUP BY c.CustomerId, c.FirstName, c.LastName HAVING SUM(i.Total) > 45',
    'SELECT g.Name, COUNT(*) AS n FROM Track t JOIN Genre g '
    'ON t.GenreId = g.GenreId GROUP BY g.Name ORDER BY n DESC LIMIT 3',
    'SELECT m.Name, AVG(t.Milliseconds) AS avg_ms FROM Track t '
    'JOIN MediaType m ON t.MediaTypeId = m.MediaTypeId GROUP BY m.Name',
    'SELECT ar.Name, COUNT(*) AS n FROM Album a JOIN Artist ar '
    'ON a.ArtistId = ar.ArtistId GROUP BY ar.Name ORDER BY n DESC LIMIT 3',
)


class GrammarExtensionTests(unittest.TestCase):
    def test_accepts_all_12_reference_queries(self):
        for number, sql in enumerate(REFERENCE_QUERIES, 1):
            with self.subTest(reference=number):
                self.assertIsInstance(parse_sql(sql), SelectQuery)

    def test_join_and_inner_join_have_the_same_ast(self):
        sql = ('SELECT a.Title FROM Album a JOIN Artist ar '
               'ON a.ArtistId = ar.ArtistId')
        self.assertEqual(parse_sql(sql), parse_sql(sql.replace(' JOIN ', ' INNER JOIN ')))

    def test_avg_in_select_having_and_order_by(self):
        query = parse_sql(
            'SELECT MediaTypeId, AVG(Milliseconds) AS mean_ms FROM Track '
            'GROUP BY MediaTypeId HAVING AVG(Milliseconds) > 200000 '
            'ORDER BY AVG(Milliseconds) DESC'
        )
        expected = Aggregate('AVG', ColumnRef('Milliseconds'))
        self.assertEqual(query.select_items[1].expression, expected)
        self.assertEqual(query.select_items[1].alias, 'mean_ms')
        self.assertEqual(query.having.aggregate, expected)
        self.assertEqual(query.order_by[0].expression, expected)

    def test_distinct_is_preserved_for_the_whole_query(self):
        query = parse_sql('SELECT DISTINCT Country, City FROM Customer')
        self.assertTrue(query.distinct)
        self.assertEqual(len(query.select_items), 2)
        self.assertFalse(parse_sql('SELECT Country FROM Customer').distinct)
        self.assertIn('SELECT     DISTINCT Country, City', format_ast(query))

    def test_new_keywords_are_case_insensitive(self):
        sql = ('SELECT DISTINCT AVG(t.Milliseconds) FROM Track t '
               'JOIN MediaType m ON t.MediaTypeId = m.MediaTypeId')
        mixed_case = sql.replace('DISTINCT', 'distinct').replace('AVG', 'avg').replace('JOIN', 'join')
        self.assertEqual(parse_sql(sql), parse_sql(mixed_case))

    def test_rejects_unsupported_join_kinds(self):
        for join in ('LEFT JOIN', 'LEFT OUTER JOIN', 'RIGHT JOIN',
                     'FULL JOIN', 'OUTER JOIN', 'CROSS JOIN', 'NATURAL JOIN'):
            # Both forms matter: without an alias LEFT used to be a possible alias.
            for table in ('Album', 'Album a'):
                with self.subTest(join=join, table=table):
                    with self.assertRaises(ParserError):
                        parse_sql(f'SELECT Title FROM {table} {join} Artist '
                                  'ON Album.ArtistId = Artist.ArtistId')

    def test_rejects_malformed_or_out_of_subset_queries(self):
        queries = (
            'SELECT AVG(*) FROM Track',
            'SELECT SUM(*) FROM Track',
            'SELECT AVG() FROM Track',
            'SELECT DISTINCT FROM Customer',
            'SELECT DISTINCT DISTINCT Country FROM Customer',
            'SELECT COUNT(DISTINCT Country) FROM Customer',
            'SELECT Title FROM Album JOIN Artist',
            'SELECT Title FROM Album JOIN Artist ON Album.ArtistId = Artist.ArtistId '
            'JOIN Track ON Track.AlbumId = Album.AlbumId',
            'SELECT Name FROM (SELECT Name FROM Artist)',
            'SELECT DISTINCT Country FROM Customer; DELETE FROM Customer',
        )
        for sql in queries:
            with self.subTest(sql=sql):
                with self.assertRaises(ParserError):
                    parse_sql(sql)


class GrammarExtensionExecutionTests(unittest.TestCase):
    def test_all_12_references_execute_on_chinook(self):
        for number, sql in enumerate(REFERENCE_QUERIES, 1):
            with self.subTest(reference=number):
                self.assertTrue(run_query(sql))

    def test_avg_matches_the_arithmetic_mean(self):
        durations = [row[0] for row in run_query('SELECT Milliseconds FROM Track')]
        result = run_query('SELECT AVG(Milliseconds) FROM Track')[0][0]
        self.assertAlmostEqual(result, sum(durations) / len(durations))

    def test_distinct_removes_duplicate_rows(self):
        rows = run_query('SELECT Country, City FROM Customer ORDER BY Country, City')
        distinct = run_query('SELECT DISTINCT Country, City FROM Customer ORDER BY Country, City')
        self.assertEqual(distinct, sorted(set(rows)))
        self.assertLess(len(distinct), len(rows))


if __name__ == '__main__':
    unittest.main()
