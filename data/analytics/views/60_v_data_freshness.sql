CREATE OR REPLACE VIEW analytics.v_data_freshness AS
 SELECT 'v_generalist_consultations'::text AS source,
    min(v_generalist_consultations.consultation_date) AS min_date,
    max(v_generalist_consultations.consultation_date) AS max_date
   FROM analytics.v_generalist_consultations
UNION ALL
 SELECT 'v_visits'::text AS source,
    min(v_visits.visit_date) AS min_date,
    max(v_visits.visit_date) AS max_date
   FROM analytics.v_visits
UNION ALL
 SELECT 'v_diagnoses'::text AS source,
    min(v_diagnoses.diagnosis_date) AS min_date,
    max(v_diagnoses.diagnosis_date) AS max_date
   FROM analytics.v_diagnoses
UNION ALL
 SELECT 'v_discharges'::text AS source,
    min(v_discharges.discharge_date) AS min_date,
    max(v_discharges.discharge_date) AS max_date
   FROM analytics.v_discharges;