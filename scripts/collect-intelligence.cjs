const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../intelligence/data'),sources=JSON.parse(fs.readFileSync(path.join(root,'sources.json'),'utf8'));
const now=new Date().toISOString(),day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const states=sources.sources.map(s=>({sourceId:s.id,status:s.integrationStatus,lastAttemptAt:null,lastSuccessAt:null,error:s.integrationStatus==='not_connected'?'第一阶段：已登记来源，尚未启用采集器；不生成空榜单。':s.note}));
const index=JSON.parse(fs.readFileSync(path.join(root,'history/index.json'),'utf8'));
for(const state of states){const observations=index.snapshots.filter(s=>s.sourceId===state.sourceId).sort((a,b)=>b.observedAt.localeCompare(a.observedAt));if(observations.length){state.lastSuccessAt=observations[0].observedAt;state.status='manual_import';state.error='已有人工核验快照；自动采集器尚未启用。';}}
const run={schemaVersion:1,generatedAt:now,date:day,mode:'architecture_phase',runner:{kind:process.env.GITHUB_ACTIONS==='true'?'github_actions':'local_validation',runId:process.env.GITHUB_RUN_ID||null},snapshotCount:index.snapshots.length,sources:states};
const runDir=path.join(root,'runs',day);fs.mkdirSync(runDir,{recursive:true});
const runId=(process.env.GITHUB_RUN_ID||now.replace(/[^0-9]/g,''))+'-'+(process.env.GITHUB_RUN_ATTEMPT||'1');
fs.writeFileSync(path.join(runDir,runId+'.json'),JSON.stringify(run,null,2)+'\n');
fs.writeFileSync(path.join(root,'health.json'),JSON.stringify(run,null,2)+'\n');
console.log(JSON.stringify({mode:run.mode,snapshotCount:run.snapshotCount,generatedAt:now,note:'Only actual snapshots enter history; unconnected sources remain explicit.'}));
