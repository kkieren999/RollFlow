(() => {
  "use strict";
  function initialise(){
    const shell=document.querySelector('[data-rf-shell="protected"]');
    if(!shell)return;
    const button=shell.querySelector('.rf-p-menu'),side=shell.querySelector('.rf-protected-sidebar');
    if(!button||!side)return;
    shell.dataset.enhanced='true';
    const toggle=open=>{shell.dataset.menuOpen=String(open);button.setAttribute('aria-expanded',String(open));};
    button.addEventListener('click',()=>toggle(button.getAttribute('aria-expanded')!=='true'));
    document.addEventListener('keydown',e=>{if(e.key==='Escape'){
      if(button.getAttribute('aria-expanded')==='true'){toggle(false);button.focus();}
      const account=shell.querySelector('.rf-p-account[open]');if(account){account.open=false;account.querySelector('summary').focus();}
    }});
    document.addEventListener('click',e=>{const account=shell.querySelector('.rf-p-account[open]');if(account&&!account.contains(e.target))account.open=false;
      if(button.getAttribute('aria-expanded')==='true'&&!side.contains(e.target)&&!button.contains(e.target))toggle(false);});
    matchMedia('(min-width:821px)').addEventListener('change',()=>toggle(false));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialise);else initialise();
})();