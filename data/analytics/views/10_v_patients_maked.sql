DROP VIEW IF EXISTS analytics.v_patients_masked;

CREATE VIEW analytics.v_patients_masked AS
SELECT analytics.patient_key(p.id::text) AS patient_key,
    analytics.norm_gender(p.gender::text) AS gender,
    CASE
        WHEN b.birth_date IS NULL THEN NULL
        WHEN b.birth_date > CURRENT_DATE THEN NULL
        WHEN date_part('year', age(CURRENT_DATE, b.birth_date)) > 120 THEN NULL
        ELSE date_part('year', age(CURRENT_DATE, b.birth_date))::int
    END AS age,
    analytics.age_group(b.birth_date, CURRENT_DATE) AS age_group,
    COALESCE(NULLIF(btrim(p.district::text), ''::text), 'Non renseigné'::text) AS district,
    COALESCE(NULLIF(btrim(p.commune::text), ''::text), 'Non renseigné'::text) AS commune,
    (p.created_at AT TIME ZONE 'Indian/Antananarivo'::text)::date AS registered_at
   FROM patients p
     CROSS JOIN LATERAL (SELECT analytics.safe_date(p.birthdate::text) AS birth_date) b
  WHERE p.deleted = 0;