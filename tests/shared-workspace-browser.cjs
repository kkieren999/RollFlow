// Current role-based navigation and full workspace rendering smoke.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const http=require('node:http');
const path=require('node:path');
const {chromium}=require('playwright-core');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const users=['admin','principal','deputy','hod','ylc','business','office','teacher','swilliams','learning','aide','relief','guidance'];
const counts={admin:10,principal:10,deputy:10,hod:7,ylc:7,business:6,office:8,teacher:7,swilliams:7,learning:5,aide:4,relief:3,guidance:3};
async function run(){
 const server=http.createServer((req,res)=>{res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(html)});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 let browser;
 try{
  browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
  for(const id of users){
   const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
   const errors=[];page.on('pageerror',e=>errors.push(String(e)));
   await page.goto(url);
   assert.match(await page.locator('.demo-auth-footer').innerText(),/Do not enter real school credentials or records/);
   await page.locator('#demo-username').fill(id);await page.locator('#demo-password').fill(id);await page.locator('#demo-login-form button[type="submit"]').click();
   await page.locator('.rf-compact-account summary').waitFor();
   assert.equal(await page.locator('.rf-training-notice').count(),0,'Persistent banner removed');
   assert.equal(await page.locator('.nav-primary button').count(),counts[id],id+' compact menu count');
   const teacher=['teacher','swilliams'].includes(id),attr=id==='admin'?'data-admin-page':teacher?'data-nav':'data-rfu-page';
   for(const label of ['My Profile','My Preferences','Help & Support']){
    await page.locator('.rf-compact-account summary').click();
    await page.locator('.rf-compact-account-panel').getByRole('button',{name:label,exact:true}).click();
    assert.equal(await page.locator('.page-bar h1').innerText(),label,id+' '+label);
    if(!teacher)assert(await page.locator('.rf-personal-main').isVisible(),id+' personal full page');
   }
   if(!teacher){
    const routes=await page.locator('.nav-primary button').evaluateAll((bs,a)=>bs.map(b=>b.getAttribute(a)).filter(Boolean),attr);
    for(const route of routes){
     await page.locator('.nav-primary ['+attr+'="'+route+'"]').click();
     assert((await page.locator('.content-shell>main').innerText()).trim().length>0,id+' '+route);
     const tabs=await page.locator('.rf-compact-tabs button').evaluateAll((bs,a)=>bs.map(b=>b.getAttribute(a)).filter(Boolean),attr);
     for(const tab of tabs){
      await page.locator('.rf-compact-tabs ['+attr+'="'+tab+'"]').click();
      assert((await page.locator('.content-shell>main').innerText()).trim().length>0,id+' '+tab);
     }
    }
   }
   await page.locator('.rf-compact-account summary').click();
   await page.locator('.rf-compact-account-panel').getByRole('button',{name:'Sign out',exact:true}).click();
   await page.locator('#demo-login-form').waitFor();
   assert.deepEqual(errors,[],id+' uncaught browser errors');
   console.log('PASS: '+id+' account pages, compact navigation and workspace rendering');
   await context.close();
  }
 }finally{if(browser)await browser.close();server.close()}
}
run().catch(e=>{console.error(e);process.exitCode=1});
