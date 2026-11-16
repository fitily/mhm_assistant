-- Schéma analytics : la seule porte d'entrée du chatbot vers les données.
CREATE SCHEMA IF NOT EXISTS analytics;

-- Tranche d'âge (13 tranches officielles, voir config/metrics.yaml)
CREATE OR REPLACE FUNCTION analytics.age_group_label(age_years integer)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE
    WHEN age_years IS NULL THEN NULL
    WHEN age_years <= 5  THEN '0-5'
    WHEN age_years <= 11 THEN '6-11'
    WHEN age_years <= 17 THEN '12-17'
    WHEN age_years <= 23 THEN '18-23'
    WHEN age_years <= 29 THEN '24-29'
    WHEN age_years <= 35 THEN '30-35'
    WHEN age_years <= 41 THEN '36-41'
    WHEN age_years <= 46 THEN '42-46'
    WHEN age_years <= 52 THEN '47-52'
    WHEN age_years <= 58 THEN '53-58'
    WHEN age_years <= 64 THEN '59-64'
    WHEN age_years <= 70 THEN '65-70'
    ELSE 'plus de 70'
  END
$$;

-- Rang de la tranche (pour trier correctement : 0-5, 6-11, 12-17, ...)
CREATE OR REPLACE FUNCTION analytics.age_group_rank(age_years integer)
RETURNS integer LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE
    WHEN age_years IS NULL THEN NULL
    WHEN age_years <= 5  THEN 1  WHEN age_years <= 11 THEN 2
    WHEN age_years <= 17 THEN 3  WHEN age_years <= 23 THEN 4
    WHEN age_years <= 29 THEN 5  WHEN age_years <= 35 THEN 6
    WHEN age_years <= 41 THEN 7  WHEN age_years <= 46 THEN 8
    WHEN age_years <= 52 THEN 9  WHEN age_years <= 58 THEN 10
    WHEN age_years <= 64 THEN 11 WHEN age_years <= 70 THEN 12
    ELSE 13
  END
$$;
