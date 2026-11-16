-- ATTENTION : colonnes SUPPOSÉES de public.admissions (id, patient_id, created_at).
-- Une ligne = une admission = une visite. Date de référence = created_at.
CREATE OR REPLACE VIEW analytics.v_visits AS
SELECT a.id::text AS visit_key,
    analytics.patient_key(a.patient_id::text) AS patient_key,
    (a.created_at AT TIME ZONE 'Indian/Antananarivo'::text)::date AS visit_date,
    COALESCE(NULLIF(btrim(cat.name::text), ''::text), 'Non renseigné'::text) AS category,
    analytics.norm_gender(p.gender::text) AS gender,
    analytics.age_group(analytics.safe_date(p.birthdate::text), (a.created_at AT TIME ZONE 'Indian/Antananarivo'::text)::date) AS age_group,
    COALESCE(NULLIF(btrim(p.district::text), ''::text), 'Non renseigné'::text) AS district,
    COALESCE(NULLIF(btrim(p.commune::text), ''::text), 'Non renseigné'::text) AS commune
   FROM admissions a
     LEFT JOIN categories cat ON a.category_id = cat.id::numeric
     LEFT JOIN patients p ON a.patient_id = p.id;