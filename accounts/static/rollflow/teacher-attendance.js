(() => {
 "use strict";
 const selects=[...document.querySelectorAll('.rf-mark-select')];
 if(!selects.length)return;
 const groups=new Map([...document.querySelectorAll('.rf-mark-buttons')].map(g=>[g.dataset.markFor,g]));
 const counts={'P':0,'A':0,'L':0,'':0};
 const counters=new Map([...document.querySelectorAll('[data-rf-count]')].map(n=>[n.dataset.rfCount,n]));
 const states=new Map();
 function showCounts(){
  for(const [key,value] of Object.entries(counts)){
   const node=counters.get(key);if(node&&node.textContent!==String(value))node.textContent=String(value);
  }
 }
 function sync(select){
  const group=groups.get(select.id);if(!group)return;
  group.querySelectorAll('button').forEach(btn=>{
   btn.setAttribute('aria-pressed',String(btn.dataset.mark===select.value));btn.disabled=select.disabled;
  });
 }
 function normal(value){return Object.hasOwn(counts,value)?value:'';}
 function rebuild(){
  for(const key of Object.keys(counts))counts[key]=0;
  selects.forEach(s=>{const value=normal(s.value);states.set(s,value);counts[value]++;sync(s);});
  showCounts();
 }
 selects.forEach(s=>{const group=groups.get(s.id);if(group)group.hidden=false;});
 // One delegated handler; changing a mark touches only that student's buttons
 // and the four counters, not all other rows. Native select is still the POST source.
 const form=selects[0].closest('form');
 if(!form)return;
 form.addEventListener('click',event=>{
  const btn=event.target.closest('.rf-mark-buttons button[data-mark]');
  if(!btn||btn.disabled)return;
  const select=document.getElementById(btn.closest('.rf-mark-buttons').dataset.markFor);
  if(!states.has(select)||select.disabled)return;
  select.value=btn.dataset.mark;select.dispatchEvent(new Event('change',{bubbles:true}));
 });
 form.addEventListener('change',event=>{
  const select=event.target;
  if(!states.has(select))return;
  const previous=states.get(select),next=normal(select.value);
  if(previous!==next){counts[previous]--;counts[next]++;states.set(select,next);}
  sync(select);showCounts();
 });
 form.addEventListener('reset',()=>requestAnimationFrame(rebuild));
 window.addEventListener('pageshow',rebuild);
 rebuild();
})();
