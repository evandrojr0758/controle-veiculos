import streamlit as st
from pathlib import Path
from datetime import datetime, timezone, timedelta
from PIL import Image
from supabase import create_client
import base64, io, html

st.set_page_config(page_title='Controle de Veículos | 10 Sul', page_icon='🚙', layout='centered', initial_sidebar_state='collapsed')
BASE=Path(__file__).parent; ASSETS=BASE/'assets'; TZ=timezone(timedelta(hours=-3))
@st.cache_resource
def get_db(): return create_client(st.secrets['SUPABASE_URL'],st.secrets['SUPABASE_KEY'])
DB=get_db()
def esc(x): return html.escape(str(x or ''))
def nowiso(): return datetime.now(TZ).isoformat()
def km(x): return f"{int(x or 0):,}".replace(',','.')+' km'
def when(x,short=False):
    try:
        d=datetime.fromisoformat(str(x).replace('Z','+00:00')).astimezone(TZ); return d.strftime('%H:%M' if short else '%d/%m/%Y %H:%M')
    except:return '—'
def duration(x):
    try:
        d=datetime.fromisoformat(str(x).replace('Z','+00:00')).astimezone(TZ); mins=max(0,int((datetime.now(TZ)-d).total_seconds()/60)); return f'{mins//60}h {mins%60:02d}min' if mins>=60 else f'{mins} min'
    except:return '—'
def img(name):
    im=Image.open(ASSETS/name).convert('RGBA'); im.thumbnail((640,440)); b=io.BytesIO(); im.save(b,'PNG',optimize=True); return base64.b64encode(b.getvalue()).decode()
def load():
    vs=DB.table('veiculos').select('*').order('placa').execute().data or []
    ms=DB.table('movimentacoes').select('*').eq('status','EM USO').order('data_hora_saida',desc=True).execute().data or []
    return vs,{m['placa']:m for m in ms}
def revision(v):
    if v.get('km_ultima_revisao') is None:return None,None,0
    start=int(v['km_ultima_revisao']); target=start+int(v.get('intervalo_revisao') or 10000); current=int(v.get('km_atual') or 0)
    pct=max(0,min(100,int(((current-start)/10000)*100))); return target,target-current,pct

st.markdown('''<style>
#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
html,body,[class*="css"]{font-family:Inter,Arial,sans-serif}.stApp{background:#f4f7fb;color:#173b5e}.block-container{max-width:430px;padding:12px 10px 70px!important}
[data-testid="stVerticalBlock"]{gap:.45rem}.topbar{height:52px;background:#fff;border-radius:13px;display:flex;align-items:center;padding:0 13px;margin-bottom:10px;box-shadow:0 2px 12px rgba(15,55,90,.07)}.mark{width:31px;height:31px;border-radius:9px;background:#0a67ad;color:white;display:flex;align-items:center;justify-content:center;font-size:17px;margin-right:9px}.brand{font-weight:950;font-size:17px;color:#083b69;letter-spacing:-.3px}.brand span{display:block;font-size:8px;color:#718399;letter-spacing:.8px;margin-top:2px}
div[data-testid="stSegmentedControl"]{background:#e8eef5;border-radius:11px;padding:3px}div[data-testid="stSegmentedControl"] button{min-height:36px!important;font-size:11px!important;font-weight:800!important;border-radius:8px!important}
.stButton>button,.stFormSubmitButton>button{width:100%;border-radius:9px!important;min-height:39px!important;font-size:10px!important;font-weight:900!important;text-transform:uppercase;box-shadow:none!important}.stButton>button[kind="secondary"]{border-color:#dce5ee}
.vehicle{background:#fff;border:1px solid #dfe7ef;border-radius:13px;overflow:hidden;box-shadow:0 3px 12px rgba(21,58,88,.06);margin-bottom:3px}.photo{height:112px;position:relative;background:#fff;display:flex;align-items:center;justify-content:center}.photo img{width:100%;height:100%;object-fit:contain;padding:2px}.badge{position:absolute;top:6px;right:6px;padding:4px 7px;border-radius:12px;color:#fff;font-size:7px;font-weight:950;letter-spacing:.2px}.available{background:#13a865}.used{background:#f27b22}.vbody{padding:8px 9px 9px}.plate{font-size:16px;font-weight:950;color:#0b3e6d;line-height:1}.model{font-size:9px;font-weight:850;color:#355875;margin-top:4px}.company{font-size:8px;color:#91a0ad;margin:2px 0 7px}.info{font-size:9px;line-height:1.65;color:#526b81}.info strong{color:#143e62}.revline{display:flex;justify-content:space-between;font-size:8px;color:#5f768a;margin-top:6px}.track{height:5px;background:#e6edf3;border-radius:8px;overflow:hidden;margin-top:3px}.fill{height:100%;background:#12b678;border-radius:8px}.usebox{font-size:9px;background:#fff7f0;border-radius:7px;padding:6px;margin-top:5px;color:#765339}.title{font-size:18px;font-weight:950;color:#093e70;margin:4px 0 10px}.back{font-size:11px;color:#315a7d}.hero{background:#fff;border:1px solid #dfe7ef;border-radius:14px;overflow:hidden;box-shadow:0 3px 12px rgba(21,58,88,.06)}.heroimg{height:190px;display:flex;align-items:center;justify-content:center}.heroimg img{width:100%;height:100%;object-fit:contain}.herodata{background:#eef7ff;padding:10px 12px;display:grid;grid-template-columns:1.25fr 1fr;gap:8px}.herodata .plate{font-size:19px}.right{text-align:right;font-size:8px;color:#71879a}.right b{font-size:11px;color:#163f63}.section{font-size:11px;font-weight:900;color:#244d70;margin:12px 0 3px}.auto{font-size:9px;color:#778a9b;margin-top:-3px}.retcard{background:#fff;border:1px solid #dfe7ef;border-radius:14px;padding:10px}.retcar{display:flex;align-items:center;gap:9px;background:#eef7ff;border-radius:9px;padding:7px}.retcar img{width:105px;height:68px;object-fit:contain}.stats{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:8px 0}.stat{background:#f2f6fa;border-radius:8px;padding:8px;text-align:center;font-size:8px;color:#718499}.stat b{display:block;font-size:13px;color:#143f63;margin-top:2px}.good b{color:#0b9a61}.panelrow{background:#fff;border:1px solid #e0e7ee;border-radius:12px;padding:9px;margin-bottom:7px}.panelrow img{width:100%;height:80px;object-fit:contain}
@media(min-width:700px){.block-container{max-width:860px}.photo{height:205px}.vehicle .plate{font-size:21px}.info{font-size:12px}.model{font-size:12px}.company{font-size:10px}}
</style>''',unsafe_allow_html=True)
st.markdown("<div class='topbar'><div class='mark'>🔧</div><div class='brand'>10 SUL<span>CONTROLE DE VEÍCULOS · SERVICE</span></div></div>",unsafe_allow_html=True)
try: vehicles,opened=load()
except Exception as ex: st.error('Não foi possível conectar ao banco online.');st.caption(str(ex));st.stop()

screen=st.session_state.get('screen','home')
if screen=='home':
    area=st.segmented_control('area',['🚙 VEÍCULOS','📊 PAINEL','⚙️ ADMIN'],default='🚙 VEÍCULOS',label_visibility='collapsed')
    if area=='🚙 VEÍCULOS':
        available=sum(v['placa'] not in opened for v in vehicles); inuse=len(opened)
        status=st.segmented_control('status',[f'DISPONÍVEIS  {available}',f'EM USO  {inuse}'],default=f'DISPONÍVEIS  {available}',label_visibility='collapsed')
        show_used=status.startswith('EM USO'); items=[v for v in vehicles if (v['placa'] in opened)==show_used]
        if not items:st.info('Nenhum veículo nesta situação.')
        cols=st.columns(2,gap='small')
        for i,v in enumerate(items):
            m=opened.get(v['placa']);target,left,pct=revision(v); badge='EM USO' if m else 'DISPONÍVEL'; cls='used' if m else 'available'
            if m:
                details=f"<div class='usebox'>👤 <strong>{esc(m['pessoas'])}</strong><br>📍 {esc(m['destino'])}<br>◷ {when(m['data_hora_saida'],True)} · {duration(m['data_hora_saida'])}<br>🚗 {km(m['km_inicial'])}</div>"
            else:
                details=f"<div class='info'>🚗 KM atual<br><strong>{km(v.get('km_atual'))}</strong><br>🔧 Próxima revisão<br><strong>{km(target) if target else 'Não cadastrada'}</strong></div>"
            progress=f"<div class='revline'><span>Revisão</span><span>{pct}%</span></div><div class='track'><div class='fill' style='width:{pct}%'></div></div>" if target else ''
            with cols[i%2]:
                st.markdown(f"<div class='vehicle'><div class='photo'><img src='data:image/png;base64,{img(v['foto'])}'><span class='badge {cls}'>{badge}</span></div><div class='vbody'><div class='plate'>{esc(v['placa'])}</div><div class='model'>{esc(v['modelo'])}</div><div class='company'>{esc(v['empresa'])}</div>{details}{progress}</div></div>",unsafe_allow_html=True)
                if st.button('↩ REGISTRAR RETORNO' if m else '➜ USAR ESTE VEÍCULO',key='car_'+v['placa'],use_container_width=True):
                    st.session_state.plate=v['placa'];st.session_state.screen='return' if m else 'out';st.rerun()
    elif area=='📊 PAINEL':
        st.markdown("<div class='title'>Painel em tempo real</div>",unsafe_allow_html=True)
        a,b,c=st.columns(3);a.metric('Frota',len(vehicles));b.metric('Livres',len(vehicles)-len(opened));c.metric('Em uso',len(opened))
        if st.button('↻ ATUALIZAR PAINEL',use_container_width=True):st.rerun()
        for v in vehicles:
            m=opened.get(v['placa']);target,left,pct=revision(v)
            st.markdown(f"<div class='panelrow'><div style='display:grid;grid-template-columns:100px 1fr;gap:9px;align-items:center'><img src='data:image/png;base64,{img(v['foto'])}'><div><div class='plate'>{esc(v['placa'])}</div><div class='model'>{esc(v['modelo'])}</div><div class='info'>{'🟠 EM USO · '+esc(m['pessoas'])+' · '+esc(m['destino']) if m else '🟢 DISPONÍVEL'}<br>KM: <strong>{km(v.get('km_atual'))}</strong>{'<br>Revisão: <strong>'+km(target)+'</strong>' if target else ''}</div></div></div></div>",unsafe_allow_html=True)
    else:
        st.markdown("<div class='title'>Revisão preventiva</div>",unsafe_allow_html=True)
        p=st.selectbox('Veículo',[v['placa'] for v in vehicles]);v=next(x for x in vehicles if x['placa']==p)
        with st.form('adminrev'):
            d=st.date_input('Data da última revisão');kr=st.number_input('KM da última revisão',min_value=0,step=1,value=int(v.get('km_ultima_revisao') or v.get('km_atual') or 0));st.info(f'Próxima revisão: {km(int(kr)+10000)}')
            if st.form_submit_button('SALVAR REVISÃO',use_container_width=True):DB.table('veiculos').update({'data_ultima_revisao':d.isoformat(),'km_ultima_revisao':int(kr),'intervalo_revisao':10000,'atualizado_em':nowiso()}).eq('placa',p).execute();st.success('Revisão atualizada.');st.rerun()

elif screen=='out':
    p=st.session_state.get('plate');v=next((x for x in vehicles if x['placa']==p),None)
    if not v or p in opened:st.session_state.screen='home';st.rerun()
    if st.button('‹ VOLTAR',use_container_width=True):st.session_state.screen='home';st.rerun()
    st.markdown("<div class='title'>Registrar Saída</div>",unsafe_allow_html=True);target,left,pct=revision(v)
    st.markdown(f"<div class='hero'><div class='heroimg'><img src='data:image/png;base64,{img(v['foto'])}'></div><div class='herodata'><div><div class='plate'>{esc(p)}</div><div class='model'>{esc(v['modelo'])}</div><div class='company'>{esc(v['empresa'])}</div></div><div class='right'>KM ATUAL<br><b>{km(v.get('km_atual'))}</b><br><br>PRÓXIMA REVISÃO<br><b>{km(target) if target else '—'}</b></div></div></div>",unsafe_allow_html=True)
    if target:st.progress(pct/100,text=f'Revisão preventiva · {pct}%')
    with st.form('saida'):
        dest=st.text_input('📍 Para onde está indo?',placeholder='Ex.: Suzano - Portaria 2');people=st.text_input('👥 Quem está indo?',placeholder='Informe o(s) nome(s)');ki=st.number_input('🚗 KM inicial',min_value=int(v.get('km_atual') or 0),value=int(v.get('km_atual') or 0),step=1);st.text_input('▣ Data / hora',value=datetime.now(TZ).strftime('%d/%m/%Y  %H:%M'),disabled=True);st.caption('Data e hora são registradas automaticamente.');save=st.form_submit_button('➤ REGISTRAR SAÍDA',use_container_width=True)
    if save:
        if not dest.strip() or not people.strip():st.error('Informe o destino e quem está indo.')
        else:
            try:
                DB.table('movimentacoes').insert({'placa':p,'destino':dest.strip(),'pessoas':people.strip(),'km_inicial':int(ki),'data_hora_saida':nowiso(),'status':'EM USO'}).execute();DB.table('veiculos').update({'km_atual':int(ki),'atualizado_em':nowiso()}).eq('placa',p).execute();st.session_state.screen='home';st.rerun()
            except Exception:st.error('Não foi possível registrar a saída. O veículo pode já estar em uso.')

elif screen=='return':
    p=st.session_state.get('plate');m=opened.get(p);v=next((x for x in vehicles if x['placa']==p),None)
    if not m or not v:st.session_state.screen='home';st.rerun()
    if st.button('‹ VOLTAR',use_container_width=True):st.session_state.screen='home';st.rerun()
    st.markdown("<div class='title'>Registrar Retorno</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='retcard'><div class='retcar'><img src='data:image/png;base64,{img(v['foto'])}'><div><div class='plate'>{esc(p)}</div><div class='model'>{esc(v['modelo'])}</div><div class='company'>{esc(v['empresa'])}</div></div></div><div class='stats'><div class='stat'>KM INICIAL<b>{km(m['km_inicial'])}</b></div><div class='stat'>SAÍDA<b>{when(m['data_hora_saida'],True)}</b></div></div><div class='info'>👤 <strong>{esc(m['pessoas'])}</strong><br>📍 {esc(m['destino'])}</div></div>",unsafe_allow_html=True)
    with st.form('retorno'):
        kf=st.number_input('🚗 KM final',min_value=int(m['km_inicial']),value=int(m['km_inicial']),step=1);run=int(kf)-int(m['km_inicial']);c1,c2=st.columns(2);c1.metric('KM rodado',km(run));c2.metric('Tempo',duration(m['data_hora_saida']));save=st.form_submit_button('✓ CONFIRMAR RETORNO',use_container_width=True)
    if save:
        DB.table('movimentacoes').update({'km_final':int(kf),'data_hora_retorno':nowiso(),'status':'DEVOLVIDO'}).eq('id',m['id']).execute();DB.table('veiculos').update({'km_atual':int(kf),'atualizado_em':nowiso()}).eq('placa',p).execute();st.session_state.screen='home';st.rerun()
