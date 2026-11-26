/* RollFlow shared schedule contract v1. No browser storage, permissions or network side effects. */
(function(root,factory){
  const api=factory();
  if(typeof module==="object" && module.exports) module.exports=api;
  else root.RollFlowSchedule=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
  "use strict";
  const VERSION=1;
  const text=(v,limit=250)=>typeof v==="string"?v.slice(0,limit):"";
  const escape=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  function validDate(value){
    if(typeof value!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
    const d=new Date(value+"T00:00:00Z");
    return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===value;
  }
  function lesson(row){
    if(!row||typeof row!=="object"||!validDate(row.date))throw new TypeError("Invalid lesson date");
    const code=text(row.code), title=text(row.title)||code;
    if(!code)throw new TypeError("Missing class code");
    return Object.freeze({date:row.date,code,title,period:text(row.period),time:text(row.time),room:text(row.room),assignment:text(row.assignment)});
  }
  function snapshot(value){
    if(!value||value.version!==VERSION||!Array.isArray(value.days)||value.days.length>7)throw new TypeError("Unsupported schedule contract");
    const seen=new Set();
    const days=value.days.map(day=>{
      if(!day||!validDate(day.date)||seen.has(day.date)||!Array.isArray(day.lessons))throw new TypeError("Invalid schedule day");
      seen.add(day.date);
      return Object.freeze({date:day.date,lessons:Object.freeze(day.lessons.map(row=>{
        const item=lesson(row);if(item.date!==day.date)throw new TypeError("Lesson belongs to another date");return item;
      }))});
    });
    return Object.freeze({version:VERSION,days:Object.freeze(days)});
  }
  // The provider is deliberately read-only. Calling code decides its authority
  // and scope before providing rows; this component never grants permission.
  function provider(load){
    if(typeof load!=="function")throw new TypeError("Schedule loader required");
    return Object.freeze({getSchedule:()=>snapshot(load())});
  }
  function title(row){
    const item=lesson(row);
    return '<h3 class="rf-shared-lesson-title">'+escape(item.title)+'</h3>';
  }
  function heading(row){
    const item=lesson(row);
    return '<div class="rf-shared-lesson-heading">'+title(item)+'<small class="rf-shared-lesson-code">'+escape(item.code)+'</small></div>';
  }
  function mount(root,source){
    const data=source.getSchedule();
    const rows=new Map();
    for(const day of data.days)for(const item of day.lessons)rows.set(JSON.stringify([item.date,item.code,item.period,item.time]),item);
    for(const el of root.querySelectorAll("[data-rf-shared-lesson]")){
      const key=JSON.stringify([el.dataset.date,el.dataset.code,el.dataset.period,el.dataset.time]);
      if(!rows.has(key))continue; // Do not invent or reveal a lesson.
      el.innerHTML=heading(rows.get(key));
    }
    return data;
  }
  return Object.freeze({VERSION,validDate,lesson,snapshot,provider,title,heading,mount});
});
