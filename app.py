import streamlit as st
from pathlib import Path
from datetime import datetime, timezone, timedelta
from supabase import create_client
import base64, html

st.set_page_config(page_title='Controle de Veículos | 10 Sul',page_icon='🚙',layout='centered',initial_sidebar_state='collapsed')
BASE=Path(__file__).parent; ASSETS=BASE/'assets'; TZ=timezone(timedelta(hours=-3))
@st.cache_resource
def get_db(): return create_client(st.secrets['SUPABASE_URL'],st.secrets['SUPABASE_KEY'])
DB=get_db()
def esc(x):return html.escape(str(x or ''))
def km(x):return f"{int(x or 0):,}".replace(',','.')+' km'
def now():return datetime.now(TZ).isoformat()
def image(name):return 'data:image/png;base64,'+base64.b64encode((ASSETS/name).read_bytes()).decode()
def clock(x):
 try:return datetime.fromisoformat(str(x).replace('Z','+00:00')).astimezone(TZ).strftime('%H:%M')
 except:return '—'
def elapsed(x):
 try:
  d=datetime.fromisoformat(str(x).replace('Z','+00:00')).astimezone(TZ);m=max(0,int((datetime.now(TZ)-d).total_seconds()/60));return f'{m//60}h {m%60:02d}min' if m>=60 else f'{m} min'
 except:return '—'
def rev(v):
 if v.get('km_ultima_revisao') is None:return None,0
 start=int(v['km_ultima_revisao']);target=start+10000;cur=int(v.get('km_atual') or 0);return target,max(0,min(100,round((cur-start)/100)))
def load():
 vs=DB.table('veiculos').select('*').order('placa').execute().data or []
 ms=DB.table('movimentacoes').select('*').eq('status','EM USO').order('data_hora_saida',desc=True).execute().data or []
 return vs,{m['placa']:m for m in ms}

st.markdown('''<style>
#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}.stApp{background:#f2f6fa;color:#173d60}.block-container{max-width:430px;padding:11px 10px 55px!important}[data-testid="stVerticalBlock"]{gap:.5rem}.top{height:52px;background:#fff;border-radius:14px;display:flex;align-items:center;padding:0 13px;box-shadow:0 3px 14px #173b5a12;margin-bottom:9px}.logo{width:31px;height:31px;border-radius:9px;background:#0868b6;color:#fff;display:grid;place-items:center;margin-right:9px}.brand{font-size:17px;font-weight:900;color:#073c6c}.brand small{display:block;font-size:8px;letter-spacing:.8px;color:#72869a;margin-top:3px}.switch{display:grid;grid-template-columns:1fr 1fr;gap:4px;background:#e5ecf3;padding:3px;border-radius:10px;margin:8px 0 10px}.switch a{text-decoration:none;text-align:center;border-radius:8px;padding:10px 3px;font-weight:800;font-size:10px;color:#526c83}.switch a.on{background:#0868b6;color:#fff;box-shadow:0 2px 7px #07538d30}.grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.card{background:#fff;border:1px solid #dce5ed;border-radius:13px;overflow:hidden;box-shadow:0 3px 12px #173b5a10}.pic{height:116px;position:relative;display:grid;place-items:center}.pic img{width:100%;height:100%;object-fit:contain}.badge{position:absolute;top:6px;right:6px;color:#fff;border-radius:12px;padding:4px 7px;font-size:7px;font-weight:900}.green{background:#14a765}.orange{background:#f27a21}.body{padding:8px}.plate{font-size:16px;font-weight:900;color:#083d6d}.model{font-size:9px;font-weight:800;margin-top:3px}.company{font-size:8px;color:#8a9baa;margin:2px 0 7px}.info{font-size:9px;line-height:1.55;color:#60778b}.info b{color:#153f63}.barrow{display:flex;justify-content:space-between;font-size:7px;color:#6e8294;margin-top:6px}.track{height:5px;background:#e5edf3;border-radius:6px;overflow:hidden;margin-top:2px}.fill{height:100%;background:#10b576}.use{background:#fff5ec;border-radius:7px;padding:6px;font-size:8px;line-height:1.5;color:#73553d}.action{display:block;text-decoration:none;text-align:center;border-radius:8px;background:#0868b6;color:#fff!important;font-size:8px;font-weight:900;padding:10px 2px;margin-top:7px}.action.ret{background:#fff0e4;color:#df6918!important}.title{font-size:18px;font-weight:900;color:#083d6d;margin:9px 1px}.back{text-decoration:none;color:#315c80;font-size:10px;font-weight:800}.hero,.box{background:#fff;border:1px solid #dce5ed;border-radius:14px;overflow:hidden;box-shadow:0 3px 12px #173b5a10}.heroimg{height:195px;display:grid;place-items:center}.heroimg img{width:100%;height:100%;object-fit:contain}.summary{background:#edf7ff;padding:10px;display:grid;grid-template-columns:1.2fr 1fr}.right{text-align:right;font-size:8px;color:#718699}.right b{font-size:11px;color:#173f62}.retcar{display:flex;gap:9px;align-items:center;background:#edf7ff;padding:8px}.retcar img{width:105px;height:70px;object-fit:contain}.stats{display:grid;grid-template-columns:1fr 1fr;gap:7px;padding:9px}.stat{background:#f1f6fa;border-radius:8px;padding:8px;text-align:center;font-size:8px;color:#718596}.stat b{display:block;font-size:13px;color:#153f63;margin-top:2px}.nav{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;background:#e5ecf3;padding:3px;border-radius:10px;margin-bottom:9px}.nav a{text-decoration:none;text-align:center;padding:9px 2px;font-size:9px;font-weight:800;color:#526c83;border-radius:8px}.nav a.on{background:#0868b6;color:#fff}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.metric{background:#fff;border:1px solid #dfe7ee;border-radius:11px;padding:9px;text-align:center;font-size:8px;color:#718596}.metric b{display:block;font-size:20px;color:#0a477b}.row{background:#fff;border:1px solid #dfe7ee;border-radius:12px;padding:8px;margin-top:7px;display:grid;grid-template-columns:90px 1fr;gap:8px;align-items:center}.row img{width:90px;height:65px;object-fit:contain}.stTextInput input,.stNumberInput input,.stDateInput input{border-radius:9px!important}.stButton button,.stFormSubmitButton button{width:100%;border-radius:9px!important;min-height:44px!important;font-weight:900!important;background:#0868b6!important;color:#fff!important;border:0!important}.stForm{border:0!important;padding:0!important}label{font-size:11px!important;font-weight:800!important}@media(min-width:700px){.block-container{max-width:860px}.pic{height:205px}.plate{font-size:20px}.info{font-size:11px}}
</style>''',unsafe_allow_html=True)

def top():st.markdown("<div class='top'><div class='logo'>🔧</div><div class='brand'>10 SUL<small>CONTROLE DE VEÍCULOS · SERVICE</small></div></div>",unsafe_allow_html=True)
def nav(active):st.markdown(f"<div class='nav'><a class='{'on' if active=='vehicles' else ''}' href='?view=vehicles'>🚙 VEÍCULOS</a><a class='{'on' if active=='panel' else ''}' href='?view=panel'>📊 PAINEL</a><a class='{'on' if active=='admin' else ''}' href='?view=admin'>⚙️ ADMIN</a></div>",unsafe_allow_html=True)

try:vs,opened=load()
except Exception as e:st.error('Falha ao conectar ao banco.');st.stop()
q=st.query_params;view=q.get('view','vehicles');plate=q.get('plate','');flt=q.get('filter','free')
top()
if view=='vehicles':
 nav('vehicles');free=sum(v['placa'] not in opened for v in vs);busy=len(opened)
 st.markdown(f"<div class='switch'><a class='{'on' if flt=='free' else ''}' href='?view=vehicles&filter=free'>DISPONÍVEIS {free}</a><a class='{'on' if flt=='used' else ''}' href='?view=vehicles&filter=used'>EM USO {busy}</a></div>",unsafe_allow_html=True)
 items=[v for v in vs if (v['placa'] in opened)==(flt=='used')];cards=[]
 for v in items:
  m=opened.get(v['placa']);target,pct=rev(v);busyv=bool(m)
  details=f"<div class='use'>👤 <b>{esc(m['pessoas'])}</b><br>📍 {esc(m['destino'])}<br>◷ {clock(m['data_hora_saida'])} · {elapsed(m['data_hora_saida'])}<br>🚗 {km(m['km_inicial'])}</div>" if m else f"<div class='info'>🚗 KM atual<br><b>{km(v.get('km_atual'))}</b><br>🔧 Próxima revisão<br><b>{km(target) if target else 'Não cadastrada'}</b></div>"
 prog=f"<div class='barrow'><span>Revisão</span><span>{pct}%</span></div><div class='track'><div class='fill' style='width:{pct}%'></div></div>" if target else ''
 cards.append(f"<div><div class='card'><div class='pic'><img src='{image(v['foto'])}'><span class='badge {'orange' if busyv else 'green'}'>{'EM USO' if busyv else 'DISPONÍVEL'}</span></div><div class='body'><div class='plate'>{esc(v['placa'])}</div><div class='model'>{esc(v['modelo'])}</div><div class='company'>{esc(v['empresa'])}</div>{details}{prog}</div></div><a class='action {'ret' if busyv else ''}' href='?view={'return' if busyv else 'out'}&plate={v['placa']}'> {'↩ REGISTRAR RETORNO' if busyv else '➜ USAR ESTE VEÍCULO'}</a></div>")
 st.markdown("<div class='grid'>"+''.join(cards)+"</div>",unsafe_allow_html=True)
elif view=='out':
 v=next((x for x in vs if x['placa']==plate),None)
 if not v or plate in opened:st.query_params.clear();st.rerun()
 st.markdown("<a class='back' href='?view=vehicles'>‹ VOLTAR</a><div class='title'>Registrar Saída</div>",unsafe_allow_html=True);target,pct=rev(v)
 st.markdown(f"<div class='hero'><div class='heroimg'><img src='{image(v['foto'])}'></div><div class='summary'><div><div class='plate'>{plate}</div><div class='model'>{esc(v['modelo'])}</div><div class='company'>{esc(v['empresa'])}</div></div><div class='right'>KM ATUAL<br><b>{km(v.get('km_atual'))}</b><br><br>PRÓXIMA REVISÃO<br><b>{km(target) if target else '—'}</b></div></div></div>"+(f"<div class='barrow'><span>Revisão preventiva</span><span>{pct}%</span></div><div class='track'><div class='fill' style='width:{pct}%'></div></div>" if target else ''),unsafe_allow_html=True)
 with st.form('saida'):
  dest=st.text_input('📍 Para onde está indo?',placeholder='Ex.: Suzano - Portaria 2');people=st.text_input('👥 Quem está indo?',placeholder='Informe o(s) nome(s)');ki=st.number_input('🚗 KM inicial',min_value=int(v.get('km_atual') or 0),value=int(v.get('km_atual') or 0),step=1);st.text_input('▣ Data / hora',value=datetime.now(TZ).strftime('%d/%m/%Y  %H:%M'),disabled=True);save=st.form_submit_button('➤ REGISTRAR SAÍDA')
 if save:
  if not dest.strip() or not people.strip():st.error('Informe destino e quem está indo.')
  else:
   DB.table('movimentacoes').insert({'placa':plate,'destino':dest.strip(),'pessoas':people.strip(),'km_inicial':int(ki),'data_hora_saida':now(),'status':'EM USO'}).execute();DB.table('veiculos').update({'km_atual':int(ki),'atualizado_em':now()}).eq('placa',plate).execute();st.query_params.from_dict({'view':'vehicles','filter':'used'});st.rerun()
elif view=='return':
 v=next((x for x in vs if x['placa']==plate),None);m=opened.get(plate)
 if not v or not m:st.query_params.clear();st.rerun()
 st.markdown("<a class='back' href='?view=vehicles&filter=used'>‹ VOLTAR</a><div class='title'>Registrar Retorno</div>",unsafe_allow_html=True)
 st.markdown(f"<div class='box'><div class='retcar'><img src='{image(v['foto'])}'><div><div class='plate'>{plate}</div><div class='model'>{esc(v['modelo'])}</div><div class='company'>{esc(v['empresa'])}</div></div></div><div class='stats'><div class='stat'>KM INICIAL<b>{km(m['km_inicial'])}</b></div><div class='stat'>SAÍDA<b>{clock(m['data_hora_saida'])}</b></div></div><div class='info' style='padding:0 10px 10px'>👤 <b>{esc(m['pessoas'])}</b><br>📍 {esc(m['destino'])}<br>⌛ {elapsed(m['data_hora_saida'])} em uso</div></div>",unsafe_allow_html=True)
 with st.form('retorno'):
  kf=st.number_input('🚗 KM final',min_value=int(m['km_inicial']),value=int(m['km_inicial']),step=1);c1,c2=st.columns(2);c1.metric('KM rodado',km(int(kf)-int(m['km_inicial'])));c2.metric('Tempo',elapsed(m['data_hora_saida']));save=st.form_submit_button('✓ CONFIRMAR RETORNO')
 if save:
  DB.table('movimentacoes').update({'km_final':int(kf),'data_hora_retorno':now(),'status':'DEVOLVIDO'}).eq('id',m['id']).execute();DB.table('veiculos').update({'km_atual':int(kf),'atualizado_em':now()}).eq('placa',plate).execute();st.query_params.from_dict({'view':'vehicles','filter':'free'});st.rerun()
elif view=='panel':
 nav('panel');busy=len(opened);st.markdown(f"<div class='title'>Painel em tempo real</div><div class='metrics'><div class='metric'>FROTA<b>{len(vs)}</b></div><div class='metric'>DISPONÍVEIS<b>{len(vs)-busy}</b></div><div class='metric'>EM USO<b>{busy}</b></div></div>",unsafe_allow_html=True)
 for v in vs:
  m=opened.get(v['placa']);target,pct=rev(v);txt=f"🟠 <b>EM USO</b> · {esc(m['pessoas'])}<br>📍 {esc(m['destino'])} · {elapsed(m['data_hora_saida'])}" if m else '🟢 <b>DISPONÍVEL</b>'
  st.markdown(f"<div class='row'><img src='{image(v['foto'])}'><div><div class='plate'>{v['placa']}</div><div class='model'>{esc(v['modelo'])}</div><div class='info'>{txt}<br>KM: <b>{km(v.get('km_atual'))}</b>{'<br>Revisão: <b>'+km(target)+'</b>' if target else ''}</div></div></div>",unsafe_allow_html=True)
 st.markdown("<meta http-equiv='refresh' content='15'>",unsafe_allow_html=True)
else:
 nav('admin');st.markdown("<div class='title'>Revisão preventiva</div>",unsafe_allow_html=True);p=st.selectbox('Veículo',[v['placa'] for v in vs]);v=next(x for x in vs if x['placa']==p)
 with st.form('admin'):
  d=st.date_input('Data da última revisão');kr=st.number_input('KM da última revisão',min_value=0,value=int(v.get('km_ultima_revisao') or v.get('km_atual') or 0),step=1);st.info(f'Próxima revisão: {km(int(kr)+10000)}');save=st.form_submit_button('SALVAR REVISÃO')
 if save:DB.table('veiculos').update({'data_ultima_revisao':d.isoformat(),'km_ultima_revisao':int(kr),'intervalo_revisao':10000,'atualizado_em':now()}).eq('placa',p).execute();st.success('Revisão atualizada.');st.rerun()
