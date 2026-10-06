import streamlit as st
from datetime import datetime, timezone, timedelta
from supabase import create_client

st.set_page_config(page_title="Admin | Controle de Veículos", page_icon="⚙️", layout="centered", initial_sidebar_state="collapsed")
TZ = timezone(timedelta(hours=-3))

@st.cache_resource
def get_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

DB = get_db()

def km(v):
    return f"{int(v or 0):,}".replace(",", ".") + " km"

def fmt_dt(v):
    if not v:
        return "—"
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(TZ)
        return d.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "—"

def now():
    return datetime.now(TZ).isoformat()

st.markdown("""
<style>
#MainMenu,footer,header,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
.stApp{background:#f2f6fa;color:#173d60}.block-container{max-width:760px;padding:12px 12px 60px!important}
.top{background:#fff;border-radius:15px;padding:14px 16px;box-shadow:0 3px 14px #173b5a12;margin-bottom:12px}
.brand{font-size:21px;font-weight:950;color:#073c6c}.sub{font-size:10px;color:#71869a;font-weight:800;letter-spacing:.5px}
.card{background:#fff;border:1px solid #dce5ed;border-radius:12px;padding:11px;margin:8px 0;box-shadow:0 2px 9px #173b5a0d}
.plate{font-size:17px;font-weight:950;color:#083d6d}.muted{font-size:10px;color:#6d8193;line-height:1.55}
.stButton button,.stFormSubmitButton button{border-radius:9px!important;min-height:40px!important;font-weight:850!important}
</style>
<div class="top"><div class="brand">⚙️ Administração da Frota</div><div class="sub">10 SUL · CONTROLE DE VEÍCULOS SERVICE</div></div>
""", unsafe_allow_html=True)

try:
    veiculos = DB.table("veiculos").select("*").order("placa").execute().data or []
except Exception as e:
    st.error("Não foi possível carregar o banco online.")
    st.stop()

aba = st.segmented_control("Admin", ["🔧 Revisões", "📋 Movimentações", "🚙 Veículos"], default="📋 Movimentações", label_visibility="collapsed")

if aba == "📋 Movimentações":
    st.subheader("Histórico de movimentações")
    filtro = st.selectbox("Veículo", ["Todos"] + [v["placa"] for v in veiculos])
    q = DB.table("movimentacoes").select("*").order("data_hora_saida", desc=True).limit(200)
    if filtro != "Todos":
        q = q.eq("placa", filtro)
    hist = q.execute().data or []
    if not hist:
        st.info("Nenhum lançamento encontrado.")
    for m in hist:
        mid = m.get("id")
        aberto = m.get("status") == "EM USO"
        rodado = None
        if m.get("km_final") is not None and m.get("km_inicial") is not None:
            rodado = int(m["km_final"]) - int(m["km_inicial"])
        st.markdown(f"""<div class='card'><div class='plate'>{m.get('placa','—')} · {'🟠 EM USO' if aberto else '✅ DEVOLVIDO'}</div>
        <div class='muted'>👤 {m.get('pessoas') or '—'}<br>📍 {m.get('destino') or '—'}<br>
        Saída: <b>{fmt_dt(m.get('data_hora_saida'))}</b><br>Retorno: <b>{fmt_dt(m.get('data_hora_retorno'))}</b><br>
        KM inicial: <b>{km(m.get('km_inicial'))}</b> · KM final: <b>{km(m.get('km_final')) if m.get('km_final') is not None else '—'}</b>
        {(' · Rodado: <b>'+km(rodado)+'</b>') if rodado is not None else ''}</div></div>""", unsafe_allow_html=True)
        key = f"del_{mid}"
        if st.session_state.get(key):
            st.warning(f"Excluir definitivamente este lançamento da placa {m.get('placa')}?")
            c1, c2 = st.columns(2)
            if c1.button("SIM, EXCLUIR", key=f"yes_{mid}", type="primary", use_container_width=True):
                try:
                    DB.table("movimentacoes").delete().eq("id", mid).execute()
                    st.session_state.pop(key, None)
                    st.success("Lançamento excluído. Se estava em uso, o veículo já voltou a aparecer como disponível.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível excluir: {e}")
            if c2.button("CANCELAR", key=f"no_{mid}", use_container_width=True):
                st.session_state.pop(key, None)
                st.rerun()
        else:
            if st.button("🗑️ EXCLUIR LANÇAMENTO", key=f"btn_{mid}", use_container_width=True):
                st.session_state[key] = True
                st.rerun()

elif aba == "🔧 Revisões":
    st.subheader("Controle de revisão preventiva")
    if not veiculos:
        st.info("Nenhum veículo cadastrado.")
        st.stop()
    placa = st.selectbox("Veículo", [v["placa"] for v in veiculos])
    v = next(x for x in veiculos if x["placa"] == placa)
    atual = int(v.get("km_atual") or 0)
    ultima = v.get("km_ultima_revisao")
    proxima = int(ultima) + 10000 if ultima is not None else None
    faltam = proxima - atual if proxima is not None else None
    c1, c2, c3 = st.columns(3)
    c1.metric("KM atual", km(atual))
    c2.metric("Próxima revisão", km(proxima) if proxima is not None else "—")
    c3.metric("Faltam", km(faltam) if faltam is not None and faltam >= 0 else ("VENCIDA" if faltam is not None else "—"))
    with st.form("revisao"):
        data_rev = st.date_input("Data da última revisão")
        km_rev = st.number_input("KM da última revisão", min_value=0, value=int(ultima or atual), step=1)
        st.info(f"A próxima revisão será automaticamente em {km(int(km_rev)+10000)}.")
        if st.form_submit_button("SALVAR REVISÃO", use_container_width=True):
            DB.table("veiculos").update({"data_ultima_revisao": data_rev.isoformat(), "km_ultima_revisao": int(km_rev), "intervalo_revisao": 10000, "atualizado_em": now()}).eq("placa", placa).execute()
            st.success("Revisão atualizada.")
            st.rerun()

else:
    st.subheader("Veículos")
    st.caption("Consulta e correção administrativa do KM atual.")
    for v in veiculos:
        with st.expander(f"🚙 {v.get('placa')} · {v.get('modelo','')}"):
            st.write(f"**Empresa:** {v.get('empresa') or '—'}")
            novo_km = st.number_input("KM atual", min_value=0, value=int(v.get("km_atual") or 0), step=1, key=f"km_{v['placa']}")
            if st.button("SALVAR KM", key=f"savekm_{v['placa']}", use_container_width=True):
                DB.table("veiculos").update({"km_atual": int(novo_km), "atualizado_em": now()}).eq("placa", v["placa"]).execute()
                st.success("KM atualizado.")
                st.rerun()
