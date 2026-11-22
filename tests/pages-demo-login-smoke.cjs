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

async function logIn(page, username, password) {
  await page.locator('#demo-login-form').waitFor();
  await page.locator('#demo-username').fill(username);
  await page.locator('#demo-password').fill(password);
  await page.locator('#demo-login-form button[type="submit"]').click();
  await page.locator('.top-user > span').waitFor();
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
    await logIn(page, 'admin', 'admin');
    assert(await page.locator('.v31-admin').count(), 'Admin demo login broke');
    console.log('PASS: swilliams login, separate class ownership, teacher switch and admin login.');
  }
  finally {
    if (browser) await browser.close();
    server.close();
  }
}

test().catch(error => { console.error(error); process.exitCode = 1; });
