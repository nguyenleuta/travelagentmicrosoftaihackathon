// Optional rendering checks: node starter_app/tests/frontend.test.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, {value:'', innerHTML:'', addEventListener(){}, setAttribute(){}});
  return nodes.get(id);
};
let downloaded, savedBlob;
class TestURL extends URL {
  static createObjectURL(blob) { savedBlob = blob; return 'blob:test'; }
  static revokeObjectURL() {}
}
const context = vm.createContext({
  document: {getElementById:get, querySelectorAll:()=>[], createElement:()=>({click(){downloaded=this.download;}})},
  Intl, URL:TestURL, Blob, setTimeout:fn=>fn(), fetch:()=>new Promise(()=>{}),
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8'), context);
const offer = {
  id:'F1', origin:'DFW', destination:'JFK', carrier:'<script>bad()</script>', total_cash_usd:200,
  price_complete:false, unknown_fee_categories:['Bags'], points_required:0,
  price_breakdown:{basis:'all travelers',traveler_count:1,known_total_usd:200,
    components:[{label:'Fare',amount_usd:200,status:'known'},{label:'Bags',amount_usd:null,status:'unknown'}]},
  verification:{status:'live_search_unverified',label:'Live listing — checkout not verified',provider:'<img src=x>',
    source_url:'javascript:alert(1)',booking_url:'https://example.com/offer',observed_utc:null,checks_needed:['Check dates']},
};
context.data = {query:{mode:'live',origin:'DFW',destination:'JFK',travelers:1,card_multiplier:3,point_value_cents:2},
  flights:[offer], hotels:[], warnings:[], summary:{modeled_trip_cash_usd:null,known_trip_cash_usd:null,recommendations:[]}};
vm.runInContext('render(data)', context);
const html = get('flights').innerHTML;
assert(html.includes('Price breakdown & source'));
assert(html.includes('<dd>Unknown</dd>'));
assert(html.includes('Observed: Unknown'));
assert(!html.includes('href="javascript:'));
assert(!html.includes('<script>'));
assert(!html.includes('<img src=x>'));
assert(html.includes('https://example.com/offer'));
assert(get('recommendations').innerHTML.includes('ONE AWARD + CASH'));
context.data.summary = {modeled_trip_cash_usd:1000,recommendations:[],comparison_illustrative_award:{
  economic_savings_usd:-100,trip_cash_outlay_usd:500,trip_economic_cost_usd:1100,points:30000,kind:'hotel',offer_id:'H1'}};
vm.runInContext('render(data)',context);
assert(get('recommendations').innerHTML.includes('Cash offers better modeled value by $100.00'));
assert(!get('recommendations').innerHTML.includes('Download comparison evidence'));
assert(get('flights').innerHTML.includes('Choose flight'));
offer.points_payment={cash_equivalents:[{name:'Chase',points:20000,balance:10000,shortfall:10000,value_cents:1},{name:'Amex',points:10000,balance:20000,shortfall:0,value_cents:2}],award_points:null,transfers:[]};
vm.runInContext('render(data)',context);
assert(get('flights').innerHTML.includes('Chase value equivalent'));
assert(get('flights').innerHTML.includes('20,000 pts'));
assert(get('flights').innerHTML.includes('Short by 10,000 points'));
assert(get('flights').innerHTML.includes('award quote unavailable'));
assert(get('flights').innerHTML.includes('not booking prices'));
console.log('Frontend rendering checks passed.');
