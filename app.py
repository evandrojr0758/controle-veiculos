import streamlit as st
import sqlite3
from pathlib import Path
from datetime import datetime
from PIL import Image
import base64, io

st.set_page_config(page_title='Controle de Veículos | 10 Sul', page_icon='🚙', layout='wide', initial_sidebar_state='collapsed')
BASE=Path(__file__).parent
DB=BASE/'veiculos.db'
ASSETS=BASE/'assets'
VEICULOS=[
 {'placa':'THC6A11','modelo':'FIAT STRADA','empresa':'SERVICE','foto':'THC6A11.png'},
 {'placa':'SJC0I24','modelo':'VW POLO','empresa':'SERVICE','foto':'SJC0I24.png'},
 {'placa':'TGM0B74','modelo':'CHEVROLET TRACKER','empresa':'SERVICE','foto':'TGM0B74.png'},
 {'placa':'QRM7G76','modelo':'FIAT DOBLÒ','empresa':'SERVICE','foto':'QRM7G76.png'},
]

def con():
 c=sqlite3.connect(DB, check_same_thread=False); c.row_factory=sqlite3.Row; return c

def init():
 c=con(); cur=c.cursor()
 cur.execute('''CREATE TABLE IF NOT EXISTS veiculos(placa TEXT PRIMARY KEY, modelo TEXT, empresa TEXT, foto TEXT, km_atual INTEGER DEFAULT 0, data_ultima_revisao TEXT, km_ultima_revisao INTEGER, intervalo_revisao INTEGER DEFAULT 10000)''')
 cur.execute('''CREATE TABLE IF NOT EXISTS viagens(id INTEGER PRIMARY KEY AUTOINCREMENT, placa TEXT, destino TEXT, pessoas TEXT, km_inicial INTEGER, saida TEXT, km_final INTEGER, retorno TEXT, status TEXT DEFAULT 'EM USO')''')
 for v in VEICULOS:
  cur.execute('''INSERT INTO veiculos(placa,modelo,empresa,foto) VALUES(?,?,?,?) ON CONFLICT(placa) DO UPDATE SET modelo=excluded.modelo, empresa=excluded.empresa, foto=excluded.foto''',(v['placa'],v['modelo'],v['empresa'],v['foto']))
 c.commit(); c.close()
init()

def img64(fname):
 p=ASSETS/fname
 im=Image.open(p).convert('RGBA'); im.thumbnail((720,520)); b=io.BytesIO(); im.save(b,'PNG',optimize=True)
 return base64.b64encode(b.getvalue()).decode()

def fmtkm(v): return f"{int(v):,}".replace(',','.')+' km' if v is not None else '—'
def agora(): return datetime.now().strftime('%d/%m/%Y %H:%M')

def dados():
 c=con(); vs=[dict(x) for x in c.execute('SELECT * FROM veiculos ORDER BY placa')]; abertas={x['placa']:dict(x) for x in c.execute("SELECT * FROM viagens WHERE status='EM USO' ORDER BY saida DESC")}; c.close(); return vs,abertas

st.markdown('''<style>
#MainMenu,footer,header{visibility:hidden}.stApp{background:#f5f8fc;color:#0c315d}.block-container{padding:1rem 1rem 4rem;max-width:1180px}
.hero{display:flex;align-items:center;gap:12px;margin:2px 0 18px}.brand{font-size:28px;font-weight:900;color:#073b70}.sub{font-size:13px;color:#536b86}
.card{background:white;border:1px solid #dce6f0;border-radius:16px;overflow:hidden;box-shadow:0 3px 12px #0d3b6610;margin-bottom:14px}.photo{display:block;height:260px;width:100%!important;max-width:none!important;object-fit:contain;object-position:center center;margin:0!important;padding:0!important;background:#fff!important}.pad{padding:14px}.plate{font-size:24px;font-weight:900;color:#0a3765}.model{font-weight:700}.company{font-size:13px;color:#60758c;margin-bottom:10px}.status{display:inline-block;padding:6px 10px;border-radius:20px;font-size:12px;font-weight:900}.ok{background:#dff7e9;color:#08783b}.busy{background:#fff0df;color:#d86500}.meta{font-size:14px;line-height:1.75;color:#203d5d}.rev{background:#f1f6fb;border-radius:10px;padding:9px;margin-top:8px}.tiny{font-size:12px;color:#6b7e92}
@media(max-width:640px){.block-container{padding:.65rem .65rem 3rem}.hero{margin-top:0}.brand{font-size:22px}.photo{height:165px}.plate{font-size:21px}.stButton button{min-height:48px;font-weight:800;border-radius:12px}}
</style>''',unsafe_allow_html=True)

st.markdown("<div class='hero'><div style='font-size:38px'>🔧</div><div><div class='brand'>10 SUL · CONTROLE DE VEÍCULOS</div><div class='sub'>SERVICE · saída, retorno e revisão preventiva</div></div></div>",unsafe_allow_html=True)
page=st.segmented_control('Navegação',['🚙 Veículos','📊 Painel','⚙️ Admin'],default='🚙 Veículos',label_visibility='collapsed')
vs,abertas=dados()

if page=='🚙 Veículos':
 filtro=st.segmented_control('Status',['Disponíveis','Em uso'],default='Disponíveis',label_visibility='collapsed')
 lista=[v for v in vs if (v['placa'] not in abertas)==(filtro=='Disponíveis')]
 if not lista: st.info('Nenhum veículo nesta situação.')
 cols=st.columns(2)
 for i,v in enumerate(lista):
  with cols[i%2]:
   aberto=abertas.get(v['placa']); status='EM USO' if aberto else 'DISPONÍVEL'; cls='busy' if aberto else 'ok'
   prox=(v['km_ultima_revisao']+v['intervalo_revisao']) if v['km_ultima_revisao'] is not None else None
   falta=(prox-v['km_atual']) if prox is not None else None
   extra=''
   if aberto: extra=f"<div class='meta'>👤 {aberto['pessoas']}<br>📍 {aberto['destino']}<br>🕐 Saída: {aberto['saida']}<br>🔢 KM inicial: {fmtkm(aberto['km_inicial'])}</div>"
   rev=f"Próxima revisão: <b>{fmtkm(prox)}</b>" if prox else 'Revisão ainda não cadastrada'
   st.markdown(f"<div class='card'><img class='photo' src='data:image/png;base64,{img64(v['foto'])}'><div class='pad'><span class='status {cls}'>{status}</span><div class='plate'>{v['placa']}</div><div class='model'>{v['modelo']}</div><div class='company'>{v['empresa']}</div><div class='meta'>🚗 KM atual: <b>{fmtkm(v['km_atual'])}</b></div><div class='rev'>🔧 {rev}"+(f"<br><span class='tiny'>Faltam {fmtkm(max(falta,0))}</span>" if falta is not None else '')+f"</div>{extra}</div></div>",unsafe_allow_html=True)
   if not aberto:
    if st.button('➜ USAR ESTE VEÍCULO',key='use'+v['placa'],use_container_width=True): st.session_state.form_saida=v['placa']; st.rerun()
   else:
    if st.button('↩ REGISTRAR RETORNO',key='ret'+v['placa'],use_container_width=True): st.session_state.form_retorno=v['placa']; st.rerun()

 placa=st.session_state.get('form_saida')
 if placa:
  v=next(x for x in vs if x['placa']==placa)
  st.divider(); st.subheader(f'Registrar Saída · {placa}')
  st.image(str(ASSETS/v['foto']),use_container_width=True)
  with st.form('saida'):
   destino=st.text_input('📍 Para onde está indo?'); pessoas=st.text_input('👥 Quem está indo?'); km=st.number_input('🔢 KM inicial',min_value=0,step=1,value=int(v['km_atual'] or 0)); st.caption('🕐 Data e hora serão registradas automaticamente.')
   ok=st.form_submit_button('REGISTRAR SAÍDA',use_container_width=True)
   if ok:
    if not destino.strip() or not pessoas.strip(): st.error('Informe o destino e quem está indo.')
    else:
     c=con(); c.execute('INSERT INTO viagens(placa,destino,pessoas,km_inicial,saida,status) VALUES(?,?,?,?,?,?)',(placa,destino.strip(),pessoas.strip(),int(km),agora(),'EM USO')); c.execute('UPDATE veiculos SET km_atual=? WHERE placa=?',(int(km),placa)); c.commit(); c.close(); st.session_state.pop('form_saida',None); st.success('Saída registrada.'); st.rerun()

 placa=st.session_state.get('form_retorno')
 if placa and placa in abertas:
  a=abertas[placa]; st.divider(); st.subheader(f'Registrar Retorno · {placa}'); st.write(f"**Destino:** {a['destino']}  \n**Quem foi:** {a['pessoas']}  \n**KM inicial:** {fmtkm(a['km_inicial'])}")
  with st.form('retorno'):
   kf=st.number_input('🔢 KM final',min_value=int(a['km_inicial']),step=1,value=int(a['km_inicial'])); st.metric('KM rodado',fmtkm(int(kf)-int(a['km_inicial']))); ok=st.form_submit_button('✓ CONFIRMAR RETORNO',use_container_width=True)
   if ok:
    c=con(); c.execute("UPDATE viagens SET km_final=?, retorno=?, status='DEVOLVIDO' WHERE id=?",(int(kf),agora(),a['id'])); c.execute('UPDATE veiculos SET km_atual=? WHERE placa=?',(int(kf),placa)); c.commit(); c.close(); st.session_state.pop('form_retorno',None); st.success('Retorno registrado.'); st.rerun()

elif page=='📊 Painel':
 st.subheader('Acompanhamento em tempo real'); c1,c2,c3=st.columns(3); c1.metric('Total',len(vs)); c2.metric('Disponíveis',len(vs)-len(abertas)); c3.metric('Em uso',len(abertas))
 for v in vs:
  a=abertas.get(v['placa']); prox=(v['km_ultima_revisao']+10000) if v['km_ultima_revisao'] is not None else None
  with st.container(border=True):
   x,y=st.columns([1,2]); x.image(str(ASSETS/v['foto']),use_container_width=True); y.markdown(f"### {v['placa']} · {v['modelo']}"); y.write(('🟠 **EM USO**' if a else '🟢 **DISPONÍVEL**')+f"  \nKM atual: **{fmtkm(v['km_atual'])}**")
   if prox: y.write(f"Próxima revisão: **{fmtkm(prox)}** · faltam **{fmtkm(max(prox-v['km_atual'],0))}**")
   if a: y.write(f"👤 {a['pessoas']}  \n📍 {a['destino']}  \n🕐 {a['saida']}")

else:
 st.subheader('Cadastro de revisão preventiva'); placa=st.selectbox('Veículo',[v['placa'] for v in vs]); v=next(x for x in vs if x['placa']==placa)
 with st.form('rev'):
  data=st.date_input('Data da última revisão'); kmr=st.number_input('KM da última revisão',min_value=0,step=1,value=int(v['km_ultima_revisao'] or v['km_atual'] or 0)); st.info(f'Próxima revisão será em {fmtkm(int(kmr)+10000)}')
  if st.form_submit_button('SALVAR REVISÃO',use_container_width=True):
   c=con(); c.execute('UPDATE veiculos SET data_ultima_revisao=?, km_ultima_revisao=?, intervalo_revisao=10000 WHERE placa=?',(data.strftime('%d/%m/%Y'),int(kmr),placa)); c.commit(); c.close(); st.success('Revisão atualizada.'); st.rerun()
