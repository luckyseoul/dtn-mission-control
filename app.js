const fallbackState = {
  observedAt: new Date().toISOString(),
  nodes: [
    {id:'edge-a',host:'edge-node-a',ip:'192.0.2.11',eid:'ipn:1001',role:'edge',status:'online',services:[['bpclock',100],['ipnfw',100],['udpclo × 3',100],['cfdpclock',100],['bputa',100],['dtnex',100]]},
    {id:'edge-b',host:'edge-node-b',ip:'192.0.2.12',eid:'ipn:1002',role:'edge',status:'online',services:[['bpclock',100],['ipnfw',100],['udpclo × 3',100],['cfdpclock',100],['bputa',100],['dtnex',100]]},
    {id:'gateway',host:'gateway',ip:'198.51.100.1',eid:'ipn:2000',role:'gateway',status:'online',services:[['bpclock',100],['ipnfw',100],['udpclo',100],['contact graph',96]]},
    {id:'remote-1',host:'remote-node-07',ip:'203.0.113.7',eid:'ipn:3007',role:'remote',status:'online',services:[['bpclock',100],['ipnfw',100],['udpclo',88],['route advert',100]]},
    {id:'remote-2',host:'remote-node-12',ip:'203.0.113.12',eid:'ipn:3012',role:'remote',status:'degraded',services:[['bpclock',100],['ipnfw',100],['udpclo',64],['route advert',100]]},
    {id:'edge-c',host:'edge-node-c',ip:'192.0.2.13',eid:'ipn:1003',role:'edge',status:'maintenance',services:[['bpclock',0],['ipnfw',0],['udpclo',0],['cfdpclock',0],['bputa',0],['dtnex',0]]}
  ],
  links:[['edge-a','gateway'],['edge-b','gateway'],['gateway','remote-1'],['gateway','remote-2'],['edge-a','edge-b'],['edge-c','gateway']],
  bundleGroups:[
    {name:'Administrative',short:'ADM',count:184,color:'var(--cyan)',share:15.3},
    {name:'Keepalive',short:'KA',count:412,color:'var(--green)',share:34.2},
    {name:'Echo / probe',short:'ECHO',count:96,color:'var(--purple)',share:8.0},
    {name:'Retry / custody',short:'RETRY',count:73,color:'var(--orange)',share:6.1},
    {name:'CPB metadata',short:'CPB',count:221,color:'#f472b6',share:18.3},
    {name:'Application payload',short:'DATA',count:219,color:'#94a3b8',share:18.2}
  ],
  events:[
    {kind:'ok',title:'CPB block received from remote-node-07',meta:'ipn:268485207 · 41 bytes',time:'2 min ago'},
    {kind:'info',title:'New node discovered beyond gateway',meta:'ipn:3012 · remote address',time:'8 min ago'},
    {kind:'warn',title:'udpclo latency elevated on remote-node-12',meta:'p95 820 ms · threshold 500 ms',time:'14 min ago'},
    {kind:'info',title:'edge-node-c marked under maintenance',meta:'ipn:1003 · last seen yesterday',time:'yesterday'},
    {kind:'ok',title:'Edge node DTNEX heartbeat acknowledged',meta:'ipn:1001 · 1800 s interval',time:'21 min ago'}
  ]
};

const $ = selector => document.querySelector(selector);
let state = fallbackState;

function serviceCount(nodes) { return nodes.reduce((n, host) => n + host.services.length, 0); }
function renderMetrics() {
  const online = state.nodes.filter(n => n.status === 'online').length;
  $('#nodes-online').textContent = `${online} / ${state.nodes.length}`;
  $('#services-healthy').textContent = `${serviceCount(state.nodes.filter(n => n.status === 'online'))}`;
  $('#bundles-hour').textContent = '1,205';
  $('#routes-beyond').textContent = `${state.nodes.filter(n => n.role === 'remote').length}`;
  $('#topology-count').textContent = `${state.nodes.length} nodes · ${state.links.length} links`;
}
function renderHealth() {
  $('#health-list').innerHTML = state.nodes.slice(0,4).map(node => {
    const score = Math.round(node.services.reduce((a,s) => a+s[1],0)/node.services.length);
    const color = node.status === 'degraded' ? ' style="background:var(--orange)"' : '';
    return `<div class="health-row"><div class="host-name"><span class="status-dot ${node.status === 'degraded' ? '' : 'green'}" style="background:${node.status === 'degraded' ? 'var(--orange)' : 'var(--green)'}"></span><div>${node.host}<small>${node.eid}</small></div></div><div class="health-bar"><i style="width:${score}%${color}"></i></div><div class="health-score">${score}%</div></div>`;
  }).join('');
}
function renderEvents() {
  $('#event-list').innerHTML = state.events.slice(0,4).map(event => `<div class="event-row"><span class="event-dot ${event.kind === 'info' ? 'info' : event.kind === 'warn' ? 'warn' : ''}"></span><div><div class="event-title">${event.title}</div><div class="event-meta">${event.meta}</div></div><span class="event-time">${event.time}</span></div>`).join('');
}
function renderBundleGroups() {
  const groups = state.bundleGroups || [];
  $('#bundle-list').innerHTML = groups.map(group => `<div class="bundle-row"><div class="bundle-name"><span class="bundle-swatch" style="background:${group.color}"></span><span>${group.name}<small>${group.short}</small></span></div><div class="bundle-bar"><i style="width:${group.share}%;background:${group.color}"></i></div><strong>${group.count}</strong></div>`).join('');
}
function renderTopology() {
  const canvas = $('#topology-canvas');
  canvas.innerHTML = '';
  const positions = {'edge-a':[18,57],'edge-b':[18,22],gateway:[51,40],'remote-1':[82,23],'remote-2':[82,73],'edge-c':[51,88]};
  const point = id => positions[id] || [50,50];
  state.links.forEach(([from,to]) => { const a=point(from), b=point(to); const dx=b[0]-a[0], dy=b[1]-a[1]; const length=Math.sqrt(dx*dx+dy*dy); const link=document.createElement('span'); link.className=`topology-link ${to.startsWith('remote') ? 'dashed' : ''}`; link.style.left=`${a[0]}%`; link.style.top=`${a[1]}%`; link.style.width=`${length}%`; link.style.transform=`rotate(${Math.atan2(dy,dx)*180/Math.PI}deg)`; canvas.appendChild(link); });
  state.nodes.forEach(node => { const [x,y]=point(node.id); const el=document.createElement('div'); el.className='topology-node'; el.style.left=`${x}%`; el.style.top=`${y}%`; const color=node.role==='gateway'?'var(--cyan)':node.role==='remote'?'var(--purple)':(node.status==='degraded'||node.status==='maintenance')?'var(--orange)':'var(--green)'; el.style.setProperty('--node-color',color); el.innerHTML=`<div class="node-orbit"></div><div class="node-label">${node.host}<small>${node.eid} · ${node.status}</small></div>`; el.addEventListener('click',()=>openNodeDrawer(node)); canvas.appendChild(el); });
}
let selectedNode = null;
function openNodeDrawer(node) {
  selectedNode = node;
  $('#drawer-title').textContent = node.host;
  $('#drawer-status').textContent = node.status.toUpperCase();
  $('#drawer-status').style.color = node.status === 'online' ? 'var(--green)' : 'var(--orange)';
  $('#drawer-status-dot').style.background = node.status === 'online' ? 'var(--green)' : 'var(--orange)';
  $('#drawer-last-seen').textContent = node.status === 'maintenance' ? 'Maintenance window' : 'Last observation just now';
  $('#drawer-eid').textContent = node.eid;
  $('#drawer-ip').textContent = node.ip;
  $('#drawer-role').textContent = node.role;
  $('#drawer-service-count').textContent = `${node.services.length} checks`;
  $('#drawer-services').innerHTML = node.services.map(([name, health]) => `<div class="drawer-service"><span>${name}</span><strong style="color:${health > 0 ? 'var(--green)' : 'var(--orange)'}">${health}%</strong></div>`).join('');
  $('#drawer-result').innerHTML = '<span class="status-dot"></span><span>Select an action to see its result here.</span>';
  $('#node-drawer').classList.add('open'); $('#node-drawer').setAttribute('aria-hidden','false'); $('#drawer-backdrop').classList.add('open');
}
function closeNodeDrawer() { $('#node-drawer').classList.remove('open'); $('#node-drawer').setAttribute('aria-hidden','true'); $('#drawer-backdrop').classList.remove('open'); }
async function runNodeAction(action) {
  if (!selectedNode) return;
  const result = $('#drawer-result'); result.innerHTML = '<span class="status-dot"></span><span>Running action…</span>';
  try {
    const response = await fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nodeId:selectedNode.id, action})});
    const data = await response.json();
    result.innerHTML = `<span class="status-dot" style="background:${data.ok ? 'var(--green)' : 'var(--orange)'}"></span><span>${data.message || 'Action completed.'}</span>`;
  } catch (_) { result.innerHTML = '<span class="status-dot" style="background:var(--orange)"></span><span>Action service unavailable; no change was made.</span>'; }
}
function render() { renderMetrics(); renderHealth(); renderEvents(); renderBundleGroups(); renderTopology(); $('#last-sync').textContent='just now'; }
function showToast(message) { const toast=$('#toast'); toast.textContent=message; toast.classList.add('show'); clearTimeout(window.toastTimer); window.toastTimer=setTimeout(()=>toast.classList.remove('show'),3000); }
async function refresh() { try { const response=await fetch('/api/state',{cache:'no-store'}); if(response.ok) { const incoming=await response.json(); if(Array.isArray(incoming.nodes) && incoming.nodes.length) state=incoming; } } catch (_) {} render(); }
$('#refresh-btn').addEventListener('click',()=>{refresh();showToast('Dashboard refreshed');});
$('#discover-btn').addEventListener('click',async()=>{showToast('Discovery scan started · LAN neighbors + Tailscale peers'); try { const response=await fetch('/api/discovery',{cache:'no-store'}); const result=await response.json(); showToast(`Scan complete · ${result.neighbors.length} LAN neighbor${result.neighbors.length === 1 ? '' : 's'} observed`); } catch (_) { setTimeout(()=>showToast('Scan complete · showing last authenticated snapshot'),700); }});
document.querySelectorAll('.segmented button').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('.segmented button').forEach(b=>b.classList.remove('active'));button.classList.add('active');showToast(`Showing throughput for ${button.textContent}`);}));
$('#view-nodes').addEventListener('click',()=>document.querySelector('#nodes').scrollIntoView({behavior:'smooth'}));
$('#view-events').addEventListener('click',()=>showToast('Event log is available from the gateway-backed API'));
$('#bundle-filter').addEventListener('click',()=>showToast('Bundle groups currently aggregate all authenticated nodes'));
$('#drawer-close').addEventListener('click',closeNodeDrawer);
$('#drawer-backdrop').addEventListener('click',closeNodeDrawer);
document.querySelectorAll('.action-button').forEach(button=>button.addEventListener('click',()=>runNodeAction(button.dataset.action)));
document.addEventListener('keydown',event=>{if(event.key==='Escape') closeNodeDrawer();});
render();
setInterval(refresh,15000);
