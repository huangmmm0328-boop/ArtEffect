const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {validateSnapshot}=require('./validate-intelligence.cjs');
if(!process.argv[2])throw Error('Pass a reviewed ranking snapshot JSON file');
const root=path.resolve(__dirname,'../intelligence/data'),snapshot=JSON.parse(fs.readFileSync(path.resolve(process.argv[2]),'utf8'));
validateSnapshot(snapshot,JSON.parse(fs.readFileSync(path.join(root,'sources.json'),'utf8')));
const hash=crypto.createHash('sha256').update(JSON.stringify(snapshot)).digest('hex').slice(0,12),relative=`history/${snapshot.sourceDate}/${snapshot.sourceId}-${snapshot.boardId}-${hash}.json`;
const indexPath=path.join(root,'history/index.json'),index=JSON.parse(fs.readFileSync(indexPath,'utf8'));
if(index.snapshots.some(s=>s.path===relative)){console.log('Identical snapshot already archived');process.exit(0);}
fs.mkdirSync(path.dirname(path.join(root,relative)),{recursive:true});fs.writeFileSync(path.join(root,relative),JSON.stringify(snapshot,null,2)+'\n');
index.snapshots.push({path:relative,sourceId:snapshot.sourceId,boardId:snapshot.boardId,sourceDate:snapshot.sourceDate,observedAt:snapshot.observedAt});index.updatedAt=new Date().toISOString();
fs.writeFileSync(indexPath,JSON.stringify(index,null,2)+'\n');console.log('Archived reviewed snapshot: '+relative);
