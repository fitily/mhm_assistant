CREATE OR REPLACE VIEW analytics.v_generalist_consultations AS
 SELECT c.id::text AS consultation_key,
    analytics.patient_key(c.patient_id::text) AS patient_key,
    (c.created_at AT TIME ZONE 'Indian/Antananarivo'::text)::date AS consultation_date,
    analytics.norm_gender(p.gender::text) AS gender,
    analytics.age_group(analytics.safe_date(p.birthdate::text), (c.created_at AT TIME ZONE 'Indian/Antananarivo'::text)::date) AS age_group,
    COALESCE(NULLIF(btrim(p.district::text), ''::text), 'Non renseigné'::text) AS district,
    COALESCE(NULLIF(btrim(p.commune::text), ''::text), 'Non renseigné'::text) AS commune,
    c.outcome::text AS outcome
   FROM generalist_consultations c
     LEFT JOIN patients p ON c.patient_id = p.id;
