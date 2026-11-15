select_stmt =
    "SELECT", select_list,
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
    "INNER", "JOIN", table_ref,
    "ON", join_condition ;

join_condition =
    column_ref, "=", column_ref ;

column_ref =
    [ identifier, "." ], identifier ;

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


#Elements lexicaux:
identifier =
    letter, { letter | digit | "_" } ;

digit = "0" | "1" | "2" | "3" | "4"
      | "5" | "6" | "7" | "8" | "9" ;

letter = "A"|"B"|"C|"D"|"E"|"F"|"G"|"H"|"I"|"J"|"K"|"L"|"M"|"N"|"O"|"P"|"Q"|"R"|"S"|"T"|"U"|"V"|"W"|"X"|"Y"|"Z"|"a"|"b"|"c"|"d"|"e"|"f"|"g"|"h"|"i"|"j"|"k"|"l"|"m"|"n"|"o"|"p"|"q"|"r"|"s"|"t"|"u"|"v"|"w"|"x"|"y"|"z"|"_";

