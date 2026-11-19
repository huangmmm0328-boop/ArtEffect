from __future__ import annotations
import io,json,sys,time,unittest
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from run_checks import Results
if __name__=='__main__':
 pattern='test_fusion.py' if '--fusion-only' in sys.argv else 'test_*.py'
 suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern);stream=io.StringIO();started=time.monotonic();result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Results).run(suite)
 report={'scope':'Authorized integration of existing site and SQLite-backed forecast evidence; no production deployment','executed_at':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-started,3),'tests_run':result.testsRun,'passed':len([o for o in result.outcomes if o['result']=='passed']),'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'successful':result.wasSuccessful(),'outcomes':result.outcomes,'data':'Actual archived observations; fault injection confined to temporary databases'}
 (ROOT/'docs/FUSION_TEST_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(ROOT/'docs/fusion-test-run.txt').write_text(stream.getvalue(),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='outcomes'},ensure_ascii=False));sys.exit(0 if result.wasSuccessful() else 1)
