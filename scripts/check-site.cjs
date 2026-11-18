const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../site'),html=fs.readFileSync(path.join(root,'index.html'),'utf8');
for(const m of html.matchAll(/(?:src|href)="([^"#]+\.(?:js|css))"/g)){
  assert(!m[1].startsWith('/'),'Entry must work under the repository path');
  assert(fs.existsSync(path.join(root,m[1])),'Missing entry '+m[1]);
}
const context={window:{}};
for(const name of ['review-config.js','media-data.js','comparison-store-data.js'])vm.runInNewContext(fs.readFileSync(path.join(root,name),'utf8'),context);
assert.equal(context.window.GAI_REVIEW_MODE,true);
let images=0,gifs=0;const files=new Set();
for(const game of context.window.GAME_MEDIA.games){
  for(const a of game.assets){images++;assert.equal(a.rightsStatus,'pending');for(const k of ['original','preview','src'])if(a[k])files.add(a[k]);}
  for(const c of game.motionClips){gifs++;files.add(c.src);files.add(c.poster);const h=fs.readFileSync(path.join(root,c.src)).subarray(0,6).toString();assert(['GIF87a','GIF89a'].includes(h));}
}
for(const game of Object.values(context.window.COMPARISON_STORE_DATA))for(const a of game.gallery){images++;files.add(a.url);}
for(const file of files){const resolved=path.resolve(root,file);assert(resolved.startsWith(root+path.sep));assert(fs.existsSync(resolved),'Missing media '+file);assert(fs.statSync(resolved).size>0);}
assert.equal(images,95);assert.equal(gifs,11);
const data=JSON.parse(fs.readFileSync(path.join(root,'data/rankings.json'),'utf8'));
assert.equal(data.boards.length,4);assert(Number.isFinite(Date.parse(data.fetchedAt)));
for(const board of data.boards)for(const row of board.rows)assert(/^https:\/\/www\.taptap\.cn\/app\/\d+$/.test(row.url));
const code=fs.readFileSync(path.join(root,'github-pages-mode.js'),'utf8');assert(code.includes('data/rankings.json'));assert(code.includes('COMPARISON_STORE_DATA'));assert(!code.includes("fetch('/api/"));
console.log(JSON.stringify({images,gifs,mediaFiles:files.size,boards:data.boards.length,rankingsFetchedAt:data.fetchedAt,repositoryPaths:'relative'}));
