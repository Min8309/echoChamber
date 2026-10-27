import test from 'node:test';
import assert from 'node:assert/strict';
import {previewResearchFile} from '../frontend/src/researchImport.mjs';
test('KOLD imports only bounded anonymous text and reference labels', async()=>{
 const records=Array.from({length:40},(_,i)=>({guid:`private-${i}`,comment:'문장 {내용} "인용" test@example.test',OFF:true,raw_labels:[{annotator_id:'secret'}]}));
 const result=await previewResearchFile(new Blob([JSON.stringify(records)]),'kold');
 assert.equal(result.rows.length,30);
 assert.equal(result.rows[0].reference_labels.OFF,'true');
 const value=JSON.stringify(result); assert.ok(!value.includes('secret')); assert.ok(!value.includes('private-')); assert.ok(!value.includes('test@example.test'));
});
test('K-HATERS JSONL preserves labels separately',async()=>{
 const result=await previewResearchFile(new Blob(['{"text":"첫 문장","label":1}\n{"text":"다음 문장","target_label":[0,1]}']),'khaters');
 assert.equal(result.rows.length,2); assert.equal(result.rows[1].reference_labels.target_label,'[0,1]');
});
