PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS games (
 id TEXT PRIMARY KEY, platform TEXT NOT NULL CHECK(platform IN ('wechat','douyin','app')),
 primary_source TEXT NOT NULL, source_game_id TEXT NOT NULL, name TEXT NOT NULL,
 publisher TEXT, official_url TEXT, icon_url TEXT, art_tags TEXT NOT NULL DEFAULT '[]',
 genre_tags TEXT NOT NULL DEFAULT '[]', identity_status TEXT NOT NULL,
 metadata_date TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(primary_source,platform,source_game_id)
);
CREATE TABLE IF NOT EXISTS game_source_ids (
 source TEXT NOT NULL, platform TEXT NOT NULL, source_game_id TEXT NOT NULL,
 game_id TEXT NOT NULL REFERENCES games(id), source_url TEXT, mapping_evidence TEXT NOT NULL,
 PRIMARY KEY(source,platform,source_game_id)
);
CREATE TABLE IF NOT EXISTS data_sources (
 source_name TEXT PRIMARY KEY, display_name TEXT NOT NULL, official_url TEXT NOT NULL,
 access_type TEXT NOT NULL, status TEXT NOT NULL, platforms TEXT NOT NULL, metrics TEXT NOT NULL,
 coverage_depth INTEGER, granularity TEXT NOT NULL, last_source_update TEXT,
 last_successful_sync TEXT, last_attempt_at TEXT, cost_note TEXT NOT NULL,
 permission_note TEXT NOT NULL, permission_status TEXT NOT NULL,
 automatic_sync_allowed INTEGER NOT NULL DEFAULT 0 CHECK(automatic_sync_allowed=0)
);
CREATE TABLE IF NOT EXISTS raw_documents (
 id TEXT PRIMARY KEY, sha256 TEXT UNIQUE NOT NULL, file_name TEXT NOT NULL,
 relative_path TEXT NOT NULL, byte_count INTEGER NOT NULL, imported_at TEXT NOT NULL,
 source TEXT NOT NULL, access_method TEXT NOT NULL, usage_scope TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshot_batches (
 id TEXT PRIMARY KEY, source TEXT NOT NULL REFERENCES data_sources(source_name),
 platform TEXT NOT NULL CHECK(platform IN ('wechat','douyin')), rank_type TEXT NOT NULL,
 data_date TEXT NOT NULL, fetched_at TEXT NOT NULL, imported_at TEXT NOT NULL,
 source_updated_at TEXT, coverage_depth INTEGER NOT NULL CHECK(coverage_depth>0),
 coverage_complete INTEGER NOT NULL CHECK(coverage_complete IN (0,1)),
 definition_version TEXT NOT NULL, snapshot_status TEXT NOT NULL CHECK(snapshot_status='ok'),
 source_url TEXT NOT NULL, raw_document_id TEXT NOT NULL REFERENCES raw_documents(id),
 content_hash TEXT NOT NULL, revision INTEGER NOT NULL, revision_of TEXT REFERENCES snapshot_batches(id),
 UNIQUE(source,platform,rank_type,data_date,content_hash),
 UNIQUE(source,platform,rank_type,data_date,revision)
);
CREATE TABLE IF NOT EXISTS ranking_snapshots (
 id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES snapshot_batches(id), source TEXT NOT NULL,
 platform TEXT NOT NULL, rank_type TEXT NOT NULL, game_id TEXT NOT NULL REFERENCES games(id),
 rank_position INTEGER NOT NULL CHECK(rank_position>0), data_date TEXT NOT NULL,
 fetched_at TEXT NOT NULL, coverage_depth INTEGER NOT NULL, snapshot_status TEXT NOT NULL,
 source_url TEXT NOT NULL, raw_record_ref TEXT NOT NULL, raw_record_json TEXT NOT NULL,
 UNIQUE(batch_id,game_id), UNIQUE(batch_id,rank_position)
);
CREATE TABLE IF NOT EXISTS sync_logs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, started_at TEXT NOT NULL,
 finished_at TEXT NOT NULL, result TEXT NOT NULL CHECK(result IN ('success','no_change','failed','blocked')),
 records_received INTEGER NOT NULL, records_saved INTEGER NOT NULL, batch_id TEXT REFERENCES snapshot_batches(id),
 error_summary TEXT, file_name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS archived_assets (
 id TEXT PRIMARY KEY, game_id TEXT NOT NULL REFERENCES games(id), legacy_case_id TEXT NOT NULL,
 kind TEXT NOT NULL, relative_path TEXT NOT NULL, sha256 TEXT NOT NULL, byte_count INTEGER NOT NULL,
 source_url TEXT NOT NULL, rights_status TEXT NOT NULL, evidence_type TEXT
);
CREATE INDEX IF NOT EXISTS snapshot_game_dates ON ranking_snapshots(game_id,data_date);
CREATE INDEX IF NOT EXISTS batch_selection ON snapshot_batches(source,platform,rank_type,data_date,revision);
CREATE TRIGGER IF NOT EXISTS protect_snapshot_update BEFORE UPDATE ON ranking_snapshots BEGIN SELECT RAISE(ABORT,'Ranking observations are immutable'); END;
CREATE TRIGGER IF NOT EXISTS protect_snapshot_delete BEFORE DELETE ON ranking_snapshots BEGIN SELECT RAISE(ABORT,'Ranking observations are immutable'); END;
CREATE TRIGGER IF NOT EXISTS protect_batch_update BEFORE UPDATE ON snapshot_batches BEGIN SELECT RAISE(ABORT,'Snapshot batches are immutable'); END;
CREATE TRIGGER IF NOT EXISTS protect_batch_delete BEFORE DELETE ON snapshot_batches BEGIN SELECT RAISE(ABORT,'Snapshot batches are immutable'); END;
