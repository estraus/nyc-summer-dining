-- Outside ratings shown next to the AI ranking so users can compare.
-- Entered by hand in /admin. Deliberately not sent to the ranking prompt.
ALTER TABLE restaurants ADD COLUMN google_rating REAL CHECK (google_rating IS NULL OR google_rating BETWEEN 1 AND 5);
ALTER TABLE restaurants ADD COLUMN google_review_count INTEGER CHECK (google_review_count IS NULL OR google_review_count >= 0);
ALTER TABLE restaurants ADD COLUMN beli_score REAL CHECK (beli_score IS NULL OR beli_score BETWEEN 0 AND 10);
