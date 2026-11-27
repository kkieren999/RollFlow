(() => {
 "use strict";
 function start(){
  const form=document.querySelector('.rf-grant-form'),config=document.getElementById('rf-scope-capabilities');
  if(!form||!config)return;
  const map=JSON.parse(config.textContent),scope=form.querySelector('#id_scope'),value=form.querySelector('#id_scope_value'),role=form.querySelector('#id_role'),template=form.querySelector('#id_template'),hint=document.getElementById('rf-scope-guidance');
  if(!scope||!value||!role||!hint)return;
  const choices=[...form.querySelectorAll('input[name="capabilities"]')];
  const instructions={school:'Whole school: leave Scope value completely empty. Destination reception requires a separate destination grant.',faculty:'Staff faculty: enter the exact existing faculty name. Only faculty-scoped modules are available.',year:'Year level: enter a number from 7 to 12.',class:'Published class: enter an exact active class code and choose a future expiry.',destination:'Movement destination: enter an active staffed destination ID. Only reception is available.'};
  function refresh(){
    const allowed=new Set(map[scope.value]||[]);
    let invalid=0;
    choices.forEach(box=>{const permitted=allowed.has(box.value);
      box.disabled=!permitted&&!box.checked;
      box.closest('div')?.setAttribute('data-rf-unavailable',permitted?'no':'yes');
      if(!permitted&&box.checked)invalid++;
    });
    value.placeholder=scope.value==='school'?'Leave empty':scope.value==='year'?'7–12':scope.value==='faculty'?'Exact faculty name':scope.value==='class'?'Published class code':scope.value==='destination'?'Destination ID':'Choose a scope';
    let text=instructions[scope.value]||'Choose a scope first. No access is selected automatically.';
    if(!template?.value&&role.value==='Head of Department'&&scope.value!=='faculty')text+=' Head of Department requires staff faculty scope.';
    if(!template?.value&&role.value==='Head of Year'&&scope.value!=='year')text+=' Head of Year requires year level scope.';
    if(template?.value)text+=' Choose the exact template scope; leave all capabilities unchecked to copy its reviewed bundle.';
    if(invalid)text+=' '+invalid+' selected capabilities are incompatible. Uncheck them or change scope before granting.';
    if(scope.value==='school'&&value.value.trim())text+=' Clear Scope value for whole school.';
    hint.textContent=text;
  }
  form.addEventListener('change',refresh);value.addEventListener('input',refresh);refresh();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();