const assert=require('node:assert/strict');
const {chromium}=require('playwright-core');
const url=process.env.RF_PROTECTED_BROWSER_URL;
const password=process.env.RF_PROTECTED_BROWSER_PASSWORD;
if(!url||!password)throw Error('Disposable protected browser fixture missing');
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try{
    const teacher=await browser.newContext(),monitor=await browser.newContext(),other=await browser.newContext();
    async function login(ctx,user){
      const page=await ctx.newPage();
      await page.route('**/*',route=>route.request().url().startsWith(url+'/')?route.continue():route.abort());
      await page.goto(url+'/login/');
      await page.locator('#username').fill(user);
      await page.locator('#password').fill(password);
      await Promise.all([page.waitForURL('**/live/'),page.getByRole('button',{name:'Sign in'}).click()]);
      return page;
    }
    const t=await login(teacher,'browser_teacher');
    const m=await login(monitor,'browser_monitor');
    const o=await login(other,'browser_other');
    const lesson='/live/roll/?code=BROWSER7&period=P1&start=00%3A00';
    assert.equal((await t.goto(url+lesson)).status(),200);
    assert.match(await t.locator('main').innerText(),/BrowserAllowed/);
    assert.doesNotMatch(await t.locator('main').innerText(),/BrowserDenied/);
    assert.equal((await o.goto(url+lesson)).status(),403);
    assert.equal((await m.goto(url+lesson)).status(),403);
    assert.equal((await t.goto(url+lesson)).status(),200);
    // RC2.2 buttons update the single existing select/form value; no parallel API.
    await t.locator('.rf-mark-buttons button[data-mark="A"]').click();
    assert.equal(await t.locator('select[name^="mark_"]').inputValue(),'A');
    assert.equal(await t.locator('[data-rf-count="A"]').innerText(),'1');
    await t.locator('.rf-mark-buttons button[data-mark="P"]').click();
    assert.equal(await t.locator('select[name^="mark_"]').inputValue(),'P');
    assert.equal(await t.locator('[data-rf-count="P"]').innerText(),'1');
    await t.locator('input[name="certify"]').check();
    await t.getByRole('button',{name:'Submit and lock'}).click();
    await t.getByText('This roll is locked.',{exact:false}).waitFor();
    assert.equal(await t.locator('select[name^="mark_"]').isDisabled(),true);
    assert.equal((await m.goto(url+'/live/attendance/')).status(),200);
    const r=m.locator('tr').filter({hasText:'BROWSER7'});
    assert.match(await r.innerText(),/Submitted/);
    assert.doesNotMatch(await m.locator('main').innerText(),/BrowserAllowed|BrowserDenied/);
    assert.equal((await o.goto(url+'/live/attendance/')).status(),403);
    assert.equal((await t.goto(url+'/live/teacher/classes/')).status(),200);
    assert.match(await t.locator('main').innerText(),/BROWSER7/);
    assert.doesNotMatch(await t.locator('main').innerText(),/BROWSER8/);
    await t.getByRole('link',{name:'View class'}).click();
    assert.match(await t.locator('main').innerText(),/BrowserAllowed/);
    assert.doesNotMatch(await t.locator('main').innerText(),/BrowserDenied/);
    await t.getByRole('link',{name:'View student'}).click();
    assert.match(await t.locator('main').innerText(),/BrowserAllowed/);
    assert.equal((await o.goto(url+'/live/teacher/classes/BROWSER7/')).status(),404);
    assert.equal((await m.goto(url+'/live/teacher/students/')).status(),403);
    await t.goto(url+'/live/day/');await t.getByRole('link',{name:'Week',exact:true}).click();
    assert.equal(await t.locator('[data-schedule-date]').count(),5);
    assert.doesNotMatch(await t.locator('main').innerText(),/BROWSER8/);
    console.log('Protected installed app: independent sessions, roster isolation, submitted roll and monitor verified.');
  }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
