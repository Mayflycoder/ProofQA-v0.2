import {VERSION,DEPARTMENTS,NODES,RELATIONS,SCENARIOS,graphGaps,traverse,analyze,recompute,closureGate,seedAssessments} from "./engine.mjs";

const KEY="changeripple.v0.1.synthetic";
const byId=new Map(NODES.map(n=>[n.id,n]));
const esc=(value)=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const short=s=>String(s).length>92?String(s).slice(0,89)+"...":String(s);
const routeNames={overview:"Overview",assessments:"Assessments",new:"New assessment",assessment:"Impact assessment",library:"Dependency library",gaps:"Coverage & gaps",about:"Methodology",report:"Assessment report"};
let ui={route:"overview",tab:"impact",search:"",focus:null,toast:""};
let model=restore();
function initial(){return {schema:1,edges:RELATIONS.map(x=>({...x})),assessments:seedAssessments(),active:"CR-001"};}
function restore(){try{const raw=localStorage.getItem(KEY),x=raw&&JSON.parse(raw);if(x&&x.schema===1&&Array.isArray(x.edges)&&Array.isArray(x.assessments)&&typeof x.active==="string")return x;}catch(_){}return initial();}
function save(){try{localStorage.setItem(KEY,JSON.stringify(model));}catch(_){ui.toast="Browser storage unavailable; changes may not survive refresh.";}}
function active(){return model.assessments.find(x=>x.id===model.active)||model.assessments[0];}
function setActive(id){if(model.assessments.some(x=>x.id===id)){model.active=id;save();}}
function countOpen(a){return a.actions.filter(x=>x.status!=="Done"&&x.status!=="Not applicable").length;}
function statusBadge(s){const color=s==="Closed"||s==="Done"||s==="Included"?"teal":s==="High"?"red":s==="In review"||s==="Pending"?"amber":s==="Not applicable"?"gray":"blue";return '<span class="badge badge-'+color+'">'+esc(s)+'</span>';}
function typeBadge(s){return '<span class="badge badge-'+(s==="NC / CAPA"?"red":s==="Supplier change"?"blue":"teal")+'">'+esc(s)+'</span>';}
function templateHeading(k,title,lead,extra=""){return '<div class="page-heading"><div><p class="eyebrow">'+esc(k)+'</p><h1>'+esc(title)+'</h1><p class="lead" style="margin-bottom:0">'+esc(lead)+'</p></div>'+extra+'</div>';}
function setRoute(s){ui.route=routeNames[s]?s:"overview";ui.toast="";if(s!=="assessment"&&s!=="report")ui.tab="impact";try{location.hash=ui.route;}catch(_){}render();window.scrollTo(0,0);}
function link(id){return '<button class="row-link" data-open="'+esc(id)+'" type="button">Open assessment ↗</button>';}
function fmtDate(s){try{return new Date(s).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"});}catch(_){return String(s);}}
function namedNode(id){const n=byId.get(id);return n?n.name:id;}
function depList(assess){return [...new Set(assess.actions.map(a=>a.department))].sort();}
function progress(assess){const all=assess.actions.length,done=assess.actions.filter(x=>x.status==="Done"||x.status==="Not applicable").length;return all?Math.round(100*done/all):0;}

function overview(){
 const gaps=graphGaps(NODES,model.edges);
 const open=model.assessments.reduce((t,a)=>t+countOpen(a),0);
 const impacts=new Set(model.assessments.flatMap(a=>a.impacts.map(x=>x.nodeId)));
 const stats=[
  ["Active assessments",model.assessments.filter(a=>!a.closed).length,"Across 3 change categories","≋"],
  ["Assets in library",NODES.length,"Cross-department records","⌘"],
  ["Impacted assets",impacts.size,"Known mapped dependencies","↗"],
  ["Open review actions",open,"Human decisions required","☷"]
 ];
 return templateHeading("Cross-functional visibility","See the ripples before they become gaps.","Map the downstream impact of a procedure change, supplier notice or NC/CAPA across teams — with transparent evidence paths and review ownership.",'<button type="button" class="btn btn-primary" data-route="new">＋ Start impact assessment</button>')+
 '<div class="grid cols-4">'+stats.map(s=>'<div class="card stat-card"><p class="stat-title">'+s[0]+'</p><div class="stat-mark">'+s[3]+'</div><p class="stat-value">'+s[1]+'</p><div class="stat-bottom">'+s[2]+'</div></div>').join("")+'</div>'+
 '<section class="section"><div class="section-head"><h2>Choose your starting point</h2><span class="text-xs muted">Three connected quality workflows</span></div><div class="grid cols-3">'+
 [["Supplier change","Trace suppliers through materials, specifications, processes, tests, and affected products.","⇄","Supplier change"],
  ["Internal procedure change","Identify cross-functional review actions and downstream documents, training, validation, and records.","▤","Procedure change"],
  ["NC / CAPA investigation","Examine extent of condition, corrective actions, evidence gaps, system impact and effectiveness.","◇","NC / CAPA"]].map(s=>
 '<div class="card workflow"><div class="mini-icon">'+s[2]+'</div><h3>'+s[0]+'</h3><p>'+s[1]+'</p><button class="btn btn-small" type="button" data-start="'+esc(s[3])+'">Begin assessment →</button></div>').join("")+'</div></section>'+
 '<section class="section grid cols-2"><div class="card"><div class="card-head"><h2>Recent assessments</h2><button class="text-link" type="button" data-route="assessments">View all →</button></div>'+
 model.assessments.map(a=>'<div class="mini-assess" style="border-top:1px solid #ebf0f3;padding:14px 0;display:flex;justify-content:space-between;gap:9px;align-items:center"><div><div class="table-title">'+esc(a.title)+'</div><div class="table-sub">'+esc(a.id)+' · '+a.impacts.length+' mapped impacts · '+countOpen(a)+' open reviews</div></div><button class="btn btn-small" data-open="'+esc(a.id)+'">Review →</button></div>').join("")+
 '</div><div class="note-card"><p class="eyebrow">THE FIRST RULE</p><h2 style="color:#164d4e">Unmapped does not mean unaffected.</h2><p>Dependency maps are only as reliable as their documented relationships. This workspace deliberately contains '+gaps.orphans.length+' disconnected and '+gaps.unowned.length+' unowned assets. Check coverage gaps and request human review before any quality decision.</p><div class="separator" style="background:#cde1de"></div><button class="btn" type="button" data-route="gaps">Explore coverage gaps →</button></div></section>';
}
function assessments(){
 return templateHeading("Assessment register","Impact assessments","Start with a change or investigation, trace approved relationships, then disposition impacts and required reviews.",'<button type="button" data-route="new" class="btn btn-primary">＋ New assessment</button>')+
 '<div class="card"><div class="card-head"><h2>All assessments</h2><span class="card-sub">'+model.assessments.length+' records · local demo</span></div>'+
 '<div class="table-wrap"><table><thead><tr><th>Assessment</th><th>Type</th><th>Impacts</th><th>Open actions</th><th>Status</th><th></th></tr></thead><tbody>'+
 model.assessments.map(a=>'<tr><td><div class="table-title">'+esc(a.title)+'</div><span class="table-sub">'+esc(a.id)+' · '+fmtDate(a.createdAt)+'</span></td><td>'+typeBadge(a.type)+'</td><td>'+a.impacts.length+'</td><td>'+countOpen(a)+'</td><td>'+statusBadge(a.closed?"Closed":"Review required")+'</td><td>'+link(a.id)+'</td></tr>').join("")+
 '</tbody></table></div></div>';
}
function newAssessment(){
 return templateHeading("New impact analysis","Start an assessment","Provide the fictional change details and choose a known source record. The engine traces only mapped relationships. No AI-generated regulatory conclusions.")+
 '<div class="card form-max"><form id="newAssessmentForm">'+
 '<div class="field"><label for="type">Change / investigation category</label><select id="type" name="type">'+SCENARIOS.map(x=>'<option value="'+esc(x.type)+'" '+(ui.preselect===x.type?"selected":"")+'>'+esc(x.type)+'</option>').join("")+'</select></div>'+
 '<div class="field"><label for="title">Assessment title</label><input id="title" name="title" maxlength="130" minlength="6" required placeholder="e.g. Update fictional incoming inspection sampling procedure"></div>'+
 '<div class="field"><label for="summary">Change description and review rationale</label><textarea id="summary" name="summary" maxlength="1100" required placeholder="Describe what changes, why, and what must be examined. Use fictional data only."></textarea></div>'+
 '<div class="field"><label for="root">Changed / source record</label><select id="root" name="root">'+[...NODES].sort((a,b)=>a.id.localeCompare(b.id)).map(n=>'<option value="'+esc(n.id)+'">'+esc(n.id+" — "+n.name+" · "+(n.department||"Unassigned"))+'</option>').join("")+'</select><small>Current MVP supports one named source per assessment and 3 propagation hops. It cannot infer unlisted relationships.</small></div>'+
 '<div class="notice">Only synthetic demo data is permitted. This tool is not a replacement for approved change control, NC/CAPA procedures or authorized quality reviewers.</div>'+
 '<div style="display:flex;gap:11px;margin-top:22px"><button class="btn btn-primary" type="submit">Analyze dependencies →</button><button type="button" class="btn" data-route="assessments">Cancel</button></div>'+
 '</form></div>';
}
function tracePath(hit,edges=model.edges){
 const labels=hit.path.map((id,i)=>'<span class="lineage-item" title="'+esc(namedNode(id))+'">'+esc(id)+'</span>'+ (i<hit.path.length-1?'<span class="lineage-arrow">→</span>':"")).join("");
 const details=hit.edgeIds.map(id=>{const e=edges.find(x=>x.id===id);return e?e.from+" "+e.type+" "+e.to:"Unmapped edge"}).join(" · ");
 return '<div class="lineage" title="'+esc(details)+'">'+labels+'</div>';
}
function impactScreen(a){
 let rows=a.impacts.map(hit=>{
  const n=byId.get(hit.nodeId)||{id:hit.nodeId,type:"Unknown",name:hit.nodeId,department:"Unassigned",revision:"?"};
  return '<article class="impact"><div class="impact-top"><div><p class="impact-title">'+esc(n.name)+' <span class="mono">'+esc(n.id)+'</span></p><div class="impact-meta">'+statusBadge(hit.priority)+'<span class="badge badge-gray">'+esc(n.type)+'</span><span class="text-xs muted">'+esc(n.department||"Unassigned")+'</span><span class="badge '+(hit.required?"badge-red":"badge-blue")+'">'+esc(hit.requirement)+'</span></div></div><span class="text-xs muted">Hop '+hit.hop+'</span></div>'+
 '<p class="impact-desc">Flagged because this record is connected through the following mapped path. This is a review candidate, not a proven product impact.</p>'+tracePath(hit)+
 '<div class="impact-review"><div><label for="i-'+esc(n.id)+'">Reviewer disposition</label><select class="inline-select" id="i-'+esc(n.id)+'" data-decision="'+esc(n.id)+'">'+["Pending","Included","Excluded"].map(s=>'<option '+(hit.decision===s?"selected":"")+'>'+s+'</option>').join("")+'</select></div><div><label for="r-'+esc(n.id)+'">Decision rationale (required to exclude)</label><input class="inline-input" id="r-'+esc(n.id)+'" data-reason="'+esc(n.id)+'" value="'+esc(hit.reason)+'" placeholder="Record the human review justification"></div></div></article>';
 }).join("");
 return '<div class="grid cols-3" style="margin-bottom:18px">'+[
 ["Identified downstream assets",a.impacts.length],
 ["Mapped required reviews",a.actions.filter(x=>x.requirement==="Required").length],
 ["Departments represented",depList(a).length]
 ].map(s=>'<div class="card card-tight"><p class="stat-title">'+s[0]+'</p><p class="stat-value" style="font-size:25px;margin:0">'+s[1]+'</p></div>').join("")+'</div>'+
 '<div class="notice" style="margin-bottom:17px">An impact is identified through known relationships up to three hops away. Relationships are not discovered automatically. Suggested impacts and required reviews are not determinations of safety, regulatory compliance or process effectiveness.</div>'+
 '<div class="impact-list">'+(rows||'<div class="notice">No downstream mapped assets found. That is a coverage gap, not evidence of no impact.</div>')+'</div>';
}
function reviewScreen(a){
 return '<div class="card" style="margin-bottom:18px"><div class="card-head"><h2>Cross-functional action register</h2><span class="card-sub">'+a.actions.length+' actions · '+progress(a)+'% dispositioned</span></div><p class="text-sm muted">Required actions must be completed or justified as not applicable. Marking Done requires a reviewer evidence note. All decisions are browser-only demo data.</p>'+
 '<div class="table-wrap"><table class="action-table"><thead><tr><th>Department / asset</th><th>Expected review</th><th>Disposition</th><th>Reviewer evidence note</th></tr></thead><tbody>'+
 a.actions.slice().sort((x,y)=>x.department.localeCompare(y.department)||x.nodeId.localeCompare(y.nodeId)).map(x=>{
 const n=byId.get(x.nodeId);
 return '<tr><td><div class="table-title">'+esc(x.department)+'</div><div class="table-sub">'+esc(x.nodeId)+" · "+esc(short(n?.name||"Unknown"))+'</div></td><td>'+statusBadge(x.requirement)+'</td><td><select class="inline-select" aria-label="Status for '+esc(x.nodeId)+'" data-action="'+esc(x.nodeId)+'">'+["Not started","In review","Done","Not applicable"].map(s=>'<option '+(x.status===s?"selected":"")+'>'+s+'</option>').join("")+'</select></td><td><textarea class="inline-note" aria-label="Evidence note for '+esc(x.nodeId)+'" data-note="'+esc(x.nodeId)+'" placeholder="Decision, reference or N/A justification">'+esc(x.note)+'</textarea></td></tr>';
 }).join("")+'</tbody></table></div></div>'+
 '<div class="card"><div class="card-head"><h2>Unverified coverage warnings</h2><span class="badge badge-amber">NOT_VERIFIED</span></div>'+
 a.warnings.map(w=>'<div style="padding:14px 0;border-top:1px solid #edf0f4"><strong class="text-sm">'+esc(w.text)+'</strong><div class="field-row" style="margin-top:9px;align-items:center"><select class="inline-select" aria-label="Coverage status '+esc(w.id)+'" data-warning="'+esc(w.id)+'"><option value="open" '+(!w.resolved?"selected":"")+'>Unresolved</option><option value="resolved" '+(w.resolved?"selected":"")+'>Reviewed with evidence</option></select><input class="inline-input" data-warning-note="'+esc(w.id)+'" value="'+esc(w.resolution)+'" placeholder="Explain scope and evidence; at least 8 characters"></div></div>').join("")+'</div>';
}
function capaScreen(a){
 if(a.type!=="NC / CAPA")return '<div class="card"><h2>NC/CAPA checklist</h2><p class="muted">This assessment is not an NC/CAPA. Open the synthetic NC/CAPA example to see extent-of-condition, correction and effectiveness checks.</p><button class="btn" data-open="CR-003">View CAPA example →</button></div>';
 return '<div class="card"><div class="card-head"><h2>NC/CAPA investigation completeness</h2><span class="badge badge-red">Human verification required</span></div>'+
 '<div class="notice">Correction ≠ corrective action; implementation ≠ effectiveness. Items marked Verified require actual referenced evidence. No checklist is automatically satisfied.</div>'+
 '<div style="margin-top:15px">'+a.checklist.map(c=>'<div class="checklist-row"><strong>'+esc(c.label)+'</strong><select class="inline-select" aria-label="Status '+esc(c.key)+'" data-check="'+esc(c.key)+'">'+["Not verified","In review","Verified"].map(s=>'<option '+(c.status===s?"selected":"")+'>'+s+'</option>').join("")+'</select><input class="inline-input" data-check-note="'+esc(c.key)+'" value="'+esc(c.evidence)+'" placeholder="Synthetic reference / evidence with reviewer assessment"></div>').join("")+'</div></div>';
}
function assessment(){
 const a=active();if(!a)return assessments();
 const gate=closureGate(a);
 const tabs=[["impact","Impact map"],["reviews","Review actions ("+a.actions.length+")"],["capa","NC/CAPA checklist"],["coverage","Coverage review"]];
 const head=templateHeading(a.id,a.title,a.summary,
 '<div class="heading-actions"><button type="button" data-export="json" class="btn">↓ JSON</button><button type="button" data-export="csv" class="btn">↓ Actions CSV</button><button type="button" data-route="report" class="btn">Print report</button></div>');
 const cols='<div class="pillrow">'+typeBadge(a.type)+statusBadge(a.closed?"Closed":"In review")+'<span class="badge badge-gray">Rules '+esc(VERSION)+'</span><span class="badge badge-gray">'+a.graphEdges+' evaluated relationships</span></div>'+
 '<div class="detail-box"><strong>Input scope:</strong> '+a.roots.map(r=>esc(namedNode(r))+' ('+esc(r)+')').join(", ")+'<br><strong>Assessed on:</strong> '+esc(fmtDate(a.createdAt))+' · <strong>Mapped coverage:</strong> '+depList(a).map(esc).join(", ")+(a.addedImpacts?.length?'<br><strong>New impacts after mapping change:</strong> '+a.addedImpacts.map(esc).join(", "):"")+'</div>';
 const tabbar='<div class="tabbar">'+tabs.map(([s,l])=>'<button class="'+(ui.tab===s?"active":"")+'" data-tab="'+s+'">'+esc(l)+'</button>').join("")+'</div>';
 let body=ui.tab==="impact"?impactScreen(a):ui.tab==="reviews"?reviewScreen(a):ui.tab==="capa"?capaScreen(a):coverageForAssessment(a);
 const gatePanel='<div class="gate '+(gate.canClose?"pass":"")+'"><div class="gate-head"><span style="font-size:23px">'+(gate.canClose?"✓":"◇")+'</span><h3 class="gate-title">'+(gate.canClose?"All configured closure checks complete":"Closure blocked — "+gate.blockers.length+" outstanding conditions")+'</h3></div><p>'+ (gate.canClose?"Configured workflow checks are satisfied in this synthetic demo. This is not regulatory approval.":"Human disposition, verified evidence and coverage review are needed before completing this prototype workflow.")+'</p>'+
 (gate.blockers.length?'<ul>'+gate.blockers.slice(0,6).map(x=>'<li>'+esc(x)+'</li>').join("")+(gate.blockers.length>6?'<li>... and '+(gate.blockers.length-6)+' more.</li>':"")+'</ul>':"")+
 '<div style="margin-top:15px;display:flex;gap:9px;flex-wrap:wrap"><button class="btn btn-primary" data-close '+(!gate.canClose||a.closed?"disabled":"")+'>'+(a.closed?"Marked closed":"Close demo review")+'</button><button class="btn" data-route="library">Review dependency mapping →</button></div></div>';
 return head+cols+'<div class="section">'+tabbar+body+gatePanel+'</div>';
}
function coverageForAssessment(a){
 const actual=depList(a),missed=DEPARTMENTS.filter(d=>!actual.includes(d));
 return '<div class="grid cols-2"><div class="card"><h2>Departments reached by known mappings</h2><div class="pillrow">'+actual.map(d=>'<span class="badge badge-teal">'+esc(d)+'</span>').join("")+'</div><p class="text-sm muted">This reflects the known graph only.</p></div><div class="card"><h2>Departments not reached</h2><div class="pillrow">'+missed.map(d=>'<span class="badge badge-amber">'+esc(d)+'</span>').join("")+'</div><p class="text-sm muted">No mapping is not evidence of no impact. Evaluate whether these departments should participate.</p></div></div>';
}
function library(){
 const gaps=graphGaps(NODES,model.edges),filter=ui.search.toLowerCase();
 const visible=NODES.filter(n=>(n.name+" "+n.id+" "+n.type+" "+n.department).toLowerCase().includes(filter));
 const relationOptions=[...new Set(model.edges.map(x=>x.type))].sort().map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join("");
 return templateHeading("Known dependency model","Dependency library","Every relationship is explicitly mapped. Add a synthetic connection, then re-run assessments to see newly triggered review actions.",'<button data-route="gaps" class="btn">Review gaps →</button>')+
 '<div class="notice" style="margin-bottom:16px">The dependency library is intentionally incomplete and includes '+gaps.orphans.length+' disconnected assets. Adding a relationship does not prove it exists in a real organization.</div>'+
 '<div class="grid cols-2"><div class="card"><div class="card-head"><h2>Add a relationship</h2><span class="badge badge-blue">Demo edit</span></div><form id="relationForm">'+
 '<div class="field"><label for="from">Source asset</label><select id="from" name="from">'+NODES.map(n=>'<option value="'+esc(n.id)+'">'+esc(n.id+" · "+n.name)+'</option>').join("")+'</select></div>'+
 '<div class="field"><label for="to">Affected asset</label><select id="to" name="to">'+NODES.map(n=>'<option value="'+esc(n.id)+'">'+esc(n.id+" · "+n.name)+'</option>').join("")+'</select></div>'+
 '<div class="field-row"><div class="field"><label for="relationType">Relationship</label><select id="relationType" name="relationType">'+relationOptions+'</select></div><div class="field"><label for="required">Review type</label><select id="required" name="required"><option value="false">Suggested</option><option value="true">Mapped required</option></select></div></div>'+
 '<button class="btn btn-primary" type="submit">Add mapping & recompute →</button></form></div>'+
 '<div class="card"><div class="card-head"><h2>Library at a glance</h2></div><div class="grid cols-2">'+[
 ["Known assets",NODES.length],["Mapped relationships",model.edges.length],["Unassigned owners",gaps.unowned.length],["Orphan records",gaps.orphans.length]
 ].map(s=>'<div class="card card-tight" style="box-shadow:none;background:#fafcfc"><div class="stat-title">'+s[0]+'</div><div class="stat-value" style="font-size:25px;margin:0">'+s[1]+'</div></div>').join("")+'</div>'+
 '<p class="text-sm muted" style="margin-top:16px">Mappings are directional. An added relationship will only be followed from source → affected asset; it is not treated as a verified quality-system dependency.</p></div></div>'+
 '<div class="section card"><div class="card-head"><h2>Controlled assets and process links</h2><span class="card-sub">'+visible.length+' assets shown</span></div>'+
 '<div class="search-line"><input id="assetSearch" value="'+esc(ui.search)+'" placeholder="Filter by asset, ID, type or department" aria-label="Filter dependency assets"></div>'+
 '<div class="table-wrap"><table><thead><tr><th>Asset</th><th>Type</th><th>Department</th><th>Revision</th><th>Outgoing links</th></tr></thead><tbody>'+
 visible.map(n=>'<tr><td><div class="table-title">'+esc(n.name)+'</div><span class="table-sub mono">'+esc(n.id)+'</span></td><td>'+esc(n.type)+'</td><td>'+esc(n.department||"UNASSIGNED")+'</td><td>'+esc(n.revision)+'</td><td>'+model.edges.filter(x=>x.from===n.id).length+'</td></tr>').join("")+'</tbody></table></div></div>';
}
function gapsScreen(){
 const g=graphGaps(NODES,model.edges);const categories=[
 ["Assets without an assigned department",g.unowned],["Disconnected assets / no mapped dependency",g.orphans],
 ["Materials with no mapped supplier",g.materialsWithoutSupplier],
 ["Operations with no directly mapped test",g.operationsWithoutTest],
 ["Products without a mapped risk file",g.productsWithoutRisk]
 ];
 const deps=new Map(DEPARTMENTS.map(d=>[d,NODES.filter(n=>n.department===d).length]));const high=Math.max(...deps.values());
 return templateHeading("Coverage audit","Find what the map cannot see","A relationship engine cannot discover dependencies that have never been mapped. Treat missing coverage as a review prompt.")+
 '<div class="grid cols-4">'+[["Unowned assets",g.unowned.length],["Disconnected assets",g.orphans.length],["Missing supplier links",g.materialsWithoutSupplier.length],["Untested operations*",g.operationsWithoutTest.length]].map(s=>'<div class="card stat-card"><p class="stat-title">'+s[0]+'</p><p class="stat-value">'+s[1]+'</p><p class="stat-bottom">Known graph review</p></div>').join("")+'</div>'+
 '<section class="section grid cols-2"><div class="card"><h2>Known assets by department</h2>'+
 [...deps.entries()].map(([name,n])=>'<div class="coverage-row"><span>'+esc(name)+'</span><div class="bar"><span style="width:'+(100*n/high)+'%"></span></div><strong>'+n+'</strong></div>').join("")+
 '</div><div class="card"><h2>Dependency gaps requiring human review</h2><div class="gaps-list">'+categories.map(([label,nodes])=>'<div class="gap-item"><div class="mini-icon">!</div><div><strong>'+esc(label)+' · '+nodes.length+'</strong><p>'+nodes.map(n=>n.id).join(", ")+'</p></div></div>').join("")+'</div><p class="file-tips" style="margin-top:18px">* An operation may have tests indirectly connected; this check only inspects direct mapped relationships.</p></div></section>'+
 '<div class="notice" style="margin-top:18px"><strong>Important limitation:</strong> zero detected impacts or zero gaps does not prove complete coverage. A reviewer must check the model against controlled source documents, business requirements, and actual process interfaces.</div>';
}
function about(){
 return templateHeading("Approach & limitations","How ChangeRipple works","A traceable, deterministic prototype for helping reviewers explore known quality-system dependencies, not an autonomous compliance authority.")+
 '<div class="grid cols-2"><div class="card"><h2>Analysis model</h2><ol class="callout-list"><li>Reviewer selects a known source asset and describes a fictional change.</li><li>Engine explores directed, explicitly mapped relationships for up to three hops.</li><li>Each identified asset retains a path, department, hop count and link evidence.</li><li>Direct mappings configured as required create required human review actions; other links are suggestions.</li><li>Reviewers disposition impacts, record rationale and evidence, and check coverage gaps.</li></ol></div>'+
 '<div class="card"><h2>What it does not do</h2><ol class="callout-list"><li>No autonomous root-cause determination, regulatory compliance certification or risk-file approval.</li><li>No background data collection, document ingestion, production system connections or hidden AI calls.</li><li>No claim that an unmapped asset is unaffected. Three-hop propagation is incomplete by definition.</li><li>No electronic signatures, immutable audit trails, validated change control, or real organizational authorization.</li><li>Browser-local storage is not a controlled record repository.</li></ol></div></div>'+
 '<section class="section"><div class="card"><h2>Future integration concept</h2><p class="about-stat">Phase 2 could ingest authorized document registers, BOM mappings, SOP cross-references, test methods, controlled training matrices and change requests via consented connectors. A future regulated-use system would require role-based access, tenant isolation, validated source extraction, data provenance, audit trail, human approvals and rigorous performance validation.</p><div class="notice">Current source repository: ProofQA v0.2. The browser QA engine remains separate and unchanged; this application lives in apps/changeripple and does not claim that ProofQA automatically tests enterprise quality processes.</div></div></section>';
}
function report(){
 const a=active(),gate=closureGate(a);
 return '<div class="page-heading"><div><p class="eyebrow">Independent review record · demonstration only</p><h1>'+esc(a.id)+' — '+esc(a.title)+'</h1><p class="lead">'+esc(a.summary)+'</p></div><div class="heading-actions no-print"><button data-export="json" class="btn">↓ Export JSON</button><button class="btn btn-primary" data-print>Print / save as PDF</button><button class="btn" data-route="assessment">Back</button></div></div>'+
 '<div class="card"><h2>Assessment scope</h2><p class="about-stat">Type: '+esc(a.type)+'<br>Model: '+esc(a.modelVersion)+'<br>Source(s): '+a.roots.map(esc).join(", ")+'<br>Mapped edges evaluated: '+a.graphEdges+'<br>Recorded: '+esc(a.createdAt)+'<br>Workflow completion: '+(a.closed?"Marked closed (demo)":"In review")+'</p>'+
 '<h2>Impact coverage ('+a.impacts.length+')</h2>'+a.impacts.map(x=>'<div style="border-bottom:1px solid #edf0f4;padding:9px 0;font-size:12px"><strong>'+esc(x.nodeId+' — '+namedNode(x.nodeId))+'</strong> · '+esc(x.requirement)+' · '+esc(x.decision)+'<div class="muted">'+esc(x.path.join(" → "))+' · '+esc(x.reason||"No review rationale recorded")+'</div></div>').join("")+
 '<h2 style="margin-top:22px">Review actions ('+a.actions.length+')</h2>'+a.actions.map(x=>'<div style="padding:8px 0;font-size:12px;border-bottom:1px solid #edf0f4"><strong>'+esc(x.nodeId)+'</strong> · '+esc(x.department)+' · '+esc(x.requirement)+' · '+esc(x.status)+'<br><span class="muted">'+esc(x.note||"No evidence note")+'</span></div>').join("")+
 '<h2 style="margin-top:22px">Not verified / unresolved</h2>'+a.warnings.map(w=>'<p class="about-stat">'+esc(w.text)+' — '+(w.resolved?"Reviewed":"NOT_VERIFIED")+' · '+esc(w.resolution)+'</p>').join("")+
 (a.checklist.length?'<h2 style="margin-top:22px">NC/CAPA completeness</h2>'+a.checklist.map(c=>'<p class="about-stat">'+esc(c.label)+': '+esc(c.status)+' — '+esc(c.evidence||"no evidence")+'</p>').join(""):"")+
 '<div class="gate '+(gate.canClose?"pass":"")+'"><strong>Configured review gate:</strong> '+(gate.canClose?"Complete in demo":"Blocked · "+gate.blockers.length+" unresolved conditions")+'</div>'+
 '<p class="text-xs muted">DEMO · SYNTHETIC DATA. This report is not approval, regulatory compliance evidence, or proof of completeness. Unmapped ≠ unaffected. Data remains in this browser.</p></div>';
}
function render(){
 const main=document.getElementById("main");if(!main)return;
 const r=ui.route;
 let body= r==="overview"?overview():r==="assessments"?assessments():r==="new"?newAssessment():r==="assessment"?assessment():r==="library"?library():r==="gaps"?gapsScreen():r==="about"?about():r==="report"?report():overview();
 main.innerHTML=(ui.toast?'<div class="notice notice-teal" role="status" style="margin-bottom:16px">'+esc(ui.toast)+'</div>':"")+body;
 document.getElementById("crumb").textContent=routeNames[r]||"Overview";
 document.querySelectorAll("[data-route]").forEach(b=>b.classList.toggle("active",b.dataset.route===r));
}
function download(filename,text,type){
 const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function csvCell(x){let t=String(x??"");if(/^[\s]*[=+\-@]/.test(t))t="'"+t;return '"'+t.replace(/"/g,'""')+'"';}
function exportData(kind){
 const a=active();if(kind==="json"){download(a.id+".json",JSON.stringify({disclaimer:"Fictional demonstration; not a controlled quality record",assessment:a,relationships:model.edges,modelVersion:VERSION},null,2),"application/json");return;}
 const cols=["Asset","Department","Requirement","Status","Evidence note","Owner"];
 const rows=[cols,...a.actions.map(x=>[x.nodeId,x.department,x.requirement,x.status,x.note,x.owner])];
 download(a.id+"-actions.csv",rows.map(r=>r.map(csvCell).join(",")).join("\r\n"),"text/csv");
}
function stamp(a){a.updatedAt=new Date().toISOString();a.closed=false;save();}
function changeValue(el){
 const a=active();if(!a)return;
 if(el.dataset.decision){const i=a.impacts.find(x=>x.nodeId===el.dataset.decision);if(i){i.decision=el.value;stamp(a);render();}}
 else if(el.dataset.reason){const i=a.impacts.find(x=>x.nodeId===el.dataset.reason);if(i){i.reason=el.value;stamp(a);render();}}
 else if(el.dataset.action){const x=a.actions.find(x=>x.nodeId===el.dataset.action);if(x){x.status=el.value;stamp(a);render();}}
 else if(el.dataset.note){const x=a.actions.find(x=>x.nodeId===el.dataset.note);if(x){x.note=el.value;stamp(a);render();}}
 else if(el.dataset.warning){const x=a.warnings.find(x=>x.id===el.dataset.warning);if(x){x.resolved=el.value==="resolved";stamp(a);render();}}
 else if(el.dataset.warningNote){const x=a.warnings.find(x=>x.id===el.dataset.warningNote);if(x){x.resolution=el.value;stamp(a);render();}}
 else if(el.dataset.check){const x=a.checklist.find(x=>x.key===el.dataset.check);if(x){x.status=el.value;stamp(a);render();}}
 else if(el.dataset.checkNote){const x=a.checklist.find(x=>x.key===el.dataset.checkNote);if(x){x.evidence=el.value;stamp(a);render();}}
}
function createAssessment(form){
 const fd=new FormData(form),type=String(fd.get("type")||""),title=String(fd.get("title")||"").trim(),summary=String(fd.get("summary")||"").trim(),root=String(fd.get("root")||"");
 if(!SCENARIOS.some(x=>x.type===type)||title.length<6||summary.length<6||!byId.has(root)){ui.toast="Enter a valid category, title, description and mapped source asset.";render();return;}
 const seq=model.assessments.length+1, a=analyze({id:"CR-"+String(seq).padStart(3,"0"),title,summary,type,roots:[root]},model.edges,NODES,new Date().toISOString());
 model.assessments.unshift(a);model.active=a.id;save();ui.tab="impact";setRoute("assessment");
}
function addRelation(form){
 const fd=new FormData(form),from=String(fd.get("from")||""),to=String(fd.get("to")||""),type=String(fd.get("relationType")||""),required=fd.get("required")==="true";
 if(!byId.has(from)||!byId.has(to)||from===to){ui.toast="Choose two different existing assets.";render();return;}
 if(model.edges.some(e=>e.from===from&&e.to===to)){ui.toast="This source-to-target relationship already exists. Review the existing mapping first.";render();return;}
 const next={id:"CUSTOM-"+String(Date.now())+"-"+model.edges.length,from,to,type,required,source:"user-demo-mapping"};
 model.edges.push(next);model.assessments=model.assessments.map(a=>recompute(a,model.edges,NODES,new Date().toISOString()));save();
 ui.toast="Synthetic relationship added; every assessment was recomputed. New impacts are identified in each report.";render();
}
document.addEventListener("click",e=>{
 const b=e.target.closest("button");if(!b)return;
 if(b.dataset.route){setRoute(b.dataset.route);return;}
 if(b.dataset.open){setActive(b.dataset.open);ui.tab="impact";setRoute("assessment");return;}
 if(b.dataset.start){ui.preselect=b.dataset.start;setRoute("new");return;}
 if(b.dataset.tab){ui.tab=b.dataset.tab;render();return;}
 if(b.dataset.export){exportData(b.dataset.export);return;}
 if(b.hasAttribute("data-print")){window.print();return;}
 if(b.hasAttribute("data-close")){const a=active(),gate=closureGate(a);if(gate.canClose){a.closed=true;a.updatedAt=new Date().toISOString();save();ui.toast="Demo review marked closed. This is not regulatory approval.";render();}else{ui.toast="Closure blocked: "+gate.blockers.length+" conditions remain.";render();}return;}
 if(b.id==="resetDemo"){if(window.confirm("Discard all local ChangeRipple demo changes and restore fictional example data?")){model=initial();save();ui.search="";ui.tab="impact";setRoute("overview");}return;}
});
document.addEventListener("change",e=>{if(e.target.matches("[data-decision],[data-reason],[data-action],[data-note],[data-warning],[data-warning-note],[data-check],[data-check-note]"))changeValue(e.target);});
document.addEventListener("submit",e=>{if(e.target.id==="newAssessmentForm"){e.preventDefault();createAssessment(e.target);}if(e.target.id==="relationForm"){e.preventDefault();addRelation(e.target);}});
document.addEventListener("input",e=>{if(e.target.id==="assetSearch"){const next=e.target.value;const pos=e.target.selectionStart;ui.search=next;render();const input=document.getElementById("assetSearch");if(input){input.focus();input.setSelectionRange(pos,pos);}}});
window.addEventListener("hashchange",()=>{const candidate=location.hash.slice(1);if(routeNames[candidate]&&ui.route!==candidate){ui.route=candidate;render();}});
const initialHash=location.hash.slice(1);if(routeNames[initialHash])ui.route=initialHash;
render();
