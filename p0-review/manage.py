from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from app.store import Store,ImportRejected
from app.bootstrap import seed_review

def main():
 parser=argparse.ArgumentParser(description='P0 SQLite 与真实文件导入。没有网络采集命令。');parser.add_argument('--database',type=Path)
 commands=parser.add_subparsers(dest='command',required=True)
 p=commands.add_parser('init');p.add_argument('--seed',action='store_true')
 p=commands.add_parser('import');p.add_argument('file',type=Path)
 p=commands.add_parser('sync');p.add_argument('--inbox',type=Path,default=Path('data/inbox'))
 p=commands.add_parser('serve');p.add_argument('--port',type=int,default=4190);p.add_argument('--merged',action='store_true')
 commands.add_parser('research');commands.add_parser('status');args=parser.parse_args();store=Store(args.database);store.initialize()
 if args.command=='init':
  if args.seed:print(json.dumps(seed_review(store),ensure_ascii=False))
  print(json.dumps(store.counts(),ensure_ascii=False))
 elif args.command=='import':
  try:print(json.dumps(store.import_file(args.file.read_bytes(),args.file.name),ensure_ascii=False))
  except ImportRejected as exc:print(str(exc),file=sys.stderr);return 1
 elif args.command=='sync':
  # A single scheduled entry reads permitted files only. No HTTP scraping is enabled.
  args.inbox.mkdir(parents=True,exist_ok=True);out=[]
  for file in sorted(args.inbox.iterdir()):
   if file.is_file() and file.suffix.lower() in ('.csv','.json'):
    try:out.append({'file':file.name,**store.import_file(file.read_bytes(),file.name)})
    except ImportRejected as exc:out.append({'file':file.name,'result':'failed','error':str(exc)})
  print(json.dumps(out,ensure_ascii=False))
 elif args.command=='research':
  from app.research import import_pack
  print(json.dumps(import_pack(store),ensure_ascii=False))
 elif args.command=='serve':
  if args.merged and (Path(__file__).parent/'config/research-pack.json').exists():
   from app.research import import_pack
   import_pack(store)
  from app import create_app
  create_app(store.path,integrated=args.merged).run(host='127.0.0.1',port=args.port,debug=False,use_reloader=False)
 else:print(json.dumps({'counts':store.counts(),'sources':store.sources()},ensure_ascii=False))
 return 0
if __name__=='__main__':raise SystemExit(main())
