import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {summarize} from '../intelligence/intelligence-ui/analytics.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../intelligence/data');
const registry=JSON.parse(fs.readFileSync(path.join(root,'sources.json'),'utf8')),index=JSON.parse(fs.readFileSync(path.join(root,'history/index.json'),'utf8'));
const snapshots=index.snapshots.map(e=>JSON.parse(fs.readFileSync(path.join(root,e.path),'utf8'))),records=[];
for(const board of registry.boards)for(const sourceId of board.sourceIds){
  const result=summarize(snapshots,{boardId:board.id,sourceId,days:90});
  if(!result.latest||!result.previous)continue;
  const record={schemaVersion:1,kind:'rank_change_record',sourceId,boardId:board.id,currentDate:result.latest.sourceDate,previousDate:result.previous.sourceDate,comparable:result.comparable,reason:result.comparable?null:'缺测日、公开范围不完整或范围变化；不判定新进与涨跌。',currentObservation:result.latest.observedAt,previousObservation:result.previous.observedAt,rows:result.rows.map(r=>({gameId:r.gameId,name:r.name,rank:r.rank,delta:r.delta,isNew:r.isNew,consecutiveObservedDays:r.streak}))};
  const relative=`changes/${record.currentDate}/${sourceId}-${board.id}.json`;fs.mkdirSync(path.dirname(path.join(root,relative)),{recursive:true});fs.writeFileSync(path.join(root,relative),JSON.stringify(record,null,2)+'\n');records.push(relative);
}
fs.mkdirSync(path.join(root,'changes'),{recursive:true});
const existingFile=path.join(root,'changes/index.json'),existing=fs.existsSync(existingFile)?JSON.parse(fs.readFileSync(existingFile,'utf8')):{records:[]};
fs.writeFileSync(existingFile,JSON.stringify({schemaVersion:1,records:[...new Set([...existing.records,...records])].sort()},null,2)+'\n');
console.log(JSON.stringify({derivedChangeRecords:records.length,marketFactsInvented:0}));
