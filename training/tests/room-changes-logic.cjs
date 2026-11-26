// Run: node tests/room-changes-logic.cjs
// Isolated room-change logic against a deterministic timetable; not a browser test.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const extract=(start,end)=>{const a=source.indexOf(start),b=source.indexOf(end,a);assert(a>=0&&b>a,'room change logic found');return source.slice(a,b)};
const logic=extract('function rfRoomPeriod(','function rfRoomDialog(')+extract('function rfRoomVisible(','function rfRoomNoticePanel(');
const fixture=String.raw`
const store={},audit=[];let rfuActor='teacher',demoRole='teacher',seq=0;
const RFU_IDENTITIES=['teacher','office','deputy','business','swilliams','aide'].map(id=>({id,role:id==='swilliams'?'teacher':id})),rfuIdentity=id=>RFU_IDENTITIES.find(p=>p.id===id),rfuConfig=id=>({roles:[rfuIdentity(id)?.role],expires:''});
const brisbaneToday=()=> '2026-11-25',dateOffset=(d,n)=>{const t=new Date(d+'T12:00:00Z');t.setUTCDate(t.getUTCDate()+n);return t.toISOString().slice(0,10)},osDateValid=d=>/^\d{4}-\d{2}-\d{2}$/.test(d)&&!Number.isNaN(Date.parse(d));
const planDays=['Monday','Tuesday','Wednesday','Thursday','Friday'],weekdayFor=d=>['Sunday',...planDays,'Saturday'][new Date(d+'T12:00:00Z').getUTCDay()];
const sarahSchoolStatus=d=>['Saturday','Sunday'].includes(weekdayFor(d))||d==='2026-11-30'?'No school':'',SARAH_2026_YEAR10_FINISH='2026-11-27';
const planning={rooms:['A','B','C','D'].map(code=>({code,active:true})),periods:[1,2,3].map(n=>({code:String(n),start:String(8+n).padStart(2,'0')+':00'})),classes:['MAT','ENG'].map(code=>({code,active:true,year:8})),slots:[{active:true,day:3,classCode:'MAT',period:'1',room:'A',teacher:'teacher'},{active:true,day:3,classCode:'MAT',period:'2',room:'A',teacher:'teacher'},{active:true,day:3,classCode:'MAT',period:'3',room:'A',teacher:'teacher'},{active:true,day:3,classCode:'ENG',period:'3',room:'C',teacher:'swilliams'},{active:true,day:4,classCode:'MAT',period:'2',room:'A',teacher:'teacher'},{active:true,day:1,classCode:'MAT',period:'2',room:'A',teacher:'teacher'}]};
const rfuRead=(k,v)=>store[k]??v,rfuWrite=(k,v)=>(store[k]=v,true),rfuAudit=(...x)=>audit.push(x),rfModuleId=()=>String(++seq),rfClassSupervisionRecords=()=>[],rfuAssignedClasses=id=>id==='aide'?['MAT']:[],esc=x=>String(x),state={date:'2026-11-25'};
`;
const cases=String.raw`
const results=[];function check(name,value){if(!value)throw Error(name);results.push(name)}
const date='2026-11-25',end='2026-11-30',key=rfRoomKey;
check('single default targets one lesson',rfRoomTargets('MAT',date,2).length===1);
check('remaining day excludes earlier period',rfRoomTargets('MAT',date,2,'day').map(x=>x.period).join()==='2,3');
check('range skips weekends and school closures',rfRoomTargets('MAT',date,2,'range',end).map(x=>key(x.date,x.period)).join()==='2026-11-25|2,2026-11-25|3,2026-11-26|2');
check('range maximum validated',rfRoomTargets('MAT',date,2,'range','2027-11-25').length===0);
const plan=rfRoomPlan('MAT',date,2,'C','range',end);
check('conflicting lesson flagged',plan[1].room===''&&plan[1].available.some(x=>x.code==='D'));
check('no partial save on conflict',!!rfRoomSaveBatch('MAT',date,2,'range',end,[{key:key(date,2),room:'C'},{key:key(date,3),room:'C'}],'Maintenance')&&rfRoomStore().length===0);
check('cannot save outside selection',!!rfRoomSaveBatch('MAT',date,2,'day',date,[{key:key(date,1),room:'C'}],'Maintenance'));
check('save alternative and selected lessons',rfRoomSaveBatch('MAT',date,2,'range',end,[{key:key(date,2),room:'C'},{key:key(date,3),room:'D'},{key:key('2026-11-26',2),room:'C'}],'Maintenance')==='');
check('effective rooms and earlier lesson preserved',rfRoomEffective('MAT',date,2,'A')==='C'&&rfRoomEffective('MAT',date,3,'A')==='D'&&rfRoomEffective('MAT',date,1,'A')==='A');
check('later date restores original automatically',rfRoomEffective('MAT','2026-12-01',2,'A')==='A');
const g=rfRoomNoticeGroups(rfRoomStore());check('one grouped notification',g.length===1&&g[0].items.length===3&&g[0].unread&&audit.length===1);
check('admin notified',g[0].items.every(x=>x.recipients.includes('office')));
check('individual reversal does not affect others',rfRoomUndo(g[0].items[1].id)===''&&rfRoomEffective('MAT',date,3,'A')==='A'&&rfRoomEffective('MAT',date,2,'A')==='C');
rfuActor='office';demoRole='staff';
store.rollflow_room_closures_v1=[{room:'A',date:'2026-11-26',period:'2'}];
check('group reversal is atomic if original room blocked',!!rfRoomUndoMany(g[0].id,true)&&rfRoomEffective('MAT',date,2,'A')==='C');
store.rollflow_room_closures_v1=[];
check('group undo by admin',rfRoomUndoMany(g[0].id,true)===''&&rfRoomEffective('MAT',date,2,'A')==='A'&&rfRoomEffective('MAT','2026-11-26',2,'A')==='A');
check('explicit exclusion leaves selected lesson unchanged',rfRoomSaveBatch('MAT',date,2,'day',date,[{key:key(date,2),room:'C'}],'Maintenance')===''&&rfRoomEffective('MAT',date,3,'A')==='A');
return results;
`;
const results=new Function(fixture+logic+cases)();
for(const name of results)console.log('PASS '+name);
console.log(results.length+' room-change logic tests passed.');
