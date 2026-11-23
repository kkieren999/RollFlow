// Regression smoke for the PUBLIC fictional GitHub Pages demo; no real school data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const vm = require('node:vm');
const { chromium } = require('playwright-core');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/);
assert(script, 'Expected inline RollFlow script');
new vm.Script(script[1], { filename: 'rollflow-pages-inline.js' });

function startServer() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((_req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
    });
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      resolve({ server, url: 'http://127.0.0.1:' + server.address().port + '/' });
    });
  });
}

async function logIn(page, username, password, destination = '.top-user > span') {
  await page.locator('#demo-login-form').waitFor();
  await page.locator('#demo-username').fill(username);
  await page.locator('#demo-password').fill(password);
  await page.locator('#demo-login-form button[type="submit"]').click();
  await page.locator(destination).waitFor();
}

async function test() {
  const { server, url } = await startServer();
  let browser;
  try {
    browser = await chromium.launch({
      executablePath: process.env.CHROME_BIN || '/usr/bin/google-chrome',
      headless: true,
      args: ['--no-sandbox', '--disable-dev-shm-usage']
    });
    const page = await browser.newPage();
    page.on('pageerror', error => { console.error('Browser error:', error); });
    await page.goto(url, { waitUntil: 'load' });
    await page.locator('#demo-login-form').waitFor();

    // Public demo rejects invented credentials.
    await page.locator('#demo-username').fill('swilliams');
    await page.locator('#demo-password').fill('wrong');
    await page.locator('#demo-login-form button[type="submit"]').click();
    assert.match(await page.locator('#demo-login-error').innerText(), /Incorrect demo credentials/);

    await logIn(page, 'swilliams', 'swilliams');
    assert.equal((await page.locator('.top-user > span').innerText()).trim(), 'Sarah Williams');
    await page.locator('[data-nav="classes"]').first().click();
    const englishClasses = await page.locator('main').innerText();
    for (const code of ['ENG071A', 'ENG091B', 'ENG101B', '10BH']) {
      assert(englishClasses.includes(code), 'Missing assigned English class ' + code);
    }
    assert(!englishClasses.includes('MAF102A'), 'Sarah was shown Alex Morgan class');
    for (const code of ['ENG081C', 'ENG101C']) {
      assert(englishClasses.includes(code), 'New 2026 fictional English group missing: ' + code);
    }

    // A real browser renders the full Monday-Friday timetable for any 2026 term week.
    await page.locator('[data-nav="timetable"]').first().click();
    await page.locator('[data-timetable-view="week"]').first().click();
    const scheduleDate = page.locator('input[data-date]').first();
    await scheduleDate.fill('2026-03-09');
    await scheduleDate.dispatchEvent('change');
    const days = page.locator('.timetable-day');
    assert.equal(await days.count(), 5, 'Week view should show all weekdays');
    const requiredPeriodPattern = /^(Home group|Period [1-5])$/;
    for (let day = 0; day < 5; day++) {
      const panel = days.nth(day);
      assert.equal(await panel.locator('.day-lesson').count(), 6,
        'Each weekday should have one home group, four English classes and one preparation period');
      const periodNames = await panel.locator('.lesson-time span').allInnerTexts();
      assert(periodNames.every(x => requiredPeriodPattern.test(x)), 'Unexpected timetable period');
      assert.equal(new Set(periodNames).size, 6, 'Teacher has overlapping periods');
      assert.equal(await panel.locator('.rf-planning-slot').count(), 1,
        'Each full timetable weekday needs one preparation period');
    }

    // Term starts in January and historical dates remain navigable.
    await page.locator('[data-timetable-view="day"]').first().click();
    async function viewDate(iso) {
      const field = page.locator('input[data-date]').first();
      await field.fill(iso);
      await field.dispatchEvent('change');
    }
    await viewDate('2026-01-27');
    assert((await page.locator('main').innerText()).includes('ENG071A'),
      'First day of school should show the assigned Year 7 English lesson');
    await viewDate('2026-05-04');
    assert.equal(await page.locator('.timetable-day .day-lesson').count(), 0,
      'Labour Day public holiday must not show any lessons');
    assert((await page.locator('main').innerText()).includes('Labour Day'));
    await viewDate('2026-08-12');
    assert.equal(await page.locator('.timetable-day .day-lesson').count(), 0,
      'Brisbane Show holiday must not show student lessons');
    await viewDate('2026-09-04');
    assert((await page.locator('main').innerText()).includes('Student-free'));
    await viewDate('2026-06-29');
    assert.equal(await page.locator('.timetable-day .day-lesson').count(), 0,
      'School holidays must not show any student lessons');
    await viewDate('2026-11-27');
    assert((await page.locator('main').innerText()).includes('10BH'),
      'Year 10 home group should operate on the finishing day');
    await viewDate('2026-11-30');
    const afterTen = await page.locator('main').innerText();
    assert(!afterTen.includes('10BH') && !afterTen.includes('ENG101B') && !afterTen.includes('ENG101C'),
      'Year 10 lessons should stop after 27 November');
    await viewDate('2026-12-11');
    assert((await page.locator('main').innerText()).includes('ENG071A'),
      'Year 7 should continue through the final school day');

    // The app must use distinct attendance and workspace stores.
    const keys = await page.evaluate(() => Object.keys(localStorage));
    assert(keys.some(key => key.startsWith('rollflow_workspace_swilliams_')),
      'Sarah-specific workspace did not initialise');
    await page.locator('[data-demo-signout]').first().click();
    await page.locator('#demo-login-form').waitFor();

    await logIn(page, 'teacher', 'teacher');
    assert.equal((await page.locator('.top-user > span').innerText()).trim(), 'Alex Morgan');
    await page.locator('[data-nav="classes"]').first().click();
    const mathsClasses = await page.locator('main').innerText();
    assert(mathsClasses.includes('MAF102A'), 'Default teacher class missing');
    assert(!mathsClasses.includes('ENG071A'), 'Default teacher inherited Sarah class');

    await page.locator('[data-demo-signout]').first().click();
    await page.locator('#demo-login-form').waitFor();
    await logIn(page, 'admin', 'admin', '.v31-admin');
    assert(await page.locator('.v31-admin').count(), 'Admin demo login broke');
    console.log('PASS: swilliams login, separate class ownership, teacher switch and admin login.');
  }
  finally {
    if (browser) await browser.close();
    server.close();
  }
}

test().catch(error => { console.error(error); process.exitCode = 1; });
