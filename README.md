# Text-to-SQL vérifié

Projet TDLOG. À terme, l’application traduira une question en français en SQL, vérifiera la requête, puis l’exécutera sur la base musicale Chinook. Pour le jalon du 23 novembre 2026, le programme part d’une requête SQL écrite à la main. Le lexer la transforme en jetons, puis le parser construit un arbre syntaxique (AST) ou indique la position de l’erreur. Une requête acceptée peut ensuite être exécutée sur Chinook en lecture seule.

## Fichiers du projet

| Fichier | Rôle |
| --- | --- |
| [`Design.md`](Design.md) | Grammaire EBNF du sous-ensemble SQL visé. |
| [`src/Lexer.py`](src/Lexer.py) | Produit des jetons typés avec leur ligne et leur colonne. |
| [`src/parser.py`](src/parser.py) | Analyse les jetons par descente récursive. `parse_sql(sql)` renvoie un `SelectQuery`. |
| [`src/sql_ast.py`](src/sql_ast.py) | Définit les dataclasses de l’AST pour les colonnes, les tables et les clauses SQL. |
| [`tests/t2s.py`](tests/t2s.py) | Fournit les commandes de démonstration `parse` et `run` et ouvre Chinook en lecture seule. |
| [`tests/cli_display.py`](tests/cli_display.py) | Met en forme l'AST et les résultats de la démonstration. |
| [`data/Chinook_Sqlite.sqlite`](data/Chinook_Sqlite.sqlite) | Base d’exemple SQLite fournie avec le projet. |
| [`tests/test_text_to_sql.py`](tests/test_text_to_sql.py) | Tests automatisés du lexer, du parser, de SQLite et de la ligne de commande. |
| [Workflow GitHub Actions](.github/workflows/tests.yml) | Lance la suite de tests à chaque push et pull request. |
| [`docs/tdlog-text-to-sql.html`](docs/tdlog-text-to-sql.html#marche) | Consigne du jalon et exemples de démonstration. |

## Tester une requête avec `t2s.py`

Depuis la racine du dépôt, entre dans le dossier `tests/` et passe la requête SQL entre guillemets.

```sh
cd tests
python t2s.py parse "SELECT FirstName FROM Customer"
python t2s.py run "SELECT FirstName FROM Customer ORDER BY CustomerId LIMIT 3"
```

- `parse` vérifie la syntaxe selon la grammaire du projet et affiche l'arbre syntaxique (AST). Si le parser rencontre une erreur, il indique la ligne et la colonne du jeton en cause.
- `run` vérifie d'abord la requête avec le parser, puis l'exécute sur Chinook en lecture seule si elle est acceptée. L'exemple affiche les prénoms des trois premiers clients par identifiant.

Ajoute `--pretty` à la fin de la commande pour afficher un AST par clause, un tableau de résultats ou un repère sous le jeton en cause. Depuis la racine du dépôt, utilise `python tests/t2s.py` à la place de `python t2s.py`.

## Lancer la démonstration

Depuis la racine du dépôt, avec Python 3.10 ou supérieur. La démonstration a été vérifiée sous Python 3.12 et utilise uniquement la bibliothèque standard.

```sh
python tests/t2s.py parse "SELECT FirstName, LastName FROM Customer LIMIT 5" --pretty
python tests/t2s.py parse "SELECT FROM Customer" --pretty
python tests/t2s.py run "SELECT FirstName FROM Customer WHERE Country = 'France' ORDER BY CustomerId LIMIT 3" --pretty
python tests/t2s.py run "DELETE FROM Customer" --pretty
```

| Exemple | Résultat attendu |
| --- | --- |
| `parse` avec les deux colonnes | Une vue de l'AST avec les clauses `SELECT`, `FROM` et `LIMIT`. |
| `parse` sans colonne | Une erreur de syntaxe avec un `^` sous `FROM`, à la ligne 1, colonne 8. |
| `run` avec `Country = 'France'` | Un tableau avec la colonne `FirstName` et les trois prénoms Camille, Dominique et Marc. |
| `run` avec `DELETE` | Un refus avant exécution avec un `^` sous `DELETE`, à la ligne 1, colonne 1. |

Le lexer découpe la requête en jetons. Le parser vérifie leur ordre et construit un arbre qui représente les clauses de la requête. Dans `SELECT FROM Customer`, il attend une colonne après `SELECT`, donc il signale `FROM`. Une requête acceptée peut être exécutée sur Chinook en lecture seule. `DELETE`, lui, est rejeté avant même l’ouverture de la base.

L'option `--pretty` met en forme la sortie pour la démonstration. Les erreurs sont affichées sur la sortie d'erreur et renvoient le code de sortie `1`. `run` appelle le parser avant d'ouvrir SQLite. La connexion est ouverte avec `mode=ro` et `PRAGMA query_only = ON`.

## Lancer les tests

```sh
python -m unittest discover -s tests -v
```

Cette commande lance 17 tests, dont des cas paramétrés pour les 16 requêtes valides et les 5 invalides du parser. La suite vérifie aussi la forme d'un AST, les positions du lexer et les deux barrières contre `DELETE`. Le test SQLite envoie le `DELETE` directement à une connexion ouverte sur une copie temporaire de Chinook. GitHub Actions lance la même commande.

Pour la présentation, `python -m unittest discover -s tests -q` affiche uniquement le bilan quand les tests passent.

## Sous-ensemble SQL

Le périmètre minimal du jalon couvre `SELECT … FROM …`, une comparaison facultative dans `WHERE` et une clause facultative `LIMIT`. Le parser accepte aussi une jointure `INNER JOIN`, les alias, `COUNT`, `SUM`, `AND`, `IS [NOT] NULL`, `GROUP BY`, `HAVING` et `ORDER BY`. L’analyse est syntaxique. SQLite se charge de résoudre les noms de tables et de colonnes lors de l’exécution.

## Jalon du 23 novembre

- [x] Base Chinook présente dans `data/`, lexer positionné, parser maison et AST en dataclasses.
- [x] Les 16 exemples valides sont parsés et les 5 invalides sont rejetés avec une position.
- [x] **Exécution et démo**. Les commandes `parse` et `run` couvrent les quatre cas de la consigne. `run` valide la requête et ouvre Chinook en lecture seule.
- [x] **Tests automatisés et CI**. La suite passe localement. Le workflow est configuré pour la lancer sur GitHub.
- [x] **Identifiants avec chiffres**. Le lexer accepte des identifiants comme `T1` en un seul jeton.
- [ ] **Documentation**. Compléter `Design.md` avec les règles `aggregate_expr` et `string_char`, des exemples acceptés et refusés, le périmètre du jalon, les critères de validation et la répartition du travail. Remplir `AGENTS.md` avec les consignes de l’équipe, dont l’usage d’un parser maison et la limitation de `sqlglot` aux tests. Confirmer l’accès de l’encadrant au dépôt GitHub.
- [ ] **Présentation de cinq minutes**. Expliquer la chaîne du Text-to-SQL et le rôle du lexer, du parser et de l’AST. Faire la démo, montrer les tests et présenter les difficultés ou questions. Chaque membre doit pouvoir expliquer le code de l’équipe.
