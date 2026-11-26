// Current role-based navigation and full workspace rendering smoke.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const http=require('node:http');
const path=require('node:path');
const {chromium}=require('playwright-core');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const screenshotDir=process.env.RF_UI_SCREENSHOTS;
if(screenshotDir)fs.mkdirSync(screenshotDir,{recursive:true});
async function capture(page,name){
 if(!screenshotDir)return;
 await page.screenshot({path:path.join(screenshotDir,name.replace(/[^a-zA-Z0-9_-]/g,'-')+'.png'),animations:'disabled',fullPage:false});
}
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
   let stage='login';try{
   await context.addInitScript(()=>{
    if(localStorage.getItem('rollflow_calendar_v1')===null){
     const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Australia/Brisbane',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
     localStorage.setItem('rollflow_calendar_v1',JSON.stringify([
      {id:'qa-operational',title:'QA pupil-free day',date:today,end:today,category:'Pupil-free day',impact:'non-teaching'},
      {id:'qa-general',title:'QA community celebration',date:today,category:'School event'}
     ]));
    }
   });
   await page.goto(url);
   assert.match(await page.locator('.demo-auth-footer').innerText(),/Do not enter real school credentials or records/);
   await page.locator('#demo-username').fill(id);await page.locator('#demo-password').fill(id);await page.locator('#demo-login-form button[type="submit"]').click();
   await page.locator('.rf-compact-account summary').waitFor();
   assert.equal(await page.locator('.rf-training-notice').count(),0,'Persistent banner removed');
   assert.equal(await page.locator('.nav-primary button').count(),counts[id],id+' compact menu count');
   assert.equal(await page.locator('.nav-primary [data-nav="school-calendar"],.nav-primary [data-rfu-page="calendar"],.rf-compact-tabs [data-nav="school-calendar"],.rf-compact-tabs [data-rfu-page="calendar"]').count(),0,id+' calendar route removed');
   assert.equal(await page.locator('.nav-primary [data-rfu-page="supervision"],.rf-compact-tabs [data-rfu-page="supervision"]').count(),0,id+' supervision route removed');
   const teacher=['teacher','swilliams'].includes(id),attr=id==='admin'?'data-admin-page':teacher?'data-nav':'data-rfu-page';
   await capture(page,id+'-desktop-landing');
   for(const label of ['My Profile','My Preferences','Help & Support']){
    stage=label;
    await page.locator('.rf-compact-account summary').click();
    await page.locator('.rf-compact-account-panel').getByRole('button',{name:label,exact:true}).click();
    assert.equal(await page.locator('.page-bar h1').innerText(),label,id+' '+label);
    if(!teacher)assert(await page.locator('.rf-personal-main').isVisible(),id+' personal full page');
    await capture(page,id+'-desktop-'+label);
   }
   if(!teacher){
    const routes=await page.locator('.nav-primary button').evaluateAll((bs,a)=>bs.map(b=>b.getAttribute(a)).filter(Boolean),attr);
    for(const route of routes){
     stage='desktop '+route;
     await page.locator('.nav-primary ['+attr+'="'+route+'"]').click();
     assert((await page.locator('.content-shell>main').innerText()).trim().length>0,id+' '+route);
     await capture(page,id+'-desktop-'+route);
     const tabs=await page.locator('.rf-compact-tabs button').evaluateAll((bs,a)=>bs.map(b=>b.getAttribute(a)).filter(Boolean),attr);
     for(const tab of tabs){
      await page.locator('.rf-compact-tabs ['+attr+'="'+tab+'"]').click();
      assert((await page.locator('.content-shell>main').innerText()).trim().length>0,id+' '+tab);
      await capture(page,id+'-desktop-'+tab);
     }
    }
   }

   if(id==='admin'||['principal','deputy','business'].includes(id)){
    const attr=id==='admin'?'data-admin-page':'data-rfu-page',route=id==='admin'?'timetable':'master';
    await page.locator('.nav-primary ['+attr+'="'+route+'"]').click();
    assert.equal(await page.locator('.rf-scheduling-manage').count(),1,id+' authorised exception manager');
    assert(!await page.locator('.content-shell>main').innerText().then(t=>t.includes('QA community celebration')),id+' general events hidden');
   }else if(!teacher){
    const route=await page.locator('.nav-primary [data-rfu-page="schedule"]').count()?'schedule':await page.locator('.nav-primary [data-rfu-page="master"]').count()?'master':'dashboard';
    await page.locator('.nav-primary [data-rfu-page="'+route+'"]').click();
    assert.equal(await page.locator('.rf-scheduling-manage').count(),0,id+' read-only exception access');
    assert.match(await page.locator('.rf-scheduling-notices').innerText(),/QA pupil-free day/);
    assert(!await page.locator('.rf-scheduling-notices').innerText().then(t=>t.includes('QA community celebration')));
   }
   if(teacher){
    await page.locator('.nav-primary [data-nav="timetable"]').click();
    assert.equal(await page.locator('.rf-compact-tabs').count(),0,id+' daily schedule has no redundant tabs');
    if(id==='teacher'){
     await page.locator('[data-date]').fill('2026-11-25');
     assert.equal(await page.locator('[data-timetable-class]').count(),4,'Alex Wednesday has home group and three classes');
     assert(await page.locator('[data-rf-duty]').count()>0,'Alex Wednesday library duty');
     const heights=await page.locator('.day-lessons .rf-timetable-card').evaluateAll(xs=>xs.map(x=>x.getBoundingClientRect().height));
     assert(heights.every(h=>h<160),'Daily cards should not stretch: '+heights.join(','));
     await page.locator('[data-timetable-view="week"]').click();
     const order=await page.locator('.rf-week-grid .timetable-day').first().locator('.rf-week-slot').evaluateAll(xs=>xs.map(x=>x.dataset.rfPeriod));
     assert(order.indexOf('2')<order.indexOf('duty:11:25')&&order.indexOf('duty:11:25')<order.indexOf('3'),'Duty at 11:25 between Period 2 and 3');
     assert(order.indexOf('3')<order.indexOf('duty:12:45')&&order.indexOf('duty:12:45')<order.indexOf('4'),'Duty at 12:45 between Period 3 and 4');
     await capture(page,'teacher-semester2-week');
     await page.locator('[data-timetable-view="day"]').click();
     for(const date of ['2026-07-13','2026-08-03','2026-09-14','2026-10-06','2026-11-25']){
      await page.locator('[data-date]').fill(date);
      assert(await page.locator('[data-timetable-class]').count()>=4,'Alex full school day '+date);
     }
     await page.locator('[data-date]').fill('2026-12-09');
     assert(await page.locator('[data-timetable-class="MAT072D"]').count()>0,'Year 7 continues in December');
     await page.locator('[data-date]').fill('2026-09-23');
     assert.equal(await page.locator('[data-timetable-class]').count(),0,'School holidays have no classes');
    }else{
     assert(await page.locator('[data-rf-duty]').count()>0,id+' allocated supervision in daily schedule');
    }
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
    stage='responsive '+size.width+'x'+size.height;
    await page.setViewportSize(size);
    await page.locator('.rf-compact-account summary').click();
    await capture(page,id+'-'+size.width+'-account-menu');
    await page.locator('.rf-compact-account-panel').getByRole('button',{name:'My Preferences',exact:true}).click();
    const theme=page.locator(teacher?'[data-v2-setting="theme"]':'[data-rf-personal-setting="theme"]');
    for(const value of ['Dark','Light']){
     await theme.selectOption(value);
     assert.equal(await page.locator('body').getAttribute('data-theme'),value);
     const geometry=await page.locator('.content-shell>main').evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth,rect:el.getBoundingClientRect().right,viewport:innerWidth}));
     assert(geometry.rect<=geometry.viewport+3,id+' '+size.width+' page outside viewport');
     assert(geometry.scroll-geometry.width<=3,id+' '+size.width+' horizontal overflow: '+JSON.stringify(geometry));
     await capture(page,id+'-'+size.width+'-preferences-'+value);
    }
   }
   if(!teacher&&['learning','aide','relief'].includes(id)){
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('.nav-primary [data-rfu-page="schedule"]').click();
    assert(await page.locator('[data-rf-duty]').count()>0,id+' allocated supervision in daily schedule');
    await page.locator('[data-rf-unified-view="week"]').click();
    const days=await page.locator('.rf-unified-schedule.week>.timetable-day').evaluateAll(nodes=>nodes.map(n=>({x:n.getBoundingClientRect().x,y:n.getBoundingClientRect().y})));
    assert.equal(days.length,5,id+' five weekdays');
    assert(days.every(n=>Math.abs(n.y-days[0].y)<2),id+' weekdays must stay in one row');
    await page.setViewportSize({width:390,height:844});
    const scroll=await page.locator('.rf-unified-week-scroll').evaluate(el=>({client:el.clientWidth,scroll:el.scrollWidth}));
    assert(scroll.scroll>scroll.client,id+' mobile week has internal horizontal scrolling');
   }
   stage='mobile sign out';
   await page.setViewportSize({width:390,height:844});
   await page.locator('.rf-compact-account summary').click();
   await page.locator('.rf-compact-account-panel').getByRole('button',{name:'Sign out',exact:true}).click();
   await page.locator('#demo-login-form').waitFor();
   assert.deepEqual(errors,[],id+' uncaught browser errors');
   console.log('PASS: '+id+' account pages, compact navigation and workspace rendering');
   }catch(error){console.error('Failure on '+id+' at '+stage);await capture(page,id+'-failure').catch(()=>{});throw error}finally{await context.close();}
  }
  // A real allocation through the workforce form must follow the selected recipient,
  // never another user's account, and must not create a separate navigation route.
  const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
  try{
   async function login(id){await page.goto(url);await page.locator('#demo-username').fill(id);await page.locator('#demo-password').fill(id);await page.locator('#demo-login-form button[type="submit"]').click();await page.locator('.rf-compact-account summary').waitFor()}
   async function logout(){await page.locator('.rf-compact-account summary').click();await page.locator('.rf-compact-account-panel [data-demo-signout]').click();await page.locator('#demo-login-form').waitFor()}
   await login('business');await page.locator('.nav-primary [data-rfu-page="workforce"]').click();
   await page.locator('.rf-duty-management summary').click();
   await page.locator('#rf-duty-form [name="owner"]').selectOption('teacher');
   await page.locator('#rf-duty-form [name="title"]').fill('QA allocated playground duty');
   await page.locator('#rf-duty-form [name="time"]').fill('10:45');
   await page.locator('#rf-duty-form [name="detail"]').fill('Junior courtyard');
   await page.locator('#rf-duty-form button[type="submit"]').click();
   assert.match(await page.locator('.rf-duty-management').innerText(),/QA allocated playground duty/);
   await logout();await login('teacher');await page.locator('.nav-primary [data-nav="timetable"]').click();
   assert.match(await page.locator('[data-rf-duty]').allInnerTexts().then(x=>x.join(' ')),/QA allocated playground duty/);
   await logout();await login('swilliams');await page.locator('.nav-primary [data-nav="timetable"]').click();
   assert(!await page.locator('[data-rf-duty]').allInnerTexts().then(x=>x.join(' ').includes('QA allocated playground duty')));
   console.log('PASS: assigned supervision follows the recipient and remains in Daily Schedule');
  }finally{await context.close()}
 }finally{if(browser)await browser.close();server.close()}
}
run().catch(e=>{console.error(e);process.exitCode=1});
