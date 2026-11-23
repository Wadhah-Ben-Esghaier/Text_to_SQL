# SQL grammar — part A

The parser accepts one SELECT statement and consumes the entire input. Keywords
are case-insensitive. Part A adds bare JOIN (equivalent to INNER JOIN), AVG, and
SELECT DISTINCT. DISTINCT applies to the complete result row, not one column.
Only one inner join is supported; other join kinds remain outside the subset.
DISTINCT inside an aggregate, such as COUNT(DISTINCT Country), is not included.

## Grammar

In this EBNF, brackets mean optional, braces mean repetition, and a vertical bar
means a choice. EOF is the end-of-input token produced by the lexer.

```ebnf
query = select_stmt, [ ";" ], EOF ;

select_stmt =
    "SELECT", [ "DISTINCT" ], select_list,
    "FROM", table_ref,
    [ inner_join ],
    [ where_clause ],
    [ group_by_clause ],
    [ having_clause ],
    [ order_by_clause ],
    [ limit_clause ] ;

#Selection des colonnes
select_list = select_item, { ",", select_item } ;

select_item =
      column_ref, [ "AS", identifier ]
    | aggregate_expr, [ "AS", identifier ] ;


#Tables et jointures
table_ref = identifier, [ [ "AS" ], identifier ] ;

inner_join =
    [ "INNER" ], "JOIN", table_ref,
    "ON", join_condition ;

join_condition =
    column_ref, "=", column_ref ;

column_ref =
    [ identifier, "." ], identifier ;

aggregate_expr =
      "COUNT", "(", ( "*" | column_ref ), ")"
    | ( "SUM" | "AVG" ), "(", column_ref, ")" ;

#Condition WHERE

where_clause = "WHERE", and_expr ;

and_expr =
    comparison, { "AND", comparison } ;

comparison =
      column_ref, comparison_operator, literal
    | column_ref, "IS", [ "NOT" ], "NULL" ;

comparison_operator =
      "="
    | "<>"
    | "<"
    | "<="
    | ">"
    | ">=" ;

#Regroupement et Having

group_by_clause =
    "GROUP", "BY", column_ref,
    { ",", column_ref } ;

having_clause =
    "HAVING", aggregate_expr,
    comparison_operator, literal ;




#Tri et limitation

order_by_clause =
    "ORDER", "BY", order_item,
    { ",", order_item } ;

order_item =
    order_expression, [ "ASC" | "DESC" ] ;

order_expression =
      column_ref
    | aggregate_expr ;


limit_clause =
    "LIMIT", unsigned_integer ;


#Types de valeurs

literal =
      number
    | string ;

number =
    [ "-" ], digit, { digit },
    [ ".", digit, { digit } ] ;

unsigned_integer =
    digit, { digit } ;

string =
    "'", { string_char | "''" }, "'" ;

string_char = ? any character except a single quote ? ;


#Elements lexicaux:
identifier =
    letter, { letter | digit | "_" } ;

digit = "0" | "1" | "2" | "3" | "4"
      | "5" | "6" | "7" | "8" | "9" ;

letter = ? a Unicode letter, as recognized by str.isalpha(), or underscore ? ;
```

Identifiers cannot be keywords. LEFT, RIGHT, FULL, OUTER, CROSS and NATURAL are
reserved even though these joins are unsupported: they must not become table
aliases followed by a bare JOIN.

## AST and implementation decisions

- JOIN and INNER JOIN produce the same JoinClause; no new join node is needed.
- AVG uses the existing Aggregate node with function="AVG". It is accepted in
  SELECT, HAVING and ORDER BY, wherever SUM is already accepted.
- SELECT DISTINCT sets SelectQuery.distinct to True; its default is False.
  This flag belongs to the whole query because duplicate removal concerns the
  combination of all selected values. A flag on each SelectItem was rejected.
- Grammar extensions belong in the lexer, parser and AST. Rewriting SQL in the
  command-line entry point would hide grammar rules from future entry points.

## Values and NULL

Integer literals become Python int, decimal literals float, and strings str.
NULL is tested with IS NULL or IS NOT NULL; comparisons such as = NULL are
outside the grammar. COUNT(*) counts rows, COUNT(column) counts non-NULL
values, and SUM/AVG ignore NULL values. On an empty input, COUNT returns 0 and
SUM/AVG return NULL. Numeric column checks belong to the semantic checker;
the parser only checks syntax.

## Examples and completion criteria

Accepted examples:

```sql
SELECT a.Title FROM Album a JOIN Artist ar ON a.ArtistId = ar.ArtistId
SELECT AVG(Milliseconds) AS mean_ms FROM Track
SELECT MediaTypeId, AVG(Milliseconds) FROM Track GROUP BY MediaTypeId HAVING AVG(Milliseconds) > 200000 ORDER BY AVG(Milliseconds) DESC
SELECT DISTINCT Country, City FROM Customer
```

Rejected examples: AVG(*), SUM(*), SELECT DISTINCT FROM Customer, LEFT JOIN,
CROSS JOIN, a second JOIN, subqueries and multiple statements. The original
subset (including INNER JOIN, COUNT and SUM) must keep working.

Part A is complete when all 12 reference queries in
docs/atelier-architecture.html are parsed and execute on Chinook, the new AST
information is preserved and displayed, DISTINCT has its own checks (none of
the 12 references uses it), and the original test suite still passes.

Run: `python -m unittest discover -s tests -v`.

