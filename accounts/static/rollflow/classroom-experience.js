(() => {
 "use strict";
 const editor=document.getElementById('rf-seat-editor'),form=document.getElementById('rf-seating-form');
 if(editor&&form){
  const grid=document.getElementById('rf-seat-grid'),student=document.getElementById('rf-seat-student'),range=document.getElementById('rf-seat-range'),message=document.getElementById('rf-seat-message'),fields=[...form.querySelectorAll('input[name^=seat_]')];
  const id=f=>f.name.slice(5),byId=new Map(fields.map(f=>[id(f),f]));
  function render(focus){
   const start=Number(range.value);grid.replaceChildren();
   for(let n=start;n<start+40;n++){
    const assigned=fields.filter(f=>Number(f.value)===n&&f.value!=='');
    const b=document.createElement('button');b.type='button';b.dataset.seat=String(n);
    b.className='rf-seat';b.dataset.occupied=String(assigned.length>0);
    const number=document.createElement('strong');number.textContent='Seat '+n;b.append(number);
    const label=document.createElement('span');label.textContent=assigned.length===1?assigned[0].dataset.seatName:assigned.length?'Duplicate — review':'Empty';b.append(label);
    b.setAttribute('aria-label','Seat '+n+', '+label.textContent);
    b.setAttribute('aria-pressed',String(assigned.some(f=>id(f)===student.value)));
    b.addEventListener('click',()=>{
      const chosen=byId.get(student.value);if(!chosen){message.textContent='Choose a student first.';return;}
      if(assigned.some(f=>f!==chosen)){message.textContent='Seat already occupied. Choose an empty seat or unassign its occupant first.';return;}
      chosen.value=String(n);message.textContent=chosen.dataset.seatName+' assigned to seat '+n+' in this unsaved plan.';render(n);
    });grid.append(b);
   }
   if(focus)grid.querySelector('[data-seat="'+focus+'"]')?.focus();
   const duplicates=fields.filter(f=>f.value&&fields.some(other=>other!==f&&Number(other.value)===Number(f.value)));
   fields.forEach(f=>f.setCustomValidity(duplicates.includes(f)?'Each seat may have only one student.':''));
  }
  editor.hidden=false;document.getElementById('rf-seat-numbers').open=false;
  range.addEventListener('change',()=>render());student.addEventListener('change',()=>render());
  fields.forEach(f=>f.addEventListener('input',()=>render()));
  document.getElementById('rf-seat-clear').addEventListener('click',()=>{const f=byId.get(student.value);if(!f){message.textContent='Choose a student first.';return;}f.value='';message.textContent=f.dataset.seatName+' unassigned in this unsaved plan.';render();});
  form.addEventListener('submit',e=>{if(!form.checkValidity()){document.getElementById('rf-seat-numbers').open=true;form.reportValidity();e.preventDefault();}});
  form.addEventListener('invalid',()=>{document.getElementById('rf-seat-numbers').open=true;},true);
  render();
 }
 const picker=document.getElementById('rf-class-action-picker');
 if(picker){
  const student=document.getElementById('rf-action-student'),kind=document.getElementById('rf-action-kind'),status=document.getElementById('rf-action-status'),forms=[...document.querySelectorAll('[data-class-action]')];
  function update(){forms.forEach(f=>{f.hidden=!student.value||f.dataset.classAction!==kind.value;f.querySelector('select[name=student]').value=student.value;});
    status.textContent=student.value&&kind.value?'3. Review the details below, then explicitly submit the selected action.':'Choose a student and action to continue.';}
  picker.hidden=false;student.addEventListener('change',update);kind.addEventListener('change',update);update();
  forms.forEach(f=>f.querySelector('select[name=student]').addEventListener('change',e=>{student.value=e.target.value;update();}));
 }
})();