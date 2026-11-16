CREATE OR REPLACE VIEW analytics.v_discharges AS
 SELECT d.id::text AS discharge_key,
    analytics.patient_key(d.patient_id::text) AS patient_key,
    (d.created_at AT TIME ZONE 'Indian/Antananarivo'::text)::date AS discharge_date,
        CASE
            WHEN d.patient_dead::text = '1'::text THEN true
            WHEN d.patient_dead::text = '0'::text THEN false
            ELSE NULL::boolean
        END AS patient_dead,
    analytics.norm_gender(p.gender::text) AS gender,
    analytics.age_group(analytics.safe_date(p.birthdate::text), (d.created_at AT TIME ZONE 'Indian/Antananarivo'::text)::date) AS age_group
   FROM dismissals d
     LEFT JOIN patients p ON d.patient_id = p.id;
