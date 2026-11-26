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
const studentCalcStart=script[1].indexOf('function rfActiveStudentMemberships');
const studentCalcEnd=script[1].indexOf('function rfStudentAttendanceBody',studentCalcStart);
const attendanceFixture={classes:['OLD','NEW','EMPTY'].map(code=>({code,name:code,active:true})),slots:['OLD','NEW','EMPTY'].map(classCode=>({classCode,active:true})),enrolments:[{studentId:'S',classCode:'OLD',start:'2026-01-27',end:'2026-06-26'},{studentId:'S',classCode:'NEW',start:'2026-08-01',end:''},{studentId:'S',classCode:'EMPTY',start:'2026-07-13',end:''}]};
const fixtureMarks={'2026-03-09|OLD':{S:'P'},'2026-07-14|NEW':{S:'A'},'2026-08-03|NEW':{S:'P'},'2026-08-04|NEW':{S:'L'},'2026-08-05|NEW':{S:'A'},'2026-08-06|NEW':{S:'P'},'2026-08-07|NEW':{S:'?'}};
const fixtureSubmitted=Object.fromEntries(Object.keys(fixtureMarks).filter(k=>k!=='2026-08-06|NEW').map(k=>[k,{}]));
const calc=new Function('planning','previewStudents','SARAH_2026_YEAR10_FINISH','brisbaneToday','state','KEY','localStorage',script[1].slice(studentCalcStart,studentCalcEnd)+'return rfStudentAttendance;')(attendanceFixture,[{id:'S',status:'active'}],'2026-11-27',()=> '2026-11-24',{marks:{},submitted:{}},'',{});
const semesterResult=calc('S','2026-11-24',[{marks:fixtureMarks,submitted:fixtureSubmitted}]);
assert.deepEqual(semesterResult.rows.map(r=>r.code),['NEW','EMPTY']);
assert.equal(semesterResult.rows[0].total,3);
assert(Math.abs(semesterResult.rows[0].percent-200/3)<0.0001);
assert.equal(semesterResult.rows[1].percent,null);
console.log('PASS: semester and enrolment boundaries, late counted present, unsubmitted and unknown excluded.');


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


async function signOut(page){
 await page.locator('.rf-compact-account summary').click();
 await page.locator('.rf-compact-account-panel [data-demo-signout]').click();
 await page.locator('#demo-login-form').waitFor();
}
async function openRoute(page,attr,route){
 const teacher=attr==='data-nav';
 if(teacher&&['profile','preferences','help'].includes(route)){
  await page.locator('.rf-compact-account summary').click();
  await page.locator('.rf-compact-account-panel ['+attr+'="'+route+'"]').click();return;
 }
 if(teacher&&route==='alerts'){await page.locator('.rf-compact-header-action').click();return;}
 if(teacher&&route==='home')route='timetable';
 const parents=teacher?{'classroom-management':'finder','seating-plans':'finder','class-lists':'finder','school-calendar':'timetable','follow-ups':'student-support'}:{'student-actions':'students','master':'timetable','classes':'timetable','roles':'accounts','audit':'security','data':'oneschool'};
 const primary=parents[route]||route;
 const nav=page.locator('.nav-primary ['+attr+'="'+primary+'"]');
 if(!await nav.isVisible())await page.locator('[data-rf-portal-menu]').click();
 await nav.click();
 if(primary!==route)await page.locator('.rf-compact-tabs ['+attr+'="'+route+'"]').click();
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
    assert.match(await page.locator('.demo-auth-footer').innerText(), /Training workspace.*Do not enter real school credentials or records/);

    // Public training access rejects invented credentials.
    await page.locator('#demo-username').fill('swilliams');
    await page.locator('#demo-password').fill('wrong');
    await page.locator('#demo-login-form button[type="submit"]').click();
    assert.match(await page.locator('#demo-login-error').innerText(), /Incorrect training access details/);

    await logIn(page, 'swilliams', 'swilliams');
    assert.equal((await page.locator('.top-user > span').innerText()).trim(), 'Sarah Williams');
    assert.equal(await page.locator('.rf-training-notice').count(), 0, 'Persistent training banner was removed; disclosure remains on sign-in');
    assert.equal(await page.locator('.permanent-sidebar [data-nav="classes"]').count(), 0, 'My Classes must not appear in the menu');
    assert.equal(await page.locator('.permanent-sidebar [data-nav="roll"]').count(), 0, 'Mark Attendance must not appear in the menu');
    await openRoute(page,'data-nav','finder');
    assert.equal(await page.locator('[data-teacher-scope]').count(), 0, 'Class Finder must not show the scope selector');
    assert.equal(await page.locator('.page-right .tag').count(),0,'Class count badge removed');
    const englishOwned=[];
    for(const code of ['ENG071A','ENG091B','ENG101B','10BH','ENG081C','ENG101C','MAF102A']){
      await page.locator('#finderQuery').fill(code);
      if(await page.locator('.finder-card[data-class-code="'+code+'"][data-my-class="true"]').count())englishOwned.push(code);
    }
    const englishClasses=englishOwned.join(' ');
    for (const code of ['ENG071A', 'ENG091B', 'ENG101B', '10BH']) {
      assert(englishClasses.includes(code), 'Missing assigned English class ' + code);
    }
    assert(!englishClasses.includes('MAF102A'), 'Sarah was shown Alex Morgan class');
    for (const code of ['ENG081C', 'ENG101C']) {
      assert(englishClasses.includes(code), 'New 2026 fictional English group missing: ' + code);
    }

    // Student timetable uses the selected weekday, including recurring Sarah classes.
    await openRoute(page,'data-nav','search');
    await page.locator('#studentQuery').fill('S7001');
    await page.locator('[data-open-student="S7001"]').first().click();
    await page.locator('[data-action="showTimetable"]').click();
    assert.equal(await page.locator('[data-rf-student-day]').count(),5);
    for(const day of ['Monday','Tuesday','Wednesday','Thursday','Friday']){
      await page.locator('[data-rf-student-day="'+day+'"]').click();
      assert.equal(await page.locator('[data-rf-student-day][aria-pressed="true"]').getAttribute('data-rf-student-day'),day);
      assert.equal(await page.locator('#rf-student-day-lessons').getAttribute('aria-label'),day+' lessons');
    }
    await page.locator('#modal [data-action="closeModal"]').first().click();
    await page.locator('#overlay [data-action="closeDrawer"]').first().click();

    // Student action controls and cross-role local referral flow.
    await openRoute(page,'data-nav','search');
    await page.locator('#studentQuery').fill('S7001');
    await page.locator('[data-open-student="S7001"]').first().click();
    await page.locator('[data-rf-student-action="details"]').click();
    assert.equal(await page.locator('.rf-student-profile-grid dt').count(),28);
    assert.match(await page.locator('.rf-student-profile-grid').innerText(),/PIN #\s+Restricted/);
    await page.locator('#review-dialog [data-review-close]').first().click();
    await page.locator('[data-rf-student-action="attendance"]').click();
    assert.match(await page.locator('#review-dialog').innerText(),/Semester [12]/);
    await page.locator('#review-dialog [data-review-close]').first().click();
    await page.locator('[data-rf-classroom-picker]').click();
    await page.locator('#review-dialog [data-rf-student-action="late"]').click();
    assert(await page.locator('#rf-student-incident-form [name="time"]').isVisible());
    await page.locator('#rf-student-incident-form [name="type"]').selectOption('Late arrival');
    await page.locator('#rf-student-incident-form [name="response"]').selectOption('Refer to admin support');
    await page.locator('#rf-student-incident-form button[type="submit"]').click();
    assert.equal(await page.locator('#review-dialog').count(),0);
    await page.locator('#overlay [data-action="closeDrawer"]').click();
    await signOut(page);
    await logIn(page,'admin','admin','.v31-admin');
    await openRoute(page,'data-admin-page','student-actions');
    assert.match(await page.locator('.v31-content main').innerText(),/Awaiting support/);
    await page.locator('[data-rf-resolve-referral]').first().click();
    assert.match(await page.locator('.v31-content main').innerText(),/Resolved/);
    await page.locator('[data-rf-action-config="new"]').click();
    await page.locator('#rf-action-config-form [name="name"]').fill('Classroom follow-up');
    await page.locator('#rf-action-config-form [name="types"]').fill('Learning concern\nEquipment concern');
    await page.locator('#rf-action-config-form [name="responses"]').fill('Discussed\nRecord only');
    await page.locator('#rf-action-config-form button[type="submit"]').click();
    await page.locator('[data-rf-action-config="toggle"][data-rf-config-id="uniform"]').click();
    await signOut(page);
    await logIn(page,'swilliams','swilliams');
    await openRoute(page,'data-nav','search');
    await page.locator('#studentQuery').fill('S7001');
    await page.locator('[data-open-student="S7001"]').first().click();
    await page.locator('[data-rf-classroom-picker]').click();
    assert.equal(await page.locator('#review-dialog [data-rf-student-action="uniform"]').count(),0);
    await page.getByRole('button',{name:'Classroom follow-up',exact:false}).click();
    assert.deepEqual(await page.locator('#rf-student-incident-form [name="type"] option').allTextContents(),['Select type','Learning concern','Equipment concern']);
    await page.locator('#review-dialog [data-review-close]').first().click();
    await page.locator('#overlay [data-action="closeDrawer"]').first().click();
    console.log('PASS: student profiles, semester attendance action, incidents, admin referrals and configurable choices.');

    // Newly approved classroom modules and local teacher tools.
    for(const route of ['attendance-overview','classroom-management','student-support','follow-ups','seating-plans','class-lists','school-calendar']){
      await openRoute(page,'data-nav',''+route+'');
      assert(await page.locator('.rf-module-root').isVisible(),'Module failed to render: '+route);
    }
    await openRoute(page,'data-nav','follow-ups');
    await page.locator('#rf-followup-form [name="title"]').fill('Fictional follow-up');
    await page.locator('#rf-followup-form button[type="submit"],#rf-followup-form button').first().click();
    assert.match(await page.locator('.rf-module-task').innerText(),/Fictional follow-up/);
    await page.locator('[data-rf-followup-toggle]').first().click();
    assert.match(await page.locator('[data-rf-followup-toggle]').first().innerText(),/Reopen/);
    await openRoute(page,'data-nav','seating-plans');
    const seats=page.locator('[data-rf-seat-id]');
    if(await seats.count()>1){
      const first=await seats.nth(0).getAttribute('data-rf-seat-id'),second=await seats.nth(1).getAttribute('data-rf-seat-id');
      await seats.nth(0).click();await seats.nth(1).click();
      assert.equal(await seats.nth(0).getAttribute('data-rf-seat-id'),second);
      assert.equal(await seats.nth(1).getAttribute('data-rf-seat-id'),first);
    }
    await signOut(page);
    await logIn(page,'admin','admin','.v31-admin');
    await openRoute(page,'data-admin-page','teacher-modules');
    await page.locator('[data-rf-module-toggle="class-lists"]').click();
    await page.locator('#rf-calendar-admin [name="title"]').fill('Fictional assembly');
    await page.locator('#rf-calendar-admin button').click();
    await signOut(page);
    await logIn(page,'swilliams','swilliams');
    assert.equal(await page.locator('[data-nav="class-lists"]').count(),0);
    await openRoute(page,'data-nav','school-calendar');
    assert.match(await page.locator('.rf-module-root').innerText(),/Fictional assembly/);
    console.log('PASS: teacher modules, follow-up completion, seating swaps, admin visibility and calendar.');
    await signOut(page);
    await logIn(page,'admin','admin','.v31-admin');
    await openRoute(page,'data-admin-page','teacher-modules');
    await page.locator('[data-rf-module-toggle="class-lists"]').click();
    await signOut(page);
    await logIn(page,'swilliams','swilliams');

    // A real browser renders the full Monday-Friday timetable for any 2026 term week.
    await openRoute(page,'data-nav','timetable');
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

    // The actual lesson card travels from the day geometry to its matching week slot.
    await page.setViewportSize({width:1920,height:1200});
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.locator('[data-timetable-view="day"]').click();
    await page.emulateMedia({reducedMotion:'no-preference'});
    const morphResult = await page.evaluate(() => {
      const card = document.querySelector('.rf-timetable-workspace .rf-timetable-card[data-timetable-class="ENG071A"]');
      const key = card.dataset.rfMotion;
      const rect = el => { const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}; };
      const source = rect(card);
      document.querySelector('[data-timetable-view="week"]').click();
      const flight = [...document.querySelectorAll('.rf-morph-card[data-rf-motion]')].find(el=>el.dataset.rfMotion===key);
      const target = [...document.querySelectorAll('.rf-timetable-workspace .rf-timetable-card')].find(el=>el.dataset.rfMotion===key);
      if(!flight||!target)return {missing:true};
      const animation=flight.getAnimations()[0];animation.pause();
      animation.currentTime=0;const first=rect(flight);
      animation.currentTime=115;const middle=rect(flight);
      animation.currentTime=760;const last=rect(flight);
      return {source,first,middle,last,destination:rect(target),hidden:target.style.visibility,key};
    });
    assert(!morphResult.missing, 'Expected travelling card outside timetable grid');
    const near = (a,b) => ['x','y','w','h'].every(k=>Math.abs(a[k]-b[k])<2);
    assert(near(morphResult.source,morphResult.first), 'Morph starts at exact day card geometry');
    assert(morphResult.middle.w < morphResult.first.w && morphResult.middle.w > morphResult.destination.w, 'Card physically shrinks in flight');
    assert(near(morphResult.last,morphResult.destination), 'Morph ends in exact weekly slot');
    assert.equal(morphResult.hidden,'hidden','Destination stays hidden until the card lands');
    await page.evaluate(async()=>{const layer=document.querySelector('.rf-morph-layer');if(layer){const animations=layer.getAnimations({subtree:true});for(const a of animations)a.finish();await Promise.allSettled(animations.map(a=>a.finished));}});
    await page.locator('.rf-morph-layer').waitFor({state:'detached'});
    const reverse = await page.evaluate(key => {
      const source = [...document.querySelectorAll('.rf-timetable-workspace .rf-timetable-card')].find(el=>el.dataset.rfMotion===key);
      const width=source.getBoundingClientRect().width;
      document.querySelector('[data-timetable-view="day"]').click();
      const flight=[...document.querySelectorAll('.rf-morph-card[data-rf-motion]')].find(el=>el.dataset.rfMotion===key);
      if(!flight)return {missing:true};
      const a=flight.getAnimations()[0];a.pause();a.currentTime=115;const middle=flight.getBoundingClientRect().width;
      a.currentTime=760;const end=flight.getBoundingClientRect().width;
      return {width,middle,end};
    },morphResult.key);
    assert(!reverse.missing && reverse.middle>reverse.width && reverse.end>reverse.middle,'Week card expands into Day view');
    await page.evaluate(async()=>{const layer=document.querySelector('.rf-morph-layer');if(layer){const animations=layer.getAnimations({subtree:true});for(const a of animations)a.finish();await Promise.allSettled(animations.map(a=>a.finished));}});
    await page.locator('.rf-morph-layer').waitFor({state:'detached'});
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.locator('[data-timetable-view="week"]').click();
    assert.equal(await page.locator('.rf-morph-layer').count(),0,'Reduced motion bypasses travelling cards');

    // The full five-day grid and six-session day fit ordinary laptop and desktop viewports.
    // Turn motion off for geometry measurements so transient transforms do not affect overflow.
    await page.emulateMedia({ reducedMotion: 'reduce' });
    for (const size of [{ width: 1920, height: 1200 }, { width: 1440, height: 900 }, { width: 1280, height: 720 }, { width: 1180, height: 820 }, { width: 1024, height: 768 }, { width: 820, height: 1180 }, { width: 768, height: 1024 }]) {
      await page.setViewportSize(size);
      for (const mode of ['week', 'day']) {
        await page.locator('[data-timetable-view="' + mode + '"]').click();
        const geometry = await page.locator('.rf-timetable-workspace').evaluate(workspace => {
          const main = workspace.closest('main');
          const scroll = workspace.querySelector('.rf-week-scroll');
          const bounds = main.getBoundingClientRect();
          const cards = [...workspace.querySelectorAll('.rf-timetable-card')];
          return {
            cardCount: cards.length,
            verticalOverflow: main.scrollHeight - main.clientHeight,
            horizontalOverflow: scroll ? scroll.scrollWidth - scroll.clientWidth : 0,
            bottomOverflow: Math.max(...cards.map(card => card.getBoundingClientRect().bottom)) - bounds.bottom
          };
        });
        assert.equal(geometry.cardCount, mode === 'week' ? 30 : 6);
        assert(geometry.verticalOverflow <= 3 && geometry.bottomOverflow <= 3,
          mode + ' must fit vertically at ' + JSON.stringify(size) + ': ' + JSON.stringify(geometry));
        assert(geometry.horizontalOverflow <= 3,
          mode + ' must fit horizontally at ' + JSON.stringify(size) + ': ' + JSON.stringify(geometry));
      }
    }
    await page.emulateMedia({ reducedMotion: 'no-preference' });

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
    await openRoute(page,'data-nav','timetable');
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
      'Take Attendance', 'Shared hero must carry the primary page heading');
    const heroGradient = await hero.evaluate(el => getComputedStyle(el).backgroundImage);
    assert(heroGradient.includes('linear-gradient'),
      'Example 1 requires a prominent green title background');
    assert(await page.locator('.page-bar').isHidden(),
      'The shared page heading must not duplicate the attendance title');
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
      'The attendance hero must not show Change date');
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
    await openRoute(page,'data-nav','finder');
    const finderSearch = page.locator('#finderResults');
    assert(await finderSearch.count(), 'Class Finder should still render');

    // Student Movements Example 1 uses real browser-local pass records,
    // including live return actions and filters; no server or school records.
    await openRoute(page,'data-nav','movements');
    assert.equal(await page.locator('.rf-movements-hero h1').innerText(),
      '↔ Student Movements', 'New dashboard header should render');
    assert.equal(await page.locator('.rf-movement-stat').count(), 3,
      'Currently out, Returned and Total passes summaries are required');
    assert.equal(await page.locator('#movementStudentSearch').count(), 1,
      'Existing student autocomplete must remain on the new page');
    assert.equal(await page.locator('#movementDestination').count(), 1);
    assert.equal(await page.locator('#movementIssueButton').count(), 1);
    assert.equal(await page.locator('#rfMovementView').count(), 1,
      'Movement status filter must remain usable');

    const dateParts = Object.fromEntries(new Intl.DateTimeFormat('en-AU', {
      timeZone: 'Australia/Brisbane', year: 'numeric', month: '2-digit',
      day: '2-digit'
    }).formatToParts(new Date()).map(part => [part.type, part.value]));
    const today = dateParts.year + '-' + dateParts.month + '-' + dateParts.day;
    const movementDate = page.locator('#rf-movements-date');
    await movementDate.fill(today);
    await movementDate.dispatchEvent('change');
    assert.equal(await page.locator('.rf-movement-stat-out strong').innerText(), '0');
    const initialReturned = Number(await page.locator('.rf-movement-stat-returned strong').innerText());
    const initialTotal = Number(await page.locator('.rf-movement-stat-total strong').innerText());
    assert.equal(initialTotal, initialReturned,
      'Prefilled examples must all be completed, not active live passes');
    assert.equal(await page.getByText('DAILY SERVICE USAGE', { exact: false }).count(), 0,
      'Unused Daily Service Usage section should be removed');
    assert.equal(await page.getByText('STUDENTS USING EACH SERVICE', { exact: false }).count(), 0);
    assert.equal(await page.getByText('VISITS TO EACH SERVICE', { exact: false }).count(), 0);
    assert.equal(await page.locator('.movement-chart-grid').count(), 0,
      'Student Movements should show the compact dashboard without service-usage charts');

    const samples = await page.evaluate(() => {
      const key = Object.keys(localStorage).find(x => x.startsWith('rollflow_workspace_swilliams_'));
      const stored = JSON.parse(localStorage.getItem(key) || '{}');
      return stored.sampleMovementHistory || [];
    });
    assert(samples.length >= 50 && samples.length < 150,
      'Sample movement history should be varied, not generated for every student');
    assert(samples.every(m => m.sample && m.returnedAt && m.minutes > 0 &&
      m.id.startsWith('rf-fictional-2026-')), 'Samples must all be visibly completed fictional visits');
    const countsByStudent = Object.values(samples.reduce((acc, m) => {
      acc[m.studentId] = (acc[m.studentId] || 0) + 1; return acc;
    }, {}));
    assert(Math.max(...countsByStudent) >= 12, 'At least one fictional student should use services frequently');
    assert(Math.min(...countsByStudent) === 1, 'Some fictional students should only have one visit');
    assert(new Set(samples.map(m => m.destination)).size === 4,
      'Include a variety of destinations');
    const newestSampleDate = samples.map(m => m.date).sort().at(-1);
    await page.locator('#rf-movements-date').fill(newestSampleDate);
    await page.locator('#rf-movements-date').dispatchEvent('change');
    assert(Number(await page.locator('.rf-movement-stat-returned strong').innerText()) > 0,
      'Fictional completed movements should appear in the dated movement log');
    assert.match(await page.locator('.rf-movement-table tbody').innerText(), /Training record/,
      'Sample history must be clearly labelled rather than mistaken for real passes');
    await page.locator('#rf-movements-date').fill(today);
    await page.locator('#rf-movements-date').dispatchEvent('change');

    await page.locator('#movementStudentSearch').fill('S7001');
    await page.locator('[data-movement-choice="S7001"]').click();
    assert(await page.locator('#movementIssueButton').isEnabled());
    await page.locator('#movementDestination').selectOption('Library');
    await page.locator('#movementIssueButton').click();
    assert.equal(await page.locator('.rf-movement-stat-out strong').innerText(), '1');
    assert.equal(Number(await page.locator('.rf-movement-stat-total strong').innerText()), initialTotal + 1);
    assert.match(await page.locator('.rf-movement-table tbody').innerText(), /Library/);
    assert.equal(await page.locator('.rf-movement-return-button').count(), 1);
    const livePass = await page.evaluate(() => {
      const stored = JSON.parse(localStorage.getItem('rollflow_teacher_swilliams_2026_v1') || '{}');
      return stored.movements?.at(-1);
    });
    assert(livePass?.departedISO && !Number.isNaN(Date.parse(livePass.departedISO)),
      'New service passes need a real departure timestamp for duration');
    assert.equal(typeof livePass.session, 'string',
      'Store the actual Care/Period session on newly issued services');
    assert(livePass?.time, 'The service visit must record a readable departure time');
    assert(await page.locator('.rf-movement-view-day').count() > 0,
      'Each service log entry needs a way to display its day template');
    const issuedRow = page.locator('.rf-movement-table tbody tr').filter({hasText:'S7001'}).first();
    await issuedRow.locator('[data-rf-view-day="S7001"]').click();
    assert.match(await page.locator('.rf-day-selected-student').innerText(), /S7001/);
    assert.match(await page.locator('#rf-day-period-result').innerText(), /Library/,
      'The just-issued service pass must automatically appear in the student day template');
    assert.match(await page.locator('#rf-day-period-result').innerText(), /Currently out/,
      'The template should update while the student is out');
    assert.equal(await page.locator('#rf-movements-date').inputValue(), today,
      'Opening a current pass must keep the current date');


    await page.locator('#rfMovementView').selectOption('returned');
    assert.equal(await page.locator('.rf-movement-return-button').count(), 0,
      'Returned filter must hide active student passes');
    await page.locator('#rfMovementView').selectOption('out');
    assert.equal(await page.locator('.rf-movement-return-button').count(), 1);
    await page.locator('#rfMovementView').selectOption('all');
    await page.locator('.rf-movement-return-button').click();
    assert.match(await page.locator('#rf-day-period-result').innerText(), /Library/,
      'Completing a service must not remove its entry from the student day');
    assert.match(await page.locator('#rf-day-period-result').innerText(), /Returned/,
      'The selected student template must refresh to show a returned service');
    assert.equal(await page.locator('.rf-movement-stat-out strong').innerText(), '0');
    assert.equal(Number(await page.locator('.rf-movement-stat-returned strong').innerText()), initialReturned + 1);
    assert.equal(Number(await page.locator('.rf-movement-stat-total strong').innerText()), initialTotal + 1);
    assert.match(await page.locator('.rf-movement-table tbody').innerText(), /Returned/);

    await page.locator('#rf-movements-date').fill('2026-03-09');
    await page.locator('#rf-movements-date').dispatchEvent('change');
    await page.locator('#movementStudentSearch').fill('S7001');
    await page.locator('[data-movement-choice="S7001"]').click();
    assert(await page.locator('#movementIssueButton').isDisabled(),
      'Historical dates must not allow new live movement passes');
    assert.match(await page.locator('#movementFeedback').innerText(), /selected/);

    // A read-only student day template sits below the main movement log.
    const studentDaySection = page.locator('.rf-day-review');
    assert(await studentDaySection.isVisible());
    assert(await page.locator('.rf-movement-log').evaluate(el =>
      el.nextElementSibling?.classList.contains('rf-day-review') === true),
      'Student day review must sit directly below Movement log');
    assert.deepEqual(await page.locator('.rf-day-period-table tbody th strong').allInnerTexts(),
      ['Care class','Period 1','Period 2','Period 3','Period 4']);
    assert.equal(await page.locator('.rf-day-period-cell').count(), 5);
    assert((await page.locator('.rf-day-period-cell').allInnerTexts()).every(text => text.trim() === ''),
      'No student selected: all template cells must be visually blank');

    await page.locator('#rf-day-student-search').fill('S18030');
    assert.equal(await page.locator('[data-rf-day-student="S18030"]').count(), 1,
      'The new search should offer matching student IDs');
    await page.locator('#rf-day-student-search').press('Enter');
    assert.match(await page.locator('.rf-day-selected-student').innerText(), /Daniel Murphy/);
    assert((await page.locator('.rf-day-period-cell').allInnerTexts()).every(text => text.trim() === ''),
      'A student with no movements must have five blank sessions');

    const sampleInPeriodOne = samples.find(m => m.studentId === 'S7001' &&
      m.date !== today && /^9:\d{2} am$/.test(m.time));
    assert(sampleInPeriodOne, 'Expected a fictional Year 7 visit in Period 1');
    await page.locator('#rf-movements-date').fill(sampleInPeriodOne.date);
    await page.locator('#rf-movements-date').dispatchEvent('change');
    assert.match(await page.locator('.rf-day-selected-student').innerText(), /Daniel Murphy/,
      'Selecting another date should preserve the selected student');
    assert((await page.locator('.rf-day-period-cell').allInnerTexts()).every(text => text.trim() === ''),
      'The period view must filter on the selected date');
    assert(await page.locator('.rf-day-quick-picks').isVisible(),
      'Students with service movements on this date must be directly selectable');
    assert(await page.locator('.rf-day-quick-pick[data-rf-day-quick-student="S7001"]').isVisible());
    const logVisitRow = page.locator('.rf-movement-table tbody tr').filter({hasText:'S7001'}).first();
    assert(await logVisitRow.locator('[data-rf-view-day="S7001"]').isVisible(),
      'A recorded service visit should offer View in template from the Movement log');
    await logVisitRow.locator('[data-rf-view-day="S7001"]').click();
    assert.match(await page.locator('.rf-day-selected-student').innerText(), /S7001/);
    assert.match(await page.locator('.rf-day-visit-count').innerText(), /1 recorded service visit/);
    const p1 = page.locator('[data-rf-day-period="p1"] .rf-day-period-cell');
    assert.match(await p1.innerText(), new RegExp(sampleInPeriodOne.destination));
    assert.match(await p1.innerText(), /Training record/);
    for (const periodId of ['care','p2','p3','p4']) {
      assert.equal((await page.locator('[data-rf-day-period="' + periodId + '"] .rf-day-period-cell')
        .innerText()).trim(), '', periodId + ' should remain blank without a visit');
    }
    await page.locator('#rf-movements-date').fill('2026-12-24');
    await page.locator('#rf-movements-date').dispatchEvent('change');
    assert.match(await page.locator('.rf-day-selected-student').innerText(), /S7001/);
    assert((await page.locator('.rf-day-period-cell').allInnerTexts()).every(text => text.trim() === ''),
      'The template must show no visits on a date without records');

    // Simulate multiple completed visits on one school day in browser-only
    // fictional attendance storage. This must never invent "present" marks.
    await page.evaluate(() => {
      const key = 'rollflow_teacher_swilliams_2026_v1';
      const stored = JSON.parse(localStorage.getItem(key) || '{}');
      const stamp = '2026-03-09';
      const example = [
        ['care', '8:40 am', 'Library', '8:46 am'],
        ['p1-a', '9:15 am', 'Toilet', '9:21 am'],
        ['p1-b', '9:42 am', 'Student services', '9:54 am'],
        ['p4', '1:31 pm', 'School office', '1:44 pm'],
        ['other', '3:05 pm', 'Library', '3:12 pm']
      ].map(([id,time,destination,returnedAt]) => ({
        id:'period-template-test-' + id,studentId:'S18030',
        date:stamp,time,destination,returnedAt
      }));
      stored.movements=[...(stored.movements||[]),...example];
      localStorage.setItem(key,JSON.stringify(stored));
    });
    await page.reload();
    await openRoute(page,'data-nav','movements');
    await page.locator('#rf-movements-date').fill('2026-03-09');
    await page.locator('#rf-movements-date').dispatchEvent('change');
    const loggedRow = page.locator('.rf-movement-table tbody tr').filter({hasText:'S18030'}).first();
    await loggedRow.locator('[data-rf-view-day="S18030"]').click();
    assert.match(await page.locator('.rf-day-visit-count').innerText(), /5 recorded service visits/);
    assert.equal(await page.locator('[data-rf-day-period="care"] .rf-day-movement-entry').count(),1);
    assert.equal(await page.locator('[data-rf-day-period="p1"] .rf-day-movement-entry').count(),2,
      'Show multiple movements within the same period, not just the first');
    assert.equal(await page.locator('[data-rf-day-period="p2"] .rf-day-movement-entry').count(),0);
    assert.equal(await page.locator('[data-rf-day-period="p3"] .rf-day-movement-entry').count(),0);
    assert.equal(await page.locator('[data-rf-day-period="p4"] .rf-day-movement-entry').count(),1);
    assert.match(await page.locator('.rf-day-outside-periods').innerText(), /3:05 pm/,
      'Keep movements outside Care–Period 4 visible without misclassifying them');
    assert.match(await page.locator('[data-rf-day-period="p1"]').innerText(), /9:15 am.*Toilet|Toilet.*9:15 am/s);
    await page.locator('#rf-movements-date').fill('2026-03-10');
    await page.locator('#rf-movements-date').dispatchEvent('change');
    assert((await page.locator('.rf-day-period-cell').allInnerTexts()).every(text => text.trim() === ''),
      'Movements from a different date must not appear in this day template');
    await page.locator('[data-rf-day-clear]').click();
    assert.equal(await page.locator('#rf-day-student-search').inputValue(),'');
    assert((await page.locator('.rf-day-period-cell').allInnerTexts()).every(text => text.trim() === ''),
      'Clearing the selected student must return to an empty day template');

    // The app must use distinct attendance and workspace stores.
    const keys = await page.evaluate(() => Object.keys(localStorage));
    assert(keys.some(key => key.startsWith('rollflow_workspace_swilliams_')),
      'Sarah-specific workspace did not initialise');
    await signOut(page);
    await page.locator('#demo-login-form').waitFor();

    await logIn(page, 'teacher', 'teacher');
    assert.equal((await page.locator('.top-user > span').innerText()).trim(), 'Alex Morgan');
    assert.equal(await page.locator('.permanent-sidebar [data-nav="classes"]').count(), 0, 'My Classes must not appear in the menu');
    assert.equal(await page.locator('.permanent-sidebar [data-nav="roll"]').count(), 0, 'Mark Attendance must not appear in the menu');
    await openRoute(page,'data-nav','finder');
    assert.equal(await page.locator('[data-teacher-scope]').count(), 0, 'Class Finder must not show the scope selector');
    assert.equal(await page.locator('.page-right .tag').count(),0,'Class count badge removed');
    const mathsOwned=[];
    for(const code of ['MAF102A','ENG071A']){
      await page.locator('#finderQuery').fill(code);
      if(await page.locator('.finder-card[data-class-code="'+code+'"][data-my-class="true"]').count())mathsOwned.push(code);
    }
    const mathsClasses=mathsOwned.join(' ');
    assert(mathsClasses.includes('MAF102A'), 'Default teacher class missing');
    assert(!mathsClasses.includes('ENG071A'), 'Default teacher inherited Sarah class');

    await signOut(page);
    await page.locator('#demo-login-form').waitFor();
    await logIn(page, 'admin', 'admin', '.v31-admin');
    assert(await page.locator('.v31-admin').count(), 'Admin demo login broke');

    // Admin-managed destinations must persist in this browser, be shared
    // between demo roles, and never mutate historical movement records.
    assert.equal(await page.locator('.rf-training-notice').count(),0,'Persistent workspace banner remains removed');
    for (const id of ['relief', 'notices', 'reports']) {
      assert.equal(await page.locator('.nav-primary [data-admin-page="' + id + '"]').count(), 0, 'Unimplemented menu item must not be offered: ' + id);
    }
    await openRoute(page,'data-admin-page','staff');
    assert.equal(await page.locator('[data-admin-reset]').count(), 0, 'No simulated password reset control');
    assert.equal(await page.getByText('Built-in training access', { exact: true }).count(), 3, 'All three public access identities must be protected');
    await openRoute(page,'data-admin-page','movements');
    assert.equal((await page.locator('#rf-admin-destinations-title').innerText()).trim(),
      'Manage movement destinations');
    assert.equal(await page.locator('.rf-admin-destination-item').count(), 4,
      'The four defaults should be available initially');
    await page.locator('#rf-new-movement-destination').fill('Wellbeing Centre');
    await page.locator('#rf-add-movement-destination button[type="submit"]').click();
    assert.equal(await page.locator('.rf-admin-destination-item').count(), 5);
    assert(await page.getByRole('button', {name:'Remove Wellbeing Centre'}).isVisible());
    assert((await page.evaluate(() =>
      JSON.parse(localStorage.getItem('rollflow_demo_movement_destinations_v1'))
    )).includes('Wellbeing Centre'), 'New destination was not saved');
    await page.reload();
    await openRoute(page,'data-admin-page','movements');
    assert(await page.getByRole('button', {name:'Remove Wellbeing Centre'}).isVisible(),
      'Admin destination changes should survive a reload');

    await page.locator('#rf-new-movement-destination').fill('wellbeing centre');
    await page.locator('#rf-add-movement-destination button[type="submit"]').click();
    assert.equal(await page.locator('.rf-admin-destination-item').count(), 5,
      'Duplicate destination should be rejected case-insensitively');
    assert.match(await page.locator('.v31-message').innerText(), /already exists/i);

    await page.locator('#rf-new-movement-destination').fill('Bad <tag>');
    await page.locator('#rf-add-movement-destination button[type="submit"]').click();
    assert.equal(await page.locator('.rf-admin-destination-item').count(), 5,
      'HTML-like destination names must be rejected');

    await signOut(page);
    await page.locator('#demo-login-form').waitFor();
    await logIn(page, 'swilliams', 'swilliams');
    await openRoute(page,'data-nav','movements');
    await page.locator('#rf-movements-date').fill(today);
    await page.locator('#rf-movements-date').dispatchEvent('change');
    assert(await page.locator('#movementDestination option[value="Wellbeing Centre"]').count(),
      'Teacher should see the new administrator destination');
    assert.equal(await page.locator('[data-rf-remove-movement-destination]').count(), 0,
      'Teacher page must not expose admin removal controls');

    await page.locator('#movementStudentSearch').fill('S7001');
    await page.locator('[data-movement-choice="S7001"]').click();
    await page.locator('#movementDestination').selectOption('Wellbeing Centre');
    await page.locator('#movementIssueButton').click();
    assert.equal(await page.locator('.rf-movement-return-button').count(), 1,
      'New destination needs to work with the existing live pass action');
    await page.locator('.rf-movement-return-button').click();
    assert.match(await page.locator('.rf-movement-table tbody').innerText(), /Wellbeing Centre/);

    await signOut(page);
    await page.locator('#demo-login-form').waitFor();
    await logIn(page, 'admin', 'admin', '.v31-admin');
    await openRoute(page,'data-admin-page','movements');
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', {name:'Remove Wellbeing Centre'}).click();
    assert.equal(await page.locator('.rf-admin-destination-item').count(), 4);
    assert.equal(await page.getByRole('button', {name:'Remove Wellbeing Centre'}).count(), 0);
    assert(!(await page.evaluate(() =>
      JSON.parse(localStorage.getItem('rollflow_demo_movement_destinations_v1'))
    )).includes('Wellbeing Centre'));

    await signOut(page);
    await page.locator('#demo-login-form').waitFor();
    await logIn(page, 'swilliams', 'swilliams');
    await openRoute(page,'data-nav','movements');
    await page.locator('#rf-movements-date').fill(today);
    await page.locator('#rf-movements-date').dispatchEvent('change');
    assert.equal(await page.locator('#movementDestination option[value="Wellbeing Centre"]').count(), 0,
      'Removed destination must not be selectable for new passes');
    assert.match(await page.locator('.rf-movement-table tbody').innerText(), /Wellbeing Centre/,
      'Previously returned passes must keep their destination after deletion');

    await page.locator('#movementStudentSearch').fill('S7001');
    await page.locator('[data-movement-choice="S7001"]').click();
    await page.evaluate(() => {
      const select = document.getElementById('movementDestination');
      select.add(new Option('Wellbeing Centre', 'Wellbeing Centre'));
      select.value = 'Wellbeing Centre';
    });
    const beforeInvalid = await page.locator('.rf-movement-stat-total strong').innerText();
    await page.locator('#movementIssueButton').click();
    assert.equal(await page.locator('.rf-movement-stat-total strong').innerText(), beforeInvalid,
      'A stale/forged removed destination should not create a pass');

    // Exercise visible teacher/admin navigation across representative desktop and iPad sizes.
    async function assertWorkspaceFits(label, selector) {
      const result = await page.locator(selector).first().evaluate(main => {
        const r = main.getBoundingClientRect();
        return { left:r.left, right:r.right, bottom:r.bottom, width:innerWidth, height:innerHeight,
          xOverflow:main.scrollWidth-main.clientWidth };
      });
      assert(result.left >= -3 && result.right <= result.width+3 && result.bottom <= result.height+3,
        label+' workspace exceeds viewport: '+JSON.stringify(result));
      assert(result.xOverflow <= 3, label+' page has horizontal overflow: '+JSON.stringify(result));
    }
    const deviceSizes = [{width:1920,height:1200},{width:1024,height:768},{width:768,height:1024},{width:820,height:1180}];
    for (const size of deviceSizes) {
      await page.setViewportSize(size);
      for (const route of ['home','timetable','master','finder','search','movements','alerts','profile','preferences','help','attendance-overview','classroom-management','student-support','follow-ups','seating-plans','class-lists','school-calendar']) {
        await openRoute(page,'data-nav',route);
        await assertWorkspaceFits('Teacher '+route+' '+JSON.stringify(size), '.content-shell>.main');
      }
    }
    await signOut(page);
    await logIn(page, 'admin', 'admin', '.v31-admin');
    for (const size of deviceSizes) {
      await page.setViewportSize(size);
      for (const route of ['dashboard','staff','students','classes','timetable','master','movements','student-actions','teacher-modules','roles','data','oneschool','audit']) {
        await openRoute(page,'data-admin-page',route);
        await assertWorkspaceFits('Admin '+route+' '+JSON.stringify(size), '.v31-content>main');
      }
    }

    console.log('PASS: swilliams login, separate class ownership, teacher switch and admin login.');
  }
  finally {
    if (browser) await browser.close();
    server.close();
  }
}

test().catch(error => { console.error(error); process.exitCode = 1; });
