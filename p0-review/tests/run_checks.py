"""Run actual archived-data tests and save reproducible acceptance results."""
from __future__ import annotations
import io,json,sys,time,unittest
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
class Results(unittest.TextTestResult):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.outcomes=[]
 def addSuccess(self,test):super().addSuccess(test);self.outcomes.append({'test':test.id(),'result':'passed'})
 def addFailure(self,test,err):super().addFailure(test,err);self.outcomes.append({'test':test.id(),'result':'failed'})
 def addError(self,test,err):super().addError(test,err);self.outcomes.append({'test':test.id(),'result':'error'})

if __name__=='__main__':
 stream=io.StringIO();start=time.monotonic();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
 result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Results).run(suite)
 (ROOT/'docs/test-run.txt').write_text(stream.getvalue(),encoding='utf8')
 report={'stage':'P0','executed_at':datetime.now(timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-start,3),'tests_run':result.testsRun,'passed':len([r for r in result.outcomes if r['result']=='passed']),'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),'input':'Actual archived MomoRank Douyin 2026-11-18 and 2026-11-19 observations. Fault-injection copies are isolated test inputs, never delivery records.','outcomes':result.outcomes,'production_deployment':False,'scope':'P0 only; user acceptance pending'}
 (ROOT/'docs/TEST_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='outcomes'},ensure_ascii=False));sys.exit(0 if result.wasSuccessful() else 1)
