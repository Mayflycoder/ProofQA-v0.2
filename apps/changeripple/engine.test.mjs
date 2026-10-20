import test from "node:test";
import assert from "node:assert/strict";
import {NODES,RELATIONS,VERSION,SCENARIOS,traverse,analyze,recompute,seedAssessments,graphGaps,closureGate} from "./engine.mjs";

test("synthetic quality graph meets useful minimum coverage",()=>{
 assert.ok(NODES.length>=30);
 assert.ok(RELATIONS.length>=40);
 assert.equal(SCENARIOS.length,3);
 assert.ok(NODES.every(n=>n.id&&n.type&&n.name));
 assert.ok(RELATIONS.every(e=>NODES.some(n=>n.id===e.from)&&NODES.some(n=>n.id===e.to)));
});
test("supplier change propagates to material and downstream controls",()=>{
 const impacts=traverse(["SUP-101"]);
 const ids=impacts.map(x=>x.nodeId);
 assert.ok(ids.includes("MAT-201"));
 assert.ok(ids.includes("SPEC-301"));
 assert.ok(ids.includes("PROC-503"));
 assert.ok(ids.includes("TEST-601")||ids.includes("RISK-802"));
 assert.ok(impacts.every(x=>x.hop<=3));
 assert.equal(impacts.filter(x=>x.nodeId==="MAT-201").length,1);
});
test("internal procedure change triggers cross-functional records, training and testing",()=>{
 const impacts=traverse(["SOP-401"]);
 const ids=impacts.map(x=>x.nodeId);
 assert.ok(ids.includes("PROC-502"));
 assert.ok(ids.includes("TRAIN-903"));
 assert.ok(ids.includes("REC-1001"));
 assert.ok(ids.includes("TEST-601"));
});
test("deterministic propagation irrespective of input link ordering",()=>{
 const roots=["SUP-101","SOP-401"];
 const a=traverse(roots,RELATIONS);
 const b=traverse([...roots].reverse(),[...RELATIONS].reverse());
 assert.deepEqual(a,b);
});
test("unknown or invalid mapping cannot be used to fabricate impacts",()=>{
 const results=traverse(["NO-SUCH-NODE"],[{id:"bad",from:"NO-SUCH-NODE",to:"SOP-401",type:"affects",required:true}]);
 assert.deepEqual(results,[]);
});
test("strong source mapping requires explicit review, distant paths are suggestions",()=>{
 const a=analyze(SCENARIOS[0]);
 assert.equal(a.modelVersion,VERSION);
 assert.equal(a.impacts.find(x=>x.nodeId==="MAT-201").requirement,"Mapped review required");
 assert.equal(a.impacts.find(x=>x.nodeId==="PROC-503").requirement,"Suggested review");
 assert.ok(a.impacts.every(x=>x.path.length===x.hop+1));
});
test("recompute preserves prior human dispositions and flags new connections",()=>{
 const a=analyze(SCENARIOS[1]);
 a.impacts[0].decision="Excluded";a.impacts[0].reason="Verified not applicable in synthetic review.";
 a.actions[0].status="Done";a.actions[0].note="Reviewed fictional record";
 const next=[...RELATIONS,{id:"DEMO-NEW",from:"SOP-401",to:"EQ-1202",type:"references",required:false,source:"test"}];
 const b=recompute(a,next);
 assert.ok(b.addedImpacts.includes("EQ-1202"));
 assert.equal(b.impacts.find(x=>x.nodeId===a.impacts[0].nodeId).decision,"Excluded");
 assert.equal(b.actions.find(x=>x.nodeId===a.actions[0].nodeId).status,"Done");
});
test("gap detector reports omitted owners, disconnected records and source links",()=>{
 const g=graphGaps();
 assert.ok(g.unowned.some(x=>x.id==="EQ-1202"));
 assert.ok(g.orphans.some(x=>x.id==="SOP-411"));
 assert.ok(g.materialsWithoutSupplier.some(x=>x.id==="MAT-203"));
 assert.ok(g.productsWithoutRisk.some(x=>x.id==="PROD-1102"));
});
test("review gate rejects unfinished required actions and pending impacts",()=>{
 const a=seedAssessments()[0],g=closureGate(a);
 assert.equal(g.canClose,false);
 assert.ok(g.blockers.some(x=>x.includes("required review unresolved")));
 assert.ok(g.blockers.some(x=>x.includes("impact has not been dispositioned")));
});
test("review gate rejects missing N/A and Done evidence and unsupported exclusion",()=>{
 const a=seedAssessments()[0];
 a.impacts[0].decision="Excluded";
 a.actions[0].status="Not applicable";
 a.actions[1].status="Done";
 const result=closureGate(a).blockers.join("\n");
 assert.match(result,/exclusion needs a reason/);
 assert.match(result,/N\/A needs justification/);
 assert.match(result,/Done needs reviewer evidence note/);
});
test("NC CAPA verification requires evidence, not a status alone",()=>{
 const a=seedAssessments()[2];
 assert.equal(a.checklist.length,9);
 a.checklist[0].status="Verified";
 assert.ok(closureGate(a).blockers.some(x=>x.includes("CAPA Containment")));
});
test("review gate permits a fictional closed state only when all configured requirements resolved",()=>{
 const a=seedAssessments()[0];
 a.impacts.forEach(x=>{x.decision="Included";});
 a.actions.forEach(x=>{x.status="Done";x.note="Fictional evidence reviewed";});
 a.warnings.forEach(x=>{x.resolved=true;x.resolution="Reviewer checked fictional library gaps";});
 assert.deepEqual(closureGate(a),{canClose:true,blockers:[]});
});
