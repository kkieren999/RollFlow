const fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
function cut(a,b){const x=source.indexOf(a),y=source.indexOf(b,x);if(x<0||y<0)throw Error('Missing '+a);return source.slice(x,y)}
const roles=cut('const RFU_ROLES={','const RFU_IDENTITIES=');
const grouping=cut('function rfCompactGroups(','function rfCompactNavigation(');
const grants=cut('function rfuGrants(','function rfuRoleText(');
const scope=cut('function rfuRecordAllowed(','function rfuRows(');
const test=String.raw`
const students=[{id:'s1',year:8,status:'active'},{id:'s2',year:9,status:'active'},{id:'s3',year:8,status:'inactive'}];
const previewStudents=students,planning={enrolments:[{studentId:'s1',classCode:'M8',start:'2026-01-01'},{studentId:'s2',classCode:'E9',start:'2026-01-01'}]};
let config={roles:['aide'],disabled:[],expires:'',faculty:'Mathematics',year:'8'},rfuActor='actor';
const rfuConfig=()=>config,brisbaneToday=()=> '2026-11-26',rfuAssignedStudents=()=>['s1'],rfuReferredStudents=()=>['s2'];
const rfuActiveClasses=()=>[{code:'M8',subject:'Mathematics',year:8},{code:'E9',subject:'English',year:9}];
const rfuClassAllowed=(c,g)=>g.scope==='school'||g.scope==='assigned'&&c.code==='M8'||g.scope==='year'&&String(c.year)===config.year||g.scope==='faculty'&&c.subject===config.faculty;
const checks=[];function check(name,v){if(!v)throw Error(name);checks.push(name)}
const teacher=rfCompactGroups('teacher',['finder','classroom-management','seating-plans','class-lists','timetable']);
check('Class Finder stands alone',teacher.find(g=>g.label==='Class Finder').routes.join(',')==='finder');
check('Classroom Management stands alone',teacher.find(g=>g.label==='Classroom Management').routes.join(',')==='classroom-management');
check('Seating Plans and Class Lists absent',!teacher.flatMap(g=>g.routes).some(x=>['seating-plans','class-lists'].includes(x)));
check('Staff Classroom Management stands alone',rfCompactGroups('staff',['classes','classroom-management'],['aide']).find(g=>g.label==='Classroom Management').routes.length===1);
check('No classroom menu without authorised route',!rfCompactGroups('staff',['classes'],['office']).some(g=>g.routes.includes('classroom-management')));
for(const role of ['teacher','aide','learning','relief','hod','ylc','principal','deputy']){config.roles=[role];check(role+' can create',rfuCan('classroom-management',['create']))}
for(const role of ['system','office','business','guidance']){config.roles=[role];check(role+' not granted by default',!rfuCan('classroom-management'))}
config.roles=['aide'];const allowed=(studentId,classCode='')=>rfuRecordAllowed('classroom-management',{studentId,classCode,owner:'actor'},'actor',['create']);
check('Aide assigned student and class allowed',allowed('s1','M8'));
check('Aide unrelated student blocked',!allowed('s2'));
check('Aide unrelated class blocked',!allowed('s1','E9'));
check('Inactive student blocked',!allowed('s3'));
config.disabled=['classroom-management'];check('Disabled module blocked',!allowed('s1'));
config.disabled=[];config.expires='2026-11-25';check('Expired relief or staff access blocked',!allowed('s1'));
config.expires='';config.roles=['hod'];check('Faculty scope enforced',allowed('s1','M8')&&!allowed('s2','E9'));
config.roles=['ylc'];check('Year scope enforced',allowed('s1','M8')&&!allowed('s2','E9'));
config.roles=['principal'];check('School scope allowed',allowed('s1','M8')&&allowed('s2','E9'));
return checks;
`;
for(const name of new Function(roles+grouping+grants+scope+test)())console.log('PASS '+name);
