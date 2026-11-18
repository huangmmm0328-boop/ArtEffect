const fs = require('node:fs');
const path = require('node:path');
const {getRankings} = require('./ranking-source.cjs');
const root = path.resolve(__dirname, '..', 'site');
(async () => {
  let data;
  try {
    data = {...await getRankings(true), updateStatus:'ok', lastAttemptAt:new Date().toISOString()};
  } catch (error) {
    console.warn('Ranking source unavailable; keeping the dated snapshot:', error.message);
    data = {...JSON.parse(fs.readFileSync(path.join(root,'data/rankings.json'),'utf8')), updateStatus:'failed', lastAttemptAt:new Date().toISOString()};
  }
  fs.writeFileSync(path.join(root,'data/rankings.json'), JSON.stringify(data));
  fs.writeFileSync(path.join(root,'rankings-snapshot.js'), 'window.RANKING_SNAPSHOT='+JSON.stringify(data)+';\n');
  console.log(JSON.stringify({boards:data.boards.length, fetchedAt:data.fetchedAt, updateStatus:data.updateStatus}));
})().catch(error => {console.error(error);process.exitCode=1;});
