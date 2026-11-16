DROP VIEW IF EXISTS analytics.v_data_freshness;
DROP VIEW IF EXISTS analytics.v_diagnoses;

CREATE VIEW analytics.v_diagnoses AS
SELECT dp.id::text AS diagnosis_key,
    analytics.patient_key(dp.patient_id::text) AS patient_key,
    (dp.created_at AT TIME ZONE 'Indian/Antananarivo'::text)::date AS diagnosis_date,
    COALESCE(NULLIF(btrim(di.description::text), ''::text), 'Non renseigné'::text) AS diagnosis_label,
    NULLIF(btrim(di.cim_ten::text), ''::text) AS icd10_code,
    analytics.norm_gender(p.gender::text) AS gender,
    analytics.age_group(analytics.safe_date(p.birthdate::text), (dp.created_at AT TIME ZONE 'Indian/Antananarivo'::text)::date) AS age_group,
    COALESCE(NULLIF(btrim(p.district::text), ''::text), 'Non renseigné'::text) AS district
   FROM diagnose_patients dp
     LEFT JOIN diagnose_items di ON NULLIF(btrim(dp.diagnose_item_id::text), ''::text)::bigint = di.id
     LEFT JOIN patients p ON dp.patient_id = p.id;