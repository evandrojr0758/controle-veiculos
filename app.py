import streamlit as st
from pathlib import Path
from datetime import datetime, timezone, timedelta
from PIL import Image
from supabase import create_client
import base64, io, html

st.set_page_config(page_title='Controle de Veículos | 10 Sul', page_icon='🚙', layout='centered', initial_sidebar_state='collapsed')
BASE=Path(__file__).parent; ASSETS=BASE/'assets'; TZ=timezone(timedelta(hours=-3))
@st.cache_resource
def db(): return create_client(st.secrets['SUPABASE_URL'],st.secrets['SUPABASE_KEY'])
DB=db()
def e(x): return html.escape(str(x or ''))
def nowiso(): return datetime.now(TZ).isoformat()
def km(x): return f"{int(x or 0):,}".replace(',','.')+' km'
def dt(x,only_time=False):
    try:
        d=datetime.fromisoformat(str(x).replace('Z','+00:00')).astimezone(TZ); return d.strftime('%H:%M' if only_time else '%d/%m/%Y %H:%M')
    except: return '—'
def elapsed(x):
    try:
        d=datetime.fromisoformat(str(x).replace('Z','+00:00')).astimezone(TZ); m=max(0,int((datetime.now(TZ)-d).total_seconds()//60)); return f'{m//60}h {m%60:02d}min' if m>=60 else f'{m}min'
    except: return '—'
def b64(name):
    im=Image.open(ASSETS/name).convert('RGBA'); im.thumbnail((620,420)); out=io.BytesIO(); im.save(out,'PNG',optimize=True); return base64.b64encode(out.getvalue()).decode()
def load():
    v=DB.table('veiculos').select('*').order('placa').execute().data or []
    m=DB.table('movimentacoes').select('*').eq('status','EM USO').order('data_hora_saida',desc=True).execute().data or []
    return v,{x['placa']:x for x in m}
def rev(v):
    if v.get('km_ultima_revisao') is None:return None,None,0
    ini=int(v['km_ultima_revisao']); prox=ini+int(v.get('intervalo_revisao') or 10000); atual=int(v.get('km_atual') or 0); pct=max(0,min(100,round((atual-ini)/(prox-ini)*100))) if prox>ini else 100
    return prox,prox-atual,pct

st.markdown('''<style>
#MainMenu,footer,header,[data-testid="stToolbar"]{display:none!important}.stApp{background:#f3f7fb}.block-container{max-width:470px;padding:.65rem .65rem 5rem!important}.stButton>button{border-radius:9px;min-height:42px;font-weight:800;border:1px solid #d8e2ec}.top{display:flex;align-items:center;gap:9px;margin:2px 2px 12px}.logo{font-size:25px}.brand{font-size:20px;line-height:1;font-weight:950;color:#063c70}.brand small{display:block;font-size:9px;font-weight:700;margin-top:5px;color:#536b82}.tabs{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0 12px}.tab{padding:11px;border-radius:8px;text-align:center;font-size:13px;font-weight:850;background:#e8eef5;color:#153e65}.tab.on{background:#0868bd;color:white}.grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.car{background:white;border:1px solid #dbe5ef;border-radius:12px;overflow:hidden;box-shadow:0 2px 7px #173c5f10;margin-bottom:4px}.picwrap{height:128px;position:relative;background:#fff;display:flex;align-items:center;justify-content:center}.pic{width:100%;height:100%;object-fit:contain;padding:3px}.badge{position:absolute;right:6px;top:6px;border-radius:12px;padding:4px 7px;font-size:9px;font-weight:950;color:white}.green{background:#16a765}.orange{background:#f47b20}.body{padding:8px}.plate{font-size:17px;font-weight:950;color:#093c70;line-height:1.05}.model{font-size:10px;font-weight:850;color:#244a70;margin-top:3px}.company{font-size:9px;color:#75889b;margin-bottom:8px}.line{font-size:10px;color:#24425e;line-height:1.7}.line b{color:#0b3d69}.progress{height:6px;background:#e6edf3;border-radius:8px;overflow:hidden;margin:5px 0 1px}.bar{height:100%;background:#10b777;border-radius:8px}.pctl{font-size:8px;text-align:right;color:#647b90}.action{margin-top:7px;padding:9px 3px;text-align:center;border-radius:7px;font-size:9px;font-weight:950;color:white;background:#0765ae}.action.ret{background:#fff0e4;color:#e46c13}.formhead{display:flex;align-items:center;justify-content:space-between;color:#083d70;font-weight:950;font-size:17px;margin:5px 0 10px}.formhero{background:white;border-radius:12px;border:1px solid #dce6ef;overflow:hidden;margin-bottom:10px}.formhero img{width:100%;height:205px;object-fit:contain}.summary{display:grid;grid-template-columns:1.5fr 1fr;background:#eef7ff;padding:9px}.summary .plate{font-size:18px}.sumright{font-size:9px;color:#567087}.fieldnote{font-size:10px;color:#61798e}.returnbox{background:white;border:1px solid #dbe5ef;border-radius:12px;padding:10px}.returncar{display:flex;gap:9px;align-items:center;background:#edf7ff;border-radius:9px;padding:7px}.returncar img{width:95px;height:65px;object-fit:contain}.twostat{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}.stat{background:#f2f7fb;border-radius:8px;text-align:center;padding:9px;color:#36536d;font-size:10px}.stat b{display:block;color:#087653;font-size:14px}.desktopnav{margin-bottom:8px}
@media(min-width:700px){.block-container{max-width:980px}.picwrap{height:220px}.plate{font-size:22px}.model,.line{font-size:13px}.company{font-size:11px}.action{font-size:12px}.brand{font-size:26px}}
</style>''',unsafe_allow_html=True)
st.markdown("<div class='top'><div class='logo'>🔧</div><div class='brand'>10 SUL <small>CONTROLE DE VEÍCULOS · SERVICE</small></div></div>",unsafe_allow_html=True)
try: vehicles,openm=load()
except Exception as ex: st.error('Falha ao conectar ao banco online.');st.caption(str(ex));st.stop()

mode=st.session_state.get('screen','home')
if mode=='home':
    page=st.segmented_control('Área',['🚙 Veículos','📊 Painel','⚙️ Admin'],default='🚙 Veículos',label_visibility='collapsed')
    if page=='🚙 Veículos':
        av=sum(1 for v in vehicles if v['placa'] not in openm); busy=len(openm)
        filt=st.segmented_control('Situação',[f'🚗 Disponíveis ({av})',f'🚙 Em uso ({busy})'],default=f'🚗 Disponíveis ({av})',label_visibility='collapsed')
        wantbusy='Em uso' in filt; lst=[v for v in vehicles if (v['placa'] in openm)==wantbusy]
        if not lst: st.info('Nenhum veículo nesta situação.')
        cols=st.columns(2,gap='small')
        for i,v in enumerate(lst):
            a=openm.get(v['placa']); prox,falta,pct=rev(v); badge='EM USO' if a else 'DISPONÍVEL'; bc='orange' if a else 'green'
            info=(f"<div class='line'>👤 <b>{e(a['pessoas'])}</b><br>📍 {e(a['destino'])}<br>◷ Saída: {dt(a['data_hora_saida'],True)}<br>⌛ {elapsed(a['data_hora_saida'])} em uso<br>🚗 KM inicial: {km(a['km_inicial'])}</div>" if a else f"<div class='line'>🚗 KM atual: <b>{km(v.get('km_atual'))}</b><br>🔧 Próxima revisão: <b>{km(prox) if prox else 'não cadastrada'}</b></div>")
            prog=(f"<div class='progress'><div class='bar' style='width:{pct}%'></div></div><div class='pctl'>{pct}%</div>" if prox else '')
            with cols[i%2]:
                st.markdown(f"<div class='car'><div class='picwrap'><img class='pic' src='data:image/png;base64,{b64(v['foto'])}'><span class='badge {bc}'>{badge}</span></div><div class='body'><div class='plate'>{e(v['placa'])}</div><div class='model'>{e(v['modelo'])}</div><div class='company'>{e(v['empresa'])}</div>{info}{prog}</div></div>",unsafe_allow_html=True)
                label='↩ REGISTRAR RETORNO' if a else '➜ USAR ESTE VEÍCULO'
                if st.button(label,key='a'+v['placa'],use_container_width=True): st.session_state.screen='return' if a else 'out';st.session_state.plate=v['placa'];st.rerun()
    elif page=='📊 Painel':
        st.subheader('Painel em tempo real'); c1,c2,c3=st.columns(3);c1.metric('Frota',len(vehicles));c2.metric('Disponíveis',len(vehicles)-len(openm));c3.metric('Em uso',len(openm))
        if st.button('↻ ATUALIZAR',use_container_width=True):st.rerun()
        for v in vehicles:
            a=openm.get(v['placa']);prox,falta,pct=rev(v)
            with st.container(border=True):
                x,y=st.columns([1,2]);x.image(str(ASSETS/v['foto']),use_container_width=True);y.markdown(f"**{v['placa']} · {v['modelo']}**");y.write('🟠 EM USO' if a else '🟢 DISPONÍVEL');y.caption(f"KM atual: {km(v.get('km_atual'))}")
                if a:y.caption(f"{a['pessoas']} · {a['destino']} · {elapsed(a['data_hora_saida'])}")
                if prox:y.progress(pct/100,text=f"Revisão {km(prox)} · {pct}%")
    else:
        st.subheader('Revisão preventiva');p=st.selectbox('Veículo',[v['placa'] for v in vehicles]);v=next(x for x in vehicles if x['placa']==p)
        with st.form('revision'):
            d=st.date_input('Data da última revisão');kr=st.number_input('KM da última revisão',min_value=0,step=1,value=int(v.get('km_ultima_revisao') or v.get('km_atual') or 0));st.info(f'Próxima revisão: {km(int(kr)+10000)}')
            if st.form_submit_button('SALVAR',use_container_width=True):DB.table('veiculos').update({'data_ultima_revisao':d.isoformat(),'km_ultima_revisao':int(kr),'intervalo_revisao':10000,'atualizado_em':nowiso()}).eq('placa',p).execute();st.success('Revisão salva.');st.rerun()
elif mode=='out':
    p=st.session_state.plate;v=next((x for x in vehicles if x['placa']==p),None)
    if not v or p in openm:st.session_state.screen='home';st.rerun()
    if st.button('‹  Registrar Saída',use_container_width=True):st.session_state.screen='home';st.rerun()
    prox,falta,pct=rev(v)
    st.markdown(f"<div class='formhero'><img src='data:image/png;base64,{b64(v['foto'])}'><div class='summary'><div><div class='plate'>{e(p)}</div><div class='model'>{e(v['modelo'])}</div><div class='company'>{e(v['empresa'])}</div></div><div class='sumright'>KM atual<br><b>{km(v.get('km_atual'))}</b><br><br>Próxima revisão<br><b>{km(prox) if prox else '—'}</b></div></div></div>",unsafe_allow_html=True)
    if prox:st.progress(pct/100,text=f'Revisão preventiva · {pct}%')
    with st.form('out'):
        dest=st.text_input('📍 Para onde está indo?',placeholder='Suzano - Portaria 2');people=st.text_input('👥 Quem está indo?',placeholder='Evandro / João');ki=st.number_input('🚗 KM inicial',min_value=int(v.get('km_atual') or 0),step=1,value=int(v.get('km_atual') or 0));st.text_input('▣ Data / hora (automático)',value=datetime.now(TZ).strftime('%d/%m/%Y  %H:%M'),disabled=True)
        ok=st.form_submit_button('➤ REGISTRAR SAÍDA',use_container_width=True)
    if ok:
        if not dest.strip() or not people.strip():st.error('Informe o destino e quem está indo.')
        else:
            try:DB.table('movimentacoes').insert({'placa':p,'destino':dest.strip(),'pessoas':people.strip(),'km_inicial':int(ki),'data_hora_saida':nowiso(),'status':'EM USO'}).execute();DB.table('veiculos').update({'km_atual':int(ki),'atualizado_em':nowiso()}).eq('placa',p).execute();st.session_state.screen='home';st.rerun()
            except Exception:st.error('Não foi possível registrar a saída. Atualize e tente novamente.')
elif mode=='return':
    p=st.session_state.plate;a=openm.get(p);v=next((x for x in vehicles if x['placa']==p),None)
    if not a or not v:st.session_state.screen='home';st.rerun()
    if st.button('↩  Registrar Retorno',use_container_width=True):st.session_state.screen='home';st.rerun()
    st.markdown(f"<div class='returnbox'><div class='returncar'><img src='data:image/png;base64,{b64(v['foto'])}'><div><div class='plate'>{e(p)}</div><div class='model'>{e(v['modelo'])}</div><div class='company'>{e(v['empresa'])}</div></div></div><div class='twostat'><div class='stat'>KM inicial<b>{km(a['km_inicial'])}</b></div><div class='stat'>Saída<b>{dt(a['data_hora_saida'],True)}</b></div></div></div>",unsafe_allow_html=True)
    with st.form('ret'):
        kf=st.number_input('▣ KM final',min_value=int(a['km_inicial']),step=1,value=int(a['km_inicial']));rod=int(kf)-int(a['km_inicial']);c1,c2=st.columns(2);c1.metric('🟢 KM rodado',km(rod));c2.metric('◷ Tempo de utilização',elapsed(a['data_hora_saida']));ok=st.form_submit_button('✓ CONFIRMAR RETORNO',use_container_width=True)
    if ok:DB.table('movimentacoes').update({'km_final':int(kf),'data_hora_retorno':nowiso(),'status':'DEVOLVIDO'}).eq('id',a['id']).execute();DB.table('veiculos').update({'km_atual':int(kf),'atualizado_em':nowiso()}).eq('placa',p).execute();st.session_state.screen='home';st.rerun()
