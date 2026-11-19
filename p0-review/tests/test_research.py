from pathlib import Path
import copy,hashlib,json,shutil,sqlite3,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import create_app
from app.store import Store,ImportRejected,encode
from app.bootstrap import history_samples
from app.research import import_pack,documents,merged_games,outlook
from app.fusion import legacy_data

class PublicResearchTests(unittest.TestCase):
 def setUp(self):
  self.temp=ROOT/'tests/.tmp'/('public-'+uuid.uuid4().hex);self.temp.mkdir(parents=True);self.store=Store(self.temp/'test.sqlite');self.store.initialize();self.pack=json.loads((ROOT/'config/research-pack.json').read_text(encoding='utf8'))
 def tearDown(self):
  assert self.temp.resolve().is_relative_to((ROOT/'tests/.tmp').resolve());shutil.rmtree(self.temp)
 def load(self):return import_pack(self.store)
 def test_01_monthly_facts_do_not_fabricate_daily_history(self):
  for d in history_samples():self.store.import_file(encode(d).encode(),'actual-existing-archive.json')
  before=self.store.counts();self.load();self.assertEqual(before['ranking_snapshots'],self.store.counts()['ranking_snapshots']);self.assertEqual(sum(len(m['rows']) for m in documents(self.store,'monthly')),180)
 def test_02_repeat_is_idempotent(self):
  first=self.load();second=self.load();self.assertGreater(first['saved'],0);self.assertEqual(second['saved'],0)
 def test_03_six_same_series_boards_cover_two_platforms_three_months(self):
  self.load();data=documents(self.store,'monthly');self.assertEqual(len(data),6);self.assertEqual({(m['platform'],m['sourceMonth']) for m in data},{(p,m) for p in ['wechat','douyin'] for m in ['2026-08','2026-09','2026-10']})
  for m in data:self.assertEqual(sorted(r['rank'] for r in m['rows']),list(range(1,31)));self.assertEqual(m['seriesId'],'gamekezhan_gravity_monthly');self.assertTrue(m['sourceUrl'])
 def test_04_conflicting_reports_and_unlicensed_history_are_not_in_series(self):
  self.load();sources={s['id'] for s in documents(self.store,'source')};self.assertEqual(len(sources),3)
  for m in documents(self.store,'monthly'):self.assertIn(m['sourceId'],sources);self.assertNotIn('github',m['sourceUrl'])
 def test_05_new_material_types_are_not_relabelled_gameplay(self):
  self.load();data=documents(self.store,'case');self.assertEqual(len(data),11);assets=[a for c in data for a in c['assets']];self.assertEqual(len(assets),27);self.assertEqual(sum(a['evidenceType']=='publisher_publicity' for a in assets),24);self.assertEqual(sum(a['evidenceType']=='official_case_capture' for a in assets),3);self.assertFalse(any(a['evidenceType']=='verified_gameplay' for a in assets))
 def test_06_original_library_and_gifs_preserved(self):
  self.load();old=legacy_data('games.json');new=merged_games(self.store,old);self.assertEqual(len(new['games']),19);index={g['id']:g for g in new['games']}
  for g in old['games']:self.assertEqual(index[g['id']]['motion'],g['motion']);self.assertTrue({a['id'] for a in g['assets']}<={a['id'] for a in index[g['id']]['assets']})
 def test_07_source_and_period_visible_in_every_research_report(self):
  self.load()
  for p in documents(self.store,'report'):self.assertTrue(p['sourceUrl'].startswith('https://'));self.assertTrue(p['period']);self.assertTrue(p['publisher']);self.assertTrue(p['method'])
 def test_08_monthly_import_rejects_partial_coverage_without_erasing(self):
  self.load();before=len(documents(self.store,'monthly'));bad=copy.deepcopy(self.pack);bad['monthly'][0]['rows'].pop();path=self.temp/'bad.json';path.write_text(json.dumps(bad,ensure_ascii=False),encoding='utf8')
  with self.assertRaises(ImportRejected):import_pack(self.store,path)
  self.assertEqual(len(documents(self.store,'monthly')),before)
 def test_09_evidence_cannot_be_overwritten(self):
  self.load()
  with self.assertRaises(sqlite3.IntegrityError):
   with self.store.connection() as db:db.execute('DELETE FROM research_documents')
 def test_10_actual_archived_images_match_sha_and_private_files_stay_private(self):
  self.load();c=create_app(self.store.path,testing=True).test_client();checked=0
  for case in documents(self.store,'case'):
   for a in case['assets']:
    p=ROOT/a['localPath']
    if p.is_file():
     r=c.get('/site/assets/research/'+a['id']+'.jpg');self.assertEqual(r.status_code,200);self.assertEqual(hashlib.sha256(r.data).hexdigest(),a['sha256']);checked+=1
  if (ROOT/'data/research-expansion/archive').exists():self.assertEqual(checked,27)
  for path in ['/site/assets/research/../../data/p0.sqlite','/site/data/research-pack.json']:self.assertEqual(c.get(path).status_code,404)
 def test_11_research_scope_does_not_claim_complete_visual_coverage(self):
  self.load();r=outlook(self.store,legacy_data('games.json'));self.assertEqual(r['rankingNameCount'],56);self.assertEqual(r['visualReferenceNameCount'],15);self.assertEqual(r['unclassifiedNames'],41);self.assertEqual(r['platformOfficialCaseCount'],3);self.assertEqual(r['newAssetCount'],27)
 def test_12_early_platform_cases_are_not_current_bestsellers(self):
  self.load();r=outlook(self.store,legacy_data('games.json'));d=next(d for d in r['directions'] if d['id']=='tactile-creative');self.assertEqual(d['market']['appearances'],0);self.assertEqual(d['confidence'],'低')
 def test_13_audience_report_is_general_not_single_game_survey(self):
  self.load();c=create_app(self.store.path,testing=True).test_client();r=c.get('/site/data/audience.json').json;report=next(p for p in r['reports'] if p['id']=='ocean-audience-2026');self.assertIn('非单游戏',report['scope']);self.assertEqual(sum(f['kind']=='survey' for f in r['findings']),0)
 def test_14_same_local_bundle_updates_games_and_future(self):
  c=create_app(self.store.path,testing=True).test_client();self.assertIsNone(c.get('/site/data/style-reports.json').json['research']);self.load();self.assertEqual(c.get('/site/data/style-reports.json').json['research']['rankingRows'],180);self.assertEqual(len(c.get('/site/data/games.json').json['games']),19)
 def test_15_manual_public_sources_have_real_import_status_not_api_claims(self):
  self.load();c=create_app(self.store.path,testing=True).test_client();sources=c.get('/site/data/sources.json').json['sources'];health=c.get('/site/data/health.json').json['sources'];research=[s for s in sources if s['kind']=='research'];self.assertEqual(len(research),6)
  for s in research:
   h=next(h for h in health if h['sourceId']==s['id']);self.assertEqual(h['status'],'manual_import');self.assertTrue(h['lastSuccessAt']);self.assertIn('非自动API',s['allowedScope'])

if __name__=='__main__':unittest.main()
