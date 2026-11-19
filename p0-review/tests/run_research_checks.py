from pathlib import Path
import io,json,sys,time,unittest
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from run_checks import Results
pattern='test_research.py' if '--research-only' in sys.argv else 'test_*.py'
stream=io.StringIO();start=time.monotonic();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern);result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Results).run(suite)
report={'scope':'Public research expansion plus regression checks','executed_at':datetime.now(timezone.utc).isoformat(),'tests_run':result.testsRun,'passed':len([v for v in result.outcomes if v['result']=='passed']),'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'successful':result.wasSuccessful(),'seconds':round(time.monotonic()-start,3),'outcomes':result.outcomes}
(ROOT/'docs/RESEARCH_TEST_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(ROOT/'docs/research-test-run.txt').write_text(stream.getvalue(),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='outcomes'}));sys.exit(0 if result.wasSuccessful() else 1)
