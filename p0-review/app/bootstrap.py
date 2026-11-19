from __future__ import annotations
import csv,io,json
from pathlib import Path
from .store import Store,ROOT,identifier,now,encode

def legacy_root():
 return ROOT/'baseline' if (ROOT/'baseline/intelligence/data').exists() else ROOT.parent

def convert_legacy(snapshot):
 return {'schemaVersion':1,'source':'momorank','platform':snapshot['platform'],'rank_type':'bestselling','data_date':snapshot['sourceDate'],'fetched_at':snapshot['observedAt'],'source_updated_at':None,'coverage_depth':snapshot['coverage']['limit'],'coverage_complete':snapshot['coverage']['complete'],'definition_version':snapshot['definitionVersion'],'source_url':snapshot['sourceUrl'],'access_method':'reviewed_historical_import','usage_scope':'local_internal_review_only','rows':[{'source_game_id':str(r.get('sourceGameId') or r['gameId'].split(':')[-1]),'name':r['name'],'rank_position':r['rank'],'publisher':r.get('publisher'),'source_url':r.get('sourceUrl')} for r in snapshot['rows']]}

def history_samples():
 root=legacy_root()/'intelligence/data';index=json.loads((root/'history/index.json').read_text(encoding='utf8'))
 return [convert_legacy(json.loads((root/e['path']).read_text(encoding='utf8'))) for e in sorted(index['snapshots'],key=lambda e:e['sourceDate']) if e['sourceId']=='momorank' and e['boardId']=='douyin-bestselling']

def to_csv(document):
 metadata=['source','platform','rank_type','data_date','fetched_at','source_updated_at','coverage_depth','coverage_complete','definition_version','source_url','access_method','usage_scope']
 fields=metadata+['source_game_id','name','rank_position','publisher','game_source_url'];buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=fields);writer.writeheader()
 for row in document['rows']:writer.writerow({k:document.get(k) for k in metadata}|{'source_game_id':row['source_game_id'],'name':row['name'],'rank_position':row['rank_position'],'publisher':row.get('publisher'),'game_source_url':row['source_url']})
 return ('\ufeff'+buffer.getvalue()).encode('utf8')

def seed_archive(store):
 root=legacy_root();games=json.loads((root/'intelligence/data/games.json').read_text(encoding='utf8'))['games']
 inventory_path=ROOT/'docs/asset-inventory.json'
 inventory=json.loads(inventory_path.read_text(encoding='utf8')) if inventory_path.exists() else {'entries':[]}
 with store.connection() as db:
  for g in games:
   external=str(g.get('externalIds',{}).get('taptap') or g['id']);game_id=identifier('taptap','app',external);publisher=g.get('publisher');publisher=None if not publisher or '待核实' in publisher else publisher
   db.execute('INSERT OR IGNORE INTO games(id,platform,primary_source,source_game_id,name,publisher,art_tags,identity_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(game_id,'app','taptap',external,g['name'],publisher,encode([{'tag':g['style'],'evidence_type':'archived_manual_research'}]),'auxiliary_app_reference',now(),now()))
   db.execute('INSERT OR IGNORE INTO game_source_ids VALUES(?,?,?,?,?,?)',('taptap','app',external,game_id,g['sourceUrl'],'旧站APP视觉参考，未与小游戏平台版本合并'))
   for a in inventory['entries']:
    if a['game_id']==g['id']:db.execute('INSERT OR IGNORE INTO archived_assets VALUES(?,?,?,?,?,?,?,?,?,?)',(a['id'],game_id,g['id'],a['kind'],a['path'],a['sha256'],a['bytes'],a['source_url'],a.get('rights_status') or 'pending',a.get('evidence_type')))

def seed_review(store):
 store.initialize();seed_archive(store);results=[];evidence=ROOT/'data/evidence';evidence.mkdir(parents=True,exist_ok=True)
 manual=sorted(evidence.glob('momorank-*-*-*-*.json'));manual_docs=[json.loads(p.read_text(encoding='utf8')) for p in manual]
 manual_keys={(d['platform'],d['data_date']) for d in manual_docs}
 for document in history_samples():
  if (document['platform'],document['data_date']) in manual_keys:continue
  results.append(store.import_file(encode(document).encode(),f"reviewed-history-{document['platform']}-{document['data_date']}.json"))
 for document in manual_docs:
  name=f"manual-visible-record-{document['platform']}-{document['data_date']}.json";results.append(store.import_file(encode(document).encode(),name))
  csv_file=evidence/f"manual-recording-{document['platform']}-{document['data_date']}.csv";csv_file.write_bytes(to_csv(document))
 return results
