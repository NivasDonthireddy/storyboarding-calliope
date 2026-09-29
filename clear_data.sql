-- SQLite: permanently delete all rows from every application table.
-- Back up the selected playground.db and stop the API/demos before running.
-- Run the entire script with no active transaction, stopping on any error.
-- If a run fails or is cancelled after BEGIN (including at an IDE delete prompt),
-- execute ROLLBACK; separately in the SAME console/connection before rerunning.
-- Approve the intended full-table DELETE prompts and let the run reach COMMIT.
-- Table definitions and files on disk are preserved; AUTOINCREMENT counters reset.

PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

-- Delete dependent rows before their referenced parents.
DELETE FROM agent_events;
DELETE FROM agent_sessions;
DELETE FROM jobs;
DELETE FROM scene_characters;
DELETE FROM clips;
DELETE FROM scenes;
DELETE FROM story_beats;
DELETE FROM characters;
DELETE FROM locations;
DELETE FROM projects;

DELETE FROM sqlite_sequence;
COMMIT;
