from __future__ import annotations
import copy,hashlib,json,shutil,sys,unittest,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import create_app
from app.bootstrap import history_samples,legacy_root
from app.fusion import fused_report,sqlite_snapshots,style_reports
from app.store import Store,ImportRejected,encode

class FusionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.samples=history_samples();cls.manual=sorted((ROOT/'data/evidence').glob('momorank-*-*-*-*.json'));cls.temp_root=ROOT/'tests/.tmp';cls.temp_root.mkdir(exist_ok=True)
 def setUp(self):
  self.work=self.temp_root/('fusion-'+uuid.uuid4().hex);self.work.mkdir();self.store=Store(self.work/'fusion.sqlite');self.store.initialize()
 def tearDown(self):
  assert self.work.resolve().is_relative_to(self.temp_root.resolve()) and self.work!=self.temp_root;shutil.rmtree(self.work)
 def seed(self):
  docs=[json.loads(p.read_text(encoding='utf8')) for p in self.manual];keys={(d['platform'],d['data_date']) for d in docs}
  for d in self.samples:
   if (d['platform'],d['data_date']) not in keys:self.store.import_file(encode(d).encode(),'real-archive.json')
  for d in docs:self.store.import_file(encode(d).encode(),'real-manual.json')
 def report(self):return fused_report(self.store,'2026-11')
 def test_01_full_previous_site_and_p0_share_one_server(self):
  c=create_app(self.store.path,testing=True,integrated=True).test_client();self.assertEqual(c.get('/').location,'/site/')
  for path in ['/site/','/review','/imports','/sources','/site/intelligence-ui/app.js','/site/intelligence-ui/monthly-page.mjs','/site/intelligence-ui/fusion-panel.mjs']:self.assertEqual(c.get(path).status_code,200,path)
 def test_02_only_sqlite_verified_batches_enter_current_report(self):
  self.seed();r=self.report();self.assertEqual(r['integration']['rankingRows'],self.store.counts()['ranking_snapshots']);self.assertTrue(all(s['sourceId']=='momorank' for s in r['sources']));self.assertEqual({g['name'] for g in r['groups']} & {'彩色国风武侠'},set())
 def test_03_platform_name_matches_do_not_confirm_art_identity(self):
  self.seed();r=self.report();self.assertEqual(r['integration']['visualVersionConfirmed'],0)
  for o in r['outlook']:
   for row in o['marketEvidence']['rows']:self.assertFalse(row['visualVersionConfirmed']);self.assertEqual(row['identityStatus'],'same_title_reference_only')
 def test_04_real_positive_rank_change_has_two_immutable_records(self):
  self.seed();r=self.report();feedback=next(o for o in r['outlook'] if o['id']=='readable-feedback');row=next(x for x in feedback['marketEvidence']['rows'] if x['name']=='灵画师' and x['platform']=='douyin')
  self.assertEqual((row['previousRank'],row['rank'],row['delta']),(2,1,1));self.assertNotEqual(row['recordUrl'],row['previousRecordUrl'])
 def test_05_real_fall_restricts_old_folk_hypothesis(self):
  self.seed();o=next(o for o in self.report()['outlook'] if o['id']=='mood-identity');self.assertEqual(o['marketEvidence']['falling'],1);self.assertIn('收紧',o['revisionNote']);self.assertIn('不能',o['risk']);self.assertEqual(o['confidence'],'低')
 def test_06_repeat_import_does_not_inflate_evidence_or_days(self):
  self.seed();before=self.report();self.seed();after=self.report()
  for k in ['sampleCount','observedDays','rankingTitleCount']:self.assertEqual(before[k],after[k])
  self.assertEqual(before['integration']['batchFingerprint'],after['integration']['batchFingerprint']);self.assertEqual(before['integration']['rankingRows'],after['integration']['rankingRows'])
 def test_07_rejected_file_keeps_forecast_facts_and_shows_warning(self):
  self.seed();before=self.report()
  with self.assertRaises(ImportRejected):self.store.import_file(b'{broken','invalid.json')
  after=self.report();self.assertEqual(before['summary'],after['summary']);self.assertTrue(after['integration']['lastImportFailed']);self.assertEqual(before['integration']['batchFingerprint'],after['integration']['batchFingerprint'])
 def test_08_runtime_recomputes_after_next_real_file(self):
  old,new=sorted(self.samples,key=lambda d:d['data_date']);self.store.import_file(encode(old).encode(),'real-old.json');c=create_app(self.store.path,testing=True).test_client();before=c.get('/site/data/style-reports.json').json['reports'][0]
  self.store.import_file(encode(new).encode(),'real-new.json');after=c.get('/site/data/style-reports.json').json['reports'][0];self.assertNotEqual(before['integration']['batchFingerprint'],after['integration']['batchFingerprint']);self.assertEqual((before['observedDays'],after['observedDays']),(1,2))
 def test_09_missing_and_unclassified_never_become_zero_rank(self):
  self.seed();r=self.report();self.assertEqual(r['sampleCount']+r['unclassifiedTitleCount'],r['rankingTitleCount']);self.assertEqual(sum(g['count'] for g in r['groups']),r['sampleCount']);self.assertTrue(all(row['rank']>0 for s in sqlite_snapshots(self.store) for row in s['rows']))
 def test_10_previous_month_stays_its_original_archive(self):
  self.seed();reports=style_reports(self.store)['reports'];october=next(r for r in reports if r['month']=='2026-10');self.assertTrue(october['legacyArchive']);self.assertEqual(october['basis'],'published_monthly_ranking');self.assertNotIn('integration',october)
 def test_11_all_original_media_references_preserve_bytes(self):
  if not (legacy_root()/'site/assets').exists():self.skipTest('Original packed assets must be unpacked for binary media verification; production archives remain unchanged')
  c=create_app(self.store.path,testing=True).test_client();inventory=json.loads((ROOT/'docs/asset-inventory.json').read_text(encoding='utf8'))
  for asset in inventory['entries']:
   response=c.get('/site/'+asset['path']);self.assertEqual(response.status_code,200,asset['path']);self.assertEqual(hashlib.sha256(response.data).hexdigest(),asset['sha256']);self.assertEqual(len(response.data),asset['bytes'])
 def test_12_private_database_and_sources_are_not_static_files(self):
  c=create_app(self.store.path,testing=True).test_client()
  for path in ['/site/data/p0.sqlite','/site/data/evidence/secret.json','/site/app/fusion.py','/site/../data/p0.sqlite']:self.assertEqual(c.get(path).status_code,404)
 def test_13_confidence_stays_low_and_same_title_samples_are_unique(self):
  self.seed();r=self.report();ids=[i for g in r['groups'] for i in g['sampleIds']];self.assertEqual(len(ids),len(set(ids)));self.assertTrue(all(o['confidence']=='低' for o in r['outlook']));self.assertLessEqual(r['observedDays'],2)
 def test_14_coverage_change_blocks_short_term_style_signal(self):
  old,new=sorted(self.samples,key=lambda d:d['data_date']);self.store.import_file(encode(old).encode(),'real-old.json');d=copy.deepcopy(new);d['rows']=d['rows'][:5];d['coverage_depth']=5;self.store.import_file(encode(d).encode(),'real-subset.json');r=self.report()
  for o in r['outlook']:self.assertEqual(o['marketEvidence']['comparable'],0)

if __name__=='__main__':unittest.main()
