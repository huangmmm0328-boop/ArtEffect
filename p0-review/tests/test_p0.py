from __future__ import annotations
import copy,io,json,re,sqlite3,sys,uuid,unittest,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import create_app,chart_points
from app.bootstrap import history_samples,to_csv
from app.store import Store,ImportRejected,identifier,encode

class P0Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.samples={d['data_date']:d for d in history_samples()}
  if not {'2026-11-18','2026-11-19'}<=cls.samples.keys():raise RuntimeError('Tests require the real archived MomoRank observations, not generated fixtures')
  cls.temp_root=ROOT/'tests/.tmp';cls.temp_root.mkdir(parents=True,exist_ok=True)
 def setUp(self):
  self.work=(self.temp_root/('p0-'+uuid.uuid4().hex)).resolve();self.work.mkdir();self.store=Store(self.work/'test.sqlite');self.store.initialize()
  self.old=copy.deepcopy(self.samples['2026-11-18']);self.new=copy.deepcopy(self.samples['2026-11-19'])
 def tearDown(self):
  assert self.work.is_relative_to(self.temp_root.resolve()) and self.work!=self.temp_root.resolve()
  shutil.rmtree(self.work)
 def load(self,d=None,name='real-observation.json'):
  return self.store.import_file(encode(d or self.new).encode('utf8'),name)
 def test_01_real_archive_import_and_integrity(self):
  r=self.load();self.assertEqual(r['records_saved'],10)
  with self.store.connection() as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_02_repeated_json_does_not_duplicate_snapshot(self):
  self.load();before=self.store.counts();r=self.load();self.assertEqual(r['result'],'no_change');self.assertEqual(r['records_saved'],0);self.assertEqual(self.store.counts()['ranking_snapshots'],before['ranking_snapshots']);self.assertEqual(self.store.counts()['snapshot_batches'],1)
 def test_03_csv_json_same_facts_are_idempotent(self):
  self.load();r=self.store.import_file(to_csv(self.new),'actual-records.csv');self.assertEqual(r['records_saved'],0);self.assertEqual(self.store.counts()['ranking_snapshots'],10)
 def test_04_csv_can_start_a_real_database(self):
  r=self.store.import_file(to_csv(self.new),'actual-records.csv');self.assertEqual(r['records_saved'],10);self.assertEqual(self.store.latest_batches()[0]['data_date'],'2026-11-19')
 def test_05_failed_file_keeps_previous_rows_and_success_time(self):
  self.load();before=self.store.counts();success=self.store.sources()[0]['last_successful_sync']
  with self.assertRaises(ImportRejected):self.store.import_file(b'{broken-json','broken.json')
  self.assertEqual(self.store.counts()['ranking_snapshots'],before['ranking_snapshots']);self.assertEqual(len(self.store.market()[0]['rows']),10);self.assertEqual(self.store.sources()[0]['last_successful_sync'],success);self.assertEqual(self.store.logs()[0]['result'],'failed')
 def test_06_real_rank_improvement_and_original_records(self):
  self.load(self.old);self.load(self.new);h=self.store.history(identifier('momorank','douyin','496'))
  self.assertEqual(h['game']['name'],'灵画师');self.assertEqual([p['rank'] for p in h['points']],[2,1]);self.assertEqual(h['comparison']['delta'],1);self.assertNotEqual(h['comparison']['previous']['raw_record_ref'],h['comparison']['current']['raw_record_ref'])
 def test_07_only_one_day_has_no_line_or_change(self):
  self.load();h=self.store.history(identifier('momorank','douyin','496'));self.assertIsNone(h['comparison']['delta']);self.assertEqual(chart_points(h['points'])['segments'],[]);self.assertEqual(len(chart_points(h['points'])['dots']),1)
 def test_08_top10_rejects_claimed_top200(self):
  d=copy.deepcopy(self.new);d['coverage_depth']=200
  with self.assertRaises(ImportRejected):self.load(d)
  self.assertEqual(self.store.counts()['ranking_snapshots'],0)
 def test_09_zero_is_not_a_missing_rank(self):
  d=copy.deepcopy(self.new);d['rows'][0]['rank_position']=0
  with self.assertRaises(ImportRejected):self.load(d)
 def test_10_platform_identity_separation_uses_real_external_ids(self):
  # Both IDs were checked on the public pages: wx /games/1, dy /douyin/games/491.
  self.assertNotEqual(identifier('momorank','wechat','1'),identifier('momorank','douyin','491'))
  self.assertNotEqual(identifier('momorank','wechat','491'),identifier('momorank','douyin','491'))
 def test_11_wrong_platform_url_is_rejected(self):
  d=copy.deepcopy(self.new);d['platform']='wechat'
  with self.assertRaises(ImportRejected):self.load(d)
 def test_12_fetch_time_never_replaces_source_date(self):
  self.load(self.old);b=self.store.latest_batches()[0];self.assertEqual(b['data_date'],'2026-11-18');self.assertEqual(b['fetched_at'],self.old['fetched_at']);self.assertIsNone(b['source_updated_at'])
 def test_13_revision_keeps_both_original_batches(self):
  self.load();d=copy.deepcopy(self.new);row=next(r for r in d['rows'] if r.get('publisher'));row['publisher']=None # Controlled removal of optional data, isolated test DB only.
  self.load(d);self.assertEqual(self.store.counts()['snapshot_batches'],2);self.assertEqual(self.store.counts()['ranking_snapshots'],20)
  with self.store.connection() as db:self.assertEqual([r[0] for r in db.execute('SELECT revision FROM snapshot_batches ORDER BY revision')],[1,2])
  h=self.store.history(identifier('momorank','douyin','496'));self.assertEqual(len(h['points']),1);self.assertEqual(h['points'][0]['revision'],2)
 def test_14_immutable_rows_cannot_be_overwritten(self):
  self.load()
  with self.assertRaises(sqlite3.IntegrityError):
   with self.store.connection() as db:db.execute('UPDATE ranking_snapshots SET rank_position=rank_position')
  with self.assertRaises(sqlite3.IntegrityError):
   with self.store.connection() as db:db.execute('DELETE FROM snapshot_batches')
 def test_15_coverage_change_stops_comparison(self):
  self.load(self.old);d=copy.deepcopy(self.new);d['rows']=d['rows'][:5];d['coverage_depth']=5;self.load(d);h=self.store.history(identifier('momorank','douyin','496'));self.assertIsNone(h['comparison']['delta']);self.assertEqual(chart_points(h['points'])['segments'],[])
 def test_16_unknown_source_not_marked_connected(self):
  d=copy.deepcopy(self.new);d['source']='gravity'
  with self.assertRaises(ImportRejected):self.load(d)
  source=next(s for s in self.store.sources() if s['source_name']=='gravity');self.assertIsNone(source['last_successful_sync']);self.assertEqual(source['automatic_sync_allowed'],0)
 def test_17_no_speculative_game_without_id(self):
  d=copy.deepcopy(self.new);d['rows'][0]['source_game_id']=None
  with self.assertRaises(ImportRejected):self.load(d)
 def test_18_credential_urls_rejected(self):
  d=copy.deepcopy(self.new);d['source_url']+='?api_key=invalid-test-placeholder'
  with self.assertRaises(ImportRejected):self.load(d)
 def test_19_duplicate_ranks_rollback_entire_batch(self):
  d=copy.deepcopy(self.new);d['rows'][1]['rank_position']=d['rows'][0]['rank_position']
  with self.assertRaises(ImportRejected):self.load(d)
  self.assertEqual(self.store.counts()['games'],0)
 def test_20_unobserved_game_is_null_not_zero(self):
  self.load(self.old);self.load(self.new)
  old_ids={r['source_game_id'] for r in self.old['rows']};new_ids={r['source_game_id'] for r in self.new['rows']};removed=old_ids-new_ids;self.assertTrue(removed)
  h=self.store.history(identifier('momorank','douyin',sorted(removed)[0]));self.assertIsNone(h['points'][-1]['rank']);self.assertEqual(h['points'][-1]['status'],'not_observed_in_current_coverage');self.assertIsNone(h['comparison']['delta'])
 def test_21_api_import_requires_local_csrf_confirmation(self):
  app=create_app(self.store.path,testing=True);client=app.test_client();r=client.post('/api/import',data={'file':(io.BytesIO(encode(self.new).encode()),'real.json'),'reviewed':'yes'});self.assertEqual(r.status_code,403)
  client.get('/imports')
  with client.session_transaction() as s:token=s['_csrf']
  r=client.post('/api/import',data={'file':(io.BytesIO(encode(self.new).encode()),'real.json'),'reviewed':'yes','csrf_token':token});self.assertEqual(r.status_code,200);self.assertEqual(r.json['records_saved'],10)
 def test_22_history_page_and_evidence_links(self):
  self.load(self.old);self.load(self.new);client=create_app(self.store.path,testing=True).test_client();game_id=identifier('momorank','douyin','496');r=client.get('/games/'+game_id);self.assertEqual(r.status_code,200)
  for row_id in [p['row_id'] for p in self.store.history(game_id)['points']]:self.assertEqual(client.get('/records/'+row_id).status_code,200)
  body=r.get_data(as_text=True);self.assertIn('2026-11-18',body);self.assertIn('2026-11-19',body);self.assertIn('改善1位',body)
 def test_23_no_p1_p2_p3_functions_in_p0_navigation(self):
  self.load();client=create_app(self.store.path,testing=True).test_client();body=client.get('/').get_data(as_text=True)
  for path in ['/opportunities','/predictions','/creative','/audience']:self.assertNotIn('href="'+path+'"',body)
  self.assertEqual(client.get('/health').json['production_deployment'],False)
 def test_24_csv_mixed_dates_rejected(self):
  text=to_csv(self.new).decode('utf-8-sig');lines=text.splitlines();lines[2]=lines[2].replace('2026-11-19','2026-11-18',1)
  with self.assertRaises(ImportRejected):self.store.import_file(('\n'.join(lines)).encode(),'mixed.csv')
 def test_25_missing_date_rejected_without_capture_date_fallback(self):
  d=copy.deepcopy(self.new);d['data_date']=None
  with self.assertRaises(ImportRejected):self.load(d)
 def test_26_declared_simulation_is_never_saved(self):
  d=copy.deepcopy(self.new);d['simulated']=True
  with self.assertRaises(ImportRejected):self.load(d)

if __name__=='__main__':unittest.main(verbosity=2)
