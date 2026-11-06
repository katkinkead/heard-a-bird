const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
global.window=global;global.document={createElement:()=>({getContext:()=>({})})};const root=path.resolve(__dirname,'..');
for(const f of ['artwork/branch/product/branch-motion/registrations.js','static/tree-layout-data.js','static/painted-tree.js'])vm.runInThisContext(fs.readFileSync(path.join(root,f),'utf8'));
const ids=['robin','goldfinch','blue-tit','blackbird','woodpigeon','wren','chaffinch','greenfinch','great-tit','song-thrush','coal-tit','dunnock','bullfinch','blackcap','long-tailed-tit','siskin','goldcrest','starling','house-sparrow','nuthatch','collared-dove','redwing','fieldfare','jay','pied-wagtail'];
const tree=new PaintedTree(StaticBirds);
for(let n=1;n<=25;n++){
 tree.sync(ids.slice(0,n),true);
 assert.equal(tree.stage,n<=4?0:n<=8?1:n<=18?2:3);
 assert.equal(tree.duration,n===1?0:[5,9,19].includes(n)?10:2);
 if(n>1){assert(tree.busy);for(let j=0;j<110;j++)tree.tick(.1);assert(!tree.busy);}
 for(let i=0;i<n;i++){const p=tree.pose(ids[i],i,tree.stage);assert(p&&Number.isFinite(p.k)&&p.k>0);const b=p.r.birdBounds,anc=p.r.perchAnchor;for(const x of [b[0],b[2]])for(const y of [b[1],b[3]]){const xx=(x-anc[0])*p.k,yy=(y-anc[1])*p.k;const X=p.x+xx*Math.cos(p.angle)-yy*Math.sin(p.angle),Y=p.y+xx*Math.sin(p.angle)+yy*Math.cos(p.angle);assert(X>=0&&X<=1000&&Y>=0&&Y<=500,`${n}/${ids[i]} clips at ${X},${Y}`);}}
}
tree.reset();tree.sync(ids,false);assert(!tree.busy);assert.equal(tree.ids.length,25);
console.log('Painted tree: 1–25 bounds, arrival gates, thresholds and history restore passed.');
