from __future__ import annotations
import csv, hashlib, io, json, re, sqlite3, unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse,parse_qs

ROOT=Path(__file__).resolve().parents[1]
TZ=timezone(timedelta(hours=8))
def now(): return datetime.now(timezone.utc).isoformat()
def encode(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def identifier(source,platform,external): return 'g_'+hashlib.sha256(f'{source}|{platform}|{external}'.encode()).hexdigest()[:24]
def clean(value): return unicodedata.normalize('NFKC',str(value)).strip() if value is not None else None
class ImportRejected(ValueError): pass
def has_credentials(url):return bool(url.username or url.password or any(k.lower() in {'token','api_key','access_token','authorization','cookie','secret','session'} for k in parse_qs(url.query)))

class Store:
 def __init__(self,db_path=None):
  self.path=Path(db_path or ROOT/'data/p0.sqlite').resolve();self.path.parent.mkdir(parents=True,exist_ok=True)
  self.raw_dir=self.path.parent/'raw';self.raw_dir.mkdir(exist_ok=True)
 @contextmanager
 def connection(self):
  db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA busy_timeout=10000')
  try: yield db;db.commit()
  except Exception: db.rollback();raise
  finally: db.close()
 def initialize(self):
  with self.connection() as db:
   db.executescript((ROOT/'app/schema.sql').read_text(encoding='utf8'))
   for s in json.loads((ROOT/'config/sources.json').read_text(encoding='utf8')):
    db.execute('INSERT INTO data_sources(source_name,display_name,official_url,access_type,status,platforms,metrics,coverage_depth,granularity,cost_note,permission_note,permission_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(source_name) DO UPDATE SET display_name=excluded.display_name,official_url=excluded.official_url,access_type=excluded.access_type,platforms=excluded.platforms,metrics=excluded.metrics,coverage_depth=excluded.coverage_depth,granularity=excluded.granularity,cost_note=excluded.cost_note,permission_note=excluded.permission_note,permission_status=excluded.permission_status',tuple(s[k] if k not in ('platforms','metrics') else encode(s[k]) for k in ['source_name','display_name','official_url','access_type','status','platforms','metrics','coverage_depth','granularity','cost_note','permission_note','permission_status']))
 def counts(self):
  with self.connection() as db:
   return {t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['games','snapshot_batches','ranking_snapshots','sync_logs','archived_assets']}|{'market_games':db.execute("SELECT count(*) FROM games WHERE platform IN ('wechat','douyin')").fetchone()[0],'visual_reference_games':db.execute("SELECT count(*) FROM games WHERE platform='app'").fetchone()[0]}
 def parse(self,content,file_name):
  if len(content)>5*1024*1024:raise ImportRejected('文件超过5MB限制')
  try: text=content.decode('utf-8-sig')
  except UnicodeDecodeError as exc:raise ImportRejected('请使用UTF-8编码的CSV或JSON') from exc
  try:
   if file_name.lower().endswith('.json'):
    document=json.loads(text)
   elif file_name.lower().endswith('.csv'):
    reader=csv.DictReader(io.StringIO(text));items=list(reader)
    if not items:raise ImportRejected('CSV没有数据行')
    metadata=['source','platform','rank_type','data_date','fetched_at','source_updated_at','coverage_depth','coverage_complete','definition_version','source_url','access_method','usage_scope']
    for item in items:
     if any(item.get(k)!=items[0].get(k) for k in metadata):raise ImportRejected('一个CSV只能包含同源、同平台、同榜、同日期的数据')
    document={k:items[0].get(k) for k in metadata};document['schemaVersion']=1
    document['coverage_depth']=int(document['coverage_depth'])
    if str(document['coverage_complete']).lower() not in ('true','false','1','0'):raise ImportRejected('CSV覆盖完整性必须为true或false')
    document['coverage_complete']=str(document['coverage_complete']).lower() in ('true','1')
    document['source_updated_at']=document['source_updated_at'] or None
    document['rows']=[{'source_game_id':r.get('source_game_id'),'name':r.get('name'),'rank_position':int(r.get('rank_position','')),'publisher':r.get('publisher') or None,'source_url':r.get('game_source_url')} for r in items]
   else: raise ImportRejected('P0仅接受CSV和JSON文件')
  except (json.JSONDecodeError,ValueError,TypeError,KeyError) as exc:
   if isinstance(exc,ImportRejected):raise
   raise ImportRejected('文件格式错误：'+str(exc)) from exc
  return self.validate(document)
 def validate(self,d):
  if not isinstance(d,dict) or d.get('schemaVersion')!=1:raise ImportRejected('缺少有效schemaVersion=1')
  if any(k in d for k in ['simulated','synthetic','mock','revenue','spend','ctr','cpa','roi','dau']):raise ImportRejected('P0不接收模拟标记或未验证的经营／广告指标')
  if d.get('source')!='momorank':raise ImportRejected('该来源尚未验证允许的P0文件导入；不能因链接可访问就启用采集')
  if d.get('access_method') not in ['manual_visible_page_observation','reviewed_historical_import']:raise ImportRejected('P0仅接受人工核对记录或经审核的历史文件，不接受未经授权的自动采集')
  if d.get('usage_scope')!='local_internal_review_only':raise ImportRejected('当前许可范围仅限本地内部研究，不自动获得对外再发布权')
  if d.get('platform') not in ['wechat','douyin'] or d.get('rank_type')!='bestselling':raise ImportRejected('当前只验证微信／抖音畅销榜文件')
  try:
   source_date=date.fromisoformat(d['data_date']);assert source_date.isoformat()==d['data_date']
   if source_date>datetime.now(TZ).date():raise ValueError('数据日期晚于当前北京时间')
   fetched=datetime.fromisoformat(d['fetched_at'].replace('Z','+00:00'))
   if fetched.tzinfo is None:raise ValueError('采集时间必须带时区')
   if source_date>fetched.astimezone(TZ).date():raise ValueError('数据日期晚于采集日期')
   if d.get('source_updated_at'):
    updated=datetime.fromisoformat(d['source_updated_at'].replace('Z','+00:00'))
    if updated.tzinfo is None:raise ValueError('来源更新时间必须带时区')
  except (ValueError,TypeError,KeyError,AssertionError) as exc:raise ImportRejected('日期或时间字段无效：'+str(exc)) from exc
  expected='/douyin/rankings/bestseller' if d['platform']=='douyin' else '/rankings/bestseller'
  board=urlparse(d.get('source_url',''))
  if board.scheme!='https' or board.hostname!='www.momorank.com' or board.path.rstrip('/')!=expected or has_credentials(board):raise ImportRejected('平台与榜单原地址不一致，或地址含不应保存的凭据')
  if type(d.get('coverage_depth')) is not int or not 1<=d['coverage_depth']<=10:raise ImportRejected('当前只验证免费Top10，不能声称覆盖11—200名')
  if type(d.get('coverage_complete')) is not bool or not d.get('definition_version'):raise ImportRejected('必须提供覆盖完整性和榜单口径版本')
  rows=d.get('rows');limit=d['coverage_depth']
  if not isinstance(rows,list) or not 1<=len(rows)<=limit:raise ImportRejected('空列表或超出范围的数据不是有效快照')
  ids=set();ranks=set();normalized=[]
  for r in rows:
   external=clean(r.get('source_game_id'));name=clean(r.get('name'));rank=r.get('rank_position')
   if not external or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,100}',external) or not name:raise ImportRejected('缺少稳定来源ID或游戏名称；不能只按名称合并')
   if type(rank) is not int or not 1<=rank<=limit:raise ImportRejected('榜位必须为真实覆盖范围内的正整数，缺失不能填0')
   if external in ids or rank in ranks:raise ImportRejected('快照含重复游戏ID或重复榜位')
   ids.add(external);ranks.add(rank)
   u=urlparse(r.get('source_url') or '')
   expected_game=('/douyin/games/' if d['platform']=='douyin' else '/games/')+external
   if u.scheme!='https' or u.hostname!='www.momorank.com' or u.path.rstrip('/')!=expected_game or has_credentials(u):raise ImportRejected('游戏原地址与平台、来源ID不一致，或地址含凭据')
   normalized.append({'source_game_id':external,'name':name,'rank_position':rank,'publisher':clean(r.get('publisher')) or None,'source_url':r['source_url']})
  if d['coverage_complete'] and ranks!=set(range(1,limit+1)):raise ImportRejected('完整覆盖声明与实际榜位不一致')
  return {k:d.get(k) for k in ['source','platform','rank_type','data_date','fetched_at','source_updated_at','coverage_depth','coverage_complete','definition_version','source_url','access_method','usage_scope']}|{'rows':sorted(normalized,key=lambda r:r['rank_position'])}
 def import_file(self,content,file_name,declared_source='momorank'):
  started=now();file_name=Path(file_name).name
  try: d=self.parse(content,file_name)
  except Exception as exc:
   result='blocked' if isinstance(exc,ImportRejected) and any(w in str(exc) for w in ['允许','授权','许可','范围仅限']) else 'failed'
   with self.connection() as db:
    db.execute('INSERT INTO sync_logs(source,started_at,finished_at,result,records_received,records_saved,error_summary,file_name) VALUES(?,?,?,?,0,0,?,?)',(declared_source,started,now(),result,str(exc),file_name))
    db.execute('UPDATE data_sources SET last_attempt_at=?,status=? WHERE source_name=?',(started,'sync_failed',declared_source))
   raise ImportRejected(str(exc)) from exc
  digest=hashlib.sha256(content).hexdigest();raw_id='raw_'+digest[:24];raw_path=self.raw_dir/(digest+('.csv' if file_name.lower().endswith('.csv') else '.json'))
  raw_path.write_bytes(content)
  identity_fields={k:d[k] for k in ['source','platform','rank_type','data_date','coverage_depth','coverage_complete','definition_version']}
  facts=[{k:r[k] for k in ['source_game_id','name','rank_position','publisher']} for r in d['rows']]
  fingerprint=hashlib.sha256(encode(identity_fields|{'rows':facts}).encode()).hexdigest();batch_id='batch_'+fingerprint[:28]
  try:
   with self.connection() as db:
    db.execute('BEGIN IMMEDIATE')
    db.execute('INSERT OR IGNORE INTO raw_documents VALUES(?,?,?,?,?,?,?,?,?)',(raw_id,digest,file_name,raw_path.name,len(content),now(),d['source'],d['access_method'],d['usage_scope']))
    existing=db.execute('SELECT id FROM snapshot_batches WHERE id=?',(batch_id,)).fetchone()
    saved=0
    if not existing:
     previous=db.execute('SELECT id,revision FROM snapshot_batches WHERE source=? AND platform=? AND rank_type=? AND data_date=? ORDER BY revision DESC LIMIT 1',(d['source'],d['platform'],d['rank_type'],d['data_date'])).fetchone()
     revision=previous['revision']+1 if previous else 1
     db.execute('INSERT INTO snapshot_batches VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(batch_id,d['source'],d['platform'],d['rank_type'],d['data_date'],d['fetched_at'],now(),d['source_updated_at'],d['coverage_depth'],int(d['coverage_complete']),d['definition_version'],'ok',d['source_url'],raw_id,fingerprint,revision,previous['id'] if previous else None))
     for index,r in enumerate(d['rows']):
      game_id=identifier(d['source'],d['platform'],r['source_game_id']);stamp=now()
      db.execute('INSERT INTO games(id,platform,primary_source,source_game_id,name,publisher,identity_status,metadata_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=CASE WHEN excluded.metadata_date>=games.metadata_date THEN excluded.name ELSE games.name END,publisher=CASE WHEN excluded.metadata_date>=games.metadata_date THEN excluded.publisher ELSE games.publisher END,metadata_date=max(games.metadata_date,excluded.metadata_date),updated_at=excluded.updated_at',(game_id,d['platform'],d['source'],r['source_game_id'],r['name'],r['publisher'],'source_id_confirmed',d['data_date'],stamp,stamp))
      db.execute('INSERT OR IGNORE INTO game_source_ids VALUES(?,?,?,?,?,?)',(d['source'],d['platform'],r['source_game_id'],game_id,r['source_url'],'平台及公开资料页ID；未按名称跨平台合并'))
      row_id=batch_id+'-'+str(index+1);ref=raw_id+'#rows/'+str(index)
      db.execute('INSERT INTO ranking_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(row_id,batch_id,d['source'],d['platform'],d['rank_type'],game_id,r['rank_position'],d['data_date'],d['fetched_at'],d['coverage_depth'],'ok',r['source_url'],ref,encode(r)));saved+=1
    result='success' if saved else 'no_change'
    db.execute('INSERT INTO sync_logs(source,started_at,finished_at,result,records_received,records_saved,batch_id,file_name) VALUES(?,?,?,?,?,?,?,?)',(d['source'],started,now(),result,len(d['rows']),saved,batch_id,file_name))
    db.execute('UPDATE data_sources SET status=?,last_attempt_at=?,last_successful_sync=?,last_source_update=? WHERE source_name=?',('manual_import_verified',started,now(),d['source_updated_at'],d['source']))
   return {'result':result,'records_received':len(d['rows']),'records_saved':saved,'batch_id':batch_id,'raw_document_id':raw_id}
  except Exception as exc:
   with self.connection() as db:
    db.execute('INSERT INTO sync_logs(source,started_at,finished_at,result,records_received,records_saved,error_summary,file_name) VALUES(?,?,?,\'failed\',?,0,?,?)',(d['source'],started,now(),len(d['rows']),str(exc),file_name))
    db.execute('UPDATE data_sources SET last_attempt_at=?,status=? WHERE source_name=?',(started,'sync_failed',d['source']))
   raise ImportRejected('保存失败，旧快照保留：'+str(exc)) from exc
 def latest_batches(self,platform=None):
  with self.connection() as db:
   rows=db.execute('SELECT * FROM (SELECT b.*,ROW_NUMBER() OVER(PARTITION BY source,platform,rank_type ORDER BY data_date DESC,revision DESC) AS position FROM snapshot_batches b) WHERE position=1 ORDER BY platform').fetchall()
   return [dict(r) for r in rows if not platform or r['platform']==platform]
 def history(self,game_id,source='momorank',rank_type='bestselling'):
  with self.connection() as db:
   game=db.execute('SELECT * FROM games WHERE id=?',(game_id,)).fetchone()
   if not game:return None
   batches=db.execute('SELECT * FROM (SELECT b.*,ROW_NUMBER() OVER(PARTITION BY data_date ORDER BY revision DESC) AS position FROM snapshot_batches b WHERE source=? AND platform=? AND rank_type=?) WHERE position=1 ORDER BY data_date',(source,game['platform'],rank_type)).fetchall();points=[]
   for b in batches:
    row=db.execute('SELECT * FROM ranking_snapshots WHERE batch_id=? AND game_id=?',(b['id'],game_id)).fetchone()
    points.append({'date':b['data_date'],'rank':row['rank_position'] if row else None,'status':'ok' if row else 'not_observed_in_current_coverage','batch_id':b['id'],'row_id':row['id'] if row else None,'raw_record_ref':row['raw_record_ref'] if row else None,'source_url':row['source_url'] if row else b['source_url'],'fetched_at':b['fetched_at'],'source_updated_at':b['source_updated_at'],'coverage_depth':b['coverage_depth'],'coverage_complete':bool(b['coverage_complete']),'definition_version':b['definition_version'],'revision':b['revision']})
   comparison={'delta':None,'reason':'暂无相邻可比较记录','previous':None,'current':points[-1] if points else None}
   if len(points)>=2:
    a,b=points[-2:];comparable=(date.fromisoformat(b['date'])-date.fromisoformat(a['date'])).days==1 and a['rank'] is not None and b['rank'] is not None and a['coverage_complete'] and b['coverage_complete'] and a['coverage_depth']==b['coverage_depth'] and a['definition_version']==b['definition_version']
    comparison={'delta':a['rank']-b['rank'] if comparable else None,'reason':'前一日榜位减当前榜位；正数代表改善' if comparable else '缺测、口径变化、范围变化或未在覆盖范围观测到','previous':a,'current':b}
   return {'game':dict(game),'points':points,'comparison':comparison,'source':source,'rank_type':rank_type}
 def market(self,platform=None):
  boards=[]
  for batch in self.latest_batches(platform):
   with self.connection() as db:rows=[dict(r) for r in db.execute('SELECT r.*,g.name,g.publisher,g.source_game_id FROM ranking_snapshots r JOIN games g ON g.id=r.game_id WHERE r.batch_id=? ORDER BY rank_position',(batch['id'],))]
   for row in rows:row['comparison']=self.history(row['game_id'],batch['source'],batch['rank_type'])['comparison']
   boards.append({'batch':batch,'rows':rows})
  return boards
 def sources(self):
  with self.connection() as db:return [dict(r) for r in db.execute('SELECT * FROM data_sources ORDER BY CASE WHEN source_name=\'momorank\' THEN 0 ELSE 1 END,source_name')]
 def logs(self,limit=30):
  with self.connection() as db:return [dict(r) for r in db.execute('SELECT * FROM sync_logs ORDER BY id DESC LIMIT ?',(limit,))]
