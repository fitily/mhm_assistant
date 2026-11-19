-- Base « ambovo_app » : comptes des utilisateurs de l'assistant.
-- Base SÉPARÉE des données médicales : elle ne contient que des comptes et des mots de passe HACHÉS.
-- À exécuter une seule fois, connecté en tant qu'utilisateur « ambovo_app » :
--   psql -h localhost -U ambovo_app -d ambovo_app -f data/app/001_users.sql

CREATE TABLE IF NOT EXISTS users (
    id            bigserial   PRIMARY KEY,
    email         text        NOT NULL,
    full_name     text        NOT NULL,
    password_hash text        NOT NULL,                         -- argon2id, jamais le mot de passe
    role          text        NOT NULL CHECK (role IN ('doctor', 'admin')),
    is_active     boolean     NOT NULL DEFAULT true,            -- false = compte désactivé
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_login_at timestamptz
);

-- Un même email ne peut exister qu'une fois, sans tenir compte des majuscules.
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_uniq ON users (lower(email));
