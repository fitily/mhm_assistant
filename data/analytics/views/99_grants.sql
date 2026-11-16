-- Le rôle du chatbot ne voit QUE le schéma analytics (jamais public).
-- Remplacez chatbot_ro si votre rôle lecture seule porte un autre nom.
REVOKE ALL ON SCHEMA public FROM chatbot_ro;
GRANT USAGE ON SCHEMA analytics TO chatbot_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO chatbot_ro;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA analytics TO chatbot_ro;
ALTER ROLE chatbot_ro SET default_transaction_read_only = on;
