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
const scenarios = {
  nyc: { origin:'DALLAS',destination:'NYC',depart_date:'2027-03-11',return_date:'2027-03-15',travelers:1 },
  tokyo:{origin:'DALLAS',destination:'TOKYO',depart_date:'2027-04-23',return_date:'2027-04-30',travelers:2},
  vegas:{origin:'DALLAS',destination:'LAS VEGAS',depart_date:'2027-05-20',return_date:'2027-05-23',travelers:2}
};
const getRequest = () => ({
  chase_balance:Number(el('chaseBalance').value),amex_balance:Number(el('amexBalance').value),
  chase_value_cents:Number(el('chaseValue').value),amex_value_cents:Number(el('amexValue').value),
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
el('tripForm').addEventListener('submit',event=>{event.preventDefault();doSearch(true);});
function pointsPaymentHtml(offer){
  const p=offer.points_payment;
  if(!p)return '';
  const rows=p.cash_equivalents.map(o=>`<div><span>${safe(o.name)} value equivalent</span><b>${Number(o.points).toLocaleString()} pts</b></div>`).join('');
  const details=p.cash_equivalents.map(o=>`<p>${safe(o.name)}: assumed ${safe(o.value_cents)}? per point. Balance: ${Number(o.balance).toLocaleString()}. ${o.shortfall?`Short by ${Number(o.shortfall).toLocaleString()} points at this value.`:'Balance covers this value estimate.'}</p>`).join('');
  const award=p.award_points?`${Number(p.award_points).toLocaleString()} ${safe(p.award_program || 'loyalty points')} + ${p.award_fees_usd===null?'unknown fees':money(p.award_fees_usd)} (scenario; availability unverified)`:'Airline miles / hotel points: award quote unavailable.';
  const transfers=p.transfers.map(t=>`<p><b>${Number(t.points).toLocaleString()} ${safe(t.name)} points ? ${Number(t.partner_points).toLocaleString()} ${safe(p.award_program)} points</b><br>${safe(t.ratio_label)}. ${Number(t.leftover_partner_points).toLocaleString()} partner points left over. ${t.shortfall?`Short by ${Number(t.shortfall).toLocaleString()} bank points.`:'Entered balance covers the transfer.'}<br>${safe(t.note)} ${safeLink(t.source_url,'Transfer source')} ? Checked ${safe(t.checked_date)}</p>`).join('');
  return `<div class="points-prices">${rows}<small>Value estimates only ? not booking prices${completePrice(offer)?'':' ? excludes unknown fees'}</small><details><summary>Points & transfer details</summary>${details}<p>${award}</p>${transfers || '<p>No supported direct transfer calculation for this award program. Partner bookings require a separate award quote.</p>'}</details></div>`;
}
function offerHtml(offer,index,isHotel,mode){
  const selected=offer.id===(isHotel?lastResult.summary.hotel_offer_id:lastResult.summary.flight_offer_id);
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
  return `<article data-offer-id="${safe(offer.id)}" data-kind="${isHotel?'hotel':'flight'}" class="offer ${selected?'offer-best':''}"><div class="offer-top"><div><h4>${safe(title)}</h4><div class="sourceline">${safe(offer.source)}</div></div><div class="cost">${money(offer.total_cash_usd)}<small>${completePrice(offer)?'modeled total':'known estimate'} · ${isHotel?'full stay':'all travelers'}</small></div></div><div class="tags"><span class="tag fake">${mode==='demo'?'SYNTHETIC TEST PRICE':'UNVERIFIED LIVE SEARCH'}</span><span class="tag">${safe(details)}</span><span class="tag">${selected?'Selected for trip':'Click to choose'}</span></div><div class="sourceline">${safe(dates)}</div>${pointsPaymentHtml(offer)}<button type="button" class="choose-offer" data-choose="${safe(offer.id)}" aria-pressed="${selected}">${selected?'Selected':isHotel?'Choose hotel':'Choose flight'}</button><details class="card-details"><summary>View trip details, fees & points</summary><div class="sourceline">${meta}</div>${bags}${award}${evidenceHtml(offer)}<div class="offer-foot"><span>${safe(completeness)}</span><span>${safe(timeLabel)} · ${safe(offer.verification?.label || 'Not checkout verified')}</span></div></details></article>`;
}
function quoteComparisonForm(data){
  const selected=[...data.flights.filter(o=>o.id===data.summary.flight_offer_id).map(o=>({...o,kind:'flight'})),...data.hotels.filter(o=>o.id===data.summary.hotel_offer_id).map(o=>({...o,kind:'hotel'}))];
  if(!selected.length)return '';
  return `<details class="quote-tool"><summary>Compare a portal quote with a transfer award</summary><p>Enter prices you found for the same flight or room, dates and travelers. This calculator does not search award seats or access bank accounts.</p><form id="quoteForm"><div class="grid2"><label>Selected offer<select name="offer_id">${selected.map(o=>`<option value="${safe(o.id)}" data-kind="${safe(o.kind)}">${safe(o.name || o.carrier || o.id)} (${safe(o.id)})</option>`).join('')}</select></label><label>Transfer route<select name="route"><option value="chase_southwest">Chase to Southwest (1:1)</option><option value="amex_hilton">Amex to Hilton (1:2)</option></select></label><label>Portal price in bank points<input name="portal_points" type="number" min="1" max="100000000" step="1" required placeholder="e.g. 27500" /></label><label>Award price in partner points<input name="award_points" type="number" min="1" max="100000000" step="1" required placeholder="e.g. 20000" /></label><label>Portal cash fees (USD)<input name="portal_cash_usd" type="number" min="0" max="100000000" step="0.01" required placeholder="Enter 0 if confirmed none" /></label><label>Award cash taxes / fees (USD)<input name="award_cash_usd" type="number" min="0" max="100000000" step="0.01" required placeholder="Enter quoted fees" /></label><label>Transfer fees (USD)<input name="transfer_fee_usd" type="number" min="0" max="100000000" step="0.01" required placeholder="Enter 0 if confirmed none" /></label><label>Existing partner points<input name="partner_balance" type="number" min="0" max="100000000" step="1" value="0" required /></label><label>Your partner point value (?)<input name="partner_value_cents" type="number" min="0.1" max="10" step="0.01" value="1" required /></label></div><p>Bank balance and valuation come from the rewards settings used for this search. Change them there and search again to update.</p><label class="check"><input name="same_offer_confirmed" type="checkbox" /> I checked that both quotes cover the same trip, fare/room, travelers and required extras.</label><label class="check"><input name="eligible_confirmed" type="checkbox" /> My card can transfer to this partner and I checked award availability.</label><button type="submit" class="choose-offer">Compare quoted prices</button><div id="quoteResult" role="status" aria-live="polite"></div></form></details>`;
}
async function compareQuotedPrices(event){
  event.preventDefault();
  const form=event.currentTarget;
  const values=Object.fromEntries(new FormData(form));
  const q=lastResult.query;
  const bank=values.route==='chase_southwest'?'chase':'amex';
  const offer=[...lastResult.flights,...lastResult.hotels].find(o=>o.id===values.offer_id);
  const isHotel=lastResult.hotels.some(o=>o.id===values.offer_id);
  const result=el('quoteResult');
  if((bank==='chase' && isHotel) || (bank==='amex' && !isHotel)){
    result.textContent='Choose Chase to Southwest for a flight, or Amex to Hilton for a hotel.';return;
  }
  values.bank_balance=q[bank+'_balance'] || 0;
  values.point_value_cents=q[bank+'_value_cents'] || 1;
  values.same_offer_confirmed=form.elements.same_offer_confirmed.checked;
  values.eligible_confirmed=form.elements.eligible_confirmed.checked;
  const version=searchVersion;
  const button=form.querySelector('button[type="submit"]');button.disabled=true;
  result.textContent='Comparing quotes...';
  try{
    const response=await fetch('/api/rewards-quote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});
    if(response.status===404)throw new Error('Restart the Python server to enable quote comparisons.');
    const r=await response.json();
    if(version!==searchVersion)return;
    if(!response.ok)throw new Error(r.error || 'Comparison failed');
    const gap=r.bank_points_difference;
    const label=r.lower_economic_cost==='tie'?'Equal economic cost':r.lower_economic_cost==='transfer'?'Transfer has lower economic cost':'Portal has lower economic cost';
    result.innerHTML=`<p><b>${safe(offer.name || offer.carrier || offer.id)} ? User-entered quotes</b></p><div class="payment-comparison"><div><small>BOOK THROUGH ${safe(r.rule.name)} PORTAL</small><strong>${Number(r.portal.bank_points).toLocaleString()} pts</strong><p>+ ${money(r.portal.cash_usd)} cash<br>Economic cost: ${money(r.portal.economic_cost_usd)}<br>${r.portal.shortfall?`Short by ${Number(r.portal.shortfall).toLocaleString()} points`:'Bank balance sufficient'}</p></div><div><small>TRANSFER TO ${safe(r.rule.partner)}</small><strong>${Number(r.transfer.bank_points).toLocaleString()} ${safe(r.rule.name)} pts</strong><p>+ ${money(r.transfer.cash_usd)} cash<br>Economic cost: ${money(r.transfer.economic_cost_usd)}<br>${r.transfer.shortfall?`Short by ${Number(r.transfer.shortfall).toLocaleString()} bank points`:'Bank balance sufficient'}</p></div></div><p>${gap>=0?`Transfer uses ${Number(gap).toLocaleString()} fewer bank points.`:`Portal uses ${Number(-gap).toLocaleString()} fewer bank points.`} ${label}: difference ${money(Math.abs(r.economic_difference_usd))}.</p>${!r.both_affordable?'<p><b>Your entered bank balance cannot cover both choices. Check each shortfall above.</b></p>':''}${!r.comparison_confirmed_by_user?'<p><b>Scenario only: matching offers, eligibility or availability have not been confirmed.</b></p>':''}<details><summary>Transfer math & sources</summary><p>${Number(r.rule.bank_block).toLocaleString()} bank points to ${Number(r.rule.partner_block).toLocaleString()} partner points. Transfer ${Number(r.transfer.bank_points).toLocaleString()} bank points to receive ${Number(r.transfer.partner_points_received).toLocaleString()} partner points. Use ${Number(r.transfer.existing_partner_points_used).toLocaleString()} existing partner points. Left over from transfer: ${Number(r.transfer.leftover_partner_points).toLocaleString()} points.</p><p>${safeLink(r.rule.source,'Issuer transfer rules')} ${r.rule.ratio_source?safeLink(r.rule.ratio_source,'Ratio reference'):''} ? Checked ${safe(r.checked_date)}</p><p>${safe(r.note)}</p></details>`;
  }catch(error){if(version===searchVersion)result.textContent=error.message;}
  finally{button.disabled=false;}
}
function render(data){
  lastResult=data;
  const mode=data.query.mode;
  el('warnings').innerHTML=(data.warnings||[]).map((w,i)=>`<div class="warn">${i===0?'<strong>Important:</strong> ':''}${safe(w)}</div>`).join('');
  const summary=data.summary;
  const hasTrip=typeof summary.modeled_trip_cash_usd==='number';
  const hasKnown=typeof summary.known_trip_cash_usd==='number';
  const totalLabel=hasTrip?money(summary.modeled_trip_cash_usd):hasKnown?money(summary.known_trip_cash_usd):'Incomplete trip';
  const totalNote=hasTrip?(summary.selection_mode==='manual'?'Your selected flight + hotel • USD':'Lowest modeled cash flight + hotel • USD'):hasKnown?'Known flight + hotel estimate. Required fees are unknown.':'One or both parts of the trip are missing';
  el('summary').innerHTML=`<div class="trip-summary"><div><small>${mode==='demo'?'FICTIONAL TEST TOTAL':'UNVERIFIED LIVE ESTIMATE'}</small><strong>${totalLabel}</strong><p>${safe(totalNote)}</p><p>${safe(data.query.origin)} → ${safe(data.query.destination)} · ${safe(data.query.travelers)} traveler(s)</p></div><div class="summary-note"><small>ILLUSTRATIVE CARD REWARDS</small><strong>${Number(summary.modeled_points_earned_if_cash||0).toLocaleString()} pts</strong><p>Assumed ${safe(data.query.card_multiplier)} points / $1. Estimated value: ${money(Number(summary.modeled_points_earned_if_cash||0)*data.query.point_value_cents/100)}. This is not a cash discount.</p></div></div>`;
  el('flightCount').textContent=`${data.flights.length} result(s)`;
  el('hotelCount').textContent=`${data.hotels.length} result(s)`;
  el('flights').innerHTML=data.flights.length?data.flights.map((o,i)=>offerHtml(o,i,false,mode)).join(''):'<div class="empty">No matching flights. Demo fixtures cover the three scenario buttons; try a sample or connect live search.</div>';
  el('hotels').innerHTML=data.hotels.length?data.hotels.map((o,i)=>offerHtml(o,i,true,mode)).join(''):'<div class="empty">No matching hotels. Demo fixtures cover the three scenario buttons; try a sample or connect live search.</div>';
  const chosenFlight=data.flights.find(o=>o.id===summary.flight_offer_id);
  const chosenHotel=data.hotels.find(o=>o.id===summary.hotel_offer_id);
  const walletView=[chosenFlight,chosenHotel].filter(Boolean).map(o=>`<div><h4>${safe(o.name || o.carrier || o.id)}</h4>${pointsPaymentHtml(o)}</div>`).join('');
  const a=summary.comparison_illustrative_award || summary.best_illustrative_award;
  const savings=a?Number(a.economic_savings_usd):null;
  const verdict=a?(savings>0?`Points offer better modeled value by ${money(savings)}.`:savings<0?`Cash offers better modeled value by ${money(-savings)}.`:'Cash and points have equal modeled value.'):'No eligible points scenario to compare.';
  const unavailable=!hasTrip?'A complete trip price is needed before comparing points.':'No affordable points option with complete fee information was returned.';
  const comparison=`<div class="payment-comparison"><div><small>PAY CASH</small><strong>${hasTrip?money(summary.modeled_trip_cash_usd):hasKnown?money(summary.known_trip_cash_usd):'Not available'}</strong><p>${hasTrip?'Flight + hotel cash outlay':hasKnown?'Known estimate — required fees unknown':'Flight or hotel results missing'}</p></div><div><small>ONE AWARD + CASH · SCENARIO ONLY</small><strong>${a?money(a.trip_cash_outlay_usd):'Not available'}</strong><p>${a?`Plus ${Number(a.points).toLocaleString()} points<br>Value of points used: ${money(Number(a.points)*data.query.point_value_cents/100)}<br>Total economic cost: <b>${money(a.trip_economic_cost_usd)}</b><br>${safe(a.kind)} award: ${safe(a.offer_id)}`:safe(unavailable)}</p></div></div><p><strong>${safe(verdict)}</strong></p>${a?'<p>Economic cost = cash paid + your value of points used. Availability and program eligibility are unverified.</p>':''}`;
  el('recommendations').innerHTML=`<div class="reco-box"><h3>Your cash-versus-points comparison</h3>${comparison}${quoteComparisonForm(data)}<details class="wallet-comparison"><summary>Compare Chase, Amex & loyalty points for your selections</summary>${walletView}<p>Each balance is separate. Estimates on two cards do not confirm your wallet can pay for both.</p></details><details class="reasoning-details"><summary>How we compared these options</summary>${summary.recommendations.map(s=>`<p>${safe(s)}</p>`).join('') || '<p>No recommendation available. Try another search.</p>'}</details><p><strong>Before booking:</strong> Verify exact flights, room conditions, required fees, and award availability with the provider.</p></div>`;

  if(el('quoteForm'))el('quoteForm').addEventListener('submit',compareQuotedPrices);
}
async function chooseOffer(kind,id){
  if(!lastResult)return;
  const version=++searchVersion;
  const data=lastResult;
  const selected={flight:data.summary.flight_offer_id,hotel:data.summary.hotel_offer_id,[kind]:id};
  el('status').textContent='Updating your trip…';
  try{
    const response=await fetch('/api/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:data.query,flights:data.flights,hotels:data.hotels,selected})});
    if(response.status===404)throw new Error('Restart the Python server to enable flight and hotel selection, then refresh this page.');
    const payload=await response.json();
    if(version!==searchVersion)return;
    if(!response.ok)throw new Error(payload.error || 'Could not update selection');
    payload.warnings=data.warnings;
    render(payload);
    el('status').textContent='Trip updated. Total and points comparison reflect your selection.';
  }catch(error){if(version===searchVersion)el('status').textContent=error.message;}
  finally{if(version===searchVersion){el('searchButton').disabled=false;el('results').setAttribute('aria-busy','false');}}
}
for(const id of ['flights','hotels']){
  el(id).addEventListener('click',event=>{
    const card=event.target.closest('[data-offer-id]');
    if(!card || event.target.closest('details,a') || (event.target.closest('button') && !event.target.closest('[data-choose]')))return;
    chooseOffer(card.dataset.kind,card.dataset.offerId);
  });
}
async function doSearch(scrollToResults=false){
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
    if(scrollToResults)el('results').scrollIntoView({behavior:'smooth',block:'start'});
    el('status').textContent=`Search complete • ${payload.query.mode==='demo'?'fictional data':'preliminary live listing estimates'} • prices in USD`;
  }catch(error){
    if(version!==searchVersion)return;
    el('status').textContent='Error: '+error.message;
    el('warnings').innerHTML='<div class="warn">Check your inputs or live API configuration. See README.md.</div>';
    el('summary').innerHTML='';el('flights').innerHTML='';el('hotels').innerHTML='';el('recommendations').innerHTML='';
  }finally{if(version===searchVersion){button.disabled=false;el('results').setAttribute('aria-busy','false');}}
}
doSearch();
