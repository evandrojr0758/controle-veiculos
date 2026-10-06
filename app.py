import streamlit as st
from pathlib import Path
from datetime import datetime, timezone, timedelta
from supabase import create_client
import base64, html

st.set_page_config(page_title='Controle de Veículos | 10 Sul', page_icon='🚙', layout='centered', initial_sidebar_state='collapsed')
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
 d=dt(x); return d.strftime('%H:%M') if d else '—'
def dateclock(x):
 d=dt(x); return d.strftime('%d/%m/%Y %H:%M') if d else '—'
def duration(start,end=None):
 a=dt(start); b=dt(end) if end else datetime.now(TZ)
 if not a or not b:return '—'
 m=max(0,int((b-a).total_seconds()/60)); return f'{m//60}h {m%60:02d}min' if m>=60 else f'{m} min'
def revision(v):
 if v.get('km_ultima_revisao') is None:return None,None,0
 start=int(v.get('km_ultima_revisao') or 0); cur=int(v.get('km_atual') or 0); target=start+10000; left=target-cur; pct=max(0,min(100,round(((cur-start)/10000)*100)))
 return target,left,pct
def load():
 vs=DB.table('veiculos').select('*').order('placa').execute().data or []
 ms=DB.table('movimentacoes').select('*').eq('status','EM USO').order('data_hora_saida',desc=True).execute().data or []
 return vs,{m['placa']:m for m in ms}
def setview(view,**kwargs):
 d={'view':view}; d.update(kwargs); st.query_params.from_dict(d); st.rerun()
def top(sub): st.markdown(f"<div class='top'><div class='logo'>🔧</div><div class='brand'>10 SUL<small>CONTROLE DE VEÍCULOS · SERVICE</small></div></div><div class='mode'>{sub}</div>",unsafe_allow_html=True)

st.markdown('''<style>
#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"],section[data-testid="stSidebar"]{display:none!important}.stApp{background:#f2f6fa;color:#173d60}.block-container{max-width:430px;padding:10px 9px 55px!important}[data-testid="stVerticalBlock"]{gap:.35rem}.top{height:54px;background:#fff;border-radius:15px;display:flex;align-items:center;padding:0 13px;box-shadow:0 3px 14px #173b5a12;margin-bottom:9px}.logo{width:33px;height:33px;border-radius:9px;background:#0868b6;color:#fff;display:grid;place-items:center;margin-right:9px}.brand{font-size:18px;font-weight:950;color:#073c6c}.brand small{display:block;font-size:8px;letter-spacing:.7px;color:#72869a;margin-top:2px}.mode{font-size:9px;color:#768a9c;margin-top:-6px;margin-bottom:8px;text-align:center}.title{font-size:18px;font-weight:950;color:#083d6d;margin:8px 1px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.card,.box,.panelcard,.history,.revcard{background:#fff;border:1px solid #dce5ed;border-radius:13px;overflow:hidden;box-shadow:0 3px 12px #173b5a10}.pic{height:120px;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden}.pic img{width:100%;height:100%;object-fit:contain}.badge{position:absolute;top:6px;right:6px;color:#fff;border-radius:12px;padding:4px 7px;font-size:7px;font-weight:950}.green{background:#14a765}.orange{background:#f27a21}.body{padding:8px}.plate{font-size:16px;font-weight:950;color:#083d6d}.model{font-size:9px;font-weight:850;margin-top:3px}.company{font-size:8px;color:#8a9baa;margin:2px 0 7px}.info{font-size:9px;line-height:1.55;color:#60778b}.use{background:#fff5ec;border-radius:7px;padding:6px;font-size:8px;line-height:1.5}.action{display:block;text-decoration:none;text-align:center;border-radius:8px;background:#0868b6;color:#fff!important;font-size:8px;font-weight:950;padding:10px 2px;margin-top:7px}.action.ret{background:#fff0e4;color:#df6918!important}.heroimg{height:118px;display:flex;align-items:center;justify-content:center;padding:6px 12px;background:#fff}.heroimg img{max-width:100%;max-height:106px;object-fit:contain}.summary{background:#edf7ff;padding:7px 10px;display:grid;grid-template-columns:1.2fr 1fr;align-items:center}.right{text-align:right;font-size:7px;color:#718699}.right b{font-size:10px;color:#173f62}.retcar{display:flex;gap:9px;align-items:center;background:#edf7ff;padding:8px}.retcar img{width:105px;height:70px;object-fit:contain}.stats{display:grid;grid-template-columns:1fr 1fr;gap:7px;padding:9px}.stat{background:#f1f6fa;border-radius:8px;padding:8px;text-align:center;font-size:8px;color:#718596}.stat b{display:block;font-size:13px;color:#153f63}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:9px}.metric{background:#fff;border:1px solid #dfe7ee;border-radius:11px;padding:9px;text-align:center;font-size:8px}.metric b{display:block;font-size:20px;color:#0a477b}.panelgrid{display:grid;grid-template-columns:1fr;gap:9px}.panelcard{padding:10px;margin:0;min-width:0}.panelmain{display:grid;grid-template-columns:105px 1fr;gap:10px;align-items:center}.panelmain img{width:105px;height:82px;object-fit:contain}.pstatus{font-size:8px;font-weight:950}.free{color:#0a9b60}.busy{color:#e56a17}.revbox{margin-top:8px;background:#f4f7fa;border-radius:8px;padding:7px;font-size:8px}.adminnav{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:4px 0 10px}.history{padding:10px;margin:7px 0;font-size:9px;line-height:1.6}.revcard{padding:12px;margin:8px 0}.revgrid{display:grid;grid-template-columns:1fr 1fr;align-items:center;gap:10px}.remain{text-align:center;font-size:10px;color:#718596}.remain b{display:block;font-size:25px;color:#0872bd;line-height:1.05;margin-top:3px}.remain.alert b{color:#d71920;animation:blink 1s infinite}.remain.over b{color:#d71920}.barrow{display:flex;justify-content:space-between;font-size:7px;color:#6e8294;margin-top:6px}.track{height:5px;background:#e5edf3;border-radius:6px;overflow:hidden}.fill{height:100%;background:#10b576}.fieldcallout{background:#fff;border:2px solid #0b70bb;border-radius:12px;padding:10px 12px 5px;margin:9px 0 3px;box-shadow:0 3px 12px #0b70bb18}.fieldcallout.people{border-color:#673ab7}.fieldtitle{font-size:14px;font-weight:950;color:#083d6d;line-height:1.15}.fieldhint{font-size:9px;color:#6e8294;margin:3px 0 5px}@keyframes blink{0%,45%{opacity:1}50%,95%{opacity:.2}100%{opacity:1}}.dangerbtn button{background:#c83b3b!important}.stButton button,.stFormSubmitButton button{width:100%;border-radius:9px!important;min-height:42px!important;font-weight:900!important}.stTextInput input,.stNumberInput input,.stDateInput input,.stSelectbox>div>div{border-radius:9px!important;min-height:40px!important}label{font-size:10px!important;font-weight:800!important}.spacer{height:8px}
@media(min-width:700px){.block-container{max-width:900px}.pic{height:205px}.panelgrid{grid-template-columns:repeat(2,minmax(0,1fr))}.panelmain{grid-template-columns:125px 1fr}.panelmain img{width:125px;height:95px}.panelcard{padding:11px}}
</style>''',unsafe_allow_html=True)

try:vs,opened=load()
except Exception: st.error('Falha ao conectar ao banco online.'); st.stop()
q=st.query_params; view=q.get('view','vehicles'); plate=q.get('plate',''); flt=q.get('filter','free'); tab=q.get('tab','revisao')

if view in ('vehicles','out','return'):
 top('USO DO VEÍCULO · SAÍDA E RETORNO')
 if view=='vehicles':
  free=sum(v['placa'] not in opened for v in vs); busy=len(opened)
  c1,c2=st.columns(2)
  if c1.button(f'DISPONÍVEIS {free}',use_container_width=True,type='primary' if flt=='free' else 'secondary'): setview('vehicles',filter='free')
  if c2.button(f'EM USO {busy}',use_container_width=True,type='primary' if flt=='used' else 'secondary'): setview('vehicles',filter='used')
  items=[v for v in vs if (v['placa'] in opened)==(flt=='used')]
  cards=[]
  for v in items:
   m=opened.get(v['placa']); busyv=bool(m); details=(f"<div class='use'>👤 <b>{esc(m.get('pessoas'))}</b><br>📍 {esc(m.get('destino'))}<br>◷ {clock(m.get('data_hora_saida'))} · {duration(m.get('data_hora_saida'))}</div>" if m else f"<div class='info'>🚗 KM atual<br><b>{km(v.get('km_atual'))}</b></div>")
   cards.append(f"<div><div class='card'><div class='pic'><img src='{image(v.get('foto'))}'><span class='badge {'orange' if busyv else 'green'}'>{'EM USO' if busyv else 'DISPONÍVEL'}</span></div><div class='body'><div class='plate'>{esc(v.get('placa'))}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='company'>{esc(v.get('empresa'))}</div>{details}</div></div><a class='action {'ret' if busyv else ''}' href='?view={'return' if busyv else 'out'}&plate={esc(v.get('placa'))}' target='_self'>{'↩ REGISTRAR RETORNO' if busyv else '➜ USAR ESTE VEÍCULO'}</a></div>")
  st.markdown("<div class='grid'>"+''.join(cards)+"</div>",unsafe_allow_html=True)
 elif view=='out':
  v=next((x for x in vs if x['placa']==plate),None)
  if not v or plate in opened:setview('vehicles',filter='free')
  if st.button('‹ VOLTAR'):setview('vehicles',filter='free')
  st.markdown("<div class='title'>Registrar Saída</div>",unsafe_allow_html=True)
  st.markdown(f"<div class='box'><div class='heroimg'><img src='{image(v.get('foto'))}'></div><div class='summary'><div><div class='plate'>{esc(plate)}</div><div class='model'>{esc(v.get('modelo'))}</div></div><div class='right'>KM ATUAL<br><b>{km(v.get('km_atual'))}</b></div></div></div><div class='spacer'></div>",unsafe_allow_html=True)
  with st.form('saida'):
   st.markdown("<div class='fieldcallout'><div class='fieldtitle'>📍 DESTINO — PARA ONDE O VEÍCULO ESTÁ INDO?</div><div class='fieldhint'>Informe o local ou a finalidade do deslocamento.</div></div>",unsafe_allow_html=True)
   dest=st.text_input('Destino',placeholder='Ex.: Portaria Leste, Suzano, Buscar mecânico',label_visibility='collapsed')
   st.markdown("<div class='fieldcallout people'><div class='fieldtitle'>👥 OCUPANTES — QUEM ESTÁ INDO NO VEÍCULO?</div><div class='fieldhint'>Digite o nome das pessoas que estão usando o veículo.</div></div>",unsafe_allow_html=True)
   people=st.text_input('Ocupantes',placeholder='Ex.: Evandro, João, Carlos',label_visibility='collapsed')
   ki=st.number_input('🚗 KM inicial',min_value=int(v.get('km_atual') or 0),value=int(v.get('km_atual') or 0),step=1); save=st.form_submit_button('➤ REGISTRAR SAÍDA')
  if save:
   if not dest.strip() or not people.strip():st.error('Informe o DESTINO e os OCUPANTES antes de registrar a saída.')
   else:
    DB.table('movimentacoes').insert({'placa':plate,'destino':dest.strip(),'pessoas':people.strip(),'km_inicial':int(ki),'data_hora_saida':now(),'status':'EM USO'}).execute(); DB.table('veiculos').update({'km_atual':int(ki),'atualizado_em':now()}).eq('placa',plate).execute(); setview('vehicles',filter='used')
 else:
  v=next((x for x in vs if x['placa']==plate),None); m=opened.get(plate)
  if not v or not m:setview('vehicles',filter='used')
  if st.button('‹ VOLTAR'):setview('vehicles',filter='used')
  st.markdown("<div class='title'>Registrar Retorno</div>",unsafe_allow_html=True)
  st.markdown(f"<div class='box'><div class='retcar'><img src='{image(v.get('foto'))}'><div><div class='plate'>{esc(plate)}</div><div class='model'>{esc(v.get('modelo'))}</div></div></div><div class='stats'><div class='stat'>KM INICIAL<b>{km(m.get('km_inicial'))}</b></div><div class='stat'>TEMPO EM USO<b>{duration(m.get('data_hora_saida'))}</b></div></div></div>",unsafe_allow_html=True)
  with st.form('retorno'):
   initial=int(m.get('km_inicial') or 0); kf=st.number_input('🚗 KM final',min_value=initial,value=initial,step=1); st.caption(f'KM rodado: {km(max(0,int(kf)-initial))}'); save=st.form_submit_button('✓ CONFIRMAR RETORNO')
  if save:
   if int(kf)<=initial: st.error('O KM final deve ser maior que o KM inicial.')
   else:
    DB.table('movimentacoes').update({'km_final':int(kf),'data_hora_retorno':now(),'status':'DEVOLVIDO'}).eq('id',m['id']).execute(); DB.table('veiculos').update({'km_atual':int(kf),'atualizado_em':now()}).eq('placa',plate).execute(); setview('vehicles',filter='free')

elif view=='panel':
 top('PAINEL DA FROTA · TEMPO REAL'); busy=len(opened)
 st.markdown(f"<div class='metrics'><div class='metric'>FROTA<b>{len(vs)}</b></div><div class='metric'>DISPONÍVEIS<b>{len(vs)-busy}</b></div><div class='metric'>EM USO<b>{busy}</b></div></div>",unsafe_allow_html=True)
 panelcards=[]
 for v in vs:
  m=opened.get(v['placa']); target,left,pct=revision(v); status=(f"<div class='pstatus busy'>● EM USO</div><div class='info'>👤 <b>Com:</b> {esc(m.get('pessoas'))}<br>📍 <b>Destino:</b> {esc(m.get('destino'))}<br>⌛ <b>Tempo em uso:</b> {duration(m.get('data_hora_saida'))}</div>" if m else "<div class='pstatus free'>● DISPONÍVEL</div>")
  revtxt='Revisão não cadastrada' if target is None else (f'REVISÃO VENCIDA HÁ {km(abs(left))}' if left<0 else f'FALTAM {km(left)}')
  panelcards.append(f"<div class='panelcard'><div class='panelmain'><img src='{image(v.get('foto'))}'><div>{status}<div class='plate'>{esc(v.get('placa'))}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='info'>KM atual: <b>{km(v.get('km_atual'))}</b></div></div></div><div class='revbox'>{revtxt}</div></div>")
 st.markdown("<div class='panelgrid'>"+''.join(panelcards)+"</div>",unsafe_allow_html=True)
 st.markdown("<meta http-equiv='refresh' content='15'>",unsafe_allow_html=True)

elif view=='admin':
 top('ADMINISTRAÇÃO DA FROTA')
 c1,c2,c3=st.columns(3)
 if c1.button('🔧 REVISÕES',use_container_width=True,type='primary' if tab=='revisao' else 'secondary'):setview('admin',tab='revisao')
 if c2.button('📋 HISTÓRICO',use_container_width=True,type='primary' if tab=='historico' else 'secondary'):setview('admin',tab='historico')
 if c3.button('🚙 VEÍCULOS',use_container_width=True,type='primary' if tab=='veiculos' else 'secondary'):setview('admin',tab='veiculos')
 if tab=='revisao':
  st.markdown("<div class='title'>Controle de revisão</div>",unsafe_allow_html=True)
  opts={f"{v['placa']} — {v.get('modelo','')}":v for v in vs}; sel=st.selectbox('Veículo',list(opts)); v=opts[sel]; target,left,pct=revision(v)
  if target is None: rclass=''; rbig='NÃO CADASTRADA'; rsmall='Cadastre a última revisão'
  elif left<0:rclass='over';rbig=f'VENCIDA<br>{km(abs(left))}';rsmall='KM PARA REVISÃO'
  elif left<=2000:rclass='alert';rbig=km(left);rsmall='KM PARA REVISÃO'
  else:rclass='';rbig=km(left);rsmall='KM PARA REVISÃO'
  st.markdown(f"<div class='revcard'><div class='revgrid'><div><div class='plate'>{esc(v['placa'])}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='info'>KM atual: <b>{km(v.get('km_atual'))}</b><br>Próxima revisão: <b>{km(target) if target is not None else '—'}</b></div></div><div class='remain {rclass}'>{rsmall}<b>{rbig}</b></div></div></div>",unsafe_allow_html=True)
  with st.form('rev'):
   dr=st.date_input('Data da última revisão',value=dt(v.get('data_ultima_revisao')).date() if dt(v.get('data_ultima_revisao')) else datetime.now(TZ).date()); raw_last=v.get('km_ultima_revisao'); default_last=int(raw_last) if raw_last is not None else int(v.get('km_atual') or 0); kr=st.number_input('KM da última revisão',min_value=0,value=default_last,step=1); st.caption(f'Próxima revisão: {km(int(kr)+10000)}'); save=st.form_submit_button('💾 SALVAR / CORRIGIR ÚLTIMA REVISÃO')
  if save:
   DB.table('veiculos').update({'data_ultima_revisao':dr.isoformat(),'km_ultima_revisao':int(kr),'atualizado_em':now()}).eq('placa',v['placa']).execute(); st.success('Revisão atualizada.'); st.rerun()
 elif tab=='historico':
  st.markdown("<div class='title'>Histórico de movimentações</div>",unsafe_allow_html=True)
  hist=DB.table('movimentacoes').select('*').order('data_hora_saida',desc=True).limit(100).execute().data or []
  for m in hist:
   end=m.get('data_hora_retorno'); kf=m.get('km_final'); rod=(int(kf)-int(m.get('km_inicial') or 0)) if kf is not None else None
   st.markdown(f"<div class='history'><b>{esc(m.get('placa'))}</b> · {'🟠 EM USO' if m.get('status')=='EM USO' else '✅ DEVOLVIDO'}<br>👤 {esc(m.get('pessoas'))}<br>📍 {esc(m.get('destino'))}<br>Saída: {dateclock(m.get('data_hora_saida'))}<br>Retorno: {dateclock(end)}<br>⏱️ Tempo de uso: <b>{duration(m.get('data_hora_saida'),end) if end else duration(m.get('data_hora_saida'))}</b><br>KM inicial: {km(m.get('km_inicial'))} · KM final: {km(kf) if kf is not None else '—'} · Rodado: {km(rod) if rod is not None else '—'}</div>",unsafe_allow_html=True)
   with st.expander(f"Gerenciar lançamento #{m.get('id')}"):
    st.warning('A exclusão é definitiva. Se este lançamento estiver EM USO, o veículo voltará a aparecer como disponível.')
    st.markdown("<div class='dangerbtn'>",unsafe_allow_html=True)
    if st.button('🗑️ EXCLUIR ESTA MOVIMENTAÇÃO',key=f"del_{m.get('id')}",use_container_width=True):
     try:
      DB.table('movimentacoes').delete().eq('id',m.get('id')).execute(); st.success('Movimentação excluída.'); st.rerun()
     except Exception as e: st.error(f'Não foi possível excluir: {e}')
    st.markdown('</div>',unsafe_allow_html=True)
 else:
  st.markdown("<div class='title'>Cadastro dos veículos</div>",unsafe_allow_html=True)
  for v in vs: st.markdown(f"<div class='history'><b>{esc(v.get('placa'))}</b> · {esc(v.get('modelo'))}<br>KM atual: {km(v.get('km_atual'))}<br>Foto: {esc(v.get('foto'))}</div>",unsafe_allow_html=True)