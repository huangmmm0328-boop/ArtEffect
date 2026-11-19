"""Append-only curated public evidence, separate from daily ranking observations."""
from pathlib import Path
import hashlib,json,re
from datetime import date
from .store import ROOT,encode,now,clean,ImportRejected

SCHEMA='''CREATE TABLE IF NOT EXISTS research_documents(id TEXT PRIMARY KEY,kind TEXT NOT NULL,document_key TEXT NOT NULL,content_sha256 TEXT NOT NULL,payload TEXT NOT NULL,imported_at TEXT NOT NULL,UNIQUE(kind,document_key,content_sha256));
CREATE INDEX IF NOT EXISTS research_doc_selection ON research_documents(kind,document_key,imported_at);
CREATE TRIGGER IF NOT EXISTS protect_research_update BEFORE UPDATE ON research_documents BEGIN SELECT RAISE(ABORT,'Research evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS protect_research_delete BEFORE DELETE ON research_documents BEGIN SELECT RAISE(ABORT,'Research evidence is append-only'); END;'''
def initialize(store):
 if getattr(store,'_research_initialized',False):return
 with store.connection() as db:db.executescript(SCHEMA)
 store._research_initialized=True
def documents(store,kind):
 initialize(store)
 with store.connection() as db:return [json.loads(r['payload']) for r in db.execute('SELECT * FROM (SELECT d.*,ROW_NUMBER() OVER(PARTITION BY document_key ORDER BY rowid DESC) AS n FROM research_documents d WHERE kind=?) WHERE n=1 ORDER BY document_key',(kind,))]
def import_pack(store,path=None):
 path=Path(path or ROOT/'config/research-pack.json');pack=json.loads(path.read_text(encoding='utf8'));initialize(store)
 if pack.get('schemaVersion')!=1 or pack.get('usageScope')!='local_internal_review_only':raise ImportRejected('研究包用途或版本无效')
 for m in pack['monthly']:
  if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',m['sourceMonth']) or m['sourceMonth']>date.today().isoformat()[:7]:raise ImportRejected('无效研究期月')
  if m['dataType']!='third_party_published_monthly_ranking' or m['seriesId']!='gamekezhan_gravity_monthly':raise ImportRejected('不同来源口径不能拼成同一月度序列')
  if m['platform'] not in ['wechat','douyin'] or not m.get('sourceUrl'):raise ImportRejected('缺少平台或来源')
  if type(m.get('coverageDepth')) is not int or not m['coverageComplete'] or sorted(r['rank'] for r in m['rows'])!=list(range(1,m['coverageDepth']+1)):raise ImportRejected('月榜覆盖不完整，不能假装完整Top30')
  if len({clean(r['name']) for r in m['rows']})!=len(m['rows']):raise ImportRejected('月榜名称重复')
 for g in pack['cases']:
  for a in g['assets']:
   p=(ROOT/a['localPath']).resolve()
   if not p.is_relative_to((ROOT/'data/research-expansion').resolve()):raise ImportRejected('素材路径越界')
   if not a['reviewed'] or a['evidenceType'] not in ['publisher_publicity','official_case_capture']:raise ImportRejected('新增素材缺少人工核验或类型错误')
   if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()!=a['sha256']:raise ImportRejected('素材校验值不一致')
 entries=[('meta',{'id':'pack','reviewedAt':pack['reviewedAt'],'method':pack['method'],'usageScope':pack['usageScope'],'excludedSources':pack['excludedSources'],'candidateDatasets':pack['candidateDatasets']})]
 for key,kind in [('sources','source'),('monthly','monthly'),('cases','case'),('reports','report'),('directions','direction')]:entries += [(kind,d) for d in pack[key]]
 saved=0
 with store.connection() as db:
  for kind,d in entries:
   digest=hashlib.sha256(encode(d).encode()).hexdigest();key=d['id'];ident=kind+'-'+key+'-'+digest[:20]
   saved+=db.execute('INSERT OR IGNORE INTO research_documents VALUES(?,?,?,?,?,?)',(ident,kind,key,digest,encode(d),now())).rowcount
 return {'received':len(entries),'saved':saved,'daily_snapshots_unchanged':True}
def assets(store):return [a for g in documents(store,'case') for a in g['assets']]
def source_entries(store):
 initialize(store)
 result=[]
 for kind in ['source','report']:
  for s in documents(store,kind):
   with store.connection() as db:stamp=db.execute('SELECT MAX(imported_at) FROM research_documents WHERE kind=? AND document_key=?',(kind,s['id'])).fetchone()[0]
   result.append({'id':s['id'],'name':s.get('title',s['id']),'url':s['sourceUrl'],'kind':'research','integrationStatus':'manual_import','allowedScope':'人工核对公开研究资料；非自动API。'+s.get('relationship',s.get('method','')),'note':'发布期：'+s.get('publicationDate','未披露')+'；公开阅读不代表无限转载。','lastImportedAt':stamp})
 return result
def public_asset(a):
 p=ROOT/a['localPath'];url='assets/research/'+a['id']+'.jpg' if p.is_file() else a['remoteUrl']
 return {'id':a['id'],'url':url,'title':a['title'],'sourceUrl':a['sourceUrl'],'sourceName':a['label'],'evidenceLabel':a['label'],'evidenceType':a['evidenceType'],'collectedAt':'2026-11-19','rightsStatus':'pending','kind':'source_image'}
def merged_games(store,original):
 result=json.loads(json.dumps(original));by_id={g['id']:g for g in result['games']}
 for case in documents(store,'case'):
  g=by_id.get(case['id'])
  if not g:
   g={'id':case['id'],'name':case['name'],'aliases':[],'platforms':['douyin'] if case['visualVersionConfirmed'] else ['app'],'type':case['type'],'style':case['style'],'publisher':case['publisher'] or '来源未披露','sourceUrl':case['sourceUrl'],'summary':case['observations'][0]['text'],'platformNote':case['scope'],'assets':[],'motion':[],'observations':case['observations'],'risk':'公开资料用于研究；转载授权未确认。产品具备小游戏渠道，不等于商店图就是小游戏实录。'}
   result['games'].append(g);by_id[g['id']]=g
  ids={a['id'] for a in g['assets']};g['assets'] += [public_asset(a) for a in case['assets'] if a['id'] not in ids]
  if case['id'] in {x['id'] for x in original['games']}:
   titles={o['title'] for o in g.get('observations',[])}
   g.setdefault('observations',[]).extend({'title':'本轮来源观察 · '+o['title'],'text':o['text']} for o in case['observations'] if '本轮来源观察 · '+o['title'] not in titles)
  if g['assets']:g['hero']=g['assets'][0]['url']
 return result
def outlook(store,original_games):
 cases=documents(store,'case');monthly=documents(store,'monthly');reports=documents(store,'report');directions=documents(store,'direction');sources=documents(store,'source')
 if not cases or not monthly:return None
 games=merged_games(store,original_games)['games'];by_name={clean(g['name']):g for g in games};case_names={clean(c['name']) for c in cases};periods=sorted({m['sourceMonth'] for m in monthly});source_map={s['id']:s for s in sources};coverage=monthly[0]['coverageDepth'];result=[]
 for direction in directions:
  selected=[by_name[clean(n)] for n in direction['caseNames'] if clean(n) in by_name];names={clean(g['name']) for g in selected};matches=[]
  for m in monthly:
   entries=[r for r in m['rows'] if clean(r['name']) in names]
   matches.append({'month':m['sourceMonth'],'platform':m['platform'],'sourceId':m['sourceId'],'sourceUrl':m['sourceUrl'],'coverage':m['coverageDepth'],'count':len(entries),'top10':sum(r['rank']<=10 for r in entries),'rows':entries})
  active=[m for m in matches if m['count']];months=sorted({m['month'] for m in active});names_in_boards={clean(r['name']) for m in active for r in m['rows']};images=[]
  for game in selected:
   preferred=next((c for c in cases if c['id']==game['id']),None);a=public_asset(preferred['assets'][0]) if preferred else next((a for a in game['assets'] if a.get('evidenceType')=='verified_gameplay'),game['assets'][0] if game['assets'] else None)
   if a:images.append(a|{'gameId':game['id'],'gameName':game['name']})
  result.append(direction|{'cases':[{'id':g['id'],'name':g['name'],'sourceUrl':g['sourceUrl'],'imageCount':len(g['assets'])} for g in selected],'images':images[:3],'market':{'months':months,'periodCount':len(months),'caseCount':len(names_in_boards),'platforms':sorted({m['platform'] for m in active}),'appearances':sum(m['count'] for m in active),'boards':matches,'evidenceLabel':'近三个月持续出现' if len(months)>=3 and len(names_in_boards)>=2 else '已有市场案例' if active else '官方旧期创新案例，非当前畅销证据'},'confidence':'中低' if len(months)>=3 and len(names_in_boards)>=2 else '低','confidenceReason':'有跨月榜位背景与公开画面；尚缺风格因果、实际成本与对应端实录。' if active else '仅平台既有案例，不代表本月热度或未来增长。'})
 result.sort(key=lambda d:d.get('order',99))
 total_names={clean(r['name']) for m in monthly for r in m['rows']};matched={clean(g['name']) for g in games if clean(g['name']) in total_names}
 return {'schemaVersion':1,'reviewedAt':'2026-11-19','generatedAt':now(),'periods':periods,'boardCount':len(monthly),'rankingRows':sum(len(m['rows']) for m in monthly),'coverageDepth':coverage,'rankingNameCount':len(total_names),'visualReferenceNameCount':len(matched),'unclassifiedNames':len(total_names-matched),'caseCount':len(games),'newCaseCount':sum(c['id'] not in {g['id'] for g in original_games['games']} for c in cases),'newAssetCount':sum(len(c['assets']) for c in cases),'platformOfficialCaseCount':sum(c['visualVersionConfirmed'] for c in cases),'reportCount':len(reports),'summary':'轻中度项目先验证合成装饰的完成感、国风生活化与清楚的战斗反馈；体积化生存城建已有头部样本，更依赖完整内容产能。民俗与单屏创意保留小规模试验。','basis':'同口径三个月公开月平均排名＋官方产品展示＋平台案例／行业研究，人工综合判断。','directions':result,'reports':reports,'sources':sources,'monthly':monthly,'method':['月榜来自游戏客栈依据引力引擎整理的公开Top30图，是第三方月平均排名，不是官方收入。','只在同一来源口径、同平台、同覆盖范围内比较；没有把月榜补成日榜。','商店展示与平台案例分别标记；按名称关联仅提供视觉研究背景，不证明对应端版本或美术带来收入。','“中低”表示证据比单日样本更充分，并非概率或已验证准确率。成本为人工相对判断。','未分类游戏保留未知；没有从名称或玩法自动猜画风。'], 'excludedSources':documents(store,'meta')[0]['excludedSources']}
