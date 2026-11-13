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
context.data.summary.flight_offer_id='F1';
context.data.transfer_rules={amex_delta:{bank:'amex',name:'Amex',partner:'Delta SkyMiles',bank_block:1000,partner_block:1000,kind:'flight'}};
vm.runInContext('render(data)',context);
assert(get('recommendations').innerHTML.includes('Amex to Delta SkyMiles (1000:1000)'));
vm.runInContext(`quoteHistory=[{offer_id:'F1',rule:{name:'Amex',partner:'Delta SkyMiles'},portal:{bank_points:27500,cash_usd:0,economic_cost_usd:275},transfer:{bank_points:20000,cash_usd:17.6,economic_cost_usd:217.6,shortfall:0},lower_economic_cost:'transfer',comparison_confirmed_by_user:false}];renderQuoteHistory()`,context);
assert(get('quoteHistory').innerHTML.includes('Delta SkyMiles'));
assert(get('quoteHistory').innerHTML.includes('Unconfirmed scenario'));
assert(get('quoteHistory').innerHTML.includes('$217.60'));
vm.runInContext('render(data);renderQuoteHistory()',context);
assert.equal(get('quoteHistory').innerHTML,'');
context.data.query.mode='demo';
offer.demo_redemption={carrier:'Southwest',program:'Southwest Rapid Rewards',points:20000,cash_usd:11.2,calculation_date:'2026-11-13',note:'FICTIONAL DEMO ONLY',payments:[{bank:'chase',label:'Chase',supported:true,bank_points:16000,cash_usd:11.2,bonus_percent:25,shortfall:0,bank_block:1000,partner_block:1000,promotion_ends:'2026-11-30',bonus_saves_points:4000,received_partner_points:20000,leftover_partner_points:0,excise_fee_usd:0,economic_cost_usd:171.2},{bank:'amex',label:'Amex',supported:false,reason:'No supported direct transfer'}]};
vm.runInContext('render(data)',context);
assert(get('recommendations').innerHTML.includes('16,000 pts'));
assert(get('recommendations').innerHTML.includes('20,000 pts'));
assert(get('recommendations').innerHTML.includes('Demo +25% bonus'));
assert(get('recommendations').innerHTML.includes('No supported direct transfer'));
assert(!get('recommendations').innerHTML.includes('id="quoteForm"'));
console.log('Frontend rendering checks passed.');
