// Test the actual packaged loopback server and assets, not a mock HTML server.
// Run with Node + playwright-core and the runner's Chrome or Edge.
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright-core');
const path = require('node:path');
const fs = require('node:fs');
const http = require('node:http');
const root = path.resolve(__dirname, '..');
const py = process.env.RF_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const users = ['admin','principal','deputy','hod','ylc','business','office','teacher','swilliams','learning','aide','relief','guidance'];
// Compare actual public source menus to packaged menus rather than stale hard-coded counts.
const reference=http.createServer((req,res)=>{
 const pathname=new URL(req.url,'http://localhost').pathname;
 const asset=pathname==='/'?'index.html':pathname==='/styles/rollflow-design.css'?'styles/rollflow-design.css':null;
 if(!asset){res.writeHead(404);res.end();return;}
 res.writeHead(200,{'Content-Type':asset.endsWith('.css')?'text/css':'text/html; charset=utf-8'});
 res.end(fs.readFileSync(path.join(root,'training',asset)));
});
async function signature(page){
 return page.locator('.nav-primary button').evaluateAll(bs=>bs.map(b=>({
  label:b.innerText.trim(),route:b.getAttribute('data-admin-page')||b.getAttribute('data-nav')||b.getAttribute('data-rfu-page')||''
 })));
}
async function referenceSignature(browser,id,url){
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
 try{
  const p=await ctx.newPage();await p.goto(url);
  await p.locator('#demo-username').fill(id);await p.locator('#demo-password').fill(id);
  await p.locator('#demo-login-form button[type="submit"]').click();
  await p.locator('.rf-compact-account summary').waitFor();
  return await signature(p);
 }finally{await ctx.close()}
}
async function main(){
 const server=spawn(py,['-m','deployment.training','--port','0','--no-browser'],{cwd:root,env:{...process.env,PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe']});
 let browser;
 try{
  await new Promise((resolve,reject)=>{reference.once('error',reject);reference.listen(0,'127.0.0.1',resolve)});
  const referenceUrl='http://127.0.0.1:'+reference.address().port+'/';
  const url=await new Promise((resolve,reject)=>{
   let buf='';const timeout=setTimeout(()=>reject(Error('Training server did not start')),15000);
   server.once('error',e=>{clearTimeout(timeout);reject(e)});
   server.once('exit',c=>{clearTimeout(timeout);reject(Error('Training server exited: '+c))});
   server.stderr.on('data',d=>process.stderr.write(d));
   server.stdout.on('data',d=>{buf+=d;const match=buf.match(/http:\/\/127\.0\.0\.1:\d+\//);if(match){clearTimeout(timeout);resolve(match[0])}});
  });
  const binary=process.env.CHROME_BIN;
  browser=await chromium.launch({...(binary?{executablePath:binary}:{channel:'chrome'}),headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
  for(const id of users){
   const context=await browser.newContext({viewport:{width:1440,height:1000}});
   try{
    const page=await context.newPage(),errors=[],external=[];
    page.on('pageerror',e=>errors.push(String(e)));
    await page.route('**/*',route=>{
     const target=route.request().url();
     if(target.startsWith(url)||target.startsWith('data:')||target.startsWith('blob:'))return route.continue();
     external.push(target);return route.abort();
    });
    const response=await page.goto(url);
    assert.equal(response.status(),200);
    assert.match(response.headers()['content-security-policy'],/connect-src 'self'/);
    assert.match(await page.locator('.demo-auth-footer').innerText(),/Do not enter real school credentials or records/);
    assert.equal((await page.request.get(url+'styles/rollflow-design.css')).status(),200);
    assert.equal((await page.request.get(url+'accounts/models.py')).status(),404);
    assert.equal(await page.locator('.rfu-demo-account').count(),users.length);
    await page.locator('#demo-username').fill(id);
    await page.locator('#demo-password').fill(id);
    await page.locator('#demo-login-form button[type="submit"]').click();
    await page.locator('.rf-compact-account summary').waitFor();
    const actual=await signature(page),expected=await referenceSignature(browser,id,referenceUrl);
    assert(actual.length>0,id+' empty menu');
    assert.deepEqual(actual,expected,id+' packaged menu differs from pinned public source');
    const teacher=['teacher','swilliams'].includes(id);
    const attr=id==='admin'?'data-admin-page':teacher?'data-nav':'data-rfu-page';
    const routes=await page.locator('.nav-primary button').evaluateAll((bs,a)=>bs.map(b=>b.getAttribute(a)).filter(Boolean),attr);
    for(const route of routes){
     const nav=page.locator('.nav-primary ['+attr+'="'+route+'"]');
     if(!await nav.isVisible())await page.locator('[data-rf-portal-menu]').click();
     await nav.click();
     assert((await page.locator('.content-shell>main').innerText()).trim(),id+' '+route);
     const tabs=await page.locator('.rf-compact-tabs button').evaluateAll((bs,a)=>bs.map(b=>b.getAttribute(a)).filter(Boolean),attr);
     for(const tab of tabs){
      const item=page.locator('.rf-compact-tabs ['+attr+'="'+tab+'"]');
      if(await item.isVisible()){
       await item.click();
       assert((await page.locator('.content-shell>main').innerText()).trim(),id+' '+tab);
      }
     }
    }
    await page.locator('.rf-compact-account summary').click();
    await page.locator('.rf-compact-account-panel [data-demo-signout]').click();
    await page.locator('#demo-login-form').waitFor();
    assert.deepEqual(errors,[],id+' browser errors');
    assert.deepEqual(external,[],id+' external requests');
    console.log('PASS packaged workspace: '+id+' ('+routes.length+' primary routes)');
   }finally{await context.close()}
  }
 }finally{if(browser)await browser.close();server.kill();reference.close()}
}
main().catch(e=>{console.error(e);process.exitCode=1});
