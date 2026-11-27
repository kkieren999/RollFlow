// Capture actual installed authenticated UI alongside the pinned fictional website.
// Neither account grants nor student records are copied from reference JS.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('playwright-core');
const url=process.env.RF_PROTECTED_BROWSER_URL,password=process.env.RF_PROTECTED_BROWSER_PASSWORD;
const target=process.env.RF_UI_SCREENSHOTS;
if(!url||!password||!target)throw Error('Disposable UI evidence environment missing');
fs.mkdirSync(target,{recursive:true});
const root=path.resolve(__dirname,'..','training');
const ref=http.createServer((req,res)=>{
 const p=new URL(req.url,'http://localhost').pathname;
 const file=p==='/'?'index.html':p==='/styles/rollflow-design.css'?'styles/rollflow-design.css':null;
 if(!file){res.writeHead(404);res.end();return}
 res.writeHead(200,{'Content-Type':file.endsWith('.css')?'text/css':'text/html; charset=utf-8'});res.end(fs.readFileSync(path.join(root,file)));
});
const mapping={admin:'admin',principal:'principal',deputy:'deputy',hod:'hod',ylc:'ylc',business:'business',office:'office',teacher:'teacher',swilliams:'other',learning:'learning',aide:'aide',relief:'relief',guidance:'guidance'};
const expected={admin:['Staff Management','Student Management','Account Management','OneSchool Import Centre','System Management'],principal:['Student Search','Attendance Overview','Reports'],deputy:['Attendance Overview','Student Movements'],hod:['Class Finder','Master Timetable','Reports'],ylc:['Student Search','Class Finder','Reports'],business:['Staff Directory','Workforce Allocations','Reports'],office:['Student Search','Student Movements'],teacher:['Daily Schedule','Master Timetable','Class Finder','Student Search','Student Support'],swilliams:['Daily Schedule','Master Timetable','Class Finder','Student Search','Student Support'],learning:['Daily Schedule','Student Support'],aide:['Student Support'],relief:['Daily Schedule','Student Support'],guidance:['Student Support']};
async function run(){
 await new Promise((resolve,reject)=>{ref.once('error',reject);ref.listen(0,'127.0.0.1',resolve)});
 const refurl='http://127.0.0.1:'+ref.address().port;
 let browser;const evidence=[];
 const selected=(process.env.RF_UI_ACCOUNT_IDS||'').split(',').filter(Boolean);
 const batch=Number(process.env.RF_UI_BATCH);
 if(!selected.length||selected.some(id=>!Object.hasOwn(mapping,id))||!Number.isInteger(batch)||batch<0||batch>2)throw Error('Invalid isolated browser test batch');
 try{
  browser=await chromium.launch({channel:'chrome',headless:true});
  for(const [id,login] of Object.entries(mapping).filter(([id])=>selected.includes(id))){
   const rctx=await browser.newContext({viewport:{width:1440,height:900}}),ctx=await browser.newContext({viewport:{width:1440,height:900}});
   try{
    const rp=await rctx.newPage(),p=await ctx.newPage(),errors=[],external=[];
    p.on('pageerror',e=>errors.push(e.message));
    await p.route('**/*',route=>{if(route.request().url().startsWith(url+'/'))return route.continue();external.push(route.request().url());return route.abort()});
    await rp.route('**/*',route=>route.request().url().startsWith(refurl+'/')||/^(data:|blob:)/.test(route.request().url())?route.continue():route.abort());
    await rp.goto(refurl+'/');await rp.locator('#demo-username').fill(id);await rp.locator('#demo-password').fill(id);await rp.locator('#demo-login-form button[type=submit]').click();await rp.locator('.rf-compact-account summary').waitFor();
    await p.goto(url+'/login/');await p.locator('#username').fill('browser_'+login);await p.locator('#password').fill(password);
    await Promise.all([p.waitForURL('**/live/'),p.getByRole('button',{name:'Sign in'}).click()]);
    if(['teacher','swilliams'].includes(id))await p.goto(url+'/live/day/');
    if(id==='admin')await p.goto(url+'/manage/');
    const shell=p.locator('[data-rf-shell=protected]');await shell.waitFor();
    assert.equal(await shell.count(),1,id+' single shell');
    assert.equal(await shell.getAttribute('data-enhanced'),'true',id+' local script loaded');
    assert.equal(await p.locator('.rf-protected-sidebar').evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(17, 35, 50)',id+' local stylesheet loaded');
    const protectedLabels=await p.locator('.rf-p-navlink').allInnerTexts(),referenceLabels=await rp.locator('.nav-primary button').allInnerTexts();
    for(const label of expected[id])assert(protectedLabels.includes(label),id+' missing '+label);
    if(id!=='admin'){
     assert(!protectedLabels.includes('Account Management'),id+' admin link leaked');
     assert.equal((await ctx.request.get(url+'/manage/access/')).status(),403,id+' direct admin boundary');
     for(const route of ['/manage/system/','/manage/system/accounts/','/manage/system/audit/','/manage/system/settings/','/manage/system/pilot/'])assert.equal((await ctx.request.get(url+route)).status(),403,id+' administration review boundary');
    }
    assert.equal(await p.locator('main#main-content').count(),1,id+' single main landmark');
    const desktopMetrics=await p.evaluate(()=>({viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,domNodes:document.querySelectorAll('*').length,loadMs:Math.round(performance.getEntriesByType('navigation')[0]?.duration||0)}));
    await rp.screenshot({path:path.join(target,id+'-reference-1440.png'),animations:'disabled'});
    await p.screenshot({path:path.join(target,id+'-protected-1440.png'),animations:'disabled'});
    await rp.setViewportSize({width:390,height:844});await p.setViewportSize({width:390,height:844});
    await p.locator('.rf-p-menu').focus();await p.keyboard.press('Enter');assert.equal(await p.locator('.rf-p-menu').getAttribute('aria-expanded'),'true');assert(await p.locator('.rf-protected-sidebar').isVisible());
    assert(await p.locator('.rf-protected-sidebar').evaluate(el=>el.contains(document.activeElement)),id+' mobile menu focus enters sidebar');
    await p.keyboard.press('Escape');assert.equal(await p.locator('.rf-p-menu').getAttribute('aria-expanded'),'false');
    assert(await p.locator('.rf-p-menu').evaluate(el=>document.activeElement===el),id+' Escape returns focus');
    await p.locator('a.rf-skip[href="#main-content"]').focus();await p.keyboard.press('Enter');
    assert(await p.locator('#main-content').evaluate(el=>document.activeElement===el),id+' skip link reaches main');
    const mobileMetrics=await p.evaluate(()=>({viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,scrollRegions:[...document.querySelectorAll('[data-rf-scrollable="true"]')].length}));
    assert(await p.evaluate(()=>[...document.querySelectorAll('[data-rf-scrollable="true"]')].every(el=>el.tabIndex>=0&&(el.hasAttribute('aria-label')||el.hasAttribute('aria-labelledby')))),id+' overflowing tables are keyboard reachable and named');
    await p.setViewportSize({width:320,height:700});
    const narrowMetrics=await p.evaluate(()=>({viewport:innerWidth,documentWidth:document.documentElement.scrollWidth}));
    await p.setViewportSize({width:390,height:844});
    await p.locator('.rf-p-menu').focus();
    await rp.screenshot({path:path.join(target,id+'-reference-390.png'),animations:'disabled'});
    await p.screenshot({path:path.join(target,id+'-protected-390.png'),animations:'disabled'});
    if(id==='admin'){
      await p.setViewportSize({width:1440,height:900});
      for(const [label,route] of [['overview','/manage/system/'],['accounts','/manage/system/accounts/'],['audit','/manage/system/audit/'],['settings','/manage/system/settings/']]){
        assert.equal((await p.goto(url+route)).status(),200,'RC2.5 admin '+label);
        assert.equal(await p.locator('main#main-content').count(),1);
        await p.screenshot({path:path.join(target,'admin-'+label+'-1440.png'),animations:'disabled'});
      }
      assert.match(await p.locator('main').innerText(),/Production blocked/);
      assert.equal((await p.goto(url+'/manage/system/pilot/')).status(),200);
      assert.match(await p.locator('main').innerText(),/Rehearsal scenarios \(12\)/);
      assert.match(await p.locator('main').innerText(),/Open production gates \(10\)/);
      await p.screenshot({path:path.join(target,'admin-pilot-readiness-1440.png'),animations:'disabled'});
      await p.goto(url+'/manage/system/settings/');
      await p.setViewportSize({width:390,height:844});await p.screenshot({path:path.join(target,'admin-settings-390.png'),animations:'disabled'});
      await p.setViewportSize({width:1440,height:900});await p.goto(url+'/manage/access/');
      await p.locator('#id_scope').selectOption('school');
      assert(await p.locator('input[name=capabilities][value=movement_receive]').isDisabled());
      assert(!(await p.locator('input[name=capabilities][value=attendance_monitor]').isDisabled()));
      await p.locator('input[name=capabilities][value=attendance_monitor]').check();
      await p.locator('#id_scope').selectOption('faculty');
      assert(await p.locator('input[name=capabilities][value=attendance_monitor]').isChecked());
      assert.match(await p.locator('#rf-scope-guidance').innerText(),/incompatible/);
      await p.locator('input[name=capabilities][value=attendance_monitor]').uncheck();
      assert(await p.locator('input[name=capabilities][value=attendance_monitor]').isDisabled());
      await p.screenshot({path:path.join(target,'admin-grant-scope.png'),animations:'disabled'});
    }
    if(id==='teacher'){
      await p.setViewportSize({width:1440,height:900});await p.locator('.rf-p-account summary').click();
      await Promise.all([p.waitForNavigation(),p.getByRole('button',{name:'Dark mode'}).click()]);
      assert.equal(await p.locator('[data-rf-shell=protected]').getAttribute('data-theme'),'dark');
      await p.reload();assert.equal(await p.locator('[data-rf-shell=protected]').getAttribute('data-theme'),'dark');
      await p.screenshot({path:path.join(target,'teacher-protected-dark.png'),animations:'disabled'});
      for(const [label,route] of [['week','/teacher/week/'],['master','/live/teacher/master/'],['classes','/live/teacher/classes/'],['class-detail','/live/teacher/classes/BROWSER7/'],['students','/live/teacher/students/'],['roll','/live/roll/?code=BROWSER7&period=P1&start=00%3A00'],['classroom','/live/classroom/?code=BROWSER7&period=P1&start=00%3A00'],['support','/live/support/'],['movements','/live/movements/']]){
        const res=await p.goto(url+route);assert.equal(res.status(),200,'RC2.2 '+label);
        assert.doesNotMatch(await p.locator('main').innerText(),/BrowserDenied|BROWSER8/);
        if(label==='movements'){
          await p.locator('#rf-movement-search[data-ready=true]').waitFor({state:'visible',timeout:10000});
          assert(await p.locator('#rf-movement-query').isEnabled(),'Movement filter script loaded');
        }
        await p.screenshot({path:path.join(target,'teacher-'+label+'-protected-dark.png'),animations:'disabled'});
      }
    }
    if(['principal','deputy','hod','ylc','business','office'].includes(id)){
      await p.setViewportSize({width:1440,height:900});
      const resp=await p.goto(url+'/live/leadership/');assert.equal(resp.status(),200,id+' leadership overview');
      assert.equal(await p.locator('[data-rf-leadership-domain]').count(),1);
      assert.doesNotMatch(await p.locator('main').innerText(),/BrowserAllowed|BrowserDenied/);
      if(id==='hod'||id==='ylc'){
        assert.equal(await p.locator('[data-rf-leadership-scope]').getAttribute('data-rf-leadership-scope'),id==='hod'?'faculty':'year');
        assert.equal((await ctx.request.get(url+'/live/leadership/?domain=attendance&scope=school')).status(),403);
        assert.equal((await ctx.request.get(url+'/live/workforce/')).status(),403);
      }
      await p.screenshot({path:path.join(target,id+'-leadership-1440.png'),animations:'disabled'});
      if(['principal','deputy','business','office'].includes(id)){
        assert.equal((await p.goto(url+'/live/workforce/?view=absence')).status(),200);
        assert.equal(await p.getByRole('link',{name:'Staff availability',exact:true}).getAttribute('aria-current'),'page');
        assert.equal(await p.getByRole('button',{name:'Approve change'}).count(),0);
        await p.screenshot({path:path.join(target,id+'-workforce-1440.png'),animations:'disabled'});
      }
    }
    assert.deepEqual(errors,[],id+' protected script errors');assert.deepEqual(external,[],id+' external requests');
    evidence.push({account:id,desktopMetrics,mobileMetrics,narrowMetrics,reference:referenceLabels,protected:protectedLabels,referenceOnly:referenceLabels.filter(x=>!protectedLabels.includes(x)),protectedOnly:protectedLabels.filter(x=>!referenceLabels.includes(x))});
    console.log('Protected/reference UI captured:',id);
   }finally{await rctx.close();await ctx.close()}
  }
  const outfile=path.join(target,'navigation-differences.json');
  const prior=batch===0?[]:JSON.parse(fs.readFileSync(outfile,'utf8')).accounts;
  const combined=[...prior,...evidence];
  assert.equal(new Set(combined.map(x=>x.account)).size,combined.length,'Duplicate evidence account');
  if(batch===2)assert.deepEqual(combined.map(x=>x.account).sort(),Object.keys(mapping).sort(),'All 13 reference accounts captured');
  fs.writeFileSync(outfile,JSON.stringify({websiteCommit:fs.readFileSync(path.join(root,'SOURCE_COMMIT.txt'),'utf8').trim(),scope:'RC2.7 protected workflow visual/accessibility checks across 13 roles; measurements are diagnostic, not capacity or compliance certification; differences are open, not approval',accounts:combined},null,2));
 }finally{if(browser)await browser.close();ref.close()}
}
run().catch(e=>{console.error(e.stack);process.exitCode=1});
