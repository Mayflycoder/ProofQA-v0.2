// ChangeRipple v0.1 — deterministic synthetic-data impact analysis.
// No remote access, regulated validation claims, or automated change approvals.
export const VERSION = "CR-DEMO-0.1";
export const DEPARTMENTS = [
  "PQA", "Warehouse", "QA", "Process Engineering", "Quality NPI",
  "Technical Support", "Supplier Quality", "Validation", "QC Lab",
  "Training", "Regulatory"
];
const node = (id, type, name, department, revision="A", note="Fictional demonstration record") =>
  ({ id, type, name, department, revision, note, status: "Active" });
export const NODES = [
  node("SUP-101","Supplier","Northstar Polymers (fictional)","Supplier Quality"),
  node("SUP-102","Supplier","Meridian Packaging (fictional)","Supplier Quality"),
  node("MAT-201","Material","Thermoforming film","Supplier Quality","C"),
  node("MAT-202","Material","Heat-seal coating","Supplier Quality","B"),
  node("MAT-203","Material","Carton board","Warehouse","D"),
  node("SPEC-301","Specification","Incoming film specification","QA","E"),
  node("SPEC-302","Specification","Seal strength specification","PQA","B"),
  node("SPEC-303","Specification","Carton identification specification","Quality NPI","C"),
  node("SOP-401","Procedure","Incoming material inspection","QA","F"),
  node("SOP-402","Procedure","Warehouse receipt and segregation","Warehouse","D"),
  node("SOP-403","Procedure","Sealing process setup","Process Engineering","G"),
  node("SOP-404","Procedure","Product acceptance and release","QA","C"),
  node("SOP-405","Procedure","Supplier change evaluation","Supplier Quality","B"),
  node("SOP-406","Procedure","NPI change transfer","Quality NPI","A"),
  node("SOP-407","Procedure","Technical complaint escalation","Technical Support","C"),
  node("SOP-408","Procedure","Change control","QA","D"),
  node("SOP-409","Procedure","Nonconformance investigation","QA","C"),
  node("SOP-410","Procedure","Corrective and preventive action","QA","E"),
  node("PROC-501","Operation","Receive and quarantine material","Warehouse"),
  node("PROC-502","Operation","Incoming acceptance inspection","QC Lab"),
  node("PROC-503","Operation","Package forming operation","Process Engineering"),
  node("PROC-504","Operation","Heat sealing operation","Process Engineering"),
  node("PROC-505","Operation","Final batch release review","QA"),
  node("TEST-601","Test method","Film identity and dimensions","QC Lab","D"),
  node("TEST-602","Test method","Seal strength test","PQA","B"),
  node("TEST-603","Test method","Package integrity test","PQA","C"),
  node("TEST-604","Test method","Environmental conditioning test","Validation","A"),
  node("VAL-701","Validation","Heat seal process qualification","Validation","C"),
  node("VAL-702","Validation","Package integrity method validation","Validation","B"),
  node("RISK-801","Risk record","Packaging process risk file","Quality NPI","D"),
  node("RISK-802","Risk record","Incoming material risk review","QA","B"),
  node("TRAIN-901","Training","Receiving operator training","Training","C"),
  node("TRAIN-902","Training","Sealing operator training","Training","B"),
  node("TRAIN-903","Training","Inspection training","Training","D"),
  node("REC-1001","Record","Incoming inspection worksheet","QC Lab","B"),
  node("REC-1002","Record","Batch acceptance record","QA","A"),
  node("PROD-1101","Product","Barrier pack model A","Quality NPI","C"),
  node("PROD-1102","Product","Barrier pack model B","Quality NPI","B"),
  node("EQ-1201","Equipment","Heat sealer station 01","Process Engineering","A"),
  node("EQ-1202","Equipment","Unused demo inspection gauge",null,"A"),
  node("NC-1301","Nonconformance","Fictional material inspection omission","QA","A"),
  node("CAPA-1401","CAPA","Improve material acceptance controls","QA","A"),
  node("SOP-411","Procedure","Unlinked maintenance instruction",null,"A")
];
const E = (from,to,type,required=false) => ({ id: "EDGE-" + from + "-" + to, from,to,type,required,source:"synthetic-mapping" });
export const RELATIONS = [
 E("SUP-101","MAT-201","supplies",true),E("SUP-102","MAT-202","supplies",true),
 E("MAT-201","SPEC-301","governed by",true),E("MAT-201","PROC-503","consumed by",true),
 E("MAT-202","PROC-504","consumed by",true),E("MAT-201","PROD-1101","used in",true),
 E("MAT-202","PROD-1101","used in",true),E("MAT-202","PROD-1102","used in",true),
 E("SPEC-301","SOP-401","referenced by",true),E("SPEC-301","TEST-601","verified by",true),
 E("SPEC-302","TEST-602","verified by",true),E("SPEC-302","SOP-403","referenced by",false),
 E("SPEC-303","PROD-1102","referenced by",false),
 E("SOP-401","PROC-502","governs",true),E("SOP-401","REC-1001","records in",true),
 E("SOP-401","TRAIN-903","training impact",true),E("SOP-401","SOP-404","feeds",false),
 E("SOP-402","PROC-501","governs",true),E("SOP-402","TRAIN-901","training impact",true),
 E("SOP-402","SOP-401","interfaces with",false),E("PROC-501","PROC-502","feeds",true),
 E("PROC-501","REC-1001","record used",false),
 E("PROC-502","TEST-601","tested by",true),E("PROC-502","REC-1001","records in",true),
 E("PROC-502","PROC-503","feeds",true),
 E("PROC-503","PROC-504","feeds",true),E("PROC-503","TEST-604","tested by",false),
 E("PROC-504","TEST-602","tested by",true),E("PROC-504","TEST-603","tested by",true),
 E("PROC-504","EQ-1201","uses equipment",true),E("PROC-504","VAL-701","validated by",true),
 E("PROC-504","TRAIN-902","training impact",true),
 E("TEST-603","VAL-702","validated by",true),
 E("PROC-504","PROC-505","feeds",true),E("PROC-505","REC-1002","records in",true),
 E("SOP-403","PROC-504","governs",true),E("SOP-403","SPEC-302","references",true),
 E("SOP-403","TRAIN-902","training impact",true),E("SOP-403","VAL-701","assessed in",true),
 E("SOP-404","PROC-505","governs",true),E("SOP-404","REC-1002","records in",true),
 E("PROD-1101","RISK-801","risk assessed in",true),
 E("PROD-1101","SPEC-302","quality specification",false),
 E("MAT-201","RISK-802","risk assessed in",true),
 E("SOP-405","SUP-101","supplier oversight",false),
 E("SOP-406","PROD-1101","change transfer",true),
 E("SOP-407","PROD-1101","complaint handling",false),
 E("SOP-408","SOP-401","change impacts",false),
 E("SOP-409","NC-1301","governs",true),
 E("NC-1301","SOP-401","potential correction",false),
 E("NC-1301","PROC-502","possible process impact",false),
 E("CAPA-1401","NC-1301","addresses",true),
 E("CAPA-1401","SOP-410","governed by",true),
 E("CAPA-1401","SOP-401","procedure improvement",false),
 E("CAPA-1401","TRAIN-903","training assessment",false),
 E("SOP-410","SOP-409","interfaces with",false),
 E("TEST-602","SPEC-302","checks criteria",false)
];
export const SCENARIOS = [
 {id:"CR-001",type:"Supplier change",title:"Supplier film resin formulation notice",summary:"Fictional supplier reports an authorized formulation revision. Review incoming specifications, test methods, products, validation and affected operational controls.",roots:["SUP-101"]},
 {id:"CR-002",type:"Procedure change",title:"Revise incoming inspection release steps",summary:"Fictional SOP revision changes the sequence for incoming inspections and release decisions across warehouse and quality.",roots:["SOP-401"]},
 {id:"CR-003",type:"NC / CAPA",title:"Material acceptance process omission",summary:"Fictional investigation examines omitted incoming sampling, extent of condition, affected product and effectiveness evidence.",roots:["CAPA-1401"]}
];
export const CAPA_CHECKS = [
 ["containment","Containment and immediate controls"],["correction","Correction / disposition of affected records"],
 ["extent","Scope and extent-of-condition review"],["root","Evidence-supported root cause"],
 ["action","Systemic corrective action"],["prevention","Related processes and prevention"],
 ["verify","Verification or validation of implemented actions"],
 ["effectiveness","Effectiveness monitoring and recurrence check"],["docs","Procedure, risk and training updates"]
];
const norm = (a,b)=>String(a||"").localeCompare(String(b||""));
export function graphGaps(nodes=NODES,edges=RELATIONS) {
 const ids = new Set(nodes.map(n=>n.id));
 const attached = new Set();
 for (const e of edges) { if (ids.has(e.from)&&ids.has(e.to)) {attached.add(e.from);attached.add(e.to);} }
 const linkedIn = nodeId => edges.some(e=>e.to===nodeId || e.from===nodeId);
 return {
  unowned:nodes.filter(n=>!n.department),
  orphans:nodes.filter(n=>!attached.has(n.id)),
  invalidEdges:edges.filter(e=>!ids.has(e.from)||!ids.has(e.to)),
  materialsWithoutSupplier:nodes.filter(n=>n.type==="Material"&&!edges.some(e=>e.type==="supplies"&&e.to===n.id)),
  operationsWithoutTest:nodes.filter(n=>n.type==="Operation"&&!edges.some(e=>e.from===n.id&&e.type==="tested by")),
  productsWithoutRisk:nodes.filter(n=>n.type==="Product"&&!edges.some(e=>e.from===n.id&&e.type==="risk assessed in"))
 };
}
export function traverse(roots,edges=RELATIONS,nodes=NODES,maxHops=3) {
 const idSet=new Set(nodes.map(n=>n.id)), validRoots=[...new Set(roots)].filter(id=>idSet.has(id)).sort(norm);
 const results=new Map(),queue=[];
 for(const r of validRoots){results.set(r,{nodeId:r,hop:0,path:[r],edgeIds:[],required:false});queue.push(r);}
 const sorted=[...edges].filter(e=>idSet.has(e.from)&&idSet.has(e.to)).sort((a,b)=>norm(a.from,b.from)||norm(a.to,b.to)||norm(a.type,b.type));
 while(queue.length){
  const cur=queue.shift(),start=results.get(cur);
  if(start.hop>=maxHops) continue;
  for(const e of sorted.filter(x=>x.from===cur)){
   if(results.has(e.to)) continue;
   const v={nodeId:e.to,hop:start.hop+1,path:[...start.path,e.to],edgeIds:[...start.edgeIds,e.id],required: start.hop===0&&!!e.required};
   results.set(e.to,v);queue.push(e.to);
  }
 }
 return [...results.values()].filter(x=>x.hop>0).sort((a,b)=>a.hop-b.hop||norm(a.nodeId,b.nodeId));
}
export function analyze(input,edges=RELATIONS,nodes=NODES,now="2026-10-19T00:00:00.000Z") {
 const hits=traverse(input.roots,edges,nodes);
 const byId=new Map(nodes.map(n=>[n.id,n]));
 const impacts=hits.map(h=>({
   ...h, decision:"Pending",reason:"",
   priority:h.hop===1&&h.required?"High":h.hop===1?"Medium":"Review",
   requirement:h.required?"Mapped review required":"Suggested review"
 }));
 const actions=hits.map(h=>({
   nodeId:h.nodeId, department:byId.get(h.nodeId)?.department||"Unassigned",
   requirement:h.required?"Required":"Suggested",
   status:"Not started",note:"",owner:"Role pending"
 }));
 const warnings=[];
 if(input.roots.some(id=>!byId.has(id)))warnings.push({id:"WARN-ROOT",text:"One or more input records are not mapped",resolved:false,resolution:""});
 if(graphGaps(nodes,edges).unowned.length)warnings.push({id:"WARN-OWNERS",text:"Dependency library includes assets without departmental owners; unmapped does not mean unaffected",resolved:false,resolution:""});
 if(graphGaps(nodes,edges).orphans.length)warnings.push({id:"WARN-ORPHAN",text:"Dependency library includes disconnected assets; some impacts cannot be traced",resolved:false,resolution:""});
 return {id:input.id||"CR-"+Math.random().toString(36).slice(2,8).toUpperCase(),type:input.type,title:input.title,summary:input.summary||"",
  roots:[...input.roots],createdAt:now,updatedAt:now,modelVersion:VERSION,graphEdges:edges.length,
  impacts,actions,warnings,checklist:input.type==="NC / CAPA"?CAPA_CHECKS.map(([key,label])=>({key,label,status:"Not verified",evidence:""})):[],
  closed:false,reviewNotes:""};
}
export function recompute(assessment,edges=RELATIONS,nodes=NODES,now="2026-10-19T00:00:00.000Z"){
 const fresh=analyze(assessment,edges,nodes,now);
 const oldImpacts=new Map(assessment.impacts.map(i=>[i.nodeId,i]));
 const oldActions=new Map(assessment.actions.map(a=>[a.nodeId,a]));
 fresh.impacts=fresh.impacts.map(i=>({...i,decision:oldImpacts.get(i.nodeId)?.decision||"Pending",reason:oldImpacts.get(i.nodeId)?.reason||""}));
 fresh.actions=fresh.actions.map(a=>({...a,status:oldActions.get(a.nodeId)?.status||a.status,note:oldActions.get(a.nodeId)?.note||"",owner:oldActions.get(a.nodeId)?.owner||"Role pending"}));
 fresh.warnings=fresh.warnings.map(w=>({...w,resolved:assessment.warnings.find(p=>p.id===w.id)?.resolved||false,resolution:assessment.warnings.find(p=>p.id===w.id)?.resolution||""}));
 fresh.checklist=assessment.checklist||fresh.checklist;
 fresh.id=assessment.id;fresh.createdAt=assessment.createdAt;fresh.updatedAt=now;fresh.reviewNotes=assessment.reviewNotes||"";
 fresh.addedImpacts=fresh.impacts.filter(i=>!oldImpacts.has(i.nodeId)).map(i=>i.nodeId);
 return fresh;
}
export function closureGate(assessment){
 const reasons=[];
 for(const i of assessment.impacts){
  if(i.decision==="Pending") reasons.push(i.nodeId+": impact has not been dispositioned");
  if(i.decision==="Excluded" && i.reason.trim().length<8) reasons.push(i.nodeId+": exclusion needs a reason");
 }
 for(const a of assessment.actions){
  if(a.requirement==="Required"&& !["Done","Not applicable"].includes(a.status)) reasons.push(a.nodeId+": required review unresolved");
  if(a.status==="Not applicable"&&a.note.trim().length<8) reasons.push(a.nodeId+": N/A needs justification");
  if(a.status==="Done"&&a.note.trim().length<5) reasons.push(a.nodeId+": Done needs reviewer evidence note");
 }
 for(const w of assessment.warnings){ if(!w.resolved||w.resolution.trim().length<8) reasons.push(w.id+": unmapped/uncertain coverage warning unresolved");}
 for(const c of assessment.checklist||[]){if(c.status!=="Verified"||c.evidence.trim().length<8)reasons.push("CAPA "+c.label+": verification evidence required");}
 return {canClose:reasons.length===0,blockers:reasons};
}
export function seedAssessments(edges=RELATIONS,nodes=NODES){
 return SCENARIOS.map(s=>analyze(s,edges,nodes,"2026-10-19T00:00:00.000Z"));
}
