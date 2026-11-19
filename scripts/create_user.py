"""Gère les comptes de l'assistant (base « ambovo_app »).

    python scripts/create_user.py create --email prenom.nom@mhm.org --name "Prénom Nom" --role doctor
    python scripts/create_user.py password --email prenom.nom@mhm.org
    python scripts/create_user.py list

Rôles : doctor (documents uniquement) ou admin (statistiques et dashboards uniquement).
Le mot de passe est demandé au clavier (jamais en argument : il resterait dans l'historique).
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core import passwords  # noqa: E402
from app.core.security import ROLES  # noqa: E402
from app.infrastructure.db import users  # noqa: E402


def ask_password() -> str:
    password = getpass.getpass("Mot de passe : ")
    if password != getpass.getpass("Confirmer le mot de passe : "):
        sys.exit("Les deux mots de passe sont différents.")
    try:
        passwords.check_strength(password)
    except ValueError as exc:
        sys.exit(str(exc))
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="créer un compte")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--role", required=True, choices=sorted(ROLES))
    reset = sub.add_parser("password", help="changer le mot de passe d'un compte")
    reset.add_argument("--email", required=True)
    sub.add_parser("list", help="afficher les comptes")
    args = parser.parse_args()

    if args.command == "create":
        if "@" not in args.email:
            sys.exit("Adresse e-mail invalide.")
        try:
            users.create(args.email, args.name, passwords.hash_password(ask_password()), args.role)
        except ValueError as exc:
            sys.exit(str(exc))
        print(f"Compte créé : {args.email.strip().lower()} ({args.role})")
    elif args.command == "password":
        if not users.set_password_hash(args.email, passwords.hash_password(ask_password())):
            sys.exit("Aucun compte avec cet email.")
        print("Mot de passe modifié.")
    else:
        for u in users.list_users():
            state = "actif" if u["is_active"] else "DÉSACTIVÉ"
            print(f"{u['email']:<35} {u['role']:<7} {state:<10} {u['full_name']}")


if __name__ == "__main__":
    main()
