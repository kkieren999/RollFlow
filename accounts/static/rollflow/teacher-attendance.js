(() => {
 "use strict";
 const controls=[...document.querySelectorAll('.rf-mark-buttons')];
 const selects=[...document.querySelectorAll('.rf-mark-select')];
 if(!selects.length)return;
 function update(){
  const counts={'P':0,'A':0,'L':0,'':0};
  selects.forEach(s=>{if(Object.hasOwn(counts,s.value))counts[s.value]++;});
  for(const [key,value] of Object.entries(counts)){const node=document.querySelector('[data-rf-count="'+key+'"]');if(node)node.textContent=String(value);}
  controls.forEach(group=>{const select=document.getElementById(group.dataset.markFor);if(!select)return;
    group.querySelectorAll('button').forEach(btn=>{btn.setAttribute('aria-pressed',String(btn.dataset.mark===select.value));btn.disabled=select.disabled;});});
 }
 controls.forEach(group=>{const select=document.getElementById(group.dataset.markFor);if(!select)return;
   group.hidden=false;
   group.addEventListener('click',event=>{const btn=event.target.closest('button[data-mark]');if(!btn||select.disabled||btn.disabled)return;
      select.value=btn.dataset.mark;select.dispatchEvent(new Event('change',{bubbles:true}));});
   select.addEventListener('change',update);
 });
 update();
})();