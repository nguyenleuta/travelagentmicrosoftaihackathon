/* FareForge student app. NEVER present fictional demo data as live travel offers. */
const el = id => document.getElementById(id);
const money = v => typeof v === 'number' && Number.isFinite(v)
  ? new Intl.NumberFormat('en-US', {style:'currency',currency:'USD'}).format(v) : 'Not available';
const safe = value => String(value ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const completePrice = offer => offer.price_complete === true || (offer.price_complete !== false && offer.fees_incomplete === false);
const bagLabel = (offer, included, fee) => offer[included] === true ? 'Included' :
  offer[included] === false && typeof offer[fee] === 'number' ? `${money(offer[fee])} per traveler` : 'Unknown';
let searchVersion = 0;
let lastResult = null;
function safeLink(value, label){
  try{
    const url=new URL(value);
    if(!['https:','http:'].includes(url.protocol) || url.username || url.password)return '';
    return `<a href="${safe(url.href)}" target="_blank" rel="noopener noreferrer">${safe(label)}</a>`;
  }catch{return '';}
}
function evidenceHtml(offer){
  const breakdown=offer.price_breakdown;
  const v=offer.verification;
  if(!breakdown || !v)return '';
  const rows=breakdown.components.map(row=>`<div><dt>${safe(row.label)}</dt><dd>${row.status==='not_selected'?'Not selected':row.status==='included'?'Included':row.amount_usd===null?'Unknown':money(row.amount_usd)}</dd></div>`).join('');
  const links=[safeLink(v.source_url,'View source'),safeLink(v.booking_url,'View provider offer')].filter(Boolean).join(' · ');
  return `<details class="evidence"><summary>Price breakdown & source</summary><p>${safe(breakdown.basis)} · USD · ${safe(breakdown.traveler_count)} traveler(s)</p><dl>${rows}<div class="breakdown-total"><dt>${offer.price_complete?'Modeled total':'Known amount'}</dt><dd>${money(breakdown.known_total_usd)}</dd></div></dl>${offer.unknown_fee_categories.length?`<p class="fee-warning">Unknown: ${safe(offer.unknown_fee_categories.join(', '))}</p>`:''}<p><b>${safe(v.label)}</b><br>Source: ${safe(v.provider)}<br>Observed: ${safe(v.observed_utc || (v.status==='synthetic_demo'?'No live observation':'Unknown'))}</p><p>${links || 'No source or booking link supplied.'}</p><p><b>Before booking</b></p><ul>${v.checks_needed.map(item=>`<li>${safe(item)}</li>`).join('')}</ul></details>`;
}
function exportComparison(){
  if(!lastResult)return;
  const offerRecord=o=>({id:o.id,total_cash_usd:o.total_cash_usd,price_complete:o.price_complete,price_breakdown:o.price_breakdown,verification:o.verification,unknown_fee_categories:o.unknown_fee_categories});
  const report={exported_utc:new Date().toISOString(),notice:'Search snapshot only. Export time is not provider observation time or checkout verification.',query:lastResult.query,summary:lastResult.summary,warnings:lastResult.warnings,flights:lastResult.flights.map(offerRecord),hotels:lastResult.hotels.map(offerRecord)};
  const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='fareforge-comparison.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
const scenarios = {
  nyc: { origin:'DALLAS',destination:'NYC',depart_date:'2027-03-11',return_date:'2027-03-15',travelers:1 },
  tokyo:{origin:'DALLAS',destination:'TOKYO',depart_date:'2027-04-23',return_date:'2027-04-30',travelers:2},
  vegas:{origin:'DALLAS',destination:'LAS VEGAS',depart_date:'2027-05-20',return_date:'2027-05-23',travelers:2}
};
const getRequest = () => ({
  origin:el('origin').value.trim(),destination:el('destination').value.trim(),
  depart_date:el('departDate').value,return_date:el('returnDate').value,
  travelers:Number(el('travelers').value),mode:el('mode').value,
  checked_bag:el('checkedBag').checked,carry_on:el('carryOn').checked,
  card_name:el('cardName').value,card_multiplier:Number(el('cardMultiplier').value),
  point_value_cents:Number(el('pointValue').value),award_points_balance:Number(el('pointsBalance').value)
});
for(const button of document.querySelectorAll('[data-case]')){
  button.addEventListener('click',()=>{
    const s=scenarios[button.dataset.case];
    el('origin').value=s.origin;el('destination').value=s.destination;
    el('departDate').value=s.depart_date;el('returnDate').value=s.return_date;
    el('travelers').value=s.travelers;el('mode').value='demo';
    doSearch();
  });
}
el('tripForm').addEventListener('submit',event=>{event.preventDefault();doSearch();});
function offerHtml(offer,index,isHotel,mode){
  const title=isHotel?offer.name:`${offer.origin} → ${offer.destination} · ${offer.carrier}`;
  const details=isHotel?`${offer.room_type || 'Room type unknown'}`:
    `${offer.stops === 0?'Nonstop':`${offer.stops} stop(s)`} · ${offer.duration_minutes?Math.round(offer.duration_minutes/60*10)/10+' h':'Duration unknown'}`;
  const meta=isHotel?`Room: ${safe(offer.refundable===true?'Refundable listed':offer.refundable===false?'Nonrefundable listed':'Refundability unknown')}`:
    `${safe(offer.fare_label||'Fare not specified')}`;
  const award=offer.points_required > 0?`<div class="award">${offer.award_affordable?'Points scenario — availability unverified':'Not enough entered points'}: <strong>${offer.points_required.toLocaleString()} points + ${offer.award_price_complete === false?'unknown cash fees':money(offer.award_fees_usd)}</strong><br>Economic cost at your valuation: ${offer.award_price_complete === false?'Unknown':money(offer.award_economic_cost_usd)}</div>`:'';
  const timeLabel=offer.observed_utc?`Observed: ${safe(offer.observed_utc)}`:mode==='demo'?"Synthetic fixture • no live observation":"Observation time unknown";
  const completeness=!completePrice(offer)?`Unknown: ${(offer.unknown_fee_categories || ['required fees']).join(', ')}. Known amount only.`:
    `Modeled fees included. Estimated cash rewards: ${Number(offer.reward_points_earned||0).toLocaleString()} points`;
  const dates=isHotel?`${offer.checkin || ''} → ${offer.checkout || ''}`:`${offer.depart_date || ''} → ${offer.return_date || ''}`;
  const bags=isHotel?'':`<p class="offer-detail">Carry-on: ${safe(bagLabel(offer,'carry_on_included','carry_on_per_traveler_usd'))} · Checked bag: ${safe(bagLabel(offer,'checked_bag_included','checked_bag_per_traveler_usd'))}</p>`;
  return `<article class="offer ${index===0?'offer-best':''}"><div class="offer-top"><div><h4>${safe(title)}</h4><div class="sourceline">${safe(offer.source)}</div></div><div class="cost">${money(offer.total_cash_usd)}<small>${completePrice(offer)?'modeled total':'known estimate'} · ${isHotel?'full stay':'all travelers'}</small></div></div><div class="tags"><span class="tag fake">${mode==='demo'?'SYNTHETIC TEST PRICE':'UNVERIFIED LIVE SEARCH'}</span><span class="tag">${safe(details)}</span><span class="tag">${safe(offer.id)}</span></div><div class="sourceline">${safe(dates)}<br>${meta}</div>${bags}${award}${evidenceHtml(offer)}<div class="offer-foot"><span>${safe(completeness)}</span><span>${safe(timeLabel)} · ${safe(offer.verification?.label || 'Not checkout verified')}</span></div></article>`;
}
function render(data){
  lastResult=data;
  const mode=data.query.mode;
  el('warnings').innerHTML=(data.warnings||[]).map((w,i)=>`<div class="warn">${i===0?'<strong>Important:</strong> ':''}${safe(w)}</div>`).join('');
  const summary=data.summary;
  const hasTrip=typeof summary.modeled_trip_cash_usd==='number';
  const hasKnown=typeof summary.known_trip_cash_usd==='number';
  const totalLabel=hasTrip?money(summary.modeled_trip_cash_usd):hasKnown?money(summary.known_trip_cash_usd):'Incomplete trip';
  const totalNote=hasTrip?'Lowest modeled cash flight + hotel • USD':hasKnown?'Known flight + hotel estimate. Required fees are unknown.':'One or both parts of the trip are missing';
  el('summary').innerHTML=`<div class="trip-summary"><div><small>${mode==='demo'?'FICTIONAL TEST TOTAL':'UNVERIFIED LIVE ESTIMATE'}</small><strong>${totalLabel}</strong><p>${safe(totalNote)}</p><p>${safe(data.query.origin)} → ${safe(data.query.destination)} · ${safe(data.query.travelers)} traveler(s)</p></div><div class="summary-note"><small>ILLUSTRATIVE CARD REWARDS</small><strong>${Number(summary.modeled_points_earned_if_cash||0).toLocaleString()} pts</strong><p>Assumed ${safe(data.query.card_multiplier)} points / $1. Estimated value: ${money(Number(summary.modeled_points_earned_if_cash||0)*data.query.point_value_cents/100)}. This is not a cash discount.</p></div></div>`;
  el('flightCount').textContent=`${data.flights.length} result(s)`;
  el('hotelCount').textContent=`${data.hotels.length} result(s)`;
  el('flights').innerHTML=data.flights.length?data.flights.map((o,i)=>offerHtml(o,i,false,mode)).join(''):'<div class="empty">No matching flights. Demo fixtures cover the three scenario buttons; try a sample or connect live search.</div>';
  el('hotels').innerHTML=data.hotels.length?data.hotels.map((o,i)=>offerHtml(o,i,true,mode)).join(''):'<div class="empty">No matching hotels. Demo fixtures cover the three scenario buttons; try a sample or connect live search.</div>';
  const a=summary.comparison_illustrative_award || summary.best_illustrative_award;
  const savings=a?Number(a.economic_savings_usd):null;
  const verdict=a?(savings>0?`Points offer better modeled value by ${money(savings)}.`:savings<0?`Cash offers better modeled value by ${money(-savings)}.`:'Cash and points have equal modeled value.'):'No eligible points scenario to compare.';
  const unavailable=!hasTrip?'A complete trip price is needed before comparing points.':'No affordable points option with complete fee information was returned.';
  const comparison=`<div class="payment-comparison"><div><small>PAY CASH</small><strong>${hasTrip?money(summary.modeled_trip_cash_usd):hasKnown?money(summary.known_trip_cash_usd):'Not available'}</strong><p>${hasTrip?'Flight + hotel cash outlay':hasKnown?'Known estimate — required fees unknown':'Flight or hotel results missing'}</p></div><div><small>ONE AWARD + CASH · SCENARIO ONLY</small><strong>${a?money(a.trip_cash_outlay_usd):'Not available'}</strong><p>${a?`Plus ${Number(a.points).toLocaleString()} points<br>Value of points used: ${money(Number(a.points)*data.query.point_value_cents/100)}<br>Total economic cost: <b>${money(a.trip_economic_cost_usd)}</b><br>${safe(a.kind)} award: ${safe(a.offer_id)}`:safe(unavailable)}</p></div></div><p><strong>${safe(verdict)}</strong></p>${a?'<p>Economic cost = cash paid + your value of points used. Availability and program eligibility are unverified.</p>':''}`;
  el('recommendations').innerHTML=`<div class="reco-box"><h3>Your cash-versus-points comparison</h3>${comparison}${summary.recommendations.map(s=>`<p>${safe(s)}</p>`).join('') || '<p>No recommendation available. Try another search.</p>'}<p><strong>Before booking:</strong> Verify exact flights, room conditions, required fees, and award availability with the provider.</p><button type="button" id="exportComparison" class="export-button">Download comparison evidence</button><p>Includes search inputs, price breakdowns, sources, and missing fees.</p></div>`;
  el('exportComparison').addEventListener('click',exportComparison);
}
async function doSearch(){
  const version=++searchVersion;
  lastResult=null;
  const button=el('searchButton');button.disabled=true;
  el('results').setAttribute('aria-busy','true');
  for(const id of ['summary','flights','hotels','recommendations','warnings','flightCount','hotelCount'])el(id).innerHTML='';
  el('status').textContent='Searching and comparing. Live API calls may take longer…';
  try{
    const response=await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(getRequest())});
    const payload=await response.json();
    if(version!==searchVersion)return;
    if(!response.ok)throw new Error(payload.error||'Search failed');
    render(payload);
    el('status').textContent=`Search complete • ${payload.query.mode==='demo'?'fictional data':'preliminary live listing estimates'} • prices in USD`;
  }catch(error){
    if(version!==searchVersion)return;
    el('status').textContent='Error: '+error.message;
    el('warnings').innerHTML='<div class="warn">Check your inputs or live API configuration. See README.md.</div>';
    el('summary').innerHTML='';el('flights').innerHTML='';el('hotels').innerHTML='';el('recommendations').innerHTML='';
  }finally{if(version===searchVersion){button.disabled=false;el('results').setAttribute('aria-busy','false');}}
}
doSearch();
