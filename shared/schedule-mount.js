/* Authenticated snapshot provider. No requests, storage or writes. */
(function(){
  "use strict";
  const root=document.querySelector("[data-rf-native-timetable]");
  const node=document.getElementById("rf-shared-schedule");
  if(!root||!node||!window.RollFlowSchedule)return;
  try{
    window.RollFlowSchedule.mount(root,window.RollFlowSchedule.provider(()=>JSON.parse(node.textContent)));
  }catch(error){
    console.warn("Shared schedule unavailable; using server-rendered schedule.");
  }
})();
