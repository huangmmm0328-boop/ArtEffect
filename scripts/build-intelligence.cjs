const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),site=path.join(root,'site'),input=path.join(root,'intelligence');
if(!fs.existsSync(path.join(site,'media-data.js')))throw Error('Unpack the existing reviewed website first');
const oldIndex=fs.readFileSync(path.join(site,'index.html'),'utf8');
if(oldIndex.includes('<script src="media-data.js"')){
  fs.writeFileSync(path.join(site,'archive.html'),oldIndex.replace('GAME ART INSIGHT · 产品评审版','GAME ART INSIGHT · 旧版资料归档（页面与功能按归档时点保留）'));
}else if(!fs.existsSync(path.join(site,'archive.html')))throw Error('Previous review archive is missing; refusing to overwrite it.');
fs.cpSync(input,site,{recursive:true});
// A single content version covers the entry, styles and relative ESM imports.
// Previously opened browsers must not combine a new HTML page with old logic.
const ui=path.join(site,'intelligence-ui'),uiFiles=fs.readdirSync(ui).filter(f=>/\.(?:js|mjs|css)$/.test(f)).sort();
const uiVersion=crypto.createHash('sha256').update(uiFiles.map(f=>f+'\n'+fs.readFileSync(path.join(ui,f),'utf8')).join('\n')).digest('hex').slice(0,12);
for(const file of uiFiles.filter(f=>/\.(?:js|mjs)$/.test(f))){const p=path.join(ui,file),source=fs.readFileSync(p,'utf8');fs.writeFileSync(p,source.replace(/(['"])(\.\/[a-zA-Z0-9.-]+\.(?:js|mjs))(?:\?[^'"]*)?\1/g,(_,q,url)=>q+url+'?v='+uiVersion+q));}
const indexPath=path.join(site,'index.html');fs.writeFileSync(indexPath,fs.readFileSync(indexPath,'utf8').replace(/((?:src|href)=")(intelligence-ui\/[^"?]+\.(?:js|css))(?:\?[^" ]*)?(")/g,(_,prefix,url,end)=>prefix+url+'?v='+uiVersion+end));
const index=JSON.parse(fs.readFileSync(path.join(input,'data/history/index.json'),'utf8'));
const earliest=new Date(Date.now()-90*86400000).toISOString().slice(0,10),snapshots=index.snapshots.filter(e=>e.sourceDate>=earliest).map(e=>{
  const file=path.resolve(input,'data',e.path);if(!file.startsWith(path.join(input,'data')+path.sep))throw Error('Invalid history path');return JSON.parse(fs.readFileSync(file,'utf8'));
});
fs.writeFileSync(path.join(site,'data/radar.json'),JSON.stringify({schemaVersion:1,snapshots}));
console.log('V2 interface overlaid; archive.html and all original images/GIFs retained.');
