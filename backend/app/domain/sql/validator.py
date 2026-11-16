"""Validation statique du SQL généré : un seul SELECT, uniquement sur les vues autorisées."""
from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

from app.core.config import get_settings

SENSITIVE_COLUMNS = {
    "id", "patient_id", "patient_key", "name", "firstname", "lastname", "phone", "tel",
    "cin", "cin_no", "birthdate", "email", "adress", "address",
}
ALLOWED_ANONYMOUS = {"date_part", "to_char", "age", "nullif", "date_trunc"}
FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop,
             exp.Alter, exp.Copy, exp.TruncateTable, exp.Command)


def _is_sensitive(name: str) -> bool:
    name = name.casefold()
    return name in SENSITIVE_COLUMNS or name.endswith("_key")


def _under_count(node: exp.Expression) -> bool:
    parent = node.parent
    while parent is not None:
        if isinstance(parent, exp.Count):
            return True
        parent = parent.parent
    return False


def validate_sql(statement: str, views: set[tuple[str, str]],
                 bound_parameters: set[str] | None = None) -> str:
    """Retourne le SQL qualifié (schema.vue) et limité, ou lève ValueError."""
    max_rows = get_settings().max_sql_rows
    try:
        statements = sqlglot.parse(statement, read="postgres")
    except sqlglot.errors.ParseError as exc:
        raise ValueError("Le SQL généré n'a pas pu être analysé.") from exc
    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Exactement une instruction SQL est requise.")
    query = statements[0]
    if not isinstance(query, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise ValueError("Seules les requêtes SELECT sont autorisées.")
    if any(query.find(n) for n in FORBIDDEN):
        raise ValueError("Les instructions qui modifient les données sont interdites.")
    if query.find(exp.Into) or query.find(exp.Lock):
        raise ValueError("SELECT INTO et les verrous de lignes sont interdits.")
    for fn in query.find_all(exp.Anonymous):
        if str(fn.this).casefold() not in ALLOWED_ANONYMOUS:
            raise ValueError(f"Fonction non autorisée : {fn.this}")
    if query.find(exp.UserDefinedFunction):
        raise ValueError("Les fonctions définies par l'utilisateur sont interdites.")
    placeholders = {str(p.this) for p in query.find_all(exp.Placeholder) if p.this}
    if bound_parameters is not None and placeholders != bound_parameters:
        raise ValueError(
            f"Paramètres SQL {sorted(placeholders)} différents des paramètres liés "
            f"{sorted(bound_parameters)}.")
    if any(clause.find(exp.Literal) for clause in query.find_all(exp.Where, exp.Having)):
        raise ValueError("Les valeurs de filtre doivent utiliser des paramètres liés.")

    for select in query.find_all(exp.Select):
        for proj in select.expressions:
            if isinstance(proj, exp.Star) or (
                isinstance(proj, exp.Column) and isinstance(proj.this, exp.Star)
            ):
                raise ValueError("SELECT * est interdit : nommez les colonnes.")
    for column in query.find_all(exp.Column):
        if _is_sensitive(column.name) and not _under_count(column):
            raise ValueError(f"La colonne {column.name} n'est autorisée que dans un COUNT.")

    cte_names = {c.alias_or_name.casefold() for c in query.find_all(exp.CTE)}
    for table in query.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier):
            raise ValueError("Les fonctions de table sont interdites.")
        name = table.name.casefold()
        if name in cte_names and not table.db:
            continue
        if table.catalog:
            raise ValueError("Les références inter-bases sont interdites.")
        if table.db:
            if (table.db.casefold(), name) not in views:
                raise ValueError(f"Table non approuvée : {table.sql(dialect='postgres')}")
        else:
            matches = [v for v in views if v[1] == name]
            if len(matches) != 1:
                raise ValueError(
                    f"Table inconnue : {table.name}. Utilisez uniquement les vues approuvées "
                    "sous la forme schéma.vue.")
            table.set("db", exp.to_identifier(matches[0][0]))

    limit = query.args.get("limit")
    ok = (limit is not None and isinstance(limit.expression, exp.Literal)
          and limit.expression.is_number and int(limit.expression.this) <= max_rows)
    if not ok:
        query.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
    sql = query.sql(dialect="postgres")
    return re.sub(r"%\(([A-Za-z_]\w*)\)s", r":\1", sql)
