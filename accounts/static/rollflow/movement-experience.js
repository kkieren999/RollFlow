(() => {
 "use strict";
 const form=document.getElementById('rf-movement-wizard');
 if(form){
  const student=form.querySelector('select[name=student]'),destination=form.querySelector('select[name=destination]'),confirm=form.querySelector('input[name=confirm]'),review=document.getElementById('rf-movement-review'),steps=[...form.querySelectorAll('.rf-wiz-steps li')];
  function update(){
    const step=!student.value?0:!destination.value?1:2;
    steps.forEach((s,i)=>{if(i===step)s.setAttribute('aria-current','step');else s.removeAttribute('aria-current');s.dataset.complete=String(i<step);});
    review.textContent=step===2?'Review: '+student.selectedOptions[0].textContent.trim()+' → '+destination.selectedOptions[0].textContent.trim()+'. Confirm only when the student is departing.':'Choose the student and destination before confirming departure.';
  }
  [student,destination].forEach(s=>s.addEventListener('change',()=>{confirm.checked=false;update();}));update();
 }
 const search=document.getElementById('rf-movement-search');
 if(search){
   const input=document.getElementById('rf-movement-query'),status=document.getElementById('rf-movement-search-status'),rows=[...document.querySelectorAll('[data-rf-pass-row]')];
   search.hidden=false;
   input.addEventListener('input',()=>{const q=input.value.trim().toLocaleLowerCase();let count=0;
     rows.forEach(r=>{r.hidden=!!q&&!r.textContent.toLocaleLowerCase().includes(q);if(!r.hidden)count++;});
     status.textContent=count+' matching displayed passes. Search is limited to the current page of authorised records.';
   });
 }
})();