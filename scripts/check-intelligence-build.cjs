const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const site=path.resolve(__dirname,'../site'),html=fs.readFileSync(path.join(site,'index.html'),'utf8');
assert(html.includes('GAME ART INTELLIGENCE V2.0'));assert(fs.readFileSync(path.join(site,'archive.html'),'utf8').includes('旧版资料归档'));
for(const m of html.matchAll(/(?:src|href)="([^"#]+\.(?:js|css))"/g))assert(fs.existsSync(path.join(site,m[1])),'Missing entry '+m[1]);
for(const name of ['sources','games','audience','health','radar','style-reports'])assert(fs.existsSync(path.join(site,'data',name+'.json')),'Missing dataset '+name);
for(const name of ['monthly-page.mjs','monthly-analysis.mjs','style-preview.mjs','monthly.css'])assert(fs.existsSync(path.join(site,'intelligence-ui',name)),'Missing monthly module '+name);
const games=JSON.parse(fs.readFileSync(path.join(site,'data/games.json'),'utf8')).games;let count=0;
for(const g of games)for(const asset of [...g.assets,...g.motion.flatMap(m=>[{url:m.url},{url:m.poster}])]){const file=path.resolve(site,asset.url);assert(file.startsWith(site+path.sep));assert(fs.existsSync(file)&&fs.statSync(file).size>0,'Missing image/GIF '+asset.url);count++;}
const radar=JSON.parse(fs.readFileSync(path.join(site,'data/radar.json'),'utf8'));for(const snapshot of radar.snapshots)assert(snapshot.rows.length>0);
assert(!fs.existsSync(path.join(site,'tests')),'Test fixtures must not be published');
console.log(JSON.stringify({built:true,games:games.length,mediaReferences:count,snapshots:radar.snapshots.length,oldArchiveRetained:true}));
