"""Previous visual research + permitted local SQLite observations.

Name matches remain reference candidates, never confirmed platform art identities.
No network collection, numeric forecast probability, or historical backfill.
"""
from __future__ import annotations
import hashlib,json
from datetime import datetime
from pathlib import Path
from flask import Blueprint,abort,jsonify,redirect,send_from_directory
from .bootstrap import legacy_root
from .store import ROOT,TZ,clean,now

def legacy_data(name):
 return json.loads((legacy_root()/'intelligence/data'/name).read_text(encoding='utf8'))

def sqlite_snapshots(store):
 """Select latest revision per actual board/date, never mix in old unverified collectors."""
 with store.connection() as db:
  batches=db.execute('SELECT * FROM (SELECT b.*,ROW_NUMBER() OVER(PARTITION BY source,platform,rank_type,data_date ORDER BY revision DESC) AS n FROM snapshot_batches b) WHERE n=1 ORDER BY data_date,platform').fetchall()
  snapshots=[]
  for b in batches:
   rows=db.execute('SELECT r.*,g.name,g.publisher,g.source_game_id FROM ranking_snapshots r JOIN games g ON g.id=r.game_id WHERE r.batch_id=? ORDER BY rank_position',(b['id'],)).fetchall()
   # Names and publisher belong to this immutable observation, not mutable current metadata.
   entries=[]
   for row in rows:
    raw=json.loads(row['raw_record_json']);entries.append({'gameId':row['game_id'],'name':raw['name'],'rank':row['rank_position'],'publisher':raw.get('publisher'),'sourceGameId':raw['source_game_id'],'sourceUrl':row['source_url'],'recordUrl':'/records/'+row['id'],'rawRecordRef':row['raw_record_ref']})
   snapshots.append({'schemaVersion':1,'kind':'public_daily_ranking','sourceId':b['source'],'boardId':b['platform']+'-bestselling','platform':b['platform'],'sourceDate':b['data_date'],'observedAt':b['fetched_at'],'sourceUpdatedAt':b['source_updated_at'],'sourceUrl':b['source_url'],'status':'ok','coverage':{'limit':b['coverage_depth'],'complete':bool(b['coverage_complete'])},'definitionVersion':b['definition_version'],'batchId':b['id'],'revision':b['revision'],'rows':entries,'accessMethod':'reviewed_local_file_import','usageScope':'local_internal_review_only'})
 return snapshots

def _offset(month,offset):
 year,number=map(int,month.split('-'));n=year*12+number-1+offset;return f'{n//12:04d}-{n%12+1:02d}'

def fused_report(store,month):
 games=legacy_data('games.json')['games'];catalog=legacy_data('visual-catalog.json');archive=legacy_data('style-reports.json')
 previous=next((r for r in archive['reports'] if r['month']==month),None)
 snapshots=[s for s in sqlite_snapshots(store) if s['sourceDate'].startswith(month)]
 observed_days=len({s['sourceDate'] for s in snapshots})
 latest={}
 for s in snapshots:
  key=(s['sourceId'],s['boardId'])
  if key not in latest or (s['sourceDate'],s['revision'])>(latest[key]['sourceDate'],latest[key]['revision']):latest[key]=s
 current=list(latest.values());rows=[(s,r) for s in current for r in s['rows']];titles={clean(r['name']) for _,r in rows}
 annotations={a['gameId']:a for a in catalog['annotations'] if a.get('reviewed')};samples=[];matched_titles=set();histories={}
 for game in games:
  annotation=annotations.get(game['id']);name=clean(game['name'])
  if not annotation or name not in titles:continue
  images=[a for a in game['assets'] if a['id'] in annotation['assetIds'] and a.get('evidenceType')=='verified_gameplay']
  if len(images)<2:continue
  references=[]
  for snapshot,row in rows:
   if clean(row['name'])!=name:continue
   if row['gameId'] not in histories:histories[row['gameId']]=store.history(row['gameId'])
   history=histories[row['gameId']];comparison=history['comparison'];a=comparison['previous'];b=comparison['current']
   # The displayed monthly board may be historical. Never use the newest month's delta for it.
   if not b or b['date']!=snapshot['sourceDate']:delta=None;before=None
   else:delta=comparison['delta'];before=a
   references.append({'gameId':row['gameId'],'platform':snapshot['platform'],'name':row['name'],'rank':row['rank'],'date':snapshot['sourceDate'],'coverage':snapshot['coverage']['limit'],'delta':delta,'previousDate':before['date'] if before else None,'previousRank':before['rank'] if before else None,'previousRecordUrl':'/records/'+before['row_id'] if before and before['row_id'] else None,'recordUrl':row['recordUrl'],'sourceUrl':row['sourceUrl'],'historyUrl':'/games/'+row['gameId'],'identityStatus':'same_title_reference_only','visualVersionConfirmed':False})
  samples.append({'gameId':game['id'],'name':game['name'],'familyId':annotation['familyId'],'features':annotation['features'],'references':references,'images':[{'id':a['id'],'url':a['url'],'title':a['title'],'sourceUrl':a['sourceUrl'],'gameId':game['id'],'gameName':game['name']} for a in images]});matched_titles.add(name)
 groups=[]
 for family in catalog['families']:
  members=[s for s in samples if s['familyId']==family['id']]
  if not members:continue
  references=[r for s in members for r in s['references']];groups.append(family|{'count':len(members),'share':round(len(members)/len(samples)*100),'images':[m['images'][0] for m in members[:2]],'sampleIds':[m['gameId'] for m in members],'marketEvidence':_evidence(references),'marketNote':'同名画面参考，不代表小游戏平台版本已核验'})
 groups.sort(key=lambda g:(-g['count'],g['order']))
 features={key:sum(key in s['features'] for s in samples) for key in ['eastern_symbols','combat_feedback','dark_atmosphere']}
 outlook=[]
 old_outlook={o['id']:o for o in (previous or {}).get('outlook',[])}
 definitions=[('light-oriental','light-oriental','oriental','清爽国风：继续观察，先验证差异','优先做清爽配色、角色轮廓和局部技能高光的同玩法对照。','当前同名国风产品仍出现在免费前10范围，支持保留该视觉方向；短期榜位不能证明风格引起增长。'),('readable-feedback',None,'cartoon','技能反馈：保留方向，控制画面密度','保持明确技能边界与有限强调色，用三档表现密度比较目标辨认速度。','今天的同名参考里既有榜位改善也有回落，说明不能把所有强反馈画面统一解释成市场上升。'),('mood-identity','dark-folk','folk','民俗氛围：缩小验证，暂不扩大判断','先用低成本氛围方案验证暗场景可读性，不据单个案例扩大投入。','当前只有一个暗调民俗画面参考；其可比榜位回落，是收紧既有判断的信号，而不是证明整个题材衰退。')]
 for ident,family,preview,title,prediction,logic in definitions:
  members=[s for s in samples if s['familyId']==family] if family else [s for s in samples if 'combat_feedback' in s['features']]
  if not members:continue
  if ident in {'light-oriental','readable-feedback'} and len(members)<2:continue
  e=_evidence([r for s in members for r in s['references']]);old=old_outlook.get(ident)
  if ident=='mood-identity':logic=f"当前只有{len(members)}份暗调民俗画面参考；"+('可比榜位出现回落，收紧该单例的既有判断，但不能证明整个题材衰退。' if e['falling'] else '证据不足，保留小范围可读性验证，不能证明题材扩张。')
  if ident=='readable-feedback':logic=f"同名档案可比{e['comparable']}个，改善{e['rising']}、回落{e['falling']}；"+'不能将强反馈画面统一解释为市场上升，也不能据榜位归因美术效果。'
  outlook.append({'id':ident,'previewStyle':preview,'title':title,'prediction':prediction,'logic':logic,'evidence':f"{len(members)}份独立画面参考，关联{e['identities']}个平台同名档案；可比{e['comparable']}个，改善{e['rising']}、持平{e['stable']}、回落{e['falling']}，另{e['unknown']}个暂无可比数据。",'risk':f'本月仅{observed_days}个观察日、免费Top10范围；平台画面版本尚未确认。不能归因于美术、推算收入、CTR或长期增长。','test':'补充对应小游戏版本实录和连续真实日榜；保持玩法一致再测试配色、轮廓与特效密度。','confidence':'低','confidenceReason':f'本月{observed_days}个观察日，视觉关联仅同名，缺少版本确认、充分历史及效果验证。','previousTitle':old['title'] if old else None,'previousPrediction':old['prediction'] if old else None,'revisionNote':'由扩展判断收紧为小范围验证' if ident=='mood-identity' and e['falling'] else '补入最新事实，保持低置信度','marketEvidence':e})
 dates=sorted({s['sourceDate'] for s in snapshots});by_platform=[]
 for platform in ['wechat','douyin']:
  subset=[s for s in snapshots if s['platform']==platform]
  if subset:by_platform.append({'platform':platform,'days':len({s['sourceDate'] for s in subset}),'records':sum(len(s['rows']) for s in subset),'latestDate':max(s['sourceDate'] for s in subset),'coverage':max(s['coverage']['limit'] for s in subset)})
 fingerprint=hashlib.sha256(json.dumps([s['batchId'] for s in snapshots],sort_keys=True).encode()).hexdigest()
 excluded=sum(clean(g['name']) in titles and clean(g['name']) not in matched_titles and any(a.get('evidenceType')=='publisher_publicity' for a in g['assets']) for g in games)
 folk=next((o for o in outlook if o['id']=='mood-identity'),None)
 summary=f"本轮最新Top10共{len(rows)}个平台档案、{len(titles)}个名称；其中{len(samples)}个名称已有实录画面参考。只对有画面与当前榜位依据的方向保留验证建议。"+('民俗氛围样本少且有回落，判断收紧。' if folk and folk['marketEvidence']['falling'] else '')+'当前均为低置信度，不构成市场增长结论。' if samples else '当前已核验榜位与画面参考没有交集，暂不输出风格结论。'
 return {'schemaVersion':1,'month':month,'outlookWindow':{'start':_offset(month,1),'end':_offset(month,3)},'generatedAt':now(),'basis':'sqlite_reviewed_current_boards','isCurrentMonth':month==datetime.now(TZ).strftime('%Y-%m'),'observedDays':len(dates),'firstDate':dates[0] if dates else None,'lastDate':dates[-1] if dates else None,'latestCapture':max((s['observedAt'] for s in snapshots),default=None),'boardCount':len(current),'sourceCount':len({s['sourceId'] for s in current}),'rankingTitleCount':len(titles),'sampleCount':len(samples),'unclassifiedTitleCount':len(titles-matched_titles),'excludedPromotional':excluded,'groups':groups,'features':{'easternSymbols':features['eastern_symbols'],'combatFeedback':features['combat_feedback'],'darkAtmosphere':features['dark_atmosphere']},'summary':summary,'outlook':outlook,'sources':[{'sourceId':s['sourceId'],'boardId':s['boardId'],'url':s['sourceUrl'],'limit':s['coverage']['limit'],'observedAt':s['observedAt']} for s in current],'integration':{'active':True,'snapshotCount':len(snapshots),'rankingRows':sum(len(s['rows']) for s in snapshots),'currentPlatformIdentities':len(rows),'visualVersionConfirmed':0,'candidatePlatformReferences':sum(len(s['references']) for s in samples),'platforms':by_platform,'batchFingerprint':fingerprint,'lastImportFailed':any(s['status']=='sync_failed' for s in store.sources() if s['source_name']=='momorank'),'previousReport':{'generatedAt':previous['generatedAt'],'sampleCount':previous['sampleCount'],'summary':previous['summary'],'basis':previous['basis']} if previous else None,'scopeWarning':'上版使用来源与范围不同，样本数量变化不能解释为风格市场份额涨跌。今日更新不增加已有相同日期的历史天数。','access':'内部核验文件导入；未启用自动采集或公开再发布'},'method':{'unit':'每个归档画面案例只计1份，不按图片张数、平台数、重复导入或出现次数加权。','scope':'同名画面仅作视觉参考，平台版本确认数为0；不会把同名关联当作产品或美术身份确认。','bias':'免费Top10是有限观察范围，旧案例也非随机抽样；未覆盖的游戏不表示表现差。','unclassified':'缺少核验实录的名称保持未分类，商店海报不进入实录风格分布。','automation':'读取同一SQLite实时重新计算；刷新只读本地数据库，不联网抓取。新增核验文件导入后，可刷新本页更新判断。'}}

def _evidence(rows):
 # One platform/source identity is one market record; art sample counts are separate.
 unique={r['gameId']:r for r in rows};rows=list(unique.values());comparable=[r for r in rows if r['delta'] is not None]
 return {'identities':len(rows),'comparable':len(comparable),'rising':sum(r['delta']>0 for r in comparable),'falling':sum(r['delta']<0 for r in comparable),'stable':sum(r['delta']==0 for r in comparable),'unknown':len(rows)-len(comparable),'rows':rows}

def style_reports(store):
 archive=legacy_data('style-reports.json');months=sorted({s['sourceDate'][:7] for s in sqlite_snapshots(store)},reverse=True)
 reports=[fused_report(store,m) for m in months]
 for old in archive['reports']:
  if old['month'] not in months:reports.append(old|{'legacyArchive':True})
 reports.sort(key=lambda r:r['month'],reverse=True)
 return {'schemaVersion':1,'generatedAt':now(),'defaultMonth':months[0] if months else archive['defaultMonth'],'monthlySourceStates':[],'reports':reports,'integrated':True,'usageScope':'local_internal_review_only'}

def frontend_sources(store):
 original=legacy_data('sources.json');states=store.sources();sources=[]
 for s in states:
  sources.append({'id':s['source_name'],'name':s['display_name'],'url':s['official_url'],'kind':'ranking','integrationStatus':'manual_import' if s['last_successful_sync'] else 'public_access_pending','allowedScope':s['permission_note'],'note':s['cost_note']})
 boards=[b|{'sourceIds':['momorank']} for b in original['boards'] if b['id'] in ['wechat-bestselling','douyin-bestselling']]
 return original|{'sources':sources,'boards':boards,'integration':True}

def register_fusion(app,store):
 bp=Blueprint('fusion',__name__)
 @bp.get('/site')
 def site_redirect():return redirect('/site/')
 @bp.get('/site/')
 def site():return send_from_directory(ROOT/'web','index.html')
 @bp.get('/site/data/<path:name>')
 def data(name):
  if name=='style-reports.json':return jsonify(style_reports(store))
  if name=='radar.json':return jsonify({'schemaVersion':1,'snapshots':sqlite_snapshots(store)})
  if name=='sources.json':return jsonify(frontend_sources(store))
  if name=='observations.json':return jsonify({'schemaVersion':1,'records':[]})
  if name=='history/index.json':return jsonify({'schemaVersion':1,'snapshots':[{'path':'/api/market','sourceId':s['sourceId'],'boardId':s['boardId'],'sourceDate':s['sourceDate'],'observedAt':s['observedAt'],'batchId':s['batchId']} for s in sqlite_snapshots(store)]})
  if name=='health.json':return jsonify({'generatedAt':now(),'mode':'local_reviewed_file_import','sources':[{'sourceId':s['source_name'],'status':'manual_import' if s['last_successful_sync'] and s['status']!='sync_failed' else 'failed' if s['status']=='sync_failed' else 'public_access_pending','lastSuccessAt':s['last_successful_sync'],'lastAttemptAt':s['last_attempt_at'],'error':s['permission_note']} for s in store.sources()]})
  if name not in {'games.json','audience.json'}:abort(404)
  return jsonify(legacy_data(name))
 @bp.get('/site/<path:name>')
 def files(name):
  if name.startswith('intelligence-ui/'):
   if Path(name).suffix not in {'.js','.mjs','.css'}:abort(404)
   return send_from_directory(ROOT/'web',name)
  media_root=legacy_root()/'site'
  if name.startswith('assets/') and Path(name).suffix.lower() in {'.png','.jpg','.jpeg','.webp','.gif','.svg','.mp4'}:return send_from_directory(media_root,name)
  # The older V1 archive is a preserved reference, not a second live data service.
  if name=='archive.html':return redirect('/site/#games')
  abort(404)
 app.register_blueprint(bp)
