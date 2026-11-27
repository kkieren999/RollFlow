(() => {
  "use strict";
  function initialise(){
    const shell=document.querySelector('[data-rf-shell="protected"]');
    if(!shell)return;
    const button=shell.querySelector('.rf-p-menu'),side=shell.querySelector('.rf-protected-sidebar');
    if(!button||!side)return;
    const mobile=matchMedia('(max-width:820px)');
    const header=shell.querySelector('.rf-protected-top');
    const account=shell.querySelector('.rf-p-account');
    const main=document.getElementById('main-content');
    shell.dataset.enhanced='true';
    if(main && !main.hasAttribute('tabindex'))main.tabIndex=-1;
    const expanded=()=>button.getAttribute('aria-expanded')==='true';
    function toggle(open,returnFocus=false){
      const next=!!open&&mobile.matches;
      shell.dataset.menuOpen=String(next);
      button.setAttribute('aria-expanded',String(next));
      if(next){
        if(header)shell.style.setProperty('--rf-mobile-header-height',header.offsetHeight+'px');
        (side.querySelector('[aria-current="location"]')||side.querySelector('a'))?.focus();
      }else if(returnFocus&&mobile.matches)button.focus();
    }
    function closeAccount(returnFocus=false){
      if(!account?.open)return;
      account.open=false;
      if(returnFocus)account.querySelector('summary')?.focus();
    }
    button.addEventListener('click',()=>{closeAccount();toggle(!expanded(),expanded());});
    document.addEventListener('keydown',e=>{
      if(e.key==='Escape'){
        if(expanded()){e.preventDefault();toggle(false,true);}
        else if(account?.open){e.preventDefault();closeAccount(true);}
      }
    });
    document.addEventListener('focusin',e=>{
      if(expanded()&&!side.contains(e.target)&&!button.contains(e.target))toggle(false);
      if(account?.open&&!account.contains(e.target))closeAccount();
    });
    document.addEventListener('click',e=>{
      if(account?.open&&!account.contains(e.target))closeAccount();
      if(expanded()&&!side.contains(e.target)&&!button.contains(e.target))toggle(false,side.contains(document.activeElement));
    });
    mobile.addEventListener('change',()=>toggle(false,mobile.matches&&side.contains(document.activeElement)));
    const skip=document.querySelector('a.rf-skip[href="#main-content"]');
    skip?.addEventListener('click',()=>main?.focus());
    // Give horizontal tables keyboard access only when they actually overflow.
    // No content or records are copied; the original form and table semantics remain.
    if(!main)return;
    const wrappers=new Set();
    main.querySelectorAll('table').forEach(table=>{
      if(table.closest('table table'))return;
      let wrapper=table.closest('.table-wrap,.live-table,.scroll,.rf-scroll-table');
      if(!wrapper){
        wrapper=document.createElement('div');wrapper.className='rf-scroll-table';
        table.before(wrapper);wrapper.append(table);
      }
      wrappers.add(wrapper);
    });
    function updateScroll(wrapper){
      const overflow=wrapper.scrollWidth>wrapper.clientWidth+2;
      wrapper.dataset.rfScrollable=String(overflow);
      if(overflow&&!wrapper.hasAttribute('tabindex')){
        wrapper.tabIndex=0;wrapper.dataset.rfAddedTabindex='true';
        if(!wrapper.hasAttribute('role')){wrapper.setAttribute('role','region');wrapper.dataset.rfAddedRole='true';}
        if(!wrapper.hasAttribute('aria-label')&&!wrapper.hasAttribute('aria-labelledby')){
          const section=wrapper.closest('section,article');
          const heading=section?.querySelector('h2,h3');
          wrapper.setAttribute('aria-label',(heading?.textContent.trim()||'Data table')+' — scroll horizontally');
          wrapper.dataset.rfAddedLabel='true';
        }
      }else if(!overflow&&wrapper.dataset.rfAddedTabindex==='true'){
        wrapper.removeAttribute('tabindex');delete wrapper.dataset.rfAddedTabindex;
        if(wrapper.dataset.rfAddedRole==='true'){wrapper.removeAttribute('role');delete wrapper.dataset.rfAddedRole;}
        if(wrapper.dataset.rfAddedLabel==='true'){wrapper.removeAttribute('aria-label');delete wrapper.dataset.rfAddedLabel;}
      }
    }
    wrappers.forEach(updateScroll);
    if('ResizeObserver' in window){
      const observer=new ResizeObserver(entries=>entries.forEach(entry=>updateScroll(entry.target)));
      wrappers.forEach(wrapper=>observer.observe(wrapper));
    }else window.addEventListener('resize',()=>wrappers.forEach(updateScroll),{passive:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialise);else initialise();
})();
