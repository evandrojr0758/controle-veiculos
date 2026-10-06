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
def esc(x): return html.escape(str(x or ''))
def km(x): return f"{int(x or 0):,}".replace(',','.')+' km'
def now(): return datetime.now(TZ).isoformat()
def image(name):
 try:return 'data:image/png;base64,'+base64.b64encode((ASSETS/name).read_bytes()).decode()
 except:return ''
def dt(x):
 try:return datetime.fromisoformat(str(x).replace('Z','+00:00')).astimezone(TZ)
 except:return None
def clock(x):
 d=dt(x);return d.strftime('%H:%M') if d else '—'
def dateclock(x):
 d=dt(x);return d.strftime('%d/%m/%Y %H:%M') if d else '—'
def elapsed(x):
 d=dt(x)
 if not d:return '—'
 m=max(0,int((datetime.now(TZ)-d).total_seconds()/60));return f'{m//60}h {m%60:02d}min' if m>=60 else f'{m} min'
def revision(v):
 if v.get('km_ultima_revisao') is None:return None,None,0
 start=int(v.get('km_ultima_revisao') or 0);cur=int(v.get('km_atual') or 0);target=start+10000;left=target-cur;pct=max(0,min(100,round(((cur-start)/10000)*100)))
 return target,left,pct
def load():
 vs=DB.table('veiculos').select('*').order('placa').execute().data or []
 ms=DB.table('movimentacoes').select('*').eq('status','EM USO').order('data_hora_saida',desc=True).execute().data or []
 return vs,{m['placa']:m for m in ms}

st.markdown('''<style>
#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
.stApp{background:#f2f6fa;color:#173d60}.block-container{max-width:430px;padding:10px 9px 55px!important}[data-testid="stVerticalBlock"]{gap:.45rem}
.top{height:54px;background:#fff;border-radius:15px;display:flex;align-items:center;padding:0 13px;box-shadow:0 3px 14px #173b5a12;margin-bottom:9px}.logo{width:33px;height:33px;border-radius:9px;background:#0868b6;color:#fff;display:grid;place-items:center;margin-right:9px}.brand{font-size:18px;font-weight:950;color:#073c6c}.brand small{display:block;font-size:8px;letter-spacing:.7px;color:#72869a;margin-top:2px}.mode{font-size:9px;color:#768a9c;margin-top:-6px;margin-bottom:8px;text-align:center}
.switch{display:grid;grid-template-columns:1fr 1fr;gap:4px;background:#e5ecf3;padding:3px;border-radius:11px;margin:6px 0 10px}.switch a{text-decoration:none;text-align:center;border-radius:8px;padding:10px 3px;font-weight:900;font-size:10px;color:#526c83}.switch a.on{background:#0868b6;color:#fff;box-shadow:0 2px 7px #07538d30}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.unit{min-width:0}.card{background:#fff;border:1px solid #dce5ed;border-radius:13px;overflow:hidden;box-shadow:0 3px 12px #173b5a10}.pic{height:120px;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden}.pic img{display:block;width:100%;height:100%;object-fit:contain}.badge{position:absolute;top:6px;right:6px;color:#fff;border-radius:12px;padding:4px 7px;font-size:7px;font-weight:950}.green{background:#14a765}.orange{background:#f27a21}.body{padding:8px}.plate{font-size:16px;font-weight:950;color:#083d6d;line-height:1.05}.model{font-size:9px;font-weight:850;margin-top:4px}.company{font-size:8px;color:#8a9baa;margin:2px 0 7px}.info{font-size:9px;line-height:1.55;color:#60778b}.info b{color:#153f63}.use{background:#fff5ec;border-radius:7px;padding:6px;font-size:8px;line-height:1.5;color:#73553d}.action{display:block;text-decoration:none;text-align:center;border-radius:8px;background:#0868b6;color:#fff!important;font-size:8px;font-weight:950;padding:10px 2px;margin-top:7px}.action.ret{background:#fff0e4;color:#df6918!important}.barrow{display:flex;justify-content:space-between;font-size:7px;color:#6e8294;margin-top:6px}.track{height:5px;background:#e5edf3;border-radius:6px;overflow:hidden;margin-top:2px}.fill{height:100%;background:#10b576}.title{font-size:19px;font-weight:950;color:#083d6d;margin:9px 1px}.back{text-decoration:none;color:#315c80;font-size:10px;font-weight:850}
.hero,.box{background:#fff;border:1px solid #dce5ed;border-radius:14px;overflow:hidden;box-shadow:0 3px 12px #173b5a10}.heroimg{height:190px;display:grid;place-items:center}.heroimg img{width:100%;height:100%;object-fit:contain}.summary{background:#edf7ff;padding:10px;display:grid;grid-template-columns:1.2fr 1fr}.right{text-align:right;font-size:8px;color:#718699}.right b{font-size:11px;color:#173f62}.retcar{display:flex;gap:9px;align-items:center;background:#edf7ff;padding:8px}.retcar img{width:105px;height:70px;object-fit:contain}.stats{display:grid;grid-template-columns:1fr 1fr;gap:7px;padding:9px}.stat{background:#f1f6fa;border-radius:8px;padding:8px;text-align:center;font-size:8px;color:#718596}.stat b{display:block;font-size:13px;color:#153f63;margin-top:2px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:9px}.metric{background:#fff;border:1px solid #dfe7ee;border-radius:11px;padding:9px;text-align:center;font-size:8px;color:#718596}.metric b{display:block;font-size:20px;color:#0a477b}.panelcard{background:#fff;border:1px solid #dfe7ee;border-radius:13px;padding:8px;margin:7px 0;box-shadow:0 2px 9px #173b5a0d}.panelmain{display:grid;grid-template-columns:95px 1fr;gap:9px;align-items:center}.panelmain img{width:95px;height:72px;object-fit:contain}.pstatus{font-size:8px;font-weight:950;margin-bottom:4px}.pstatus.free{color:#0a9b60}.pstatus.busy{color:#e56a17}.revbox{margin-top:7px;background:#f4f7fa;border-radius:8px;padding:7px;font-size:8px;color:#62798c}.danger{color:#c43e3e!important;font-weight:900}.warn{color:#d77b00!important;font-weight:900}.ok{color:#0b8f5a!important;font-weight:900}.adminnav{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:4px 0 10px}.adminnav a{text-decoration:none;text-align:center;background:#e5ecf3;color:#48667f;border-radius:9px;padding:9px;font-size:9px;font-weight:900}.adminnav a.on{background:#0868b6;color:#fff}.history{background:#fff;border:1px solid #dfe7ee;border-radius:10px;padding:8px;margin:6px 0;font-size:9px;line-height:1.55}
.stTextInput input,.stNumberInput input,.stDateInput input,.stSelectbox>div>div{border-radius:9px!important}.stButton button,.stFormSubmitButton button{width:100%;border-radius:9px!important;min-height:44px!important;font-weight:900!important;background:#0868b6!important;color:#fff!important;border:0!important}.stForm{border:0!important;padding:0!important}label{font-size:11px!important;font-weight:800!important}
@media(min-width:700px){.block-container{max-width:900px}.pic{height:205px}.plate{font-size:20px}.info{font-size:11px}.panelmain{grid-template-columns:150px 1fr}.panelmain img{width:150px;height:100px}}
</style>''',unsafe_allow_html=True)

def top(sub):
 st.markdown(f"<div class='top'><div class='logo'>🔧</div><div class='brand'>10 SUL<small>CONTROLE DE VEÍCULOS · SERVICE</small></div></div><div class='mode'>{sub}</div>",unsafe_allow_html=True)

def setview(view,**kwargs):
 d={'view':view};d.update(kwargs);st.query_params.from_dict(d);st.rerun()

try:vs,opened=load()
except Exception as e:st.error('Falha ao conectar ao banco online.');st.stop()
q=st.query_params;view=q.get('view','vehicles');plate=q.get('plate','');flt=q.get('filter','free');tab=q.get('tab','revisao')

# TELA 1 — USUÁRIO: SOMENTE SAÍDA E RETORNO
if view in ('vehicles','out','return'):
 top('USO DO VEÍCULO · SAÍDA E RETORNO')
 if view=='vehicles':
  free=sum(v['placa'] not in opened for v in vs);busy=len(opened)
  st.markdown(f"<div class='switch'><a class='{'on' if flt=='free' else ''}' href='?view=vehicles&filter=free'>DISPONÍVEIS {free}</a><a class='{'on' if flt=='used' else ''}' href='?view=vehicles&filter=used'>EM USO {busy}</a></div>",unsafe_allow_html=True)
  items=[v for v in vs if (v['placa'] in opened)==(flt=='used')];cards=[]
  for v in items:
   m=opened.get(v['placa']);busyv=bool(m)
   details=(f"<div class='use'>👤 <b>{esc(m.get('pessoas'))}</b><br>📍 {esc(m.get('destino'))}<br>◷ {clock(m.get('data_hora_saida'))} · {elapsed(m.get('data_hora_saida'))}</div>" if m else f"<div class='info'>🚗 KM atual<br><b>{km(v.get('km_atual'))}</b></div>")
   cards.append(f"<div class='unit'><div class='card'><div class='pic'><img src='{image(v.get('foto'))}'><span class='badge {'orange' if busyv else 'green'}'>{'EM USO' if busyv else 'DISPONÍVEL'}</span></div><div class='body'><div class='plate'>{esc(v.get('placa'))}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='company'>{esc(v.get('empresa'))}</div>{details}</div></div><a class='action {'ret' if busyv else ''}' href='?view={'return' if busyv else 'out'}&plate={esc(v.get('placa'))}'>{'↩ REGISTRAR RETORNO' if busyv else '➜ USAR ESTE VEÍCULO'}</a></div>")
  st.markdown("<div class='grid'>"+''.join(cards)+"</div>",unsafe_allow_html=True)
 elif view=='out':
  v=next((x for x in vs if x['placa']==plate),None)
  if not v or plate in opened:setview('vehicles',filter='free')
  st.markdown("<a class='back' href='?view=vehicles&filter=free'>‹ VOLTAR</a><div class='title'>Registrar Saída</div>",unsafe_allow_html=True)
  st.markdown(f"<div class='hero'><div class='heroimg'><img src='{image(v.get('foto'))}'></div><div class='summary'><div><div class='plate'>{esc(plate)}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='company'>{esc(v.get('empresa'))}</div></div><div class='right'>KM ATUAL<br><b>{km(v.get('km_atual'))}</b></div></div></div>",unsafe_allow_html=True)
  with st.form('saida'):
   dest=st.text_input('📍 Para onde está indo?',placeholder='Ex.: Suzano - Portaria 2');people=st.text_input('👥 Quem está indo?',placeholder='Informe o(s) nome(s)');ki=st.number_input('🚗 KM inicial',min_value=int(v.get('km_atual') or 0),value=int(v.get('km_atual') or 0),step=1);st.text_input('▣ Data / hora',value=datetime.now(TZ).strftime('%d/%m/%Y  %H:%M'),disabled=True);save=st.form_submit_button('➤ REGISTRAR SAÍDA')
  if save:
   if not dest.strip() or not people.strip():st.error('Informe o destino e quem está indo.')
   else:
    try:
     DB.table('movimentacoes').insert({'placa':plate,'destino':dest.strip(),'pessoas':people.strip(),'km_inicial':int(ki),'data_hora_saida':now(),'status':'EM USO'}).execute();DB.table('veiculos').update({'km_atual':int(ki),'atualizado_em':now()}).eq('placa',plate).execute();setview('vehicles',filter='used')
    except Exception:st.error('Não foi possível registrar. Verifique se o veículo já está em uso.')
 else:
  v=next((x for x in vs if x['placa']==plate),None);m=opened.get(plate)
  if not v or not m:setview('vehicles',filter='used')
  st.markdown("<a class='back' href='?view=vehicles&filter=used'>‹ VOLTAR</a><div class='title'>Registrar Retorno</div>",unsafe_allow_html=True)
  st.markdown(f"<div class='box'><div class='retcar'><img src='{image(v.get('foto'))}'><div><div class='plate'>{esc(plate)}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='company'>{esc(v.get('empresa'))}</div></div></div><div class='stats'><div class='stat'>KM INICIAL<b>{km(m.get('km_inicial'))}</b></div><div class='stat'>SAÍDA<b>{clock(m.get('data_hora_saida'))}</b></div></div><div class='info' style='padding:0 10px 10px'>👤 <b>{esc(m.get('pessoas'))}</b><br>📍 {esc(m.get('destino'))}<br>⌛ {elapsed(m.get('data_hora_saida'))} em uso</div></div>",unsafe_allow_html=True)
  with st.form('retorno'):
   kf=st.number_input('🚗 KM final',min_value=int(m.get('km_inicial') or 0),value=int(m.get('km_inicial') or 0),step=1);c1,c2=st.columns(2);c1.metric('KM rodado',km(int(kf)-int(m.get('km_inicial') or 0)));c2.metric('Tempo',elapsed(m.get('data_hora_saida')));save=st.form_submit_button('✓ CONFIRMAR RETORNO')
  if save:
   DB.table('movimentacoes').update({'km_final':int(kf),'data_hora_retorno':now(),'status':'DEVOLVIDO'}).eq('id',m['id']).execute();DB.table('veiculos').update({'km_atual':int(kf),'atualizado_em':now()}).eq('placa',plate).execute();setview('vehicles',filter='free')

# TELA 2 — PAINEL: SOMENTE CONSULTA
elif view=='panel':
 top('PAINEL DA FROTA · TEMPO REAL')
 busy=len(opened);st.markdown(f"<div class='metrics'><div class='metric'>FROTA<b>{len(vs)}</b></div><div class='metric'>DISPONÍVEIS<b>{len(vs)-busy}</b></div><div class='metric'>EM USO<b>{busy}</b></div></div>",unsafe_allow_html=True)
 for v in vs:
  m=opened.get(v['placa']);target,left,pct=revision(v)
  status=(f"<div class='pstatus busy'>● EM USO</div><div class='info'>👤 <b>{esc(m.get('pessoas'))}</b><br>📍 {esc(m.get('destino'))}<br>🕒 Saída {dateclock(m.get('data_hora_saida'))}<br>⌛ {elapsed(m.get('data_hora_saida'))}</div>" if m else "<div class='pstatus free'>● DISPONÍVEL</div>")
  if target is None:revtxt="🔧 Revisão ainda não cadastrada";cls=''
  elif left<0:revtxt=f"⚠️ Revisão vencida há {km(abs(left))}";cls='danger'
  elif left<=1000:revtxt=f"⚠️ Faltam {km(left)} para revisão";cls='warn'
  else:revtxt=f"🔧 Próxima revisão {km(target)} · faltam {km(left)}";cls='ok'
  progress=(f"<div class='barrow'><span>Intervalo da revisão</span><span>{pct}%</span></div><div class='track'><div class='fill' style='width:{pct}%'></div></div>" if target is not None else '')
  st.markdown(f"<div class='panelcard'><div class='panelmain'><img src='{image(v.get('foto'))}'><div>{status}<div class='plate'>{esc(v.get('placa'))}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='info'>🚗 KM atual: <b>{km(v.get('km_atual'))}</b></div></div></div><div class='revbox {cls}'>{revtxt}{progress}</div></div>",unsafe_allow_html=True)
 st.markdown("<meta http-equiv='refresh' content='15'>",unsafe_allow_html=True)

# TELA 3 — ADMIN: CONTROLE COMPLETO
elif view=='admin':
 top('ADMINISTRAÇÃO DA FROTA')
 st.markdown(f"<div class='adminnav'><a class='{'on' if tab=='revisao' else ''}' href='?view=admin&tab=revisao'>🔧 REVISÕES</a><a class='{'on' if tab=='historico' else ''}' href='?view=admin&tab=historico'>📋 HISTÓRICO</a></div>",unsafe_allow_html=True)
 if tab=='revisao':
  st.markdown("<div class='title'>Controle de revisão</div>",unsafe_allow_html=True);p=st.selectbox('Veículo',[v['placa'] for v in vs]);v=next(x for x in vs if x['placa']==p);target,left,pct=revision(v)
  st.info(f"KM atual: {km(v.get('km_atual'))}  |  Próxima revisão: {km(target) if target else 'não cadastrada'}")
  with st.form('adminrev'):
   d=st.date_input('Data da última revisão');kr=st.number_input('KM da última revisão',min_value=0,value=int(v.get('km_ultima_revisao') or v.get('km_atual') or 0),step=1);st.caption(f'Próxima revisão será em {km(int(kr)+10000)}');save=st.form_submit_button('SALVAR REVISÃO')
  if save:DB.table('veiculos').update({'data_ultima_revisao':d.isoformat(),'km_ultima_revisao':int(kr),'intervalo_revisao':10000,'atualizado_em':now()}).eq('placa',p).execute();st.success('Revisão atualizada.');st.rerun()
 else:
  st.markdown("<div class='title'>Histórico de movimentações</div>",unsafe_allow_html=True)
  hist=DB.table('movimentacoes').select('*').order('data_hora_saida',desc=True).limit(100).execute().data or []
  for m in hist:
   status='🟠 EM USO' if m.get('status')=='EM USO' else '✅ DEVOLVIDO';rodado=(int(m.get('km_final'))-int(m.get('km_inicial'))) if m.get('km_final') is not None else None
   st.markdown(f"<div class='history'><b>{esc(m.get('placa'))}</b> · {status}<br>👤 {esc(m.get('pessoas'))}<br>📍 {esc(m.get('destino'))}<br>Saída: {dateclock(m.get('data_hora_saida'))}<br>Retorno: {dateclock(m.get('data_hora_retorno')) if m.get('data_hora_retorno') else '—'}<br>KM inicial: {km(m.get('km_inicial'))} · KM final: {km(m.get('km_final')) if m.get('km_final') is not None else '—'}{f' · Rodado: {km(rodado)}' if rodado is not None else ''}</div>",unsafe_allow_html=True)
else:setview('vehicles',filter='free')
