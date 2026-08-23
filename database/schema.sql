-- Smart Graffiti Management — Database Schema (PostgreSQL)
-- This is a starting schema. Extend/normalise further as your requirements firm up.

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    display_name    VARCHAR(100),
    role            VARCHAR(20) NOT NULL DEFAULT 'citizen', -- 'citizen' | 'council_staff' | 'admin'
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reports (
    id                  SERIAL PRIMARY KEY,
    submitted_by        INTEGER REFERENCES users(id),
    image_url           TEXT NOT NULL,
    latitude             DOUBLE PRECISION NOT NULL,
    longitude            DOUBLE PRECISION NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'new', -- 'new' | 'scheduled' | 'resolved'
    submitted_at         TIMESTAMP NOT NULL DEFAULT now(),
    notes                TEXT
);

-- Results from the AI detection/classification pipeline for a given report.
-- Kept separate from `reports` so the model can be re-run / re-versioned later.
CREATE TABLE IF NOT EXISTS classifications (
    id                  SERIAL PRIMARY KEY,
    report_id           INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    surface_type        VARCHAR(50),        -- e.g. 'brick_wall', 'metal_shutter', 'signage'
    tag_category         VARCHAR(50),        -- e.g. 'tag', 'stencil', 'mural', 'offensive_content'
    detection_confidence DOUBLE PRECISION,   -- 0.0–1.0, model's confidence in the detection
    harm_score           INTEGER,            -- 1 (low) – 5 (high), from the harm classification framework
    model_version         VARCHAR(50),        -- which trained model produced this result
    classified_at         TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_location ON reports(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_classifications_report_id ON classifications(report_id);
