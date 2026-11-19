"""Check only this local P0 server, using actual records; no external collection."""
import hashlib,http.cookiejar,json,re,sys,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:4190'
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(path):
 with opener.open(BASE+path,timeout=15) as r:return r.status,r.read()
before=json.loads(get('/health')[1]);checks=[]
for route in ['/','/?platform=wechat','/?platform=douyin','/sources','/imports','/audit','/api/market','/api/sources','/health']:
 status,body=get(route);assert status==200;checks.append({'route':route,'status':status})
market=json.loads(get('/api/market')[1]);games={r['game_id'] for b in market['boards'] for r in b['rows']};rows={r['id'] for b in market['boards'] for r in b['rows']}
for gid in games:assert get('/games/'+gid)[0]==200
for rid in rows:assert get('/records/'+rid)[0]==200
token=re.search(rb'name="csrf_token" value="([^"]+)"',get('/imports')[1]).group(1).decode()
boundary='P0-'+uuid.uuid4().hex;file=ROOT/'data/evidence/manual-recording-douyin-2026-11-19.csv'
body=(f'--{boundary}\r\nContent-Disposition: form-data; name="csrf_token"\r\n\r\n{token}\r\n--{boundary}\r\nContent-Disposition: form-data; name="reviewed"\r\n\r\nyes\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file.name}"\r\nContent-Type: text/csv\r\n\r\n').encode()+file.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
req=urllib.request.Request(BASE+'/api/import',data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
with opener.open(req,timeout=15) as r:import_result=json.load(r)
after=json.loads(get('/health')[1]);assert import_result['result']=='no_change' and import_result['records_saved']==0
assert before['counts']['ranking_snapshots']==after['counts']['ranking_snapshots']==30
assert before['counts']['snapshot_batches']==after['counts']['snapshot_batches']==3
report={'routes':checks,'live_game_pages_checked':len(games),'live_raw_record_pages_checked':len(rows),'repeat_actual_csv':import_result,'counts_after':after['counts'],'sqlite_integrity':after['integrity'],'browser_upload_check':'Interrupted by browser session loss; not claimed passed. Real multipart CSV upload passed over localhost HTTP.'}
(ROOT/'docs/LIVE_CHECKS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False))
