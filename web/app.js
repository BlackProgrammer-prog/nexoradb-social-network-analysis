const API='/api/v1';
const state={users:[],relationships:[],file:null};
const titles={dashboard:'داشبورد',import:'ورود فایل',users:'مدیریت کاربران',relationships:'مدیریت ارتباط‌ها',graph:'گراف زنده',algorithms:'الگوریتم‌های تحلیل شبکه'};
const algorithms={
  GetFriends:{label:'دوستان کاربر',fields:[['user','کاربر','user'],['limit','حداکثر نتیجه','number',10]]},
  AreConnected:{label:'آیا متصل‌اند؟',fields:[['user1','کاربر اول','user'],['user2','کاربر دوم','user']]},
  ShortestPath:{label:'کوتاه‌ترین مسیر',fields:[['from','مبدأ','user'],['to','مقصد','user']]},
  MutualFriends:{label:'دوستان مشترک',fields:[['user1','کاربر اول','user'],['user2','کاربر دوم','user']]},
  FriendSuggestion:{label:'پیشنهاد دوست',fields:[['user','کاربر','user'],['limit','حداکثر نتیجه','number',10]]},
  MostConnected:{label:'پرارتباط‌ترین کاربران',fields:[['metric','معیار','choice',['total','in','out']],['limit','تعداد','number',10]]},
  NetworkStats:{label:'آمار کامل شبکه',fields:[]},
  ConnectedComponents:{label:'مولفه‌های همبند',fields:[]},
  AllDistances:{label:'فاصله‌ها از یک کاربر',fields:[['source','کاربر مبدأ','user'],['max_hops','حداکثر فاصله','number',100]]},
  BetweennessCentrality:{label:'مرکزیت بینابینی',fields:[['top','تعداد کاربران برتر','number',10]]},
  CommunityDetection:{label:'تشخیص اجتماع',fields:[['max_iterations','حداکثر تکرار','number',30],['min_community_size','حداقل اندازه','number',2]]},
  InfluenceMaximization:{label:'بیشینه‌سازی نفوذ',fields:[['k','تعداد seed','number',3],['simulations','تعداد شبیه‌سازی','number',25],['probability','احتمال انتشار','decimal',.2]]}
};

const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
function loading(on){$('#loading').classList.toggle('hidden',!on)}
function toast(message,error=false){const t=$('#toast');t.textContent=message;t.className='toast show'+(error?' error':'');clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.className='toast',3500)}
async function api(path,options={}){loading(true);try{const r=await fetch(API+path,options);let data;try{data=await r.json()}catch{data={detail:await r.text()}}if(!r.ok){let d=data.detail||'خطای نامشخص';if(typeof d==='object')d=[d.message,...(d.errors||[])].filter(Boolean).join('\n');throw new Error(d)}return data}finally{loading(false)}}
async function safe(fn){try{return await fn()}catch(e){console.error(e);toast(e.message||String(e),true);return null}}
function escapeHtml(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function options(users,selected=''){return users.map(u=>`<option value="${escapeHtml(u._id)}" ${u._id===selected?'selected':''}>${escapeHtml(u._id)} — ${escapeHtml(u.username||u._id)}</option>`).join('')}

async function showPage(name){
  $$('.page').forEach(x=>x.classList.toggle('active',x.id===`page-${name}`));
  $$('#nav button').forEach(x=>x.classList.toggle('active',x.dataset.page===name));
  $('#page-title').textContent=titles[name];
  if(name==='dashboard')await loadDashboard();
  if(name==='users')await loadUsers();
  if(name==='relationships')await loadRelationshipsPage();
  if(name==='graph')await loadGraph();
  if(name==='algorithms')await prepareAlgorithms();
}

async function checkHealth(){const data=await safe(()=>api('/health'));const el=$('#connection');if(data?.database_connected){el.textContent='● دیتابیس متصل است';el.className='connection ok'}else{el.textContent='● دیتابیس در دسترس نیست';el.className='connection bad'}}
async function loadDashboard(){const d=await safe(()=>api('/dashboard'));if(!d)return;$('#m-status').textContent=d.database_connected?'متصل':'قطع';$('#m-users').textContent=d.users;$('#m-pairs').textContent=d.mutual_relationships;$('#m-edges').textContent=d.directed_edges}
async function loadUsers(){const d=await safe(()=>api('/users?limit=10000'));if(!d)return;state.users=d.items;renderUsers();const opts=options(state.users);$('#manage-user').innerHTML=opts;$('#relation-a').innerHTML=opts;$('#relation-b').innerHTML=opts;if(state.users.length>1)$('#relation-b').selectedIndex=1}
function renderUsers(){const q=$('#user-search').value.trim().toLowerCase();const rows=state.users.filter(u=>!q||String(u._id).toLowerCase().includes(q)||String(u.username||'').toLowerCase().includes(q));$('#users-body').innerHTML=rows.length?rows.map(u=>`<tr><td>${escapeHtml(u._id)}</td><td>${escapeHtml(u.username||u._id)}</td></tr>`).join(''):'<tr><td colspan="2" class="muted">کاربری وجود ندارد.</td></tr>'}
async function loadRelationshipsPage(){await loadUsers();const d=await safe(()=>api('/relationships'));if(!d)return;state.relationships=d.items;$('#relationships-body').innerHTML=d.items.length?d.items.map(r=>`<tr><td>${escapeHtml(r.user_a)}</td><td>${escapeHtml(r.user_b)}</td><td><button class="button danger delete-relation" data-a="${escapeHtml(r.user_a)}" data-b="${escapeHtml(r.user_b)}">حذف</button></td></tr>`).join(''):'<tr><td colspan="3" class="muted">ارتباطی وجود ندارد.</td></tr>'}

async function loadGraph(){const d=await safe(()=>api('/graph'));if(!d)return;$('#graph-summary').textContent=`${d.nodes.length} کاربر و ${d.edges.length} ارتباط دوطرفه`;const svg=$('#graph-svg');svg.innerHTML='';$('#graph-empty').classList.toggle('hidden',d.nodes.length>0);svg.classList.toggle('hidden',d.nodes.length===0);if(!d.nodes.length)return;const cx=500,cy=315,r=Math.min(250,100+d.nodes.length*2.2);const pos={};d.nodes.forEach((n,i)=>{const a=2*Math.PI*i/d.nodes.length-Math.PI/2;pos[n.id]={x:cx+r*Math.cos(a),y:cy+r*Math.sin(a)}});const ns='http://www.w3.org/2000/svg';d.edges.forEach(e=>{if(!pos[e.source]||!pos[e.target])return;const l=document.createElementNS(ns,'line');l.setAttribute('x1',pos[e.source].x);l.setAttribute('y1',pos[e.source].y);l.setAttribute('x2',pos[e.target].x);l.setAttribute('y2',pos[e.target].y);l.setAttribute('class','graph-edge');svg.append(l)});d.nodes.forEach(n=>{const g=document.createElementNS(ns,'g');const c=document.createElementNS(ns,'circle');const size=8+Math.min((n.degree||0)*1.1,14);c.setAttribute('cx',pos[n.id].x);c.setAttribute('cy',pos[n.id].y);c.setAttribute('r',size);c.setAttribute('class','graph-node');const title=document.createElementNS(ns,'title');title.textContent=`${n.id} | degree=${n.degree}`;c.append(title);const t=document.createElementNS(ns,'text');t.setAttribute('x',pos[n.id].x);t.setAttribute('y',pos[n.id].y+size+15);t.setAttribute('class','graph-label');t.textContent=n.label;g.append(c,t);svg.append(g)})}

async function prepareAlgorithms(){await loadUsers();const sel=$('#algorithm-select');if(!sel.options.length)sel.innerHTML=Object.entries(algorithms).map(([v,a])=>`<option value="${v}">${a.label}</option>`).join('');renderAlgorithmFields()}
function renderAlgorithmFields(){const a=algorithms[$('#algorithm-select').value];$('#algorithm-fields').innerHTML=a.fields.map(([name,label,type,value])=>{let input;if(type==='user')input=`<select name="${name}" required>${options(state.users)}</select>`;else if(type==='choice')input=`<select name="${name}">${value.map(x=>`<option>${x}</option>`).join('')}</select>`;else input=`<input name="${name}" type="number" value="${value}" ${type==='decimal'?'min="0" max="1" step="0.05"':'min="1" step="1"'} required>`;return `<label>${label}${input}</label>`}).join('')}

$('#nav').addEventListener('click',e=>{const b=e.target.closest('button[data-page]');if(b)showPage(b.dataset.page)});$$('.goto').forEach(b=>b.onclick=()=>showPage(b.dataset.target));$('#refresh').onclick=()=>showPage($('#nav button.active').dataset.page);$('#reload-graph').onclick=loadGraph;
$('#file-input').onchange=e=>{state.file=e.target.files[0]||null;$('#file-name').textContent=state.file?`${state.file.name} — ${(state.file.size/1024).toFixed(1)} KB`:'حداکثر ۱۰ مگابایت، UTF-8';$('#import-button').disabled=!state.file;if(state.file){const reader=new FileReader();reader.onload=()=>$('#file-preview').value=String(reader.result).split(/\r?\n/).slice(0,20).join('\n');reader.readAsText(state.file)}};
$('#import-button').onclick=()=>safe(async()=>{const form=new FormData();form.append('file',state.file);const d=await api('/imports/relationships',{method:'POST',body:form});$('#import-result').classList.remove('hidden');$('#import-result').textContent=JSON.stringify(d,null,2);toast('فایل با موفقیت وارد شد.');await checkHealth()});
$('#create-user-form').onsubmit=e=>{e.preventDefault();safe(async()=>{const id=$('#new-user-id').value.trim(),username=$('#new-username').value.trim()||null;await api('/users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,username})});e.target.reset();toast('کاربر ایجاد شد.');await loadUsers()})};
$('#edit-user-button').onclick=()=>safe(async()=>{const id=$('#manage-user').value,username=$('#edit-username').value.trim();if(!id||!username)throw new Error('کاربر و نام جدید را وارد کنید.');await api(`/users/${encodeURIComponent(id)}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});toast('کاربر ویرایش شد.');await loadUsers()});
$('#delete-user-button').onclick=()=>safe(async()=>{const id=$('#manage-user').value;if(!id)return;if(!confirm(`کاربر ${id} و همه ارتباط‌های او حذف شود؟`))return;await api(`/users/${encodeURIComponent(id)}`,{method:'DELETE'});toast('کاربر حذف شد.');await loadUsers()});
$('#user-search').oninput=renderUsers;
$('#create-relationship-form').onsubmit=e=>{e.preventDefault();safe(async()=>{const user_a=$('#relation-a').value,user_b=$('#relation-b').value;if(user_a===user_b)throw new Error('دو کاربر باید متفاوت باشند.');await api('/relationships',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_a,user_b})});toast('ارتباط دوطرفه ایجاد شد.');await loadRelationshipsPage()})};
$('#relationships-body').onclick=e=>{const b=e.target.closest('.delete-relation');if(!b)return;safe(async()=>{if(!confirm(`ارتباط ${b.dataset.a} و ${b.dataset.b} حذف شود؟`))return;await api(`/relationships/${encodeURIComponent(b.dataset.a)}/${encodeURIComponent(b.dataset.b)}`,{method:'DELETE'});toast('ارتباط حذف شد.');await loadRelationshipsPage()})};
$('#algorithm-select').onchange=renderAlgorithmFields;$('#algorithm-form').onsubmit=e=>{e.preventDefault();safe(async()=>{const name=$('#algorithm-select').value,fd=new FormData(e.target),parameters={};for(const [k,v] of fd.entries())parameters[k]=e.target.elements[k].type==='number'?Number(v):v;const d=await api(`/algorithms/${name}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({parameters})});$('#algorithm-placeholder').classList.add('hidden');$('#algorithm-result').classList.remove('hidden');$('#algorithm-result').textContent=JSON.stringify(d.result,null,2);$('#algorithm-time').textContent=`${d.execution_time_ms} ms`;toast('تحلیل انجام شد.')})};

(async()=>{await checkHealth();await showPage('dashboard')})();

