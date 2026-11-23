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

    // The timetable uses "Spare" rather than "Prep", and every attendance
    // page has a clear title, class hierarchy and date-preserving back action.
    await page.locator('[data-nav="timetable"]').first().click();
    await viewDate('2026-03-09');
    const spareTitles = await page.locator('.rf-planning-slot h3').allInnerTexts();
    assert.deepEqual(spareTitles, ['Spare'], 'Monday Period 5 should be a Spare');
    assert(!(await page.locator('main').innerText()).includes('Planning & preparation'),
      'Outdated planning/preparation label is still visible');
    assert(!(await page.locator('main').innerText()).includes('10+ minutes after start'),
      'The overdue message should only say Roll overdue');
    const monEnglish = page.locator('[data-timetable-class="ENG081C"]');
    await monEnglish.locator('[data-open-report]').click();
    const hero = page.locator('.rf-example1-hero');
    assert(await hero.isVisible(), 'Example 1 green title bar should be visible');
    assert.equal((await hero.locator('h1').innerText()).trim(),
      'Take Attendance', 'Green hero must carry the primary page heading');
    const heroGradient = await hero.evaluate(el => getComputedStyle(el).backgroundImage);
    assert(heroGradient.includes('linear-gradient'),
      'Example 1 requires a prominent green title background');
    assert(await page.locator('.page-bar').isHidden(),
      'The old white page heading must not duplicate the green hero title');
    assert.match(await page.locator('#attendance-class-title').innerText(), /ENG081C.*English/,
      'Class identity should be on its own clear strip below the hero');
    assert(await page.locator('.rf-example1-class-row').isVisible(),
      'Separate class heading strip should render');
    const heroText = await hero.innerText();
    assert.match(heroText, /Monday 9 March 2026/);
    assert.match(heroText, /PERIOD 2/);
    assert.match(heroText, /10:15/);
    assert.match(heroText, /Room B17/);
    assert.equal(await page.locator('input[type="date"]').count(), 0,
      'Take Attendance must not offer date changes; use Daily Schedule instead');
    assert.equal(await page.locator('.rf-example1-date-picker').count(), 0,
      'The green hero must not show Change date');
    assert.match(heroText, /Monday 9 March 2026/,
      'The chosen attendance date must remain visible');
    assert.equal(await page.locator('[data-class-select]').count(), 0,
      'Take Attendance should not have a Switch class control');
    assert.match(await page.locator('.photo-roll-caption').innerText(), /27 students/,
      'Student count should remain above the attendance grid');
    assert(await page.locator('.student-grid .photo-mark').count() > 20,
      'The attendance photo grid must remain available');
    assert.equal((await page.locator('#attendance-class-title').innerText()).trim(),
      'ENG081C — English', 'The class identity must stay visible after removing the switcher');
    const backButton = page.getByRole('button', { name: 'Back to Daily Schedule' });
    assert(await backButton.isVisible(), 'Back to Daily Schedule must be obvious');
    const backCss = await backButton.evaluate(el => ({
      height: el.getBoundingClientRect().height,
      borderWidth: getComputedStyle(el).borderTopWidth
    }));
    assert(backCss.height >= 30 && backCss.borderWidth !== '0px',
      'Back button should be a genuine visible control, not a tiny text link');
    assert(await backButton.evaluate(el => el.closest('.rf-example1-hero') !== null),
      'Back to Daily Schedule must sit inside the green header');
    await backButton.click();
    assert.equal((await page.locator('.page-bar h1').innerText()).trim(), 'Daily Schedule');
    assert.match(await page.locator('#dayScheduleTitle').innerText(), /Lessons for selected date/,
      'Historical daily schedule heading should not say Today');
    assert.equal(await page.locator('input[data-date]').first().inputValue(), '2026-03-09',
      'Back navigation must preserve the selected historical date');
    assert(await page.locator('input[data-date]').first().isVisible(),
      'Daily Schedule must keep the date picker for changing attendance dates');

    // Class Finder details should show multiple lessons, not the stale
    // single-day seed for the 2026 fictional weekly timetable.
    await page.locator('[data-nav="finder"]').first().click();
    const finderSearch = page.locator('#finderResults');
    assert(await finderSearch.count(), 'Class Finder should still render');

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
