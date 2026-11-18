export const DAY=86400000;
export const dateKey=value=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value));
export const dayNumber=value=>Date.parse(value+'T00:00:00Z')/DAY;
export function seriesFor(snapshots,{boardId,sourceId,days=7,now=new Date().toISOString()}){
  const end=dayNumber(dateKey(now)),start=end-days+1,byDay=new Map();
  for(const s of snapshots){if(s.boardId!==boardId||s.sourceId!==sourceId||s.status!=='ok')continue;const d=dayNumber(s.sourceDate);if(d<start||d>end)continue;const prior=byDay.get(s.sourceDate);if(!prior||Date.parse(s.observedAt)>Date.parse(prior.observedAt))byDay.set(s.sourceDate,s);}
  return [...byDay.values()].sort((a,b)=>a.sourceDate.localeCompare(b.sourceDate));
}
export function summarize(snapshots,options){
  const series=seriesFor(snapshots,options),latest=series.at(-1),previous=series.at(-2),days=options.days||7;
  if(!latest)return {series,latest:null,previous:null,observedDays:0,expectedDays:days,rows:[],newcomers:null,rising:null,falling:null,consecutive:null,comparable:false};
  const comparable=!!previous&&dayNumber(latest.sourceDate)-dayNumber(previous.sourceDate)===1&&previous.coverage.complete===true&&latest.coverage.complete===true&&previous.coverage.limit===latest.coverage.limit&&previous.definitionVersion===latest.definitionVersion;
  const previousRows=new Map(previous?.rows.map(r=>[r.gameId,r])||[]);
  const rows=latest.rows.map(row=>{
    const before=previousRows.get(row.gameId);let streak=0,cursor=dayNumber(latest.sourceDate);
    for(let i=series.length-1;i>=0;i--){const s=series[i];if(dayNumber(s.sourceDate)!==cursor||s.definitionVersion!==latest.definitionVersion||s.coverage.limit!==latest.coverage.limit||!s.rows.some(r=>r.gameId===row.gameId))break;streak++;cursor--;}
    return {...row,delta:comparable&&before?before.rank-row.rank:null,isNew:comparable?!before:null,streak,points:series.map(s=>({date:s.sourceDate,rank:s.rows.find(r=>r.gameId===row.gameId)?.rank??null}))};
  });
  return {series,latest,previous,observedDays:series.length,expectedDays:days,rows,comparable,newcomers:comparable?rows.filter(r=>r.isNew).length:null,rising:comparable?rows.filter(r=>r.delta>0).length:null,falling:comparable?rows.filter(r=>r.delta<0).length:null,consecutive:series.length>=3?rows.filter(r=>r.streak>=3).length:null};
}
export function signalReadiness({observedDays,platformMatches,verifiedAds,surveyFindings}){
  return {history:observedDays>=7,crossPlatform:platformMatches>0,creative:verifiedAds>0,audience:surveyFindings>0,canCallMarketTrend:observedDays>=7&&platformMatches>0};
}
