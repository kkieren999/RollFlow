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
const expected={admin:['Staff Management','Student Management','Account Management','OneSchool Import Centre'],principal:['Student Search','Attendance Overview','Reports'],deputy:['Attendance Overview','Student Movements'],hod:['Class Finder','Master Timetable','Reports'],ylc:['Student Search','Class Finder','Reports'],business:['Staff Directory','Workforce Allocations','Reports'],office:['Student Search','Student Movements'],teacher:['Daily Schedule','Student Support'],swilliams:['Daily Schedule','Student Support'],learning:['Daily Schedule','Student Support'],aide:['Student Support'],relief:['Daily Schedule','Student Support'],guidance:['Student Support']};
async function run(){
 await new Promise((resolve,reject)=>{ref.once('error',reject);ref.listen(0,'127.0.0.1',resolve)});
 const refurl='http://127.0.0.1:'+ref.address().port;
 let browser;const evidence=[];
 try{
  browser=await chromium.launch({channel:'chrome',headless:true});
  for(const [id,login] of Object.entries(mapping)){
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
    }
    assert.equal(await p.locator('main#main-content').count(),1,id+' single main landmark');
    await rp.screenshot({path:path.join(target,id+'-reference-1440.png'),animations:'disabled'});
    await p.screenshot({path:path.join(target,id+'-protected-1440.png'),animations:'disabled'});
    await rp.setViewportSize({width:390,height:844});await p.setViewportSize({width:390,height:844});
    await p.locator('.rf-p-menu').click();assert.equal(await p.locator('.rf-p-menu').getAttribute('aria-expanded'),'true');assert(await p.locator('.rf-protected-sidebar').isVisible());
    await p.keyboard.press('Escape');assert.equal(await p.locator('.rf-p-menu').getAttribute('aria-expanded'),'false');
    await rp.screenshot({path:path.join(target,id+'-reference-390.png'),animations:'disabled'});
    await p.screenshot({path:path.join(target,id+'-protected-390.png'),animations:'disabled'});
    if(id==='admin'){
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
    }
    assert.deepEqual(errors,[],id+' protected script errors');assert.deepEqual(external,[],id+' external requests');
    evidence.push({account:id,reference:referenceLabels,protected:protectedLabels,referenceOnly:referenceLabels.filter(x=>!protectedLabels.includes(x)),protectedOnly:protectedLabels.filter(x=>!referenceLabels.includes(x))});
    console.log('Protected/reference UI captured:',id);
   }finally{await rctx.close();await ctx.close()}
  }
  fs.writeFileSync(path.join(target,'navigation-differences.json'),JSON.stringify({websiteCommit:fs.readFileSync(path.join(root,'SOURCE_COMMIT.txt'),'utf8').trim(),scope:'RC2.1 shell only; differences are open, not approval',accounts:evidence},null,2));
 }finally{if(browser)await browser.close();ref.close()}
}
run().catch(e=>{console.error(e.stack);process.exitCode=1});
