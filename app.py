import streamlit as st
from pathlib import Path
from datetime import datetime, timezone, timedelta
from PIL import Image
from supabase import create_client
import base64, io

st.set_page_config(page_title='Controle de Veículos | 10 Sul', page_icon='🚙', layout='wide', initial_sidebar_state='collapsed')
BASE = Path(__file__).parent
ASSETS = BASE / 'assets'
TZ_BR = timezone(timedelta(hours=-3))

@st.cache_resource
def get_db():
    return create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])

db = get_db()

def img64(fname):
    p = ASSETS / fname
    im = Image.open(p).convert('RGBA')
    im.thumbnail((720, 520))
    b = io.BytesIO()
    im.save(b, 'PNG', optimize=True)
    return base64.b64encode(b.getvalue()).decode()

def fmtkm(v):
    return f"{int(v or 0):,}".replace(',', '.') + ' km'

def iso_agora():
    return datetime.now(TZ_BR).isoformat()

def fmt_datahora(valor):
    if not valor:
        return '—'
    try:
        dt = datetime.fromisoformat(valor.replace('Z', '+00:00')).astimezone(TZ_BR)
        return dt.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(valor)

def dados():
    vs = db.table('veiculos').select('*').order('placa').execute().data or []
    movs = db.table('movimentacoes').select('*').eq('status', 'EM USO').order('data_hora_saida', desc=True).execute().data or []
    abertas = {m['placa']: m for m in movs}
    return vs, abertas

st.markdown('''<style>
#MainMenu,footer,header{visibility:hidden}.stApp{background:#f5f8fc;color:#0c315d}.block-container{padding:1rem 1rem 4rem;max-width:1180px}
.hero{display:flex;align-items:center;gap:12px;margin:2px 0 18px}.brand{font-size:28px;font-weight:900;color:#073b70}.sub{font-size:13px;color:#536b86}
.card{background:white;border:1px solid #dce6f0;border-radius:16px;overflow:hidden;box-shadow:0 3px 12px #0d3b6610;margin-bottom:14px}.photo{display:block;height:260px;width:100%!important;max-width:none!important;object-fit:contain;object-position:center center;margin:0!important;padding:8px!important;background:#fff!important}.pad{padding:14px}.plate{font-size:24px;font-weight:900;color:#0a3765}.model{font-weight:700}.company{font-size:13px;color:#60758c;margin-bottom:10px}.status{display:inline-block;padding:6px 10px;border-radius:20px;font-size:12px;font-weight:900}.ok{background:#dff7e9;color:#08783b}.busy{background:#fff0df;color:#d86500}.meta{font-size:14px;line-height:1.75;color:#203d5d}.rev{background:#f1f6fb;border-radius:10px;padding:9px;margin-top:8px}.tiny{font-size:12px;color:#6b7e92}
@media(max-width:640px){.block-container{padding:.55rem .55rem 3rem}.hero{margin-top:0}.brand{font-size:20px}.sub{font-size:12px}.photo{height:160px}.plate{font-size:20px}.stButton button{min-height:48px;font-weight:800;border-radius:12px}}
</style>''', unsafe_allow_html=True)

st.markdown("<div class='hero'><div style='font-size:34px'>🔧</div><div><div class='brand'>10 SUL · CONTROLE DE VEÍCULOS</div><div class='sub'>SERVICE · saída, retorno e revisão preventiva</div></div></div>", unsafe_allow_html=True)
page = st.segmented_control('Navegação', ['🚙 Veículos', '📊 Painel', '⚙️ Admin'], default='🚙 Veículos', label_visibility='collapsed')

try:
    vs, abertas = dados()
except Exception as e:
    st.error('Não foi possível conectar ao banco online. Confira os Secrets da aplicação.')
    st.caption(str(e))
    st.stop()

if page == '🚙 Veículos':
    filtro = st.segmented_control('Status', ['Disponíveis', 'Em uso'], default='Disponíveis', label_visibility='collapsed')
    lista = [v for v in vs if (v['placa'] not in abertas) == (filtro == 'Disponíveis')]
    if not lista:
        st.info('Nenhum veículo nesta situação.')
    cols = st.columns(2)
    for i, v in enumerate(lista):
        with cols[i % 2]:
            aberto = abertas.get(v['placa'])
            status = 'EM USO' if aberto else 'DISPONÍVEL'
            cls = 'busy' if aberto else 'ok'
            prox = (int(v['km_ultima_revisao']) + int(v.get('intervalo_revisao') or 10000)) if v.get('km_ultima_revisao') is not None else None
            falta = prox - int(v.get('km_atual') or 0) if prox is not None else None
            extra = ''
            if aberto:
                extra = f"<div class='meta'>👤 {aberto['pessoas']}<br>📍 {aberto['destino']}<br>🕐 Saída: {fmt_datahora(aberto['data_hora_saida'])}<br>🔢 KM inicial: {fmtkm(aberto['km_inicial'])}</div>"
            rev = f"Próxima revisão: <b>{fmtkm(prox)}</b>" if prox else 'Revisão ainda não cadastrada'
            st.markdown(f"<div class='card'><img class='photo' src='data:image/png;base64,{img64(v['foto'])}'><div class='pad'><span class='status {cls}'>{status}</span><div class='plate'>{v['placa']}</div><div class='model'>{v['modelo']}</div><div class='company'>{v['empresa']}</div><div class='meta'>🚗 KM atual: <b>{fmtkm(v.get('km_atual'))}</b></div><div class='rev'>🔧 {rev}" + (f"<br><span class='tiny'>Faltam {fmtkm(max(falta,0))}</span>" if falta is not None else '') + f"</div>{extra}</div></div>", unsafe_allow_html=True)
            if not aberto:
                if st.button('➜ USAR ESTE VEÍCULO', key='use'+v['placa'], use_container_width=True):
                    st.session_state.form_saida = v['placa']; st.rerun()
            else:
                if st.button('↩ REGISTRAR RETORNO', key='ret'+v['placa'], use_container_width=True):
                    st.session_state.form_retorno = v['placa']; st.rerun()

    placa = st.session_state.get('form_saida')
    if placa:
        v = next(x for x in vs if x['placa'] == placa)
        st.divider(); st.subheader(f'Registrar Saída · {placa}')
        st.image(str(ASSETS / v['foto']), use_container_width=True)
        with st.form('saida'):
            destino = st.text_input('📍 Para onde está indo?')
            pessoas = st.text_input('👥 Quem está indo?')
            km = st.number_input('🔢 KM inicial', min_value=0, step=1, value=int(v.get('km_atual') or 0))
            st.caption('🕐 Data e hora serão registradas automaticamente.')
            ok = st.form_submit_button('REGISTRAR SAÍDA', use_container_width=True)
            if ok:
                if not destino.strip() or not pessoas.strip():
                    st.error('Informe o destino e quem está indo.')
                else:
                    try:
                        db.table('movimentacoes').insert({'placa': placa, 'destino': destino.strip(), 'pessoas': pessoas.strip(), 'km_inicial': int(km), 'data_hora_saida': iso_agora(), 'status': 'EM USO'}).execute()
                        db.table('veiculos').update({'km_atual': int(km), 'atualizado_em': iso_agora()}).eq('placa', placa).execute()
                        st.session_state.pop('form_saida', None); st.success('Saída registrada.'); st.rerun()
                    except Exception:
                        st.error('Este veículo já pode estar em uso. Atualize a tela e tente novamente.')

    placa = st.session_state.get('form_retorno')
    if placa and placa in abertas:
        a = abertas[placa]
        st.divider(); st.subheader(f'Registrar Retorno · {placa}')
        st.write(f"**Destino:** {a['destino']}  \n**Quem foi:** {a['pessoas']}  \n**KM inicial:** {fmtkm(a['km_inicial'])}")
        with st.form('retorno'):
            kf = st.number_input('🔢 KM final', min_value=int(a['km_inicial']), step=1, value=int(a['km_inicial']))
            st.metric('KM rodado', fmtkm(int(kf)-int(a['km_inicial'])))
            ok = st.form_submit_button('✓ CONFIRMAR RETORNO', use_container_width=True)
            if ok:
                db.table('movimentacoes').update({'km_final': int(kf), 'data_hora_retorno': iso_agora(), 'status': 'DEVOLVIDO'}).eq('id', a['id']).execute()
                db.table('veiculos').update({'km_atual': int(kf), 'atualizado_em': iso_agora()}).eq('placa', placa).execute()
                st.session_state.pop('form_retorno', None); st.success('Retorno registrado.'); st.rerun()

elif page == '📊 Painel':
    st.subheader('Acompanhamento em tempo real')
    c1,c2,c3 = st.columns(3); c1.metric('Total',len(vs)); c2.metric('Disponíveis',len(vs)-len(abertas)); c3.metric('Em uso',len(abertas))
    if st.button('↻ Atualizar painel', use_container_width=True): st.rerun()
    for v in vs:
        a = abertas.get(v['placa'])
        prox = int(v['km_ultima_revisao']) + 10000 if v.get('km_ultima_revisao') is not None else None
        with st.container(border=True):
            x,y = st.columns([1,2]); x.image(str(ASSETS/v['foto']), use_container_width=True)
            y.markdown(f"### {v['placa']} · {v['modelo']}")
            y.write(('🟠 **EM USO**' if a else '🟢 **DISPONÍVEL**') + f"  \nKM atual: **{fmtkm(v.get('km_atual'))}**")
            if prox: y.write(f"Próxima revisão: **{fmtkm(prox)}** · faltam **{fmtkm(max(prox-int(v.get('km_atual') or 0),0))}**")
            if a: y.write(f"👤 {a['pessoas']}  \n📍 {a['destino']}  \n🕐 {fmt_datahora(a['data_hora_saida'])}")

else:
    st.subheader('Cadastro de revisão preventiva')
    placa = st.selectbox('Veículo', [v['placa'] for v in vs])
    v = next(x for x in vs if x['placa'] == placa)
    with st.form('rev'):
        data = st.date_input('Data da última revisão')
        kmr = st.number_input('KM da última revisão', min_value=0, step=1, value=int(v.get('km_ultima_revisao') or v.get('km_atual') or 0))
        st.info(f'Próxima revisão será em {fmtkm(int(kmr)+10000)}')
        if st.form_submit_button('SALVAR REVISÃO', use_container_width=True):
            db.table('veiculos').update({'data_ultima_revisao': data.isoformat(), 'km_ultima_revisao': int(kmr), 'intervalo_revisao': 10000, 'atualizado_em': iso_agora()}).eq('placa', placa).execute()
            st.success('Revisão atualizada.'); st.rerun()
