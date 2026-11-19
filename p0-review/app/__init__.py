from __future__ import annotations
import hmac,json,secrets
from pathlib import Path
from datetime import date
from flask import Flask,abort,flash,g,jsonify,redirect,render_template,request,send_file,session,url_for
from .store import Store,ImportRejected,ROOT,TZ

PLATFORMS={'wechat':'微信小游戏','douyin':'抖音小游戏','app':'APP视觉参考'}
STATUS={'manual_import_verified':'人工文件导入已验证','verified_visible_pending_import':'免费可见已验证，待导入','sync_failed':'最近导入失败，旧快照保留','permission_pending':'采集许可待确认','date_and_permission_pending':'日期与许可待确认','account_qualification_pending':'账号资格待确认','not_verified':'待核验','disabled_zero_budget':'零预算禁用'}

def create_app(db_path=None,testing=False):
 app=Flask(__name__,template_folder=str(ROOT/'templates'),static_folder=str(ROOT/'static'))
 app.config.update(SECRET_KEY=secrets.token_hex(32),MAX_CONTENT_LENGTH=5*1024*1024,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',TRUSTED_HOSTS=['127.0.0.1','localhost'],TESTING=testing)
 store=Store(db_path);store.initialize();app.extensions['p0_store']=store
 @app.before_request
 def request_scope():
  if '_csrf' not in session:session['_csrf']=secrets.token_hex(24)
  if request.method=='POST':
   token=request.headers.get('X-CSRF-Token') or request.form.get('csrf_token','')
   if not hmac.compare_digest(str(token),session['_csrf']):abort(403,description='请从本地预览页提交导入请求')
 @app.after_request
 def headers(response):
  response.headers['Cache-Control']='no-store';response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY'
  response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
  return response
 @app.context_processor
 def context():return {'platform_names':PLATFORMS,'status_names':STATUS,'csrf_token':session.get('_csrf'),'production_url':'https://huangmmm0328-boop.github.io/ArtEffect/'}
 @app.template_filter('delta')
 def delta(value):return '暂无可比数据' if value is None else ('改善'+str(value)+'位' if value>0 else '下降'+str(-value)+'位' if value<0 else '持平')
 @app.template_filter('timefmt')
 def timefmt(value):
  if not value:return '未提供／尚无记录'
  try:
   from datetime import datetime
   return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(TZ).strftime('%Y-%m-%d %H:%M')
  except (ValueError,TypeError):return value
 @app.get('/')
 def market():
  platform=request.args.get('platform')
  if platform not in (None,'wechat','douyin'):abort(400)
  return render_template('market.html',boards=store.market(platform),counts=store.counts(),platform=platform,sources=store.sources())
 @app.get('/games/<game_id>')
 def game_history(game_id):
  result=store.history(game_id)
  if not result:abort(404)
  return render_template('history.html',record=result,chart=chart_points(result['points']))
 @app.get('/sources')
 def sources():return render_template('sources.html',sources=store.sources(),logs=store.logs())
 @app.get('/audit')
 def audit():
  inventory=read_json(ROOT/'docs/asset-inventory.json',{});backup=read_json(ROOT/'backups/backup-manifest.json',read_json(ROOT/'docs/backup-summary.json',{}))
  return render_template('audit.html',inventory=inventory,backup=backup,counts=store.counts())
 @app.get('/imports')
 def imports():return render_template('imports.html',logs=store.logs())
 @app.post('/imports')
 @app.post('/api/import')
 def import_file():
  if request.form.get('reviewed')!='yes':abort(400,description='导入前请核对来源、日期与内部使用范围')
  upload=request.files.get('file')
  if not upload or not upload.filename:abort(400,description='请选择CSV或JSON文件')
  try:result=store.import_file(upload.read(),upload.filename)
  except ImportRejected as exc:
   if request.path.startswith('/api/'):return jsonify({'error':str(exc),'previous_data_preserved':True}),422
   flash(str(exc)+'；旧快照已保留。','error');return render_template('imports.html',logs=store.logs()),422
  if request.path.startswith('/api/'):return jsonify(result)
  flash('导入成功，保存'+str(result['records_saved'])+'条榜位。' if result['records_saved'] else '重复数据已识别，没有新增榜位或覆盖旧快照。','success')
  return redirect(url_for('sources'))
 @app.get('/records/<row_id>')
 def raw_record(row_id):
  with store.connection() as db:
   record=db.execute('SELECT r.*,b.source_updated_at,b.imported_at,b.revision,b.definition_version,d.file_name,d.sha256 FROM ranking_snapshots r JOIN snapshot_batches b ON b.id=r.batch_id JOIN raw_documents d ON d.id=b.raw_document_id WHERE r.id=?',(row_id,)).fetchone()
  if not record:abort(404)
  record=dict(record);record['fields']=json.loads(record.pop('raw_record_json'))
  return render_template('record.html',record=record)
 @app.get('/api/market')
 def market_api():
  p=request.args.get('platform')
  if p not in (None,'wechat','douyin'):abort(400)
  return jsonify({'boards':store.market(p),'counts':store.counts()})
 @app.get('/api/games/<game_id>/history')
 def history_api(game_id):
  result=store.history(game_id)
  if result is None:abort(404)
  return jsonify(result)
 @app.get('/api/sources')
 def sources_api():return jsonify({'sources':store.sources(),'sync_logs':store.logs()})
 @app.get('/health')
 def health():
  with store.connection() as db:integrity=db.execute('PRAGMA quick_check').fetchone()[0]
  return jsonify({'stage':'P0','database':'SQLite','integrity':integrity,'production_deployment':False,'counts':store.counts()})
 @app.get('/reports/<name>')
 def report_file(name):
  if name not in {'P0_ACCEPTANCE.md','AUDIT.md','SOURCE_VERIFICATION.md','DATABASE.md','MIGRATION.md','TEST_RESULTS.json','asset-inventory.json','source-catalog.json'}:abort(404)
  p=ROOT/'docs'/name
  if not p.is_file():abort(404)
  return send_file(p,mimetype='application/json' if name.endswith('.json') else 'text/plain; charset=utf-8')
 return app

def read_json(path,default):
 try:return json.loads(Path(path).read_text(encoding='utf8'))
 except FileNotFoundError:return default

def chart_points(points):
 # Plot only observed dates and real ranks; gaps break the line.
 if not points:return {'segments':[],'dots':[],'labels':[],'depth':10}
 start=date.fromisoformat(points[0]['date']);end=date.fromisoformat(points[-1]['date']);span=max(1,(end-start).days);depth=max(p['coverage_depth'] for p in points)
 def position(p):return 55+(date.fromisoformat(p['date'])-start).days/span*800,35+(p['rank']-1)/max(1,depth-1)*190
 segments=[];dots=[];current=[];previous=None
 for p in points:
  if p['rank'] is None or previous and ((date.fromisoformat(p['date'])-date.fromisoformat(previous['date'])).days!=1 or p['coverage_depth']!=previous['coverage_depth'] or p['definition_version']!=previous['definition_version'] or not p['coverage_complete'] or not previous['coverage_complete']):
   if len(current)>1:segments.append(current)
   current=[]
  if p['rank'] is not None:
   x,y=position(p);current.append((x,y));dots.append({'x':x,'y':y,'date':p['date'],'rank':p['rank']})
  previous=p
 if len(current)>1:segments.append(current)
 return {'segments':[' '.join(('M' if i==0 else 'L')+f'{x:.1f},{y:.1f}' for i,(x,y) in enumerate(segment)) for segment in segments],'dots':dots,'labels':[points[0]['date'],points[-1]['date']],'depth':depth}
