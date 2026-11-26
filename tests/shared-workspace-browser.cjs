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

   if(teacher){
    await page.locator('.nav-primary [data-nav="finder"]').click();
    const code=id==='swilliams'?'ENG071A':'MAF102A';
    await page.locator('#finderQuery').fill(code);
    const card=page.locator('.finder-card[data-class-code="'+code+'"][data-my-class="true"]');
    assert.equal(await card.count(),1,id+' assigned class ownership');
    assert.match(await card.innerText(),/My class/);
    await page.locator('#finderQuery').fill('');
    await page.locator('select[data-finder-field="year"]').selectOption(id==='swilliams'?'7':'10');
    assert(await page.locator('.finder-card').count()>0,id+' filter-only search');
   }
   // Representative full-page geometry and light/dark checks on each account.
   for(const size of [{width:1366,height:768},{width:1024,height:768},{width:820,height:1180},{width:390,height:844}]){
    await page.setViewportSize(size);
    await page.locator('.rf-compact-account summary').click();
    await page.locator('.rf-compact-account-panel').getByRole('button',{name:'My Preferences',exact:true}).click();
    const theme=page.locator(teacher?'[data-v2-setting="theme"]':'[data-rf-personal-setting="theme"]');
    for(const value of ['Dark','Light']){
     await theme.selectOption(value);
     assert.equal(await page.locator('body').getAttribute('data-theme'),value);
     const geometry=await page.locator('.content-shell>main').evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth,rect:el.getBoundingClientRect().right,viewport:innerWidth}));
     assert(geometry.rect<=geometry.viewport+3,id+' '+size.width+' page outside viewport');
     assert(geometry.scroll-geometry.width<=3,id+' '+size.width+' horizontal overflow: '+JSON.stringify(geometry));
    }
   }
   if(!teacher&&['learning','aide','relief'].includes(id)){
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('.nav-primary [data-rfu-page="schedule"]').click();
    await page.locator('[data-rf-unified-view="week"]').click();
    const days=await page.locator('.rf-unified-schedule.week>.timetable-day').evaluateAll(nodes=>nodes.map(n=>({x:n.getBoundingClientRect().x,y:n.getBoundingClientRect().y})));
    assert.equal(days.length,5,id+' five weekdays');
    assert(days.every(n=>Math.abs(n.y-days[0].y)<2),id+' weekdays must stay in one row');
    await page.setViewportSize({width:390,height:844});
    const scroll=await page.locator('.rf-unified-week-scroll').evaluate(el=>({client:el.clientWidth,scroll:el.scrollWidth}));
    assert(scroll.scroll>scroll.client,id+' mobile week has internal horizontal scrolling');
   }
   await page.setViewportSize({width:1440,height:1000});
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
