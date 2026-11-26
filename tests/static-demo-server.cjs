const fs=require("node:fs");
const path=require("node:path");
const ROOT=path.join(__dirname,"..");
const assets={"/styles/rollflow-design.css":"text/css", "/shared/schedule-core.js":"application/javascript", "/shared/schedule.css":"text/css"};
module.exports=(html)=>(req,res)=>{
  const name=new URL(req.url,"http://localhost").pathname;
  if(name==="/"||name==="/index.html"){res.writeHead(200,{"Content-Type":"text/html; charset=utf-8"});return res.end(html)}
  if(Object.hasOwn(assets,name)){res.writeHead(200,{"Content-Type":assets[name]+"; charset=utf-8"});return res.end(fs.readFileSync(path.join(ROOT,name.slice(1))))}
  res.writeHead(404);res.end();
};
