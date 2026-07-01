-- Async GEE processing status (production job tracking)

ALTER TABLE fields
  ADD COLUMN IF NOT EXISTS processing_status TEXT NOT NULL DEFAULT 'idle',
  ADD COLUMN IF NOT EXISTS processing_error TEXT,
  ADD COLUMN IF NOT EXISTS processing_updated_at TIMESTAMPTZ;

ALTER TABLE fields
  DROP CONSTRAINT IF EXISTS fields_processing_status_check;

ALTER TABLE fields
  ADD CONSTRAINT fields_processing_status_check
  CHECK (processing_status IN ('idle', 'processing', 'ready', 'failed'));

CREATE INDEX IF NOT EXISTS fields_processing_status_idx ON fields (processing_status)
  WHERE processing_status = 'processing';

COMMENT ON COLUMN fields.processing_status IS 'idle | processing | ready | failed — satellite analysis lifecycle';
