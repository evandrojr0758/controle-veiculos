import streamlit as st
from pathlib import Path
from datetime import datetime, timezone, timedelta
from supabase import create_client
import base64, html
from urllib.parse import urlencode
from gps_bridge import gps_suggestion
from fleet_units import UNITS, resolve_unit, scope_fleet, route_params

st.set_page_config(page_title='Controle de Veículos | 10 Sul', page_icon='🚙', layout='centered', initial_sidebar_state='collapsed')
BASE=Path(__file__).parent; ASSETS=BASE/'assets'; TZ=timezone(timedelta(hours=-3))
@st.cache_resource
def get_db(): return create_client(st.secrets['SUPABASE_URL'],st.secrets['SUPABASE_KEY'])
DB=get_db()
def esc(x): return html.escape(str(x or ''))
def km(x):
 if x is None: return 'PENDENTE'
 return f"{int(x or 0):,}".replace(',','.')+' km'
def now(): return datetime.now(TZ).isoformat()
def image(name):
 try:return ('data:image/jpeg;base64,' if str(name).lower().endswith(('.jpg','.jpeg')) else 'data:image/png;base64,')+base64.b64encode((ASSETS/name).read_bytes()).decode()
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
def revision_appointment_date(v):
 try:return datetime.strptime(str(v.get('data_revisao_agendada') or ''),'%Y-%m-%d').date()
 except (ValueError,TypeError):return None

def revision_appointment_time(v):
 try:return datetime.strptime(str(v.get('hora_revisao_agendada') or '')[:5],'%H:%M').time()
 except (ValueError,TypeError):return None

def revision_appointment_banner(v):
 scheduled=revision_appointment_date(v)
 if scheduled is None:return ''
 appointment_time=revision_appointment_time(v)
 hour_text=appointment_time.strftime('%H:%M') if appointment_time else 'Horário não informado'
 today=datetime.now(TZ).date()
 urgent=scheduled<=today
 label='REVISÃO AGENDADA PARA HOJE' if scheduled==today else ('DATA AGENDADA JÁ PASSOU — CONFIRA A REVISÃO' if scheduled<today else 'PRÓXIMA REVISÃO AGENDADA')
 bg,border,fg=('#fee2e2','#dc2626','#991b1b') if urgent else ('#fff4cc','#f59e0b','#78350f')
 return f"<div role='note' style='margin:12px 0;padding:14px;border:2px solid {border};border-radius:12px;background:{bg};color:{fg};line-height:1.4'><div style='font-size:12px;font-weight:850'>📅 {label}</div><div style='font-size:26px;font-weight:900'>{scheduled.strftime('%d/%m/%Y')} · {hour_text}</div><div style='font-size:12px'>Organize o uso do veículo considerando este agendamento.</div></div>"

def revision(v):
 if v.get('km_ultima_revisao') is None or v.get('km_atual') is None:return None,None,0
 interval=int(v.get('intervalo_revisao') or 10000)
 start=int(v.get('km_ultima_revisao') or 0); cur=int(v.get('km_atual') or 0); target=start+interval; left=target-cur; pct=max(0,min(100,round(((cur-start)/interval)*100)))
 return target,left,pct

def revision_completion_values(v,completed_date,completed_km):
 if completed_date is None or completed_date>datetime.now(TZ).date():
  raise ValueError('Informe a data em que a revisão foi realizada, sem data futura.')
 last_date=str(v.get('data_ultima_revisao') or '')[:10]
 if last_date and completed_date.isoformat()<last_date:
  raise ValueError('A conclusão não pode ser anterior à última revisão. Use a correção do cadastro se necessário.')
 last_km=v.get('km_ultima_revisao')
 if completed_km<=0 or (last_km is not None and completed_km<=int(last_km)):
  raise ValueError('O KM realizado deve ser maior que o da última revisão. Para corrigir um registro, use a opção de correção abaixo.')
 if v.get('km_atual') is None or completed_km>int(v['km_atual']):
  raise ValueError('O KM da revisão não pode superar o KM atual. Confira o hodômetro no cadastro do veículo.')
 return {'data_ultima_revisao':completed_date.isoformat(),'km_ultima_revisao':int(completed_km),'data_revisao_agendada':None,'hora_revisao_agendada':None}
def load():
 vs=DB.table('veiculos').select('*').order('placa').execute().data or []
 ms=DB.table('movimentacoes').select('*').eq('status','EM USO').order('data_hora_saida',desc=True).execute().data or []
 return vs,{m['placa']:m for m in ms}
def editar_km_inicial_em_uso(m,prefixo):
 st.markdown('**✏️ Corrigir KM inicial da viagem em uso**')
 with st.form(f"corrigir_km_inicial_{prefixo}_{m['id']}"):
  novo_km=st.number_input('KM inicial correto',min_value=1,value=max(1,int(m.get('km_inicial') or 0)),step=1)
  salvar=st.form_submit_button('💾 SALVAR KM INICIAL')
 if st.session_state.get('km_inicial_corrigido')==m['id']:
  st.success('KM inicial corrigido. A viagem continua em uso.')
  st.session_state.pop('km_inicial_corrigido',None)
 if salvar:
  try:
   resultado=DB.rpc('corrigir_km_inicial_em_uso',{'p_movimentacao_id':m['id'],'p_km_esperado':m.get('km_inicial'),'p_novo_km':int(novo_km)}).execute()
   if not resultado.data or resultado.data.get('km_inicial')!=int(novo_km):
    st.error('Não foi possível confirmar a correção. Atualize a tela.')
   else:
    st.session_state['km_inicial_corrigido']=m['id']
    st.rerun()
  except Exception as e:
   st.error(getattr(e,'message','Não foi possível corrigir o KM inicial. Atualize a tela e tente novamente.'))

def setview(view,**kwargs):
 d=route_params(view,UNIT,**kwargs)
 if st.session_state.get('native_android'): d['native']='android'
 st.query_params.from_dict(d); st.rerun()

def gps_command(action,m):
 params={'native_command':action,'id':str(m['id']),'unidade':UNIT}
 if action=='start': params.update(plate=m['placa'],initial=int(m.get('km_inicial') or 0))
 url='https://controle-veiculos-jpnsn36kukknr96dv9noma.streamlit.app/?'+urlencode(params)
 label='📍 INICIAR CONTAGEM POR GPS' if action=='start' else '✓ Retorno confirmado'
 st.markdown(f"<a class='action' data-gps-command='{action}' href='{esc(url)}' target='_self'>{label}</a>",unsafe_allow_html=True)
def top(sub): st.markdown(f"<div class='top'><div class='logo'>🔧</div><div class='brand'>10 SUL<small>CONTROLE DE VEÍCULOS · SERVICE</small></div></div><div class='mode'>{sub} · {esc(UNITS[UNIT])}</div>",unsafe_allow_html=True)

@st.dialog('O km está correto?')
def confirmar_km_inicial(placa,destino,ocupantes,km_inicial,condutor):
 st.markdown(f"**Veículo:** {placa}")
 st.markdown(f"**Condutor:** {condutor}")
 st.markdown(f"**KM inicial informado:** {km(km_inicial)}")
 confirmar,corrigir=st.columns(2)
 if confirmar.button('✅ SIM, REGISTRAR',key='confirmar_km_inicial',use_container_width=True,type='primary'):
  result=DB.table('movimentacoes').insert({'placa':placa,'destino':destino,'pessoas':ocupantes,'condutor':condutor.strip(),'km_inicial':int(km_inicial),'data_hora_saida':now(),'status':'EM USO'}).execute()
  DB.table('veiculos').update({'km_atual':int(km_inicial),'atualizado_em':now()}).eq('placa',placa).execute()
  if st.session_state.get('native_android') and result.data:
   st.session_state['gps_start']=result.data[0]
  setview('vehicles',filter='used')
 if corrigir.button('✏️ NÃO, CORRIGIR',key='corrigir_km_inicial',use_container_width=True):
  st.rerun()

@st.dialog('O km está correto?')
def confirmar_km_final(placa,movimentacao_id,km_inicial,km_final):
 st.markdown(f"**Veículo:** {placa}")
 st.markdown(f"**KM final informado:** {km(km_final)}")
 st.markdown(f"**KM rodado:** {km(int(km_final)-int(km_inicial))}")
 confirmar,corrigir=st.columns(2)
 if confirmar.button('✅ SIM, REGISTRAR',key='confirmar_km_final',use_container_width=True,type='primary'):
  DB.table('movimentacoes').update({'km_final':int(km_final),'data_hora_retorno':now(),'status':'DEVOLVIDO'}).eq('id',movimentacao_id).execute()
  DB.table('veiculos').update({'km_atual':int(km_final),'atualizado_em':now()}).eq('placa',placa).execute()
  if st.session_state.get('native_android'): st.session_state['gps_complete']={'id':movimentacao_id}
  setview('vehicles',filter='free')
 if corrigir.button('✏️ NÃO, CORRIGIR',key='corrigir_km_final',use_container_width=True):
  st.rerun()

st.markdown('''<style>
#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"],section[data-testid="stSidebar"]{display:none!important}.stApp{background:#f2f6fa;color:#173d60}.block-container{max-width:430px;padding:10px 9px 55px!important}[data-testid="stVerticalBlock"]{gap:.35rem}.top{height:54px;background:#fff;border-radius:15px;display:flex;align-items:center;padding:0 13px;box-shadow:0 3px 14px #173b5a12;margin-bottom:9px}.logo{width:33px;height:33px;border-radius:9px;background:#0868b6;color:#fff;display:grid;place-items:center;margin-right:9px}.brand{font-size:18px;font-weight:950;color:#073c6c}.brand small{display:block;font-size:8px;letter-spacing:.7px;color:#72869a;margin-top:2px}.mode{font-size:9px;color:#768a9c;margin-top:-6px;margin-bottom:8px;text-align:center}.title{font-size:18px;font-weight:950;color:#083d6d;margin:8px 1px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.card,.box,.panelcard,.history,.revcard{background:#fff;border:1px solid #dce5ed;border-radius:13px;overflow:hidden;box-shadow:0 3px 12px #173b5a10}.pic{height:120px;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden}.pic img{width:100%;height:100%;object-fit:contain}.badge{position:absolute;top:6px;right:6px;color:#fff;border-radius:12px;padding:4px 7px;font-size:7px;font-weight:950}.green{background:#14a765}.orange{background:#f27a21}.body{padding:8px}.plate{font-size:16px;font-weight:950;color:#083d6d}.model{font-size:9px;font-weight:850;margin-top:3px}.company{font-size:8px;color:#8a9baa;margin:2px 0 7px}.info{font-size:9px;line-height:1.55;color:#60778b}.use{background:#fff5ec;border-radius:7px;padding:6px;font-size:8px;line-height:1.5}.action{display:block;text-decoration:none;text-align:center;border-radius:8px;background:#0868b6;color:#fff!important;font-size:8px;font-weight:950;padding:10px 2px;margin-top:7px}.action.ret{background:#fff0e4;color:#df6918!important}.heroimg{height:118px;display:flex;align-items:center;justify-content:center;padding:6px 12px;background:#fff}.heroimg img{max-width:100%;max-height:106px;object-fit:contain}.summary{background:#edf7ff;padding:7px 10px;display:grid;grid-template-columns:1.2fr 1fr;align-items:center}.right{text-align:right;font-size:7px;color:#718699}.right b{font-size:10px;color:#173f62}.retcar{display:flex;gap:9px;align-items:center;background:#edf7ff;padding:8px}.retcar img{width:105px;height:70px;object-fit:contain}.stats{display:grid;grid-template-columns:1fr 1fr;gap:7px;padding:9px}.stat{background:#f1f6fa;border-radius:8px;padding:8px;text-align:center;font-size:8px;color:#718596}.stat b{display:block;font-size:13px;color:#153f63}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:9px}.metric{background:#fff;border:1px solid #dfe7ee;border-radius:11px;padding:9px;text-align:center;font-size:8px}.metric b{display:block;font-size:20px;color:#0a477b}.panelgrid{display:grid;grid-template-columns:1fr;gap:9px}.panelcard{padding:10px;margin:0;min-width:0}.panelmain{display:grid;grid-template-columns:105px 1fr;gap:10px;align-items:center}.panelmain img{width:105px;height:82px;object-fit:contain}.pstatus{font-size:8px;font-weight:950}.free{color:#0a9b60}.busy{color:#e56a17}.revbox{margin-top:8px;background:#f4f7fa;border-radius:8px;padding:7px;font-size:8px}.adminnav{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:4px 0 10px}.history{padding:10px;margin:7px 0;font-size:9px;line-height:1.6}.revcard{padding:12px;margin:8px 0}.revgrid{display:grid;grid-template-columns:1fr 1fr;align-items:center;gap:10px}.remain{text-align:center;font-size:10px;color:#718596}.remain b{display:block;font-size:25px;color:#0872bd;line-height:1.05;margin-top:3px}.remain.alert b{color:#d71920;animation:blink 1s infinite}.remain.over b{color:#d71920}.barrow{display:flex;justify-content:space-between;font-size:7px;color:#6e8294;margin-top:6px}.track{height:5px;background:#e5edf3;border-radius:6px;overflow:hidden}.fill{height:100%;background:#10b576}.fieldcallout{background:#fff;border:2px solid #0b70bb;border-radius:12px;padding:10px 12px 5px;margin:9px 0 3px;box-shadow:0 3px 12px #0b70bb18}.fieldcallout.people{border-color:#673ab7}.fieldtitle{font-size:14px;font-weight:950;color:#083d6d;line-height:1.15}.fieldhint{font-size:9px;color:#6e8294;margin:3px 0 5px}@keyframes blink{0%,45%{opacity:1}50%,95%{opacity:.2}100%{opacity:1}}.dangerbtn button{background:#c83b3b!important}.stButton button,.stFormSubmitButton button{width:100%;border-radius:9px!important;min-height:42px!important;font-weight:900!important}.stTextInput input,.stNumberInput input,.stDateInput input,.stSelectbox>div>div{border-radius:9px!important;min-height:40px!important}label{font-size:10px!important;font-weight:800!important}.spacer{height:8px}
@media(min-width:700px){.block-container{max-width:900px}.pic{height:205px}.panelgrid{grid-template-columns:repeat(2,minmax(0,1fr))}.panelmain{grid-template-columns:125px 1fr}.panelmain img{width:125px;height:95px}.panelcard{padding:11px}}
</style>''',unsafe_allow_html=True)

try:vs,opened=load()
except Exception: st.error('Falha ao conectar ao banco online.'); st.stop()
q=st.query_params; view=q.get('view','vehicles'); plate=q.get('plate',''); flt=q.get('filter','free'); tab=q.get('tab','revisao')
all_vs=vs; UNIT=resolve_unit(q,all_vs)
if q.get('native')=='android' and view=='vehicles' and not q.get('gps_return'):
 if not q.get('unidade'): UNIT=st.session_state.get('native_unit',UNIT)
 native_unit=st.selectbox('Unidade de operação',['ARA','BA'],index=['ARA','BA'].index(UNIT),format_func=lambda key:UNITS[key],key='native_fleet_unit_'+UNIT)
 st.session_state['native_unit']=native_unit
 if native_unit!=UNIT:
  UNIT=native_unit; setview('vehicles',filter=flt)
if view=='admin':
 choices=list(UNITS)
 selected=st.selectbox('Unidade',choices,index=choices.index(UNIT),format_func=lambda key:UNITS[key],key='fleet_unit_'+UNIT)
 if selected!=UNIT:
  UNIT=selected; setview('admin',tab=tab)
vs,opened=scope_fleet(all_vs,opened,UNIT)
units_by_plate={v['placa']:UNITS.get(v.get('unidade','ARA'),'Unidade não informada') for v in all_vs}
if q.get('native')=='android': st.session_state['native_android']=True
if q.get('gps_return')=='1':
 view='return'
 if st.session_state.get('native_android') and plate not in opened and q.get('gps_id'):
  finished=DB.table('movimentacoes').select('id,placa,status').eq('id',q.get('gps_id')).eq('placa',plate).eq('status','DEVOLVIDO').limit(1).execute().data or []
  if finished:
   st.session_state['gps_complete']=finished[0]
   view='vehicles'; flt='free'
if st.session_state.get('native_android'):
 complete=st.session_state.pop('gps_complete',None)
 if complete: gps_command('complete',complete)
 start=st.session_state.pop('gps_start',None)
 if start and str(opened.get(start['placa'],{}).get('id'))==str(start['id']):
  gps_command('start',start)
  st.caption('Autorize o GPS no aplicativo para iniciar a contagem desta viagem.')

if view in ('vehicles','out','return'):
 top('USO DO VEÍCULO · SAÍDA E RETORNO')
 if view=='vehicles':
  free=sum(v['placa'] not in opened for v in vs); busy=len(opened)
  c1,c2=st.columns(2)
  if c1.button(f'DISPONÍVEIS {free}',use_container_width=True,type='primary' if flt=='free' else 'secondary'): setview('vehicles',filter='free')
  if c2.button(f'EM USO {busy}',use_container_width=True,type='primary' if flt=='used' else 'secondary'): setview('vehicles',filter='used')
  if not st.session_state.get('native_android'):
   st.link_button('📲 APLICATIVO ANDROID · KM AUTOMÁTICO', 'https://github.com/evandrojr0758/controle-veiculos/raw/refs/heads/main/downloads/VEICULOS_10_SUL_GPS_v1.apk',use_container_width=True)
  items=[v for v in vs if (v['placa'] in opened)==(flt=='used')]
  cards=[]
  native_suffix='&unidade='+UNIT+('&native=android' if st.session_state.get('native_android') else '')
  for v in items:
   m=opened.get(v['placa']); busyv=bool(m); details=(f"<div class='use'>👤 <b>{esc(m.get('pessoas'))}</b><br>📍 {esc(m.get('destino'))}<br>◷ {clock(m.get('data_hora_saida'))} · {duration(m.get('data_hora_saida'))}</div>" if m else f"<div class='info'>🚗 KM atual<br><b>{km(v.get('km_atual'))}</b></div>")
   cards.append(f"<div><div class='card'><div class='pic'><img src='{image(v.get('foto'))}'><span class='badge {'orange' if busyv else 'green'}'>{'EM USO' if busyv else 'DISPONÍVEL'}</span></div><div class='body'><div class='plate'>{esc(v.get('placa'))}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='company'>{esc(v.get('empresa'))} · {esc(units_by_plate[v['placa']])}</div>{revision_appointment_banner(v)}{details}</div></div><a class='action {'ret' if busyv else ''}' href='?view={'return' if busyv else 'out'}&plate={esc(v.get('placa'))}{native_suffix}' target='_self'>{'↩ REGISTRAR RETORNO' if busyv else '➜ USAR ESTE VEÍCULO'}</a></div>")
  st.markdown("<div class='grid'>"+''.join(cards)+"</div>",unsafe_allow_html=True)
 elif view=='out':
  v=next((x for x in vs if x['placa']==plate),None)
  if not v or plate in opened:setview('vehicles',filter='free')
  if st.button('‹ VOLTAR'):setview('vehicles',filter='free')
  st.markdown("<div class='title'>Registrar Saída</div>",unsafe_allow_html=True)
  st.markdown(f"<div class='box'><div class='heroimg'><img src='{image(v.get('foto'))}'></div><div class='summary'><div><div class='plate'>{esc(plate)}</div><div class='model'>{esc(v.get('modelo'))}</div></div><div class='right'>KM ATUAL<br><b>{km(v.get('km_atual'))}</b></div></div></div><div class='spacer'></div>",unsafe_allow_html=True)
  st.markdown(revision_appointment_banner(v),unsafe_allow_html=True)
  with st.form('saida'):
   st.markdown("<div class='fieldcallout'><div class='fieldtitle'>📍 DESTINO — PARA ONDE O VEÍCULO ESTÁ INDO?</div><div class='fieldhint'>Informe o local ou a finalidade do deslocamento.</div></div>",unsafe_allow_html=True)
   dest=st.text_input('Destino',placeholder='Ex.: Portaria Leste, Suzano, Buscar mecânico',label_visibility='collapsed')
   st.markdown("<div class='fieldcallout people'><div class='fieldtitle'>👥 OCUPANTES — QUEM ESTÁ INDO NO VEÍCULO?</div><div class='fieldhint'>Digite o nome das pessoas que estão usando o veículo.</div></div>",unsafe_allow_html=True)
   people=st.text_input('Ocupantes',placeholder='Ex.: Evandro, João, Carlos',label_visibility='collapsed')
   driver=st.text_input('👤 CONDUTOR — QUEM ESTÁ DIRIGINDO?',placeholder='Nome do condutor')
   ki=st.number_input('🚗 KM inicial',min_value=int(v.get('km_atual') or 0),value=int(v.get('km_atual') or 0),step=1); save=st.form_submit_button('➤ REGISTRAR SAÍDA')
  if save:
   if v.get('km_atual') is None and int(ki)<=0:st.error('Informe o KM atual do hodômetro para iniciar o controle deste veículo.')
   elif not dest.strip() or not people.strip() or not driver.strip():st.error('Informe o DESTINO, os OCUPANTES e o CONDUTOR antes de registrar a saída.')
   else:
    confirmar_km_inicial(plate,dest.strip(),people.strip(),int(ki),driver.strip())
 else:
  v=next((x for x in vs if x['placa']==plate),None); m=opened.get(plate)
  if not v or not m:setview('vehicles',filter='used')
  if st.button('‹ VOLTAR'):setview('vehicles',filter='used')
  st.markdown("<div class='title'>Registrar Retorno</div>",unsafe_allow_html=True)
  st.markdown(f"<div class='box'><div class='retcar'><img src='{image(v.get('foto'))}'><div><div class='plate'>{esc(plate)}</div><div class='model'>{esc(v.get('modelo'))}</div></div></div><div class='stats'><div class='stat'>KM INICIAL<b>{km(m.get('km_inicial'))}</b></div><div class='stat'>TEMPO EM USO<b>{duration(m.get('data_hora_saida'))}</b></div></div></div>",unsafe_allow_html=True)
  initial=int(m.get('km_inicial') or 0)
  suggested=gps_suggestion(m,q)
  if suggested is not None:
   st.info(f'GPS: {q.get("gps_km")} km estimados. Confira o hodômetro antes de confirmar o retorno.')
   if q.get('gps_gap')=='1': st.warning('Houve interrupção no GPS. A distância pode estar incompleta; informe o KM do hodômetro.')
  elif st.session_state.get('native_android'):
   gps_command('start',m)
  st.markdown(revision_appointment_banner(v),unsafe_allow_html=True)
  with st.form('retorno'):
   kf=st.number_input('🚗 KM final',min_value=initial,value=suggested if suggested is not None else initial,step=1,key=f'return_km_{m["id"]}_{suggested}'); st.caption(f'KM rodado: {km(max(0,int(kf)-initial))}'); save=st.form_submit_button('✓ CONFIRMAR RETORNO')
  if save:
   if int(kf)<=initial: st.error('O KM final deve ser maior que o KM inicial.')
   else:
    confirmar_km_final(plate,m['id'],initial,int(kf))

elif view=='panel':
 top('PAINEL DA FROTA · TEMPO REAL'); busy=len(opened)
 st.markdown(f"<div class='metrics'><div class='metric'>FROTA<b>{len(vs)}</b></div><div class='metric'>DISPONÍVEIS<b>{len(vs)-busy}</b></div><div class='metric'>EM USO<b>{busy}</b></div></div>",unsafe_allow_html=True)
 panelcards=[]
 for v in vs:
  m=opened.get(v['placa']); target,left,pct=revision(v); status=(f"<div class='pstatus busy'>● EM USO</div><div class='info'>👤 <b>Com:</b> {esc(m.get('pessoas'))}<br>📍 <b>Destino:</b> {esc(m.get('destino'))}<br>⌛ <b>Tempo em uso:</b> {duration(m.get('data_hora_saida'))}</div>" if m else "<div class='pstatus free'>● DISPONÍVEL</div>")
  revtxt='Revisão não cadastrada' if target is None else (f'REVISÃO VENCIDA HÁ {km(abs(left))}' if left<0 else f'FALTAM {km(left)}')
  panelcards.append(f"<div class='panelcard'><div class='panelmain'><img src='{image(v.get('foto'))}'><div>{status}<div class='plate'>{esc(v.get('placa'))}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='company'>{esc(units_by_plate[v['placa']])}</div><div class='info'>KM atual: <b>{km(v.get('km_atual'))}</b></div></div></div><div class='revbox'>{revtxt}</div>{revision_appointment_banner(v)}</div>")
 st.markdown("<div class='panelgrid'>"+''.join(panelcards)+"</div>",unsafe_allow_html=True)
 st.markdown("<meta http-equiv='refresh' content='15'>",unsafe_allow_html=True)

elif view=='admin':
 top('ADMINISTRAÇÃO DA FROTA')
 st.link_button('🔔 ATIVAR NOTIFICAÇÕES NESTE CELULAR', 'https://central-10sul.peachycrown16.chatgpt.site/alertas-gerencial',use_container_width=True)
 st.caption('Toque no botão, confirme sua identificação de responsável e permita as notificações. Não precisa copiar ou colar código.')
 painel,uso=st.columns(2)
 if painel.button('📊 PAINEL',key='admin_painel',use_container_width=True):setview('panel')
 if uso.button('🚗 INFORMAR USO',key='admin_informar_uso',use_container_width=True):setview('vehicles',filter='used')
 c1,c2,c3=st.columns(3)
 if c1.button('🔧 REVISÕES',use_container_width=True,type='primary' if tab=='revisao' else 'secondary'):setview('admin',tab='revisao')
 if c2.button('📋 HISTÓRICO',use_container_width=True,type='primary' if tab=='historico' else 'secondary'):setview('admin',tab='historico')
 if c3.button('🚙 VEÍCULOS',use_container_width=True,type='primary' if tab=='veiculos' else 'secondary'):setview('admin',tab='veiculos')
 if not vs:
  st.info('Nenhum veículo cadastrado nesta unidade.'); st.stop()
 if tab=='revisao':
  st.markdown("<div class='title'>Controle de revisão</div>",unsafe_allow_html=True)
  opts={f"{v['placa']} — {v.get('modelo','')} · {units_by_plate[v['placa']]}":v for v in vs}; sel=st.selectbox('Veículo',list(opts)); v=opts[sel]; target,left,pct=revision(v)
  if target is None: rclass=''; rbig='NÃO CADASTRADA'; rsmall='Cadastre a última revisão'
  elif left<0:rclass='over';rbig=f'VENCIDA<br>{km(abs(left))}';rsmall='KM PARA REVISÃO'
  elif left<=2000:rclass='alert';rbig=km(left);rsmall='KM PARA REVISÃO'
  else:rclass='';rbig=km(left);rsmall='KM PARA REVISÃO'
  st.markdown(f"<div class='revcard'><div class='revgrid'><div><div class='plate'>{esc(v['placa'])}</div><div class='model'>{esc(v.get('modelo'))}</div><div class='company'>{esc(units_by_plate[v['placa']])}</div><div class='info'>KM atual: <b>{km(v.get('km_atual'))}</b><br>Próxima revisão: <b>{km(target) if target is not None else '—'}</b></div></div><div class='remain {rclass}'>{rsmall}<b>{rbig}</b></div></div></div>",unsafe_allow_html=True)
  st.markdown(revision_appointment_banner(v),unsafe_allow_html=True)
  aviso=st.session_state.pop('aviso_conclusao_revisao',None)
  if aviso:
   st.success(aviso)
   st.session_state.pop('data_agendamento_'+v['placa'],None)
   st.session_state.pop('hora_agendamento_'+v['placa'],None)
  st.markdown("### 📅 Agendamento da próxima revisão")
  if st.session_state.get('aviso_agendamento_revisao'):
   st.success(st.session_state.pop('aviso_agendamento_revisao'))
  with st.form('agendar_revisao_'+v['placa']):
   data_agendada=st.date_input('Data agendada da próxima revisão',value=revision_appointment_date(v),format='DD/MM/YYYY',key='data_agendamento_'+v['placa'])
   hora_agendada=st.time_input('Horário agendado da revisão',value=revision_appointment_time(v),step=60,key='hora_agendamento_'+v['placa'])
   st.caption('Data e hora aparecerão em destaque para quem for usar este veículo. Horário de Brasília. Para remarcar, altere a data e o horário e salve.')
   salvar_agendamento=st.form_submit_button('💾 SALVAR / ATUALIZAR AGENDAMENTO')
   st.divider()
   st.markdown('**✅ Conclusão deste agendamento**')
   tem_agendamento=revision_appointment_date(v) is not None
   if not tem_agendamento:st.caption('Salve o agendamento para habilitar a confirmação da conclusão.')
   st.caption('Depois de realizar o serviço, informe a data e o KM reais. A confirmação encerra este agendamento e inicia a contagem para a próxima revisão.')
   concluida_data=st.date_input('Data em que a revisão foi realizada',value=None,max_value=datetime.now(TZ).date(),format='DD/MM/YYYY',disabled=not tem_agendamento)
   concluida_km=st.number_input('KM em que a revisão foi realizada',min_value=0,value=None,step=1,placeholder='Informe o KM do serviço',disabled=not tem_agendamento)
   confirma_conclusao=st.checkbox('Confirmo que a revisão foi realizada e conferi a data e o KM.',disabled=not tem_agendamento)
   concluir_revisao=st.form_submit_button('✅ CONFIRMAR CONCLUSÃO DA REVISÃO',type='primary',disabled=not tem_agendamento)
  if salvar_agendamento:
   if data_agendada is None or hora_agendada is None:
    st.error('Informe a data e o horário da próxima revisão.')
   else:
    valor_agendamento=data_agendada.isoformat()
    valor_hora=hora_agendada.isoformat()
    try:
     confirmado=DB.table('veiculos').update({'data_revisao_agendada':valor_agendamento,'hora_revisao_agendada':valor_hora,'atualizado_em':now()}).eq('placa',v['placa']).execute()
     if not confirmado.data or confirmado.data[0].get('data_revisao_agendada')!=valor_agendamento or confirmado.data[0].get('hora_revisao_agendada')!=valor_hora:
      st.error('Não foi possível confirmar o agendamento. Atualize e tente novamente.')
     else:
      st.session_state['aviso_agendamento_revisao']='Agendamento da próxima revisão salvo.'
      st.rerun()
    except Exception:
     st.error('Não foi possível salvar o agendamento. Tente novamente.')
  if concluir_revisao:
   try:
    if not confirma_conclusao or concluida_km is None:raise ValueError('Informe a data e o KM e marque a confirmação do serviço realizado.')
    valores=revision_completion_values(v,concluida_data,int(concluida_km))
    # One conditional update: never clear a newer appointment or overwrite
    # another user's revision if this page is stale.
    consulta=DB.table('veiculos').update({**valores,'atualizado_em':now()}).eq('placa',v['placa'])
    for campo in ('data_ultima_revisao','km_ultima_revisao','km_atual','data_revisao_agendada','hora_revisao_agendada'):
     consulta=consulta.is_(campo,'null') if v.get(campo) is None else consulta.eq(campo,v[campo])
    resultado=consulta.execute()
    if not resultado.data or any(resultado.data[0].get(campo)!=valor for campo,valor in valores.items()):
     st.error('O cadastro mudou ou a conclusão não pôde ser confirmada. Atualize a tela e confira antes de tentar novamente.')
    else:
     proxima=int(concluida_km)+int(v.get('intervalo_revisao') or 10000)
     st.session_state['aviso_conclusao_revisao']=f'Revisão concluída em {concluida_data.strftime("%d/%m/%Y")} aos {km(concluida_km)}. Agendamento encerrado. Próxima revisão: {km(proxima)}.'
     st.rerun()
   except ValueError as e:st.error(str(e))
   except Exception:st.error('Não foi possível registrar a conclusão. Confira o cadastro e tente novamente.')
  st.markdown('### ✏️ Cadastro / correção da última revisão')
  st.caption('Esta opção corrige o cadastro. Para encerrar um agendamento após realizar o serviço, use Confirmar conclusão.')
  with st.form('rev_'+v['placa']):
   dr=st.date_input('Data da última revisão',value=datetime.strptime(str(v['data_ultima_revisao'])[:10],'%Y-%m-%d').date() if v.get('data_ultima_revisao') else datetime.now(TZ).date()); raw_last=v.get('km_ultima_revisao'); default_last=int(raw_last) if raw_last is not None else int(v.get('km_atual') or 0); kr=st.number_input('KM da última revisão',min_value=0,value=default_last,step=1); st.caption(f'Próxima revisão: {km(int(kr)+int(v.get("intervalo_revisao") or 10000))}'); save=st.form_submit_button('💾 SALVAR / CORRIGIR ÚLTIMA REVISÃO')
  if save:
   DB.table('veiculos').update({'data_ultima_revisao':dr.isoformat(),'km_ultima_revisao':int(kr),'atualizado_em':now()}).eq('placa',v['placa']).execute(); st.success('Revisão atualizada.'); st.rerun()
 elif tab=='historico':
  st.markdown("<div class='title'>Histórico de movimentações</div>",unsafe_allow_html=True)
  hist=DB.table('movimentacoes').select('*').in_('placa',[v['placa'] for v in vs]).order('data_hora_saida',desc=True).limit(100).execute().data or []
  modelos_historico={v['placa']:str(v.get('modelo') or 'Modelo não informado') for v in vs}
  for m in hist:
   modelo_historico=modelos_historico.get(m.get('placa'),'Modelo não informado')
   end=m.get('data_hora_retorno'); kf=m.get('km_final'); rod=(int(kf)-int(m.get('km_inicial') or 0)) if kf is not None else None
   st.markdown(f"<div class='history'><div style='font-size:20px;font-weight:900;color:#10284a;line-height:1.3'>🚗 {esc(modelo_historico)}</div><div style='font-size:17px;font-weight:800;margin:5px 0'>PLACA: {esc(m.get('placa'))}</div>{esc(units_by_plate.get(m['placa']))} · {'🟠 EM USO' if m.get('status')=='EM USO' else '✅ DEVOLVIDO'}<br>👤 {esc(m.get('pessoas'))}<br>📍 {esc(m.get('destino'))}<br>Saída: {dateclock(m.get('data_hora_saida'))}<br>Retorno: {dateclock(end)}<br>⏱️ Tempo de uso: <b>{duration(m.get('data_hora_saida'),end) if end else duration(m.get('data_hora_saida'))}</b><br>KM inicial: {km(m.get('km_inicial'))} · KM final: {km(kf) if kf is not None else '—'} · Rodado: {km(rod) if rod is not None else '—'}</div>",unsafe_allow_html=True)
   with st.expander(f"Gerenciar lançamento #{m.get('id')} — {modelo_historico} · {m.get('placa')}"):
    if m.get('status')=='EM USO':
     editar_km_inicial_em_uso(m,'historico')
    st.warning('A exclusão é definitiva. Se este lançamento estiver EM USO, o veículo voltará a aparecer como disponível.')
    st.markdown("<div class='dangerbtn'>",unsafe_allow_html=True)
    if st.button('🗑️ EXCLUIR ESTA MOVIMENTAÇÃO',key=f"del_{m.get('id')}",use_container_width=True):
     try:
      DB.table('movimentacoes').delete().eq('id',m.get('id')).execute(); st.success('Movimentação excluída.'); st.rerun()
     except Exception as e: st.error(f'Não foi possível excluir: {e}')
    st.markdown('</div>',unsafe_allow_html=True)
 else:
  st.markdown("<div class='title'>Cadastro dos veículos</div>",unsafe_allow_html=True)
  for v in vs:
   st.markdown(f"<div class='history'><b>{esc(v.get('placa'))}</b> · {esc(v.get('modelo'))}<br><b>Unidade: {esc(units_by_plate[v['placa']])}</b><br>KM atual: {km(v.get('km_atual'))}</div>",unsafe_allow_html=True)
   with st.expander(f"Informar / corrigir KM — {v['placa']}"):
    if v['placa'] in opened:
     editar_km_inicial_em_uso(opened[v['placa']],'cadastro')
    else:
     with st.form('km_vehicle_'+v['placa']):
      current=st.number_input('KM atual do hodômetro',min_value=0,value=int(v.get('km_atual') or 0),step=1)
      save_km=st.form_submit_button('💾 SALVAR KM ATUAL')
     if save_km:
      if current<=0:st.error('Informe o KM atual do hodômetro.')
      elif v['placa'] in opened:st.error('Este veículo está em uso. Informe o KM no retorno da viagem.')
      else:
       DB.table('veiculos').update({'km_atual':int(current),'atualizado_em':now()}).eq('placa',v['placa']).execute();st.success('KM atualizado.');st.rerun()



