"""Read-only fuel reporting. Source records never update fleet odometers."""
import re
import html

MONTHS = {'01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril',
          '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto',
          '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'}


def normalize_plate(value):
    return re.sub(r'[\s-]', '', str(value or '')).upper()


def period_label(period):
    return f"{MONTHS[period[5:7]]} / {period[:4]}"


def number(value, decimals=2):
    return f'{value:,.{decimals}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def load_reports(db):
    response = db.table('consumo_relatorios').select('conteudo').order('periodo').execute()
    return [row['conteudo'] for row in (response.data or [])]


def report_rows(reports, fleet, unit='TODAS'):
    """Link only exact normalized plates; never guess a vehicle or its unit."""
    by_plate = {normalize_plate(v['placa']): v for v in fleet}
    summaries = []
    groups = {}
    for report in reports:
        for item in report['veiculos']:
            key = (report['periodo'], normalize_plate(item['placa']))
            group = groups.setdefault(key, {'placa': item['placa'], 'modelo': 'Modelo não informado',
                                            'registros': [], 'baselines': [], 'seen': set(), 'origens': set()})
            if item.get('modelo') and item['modelo'] != 'Modelo não informado':
                group['modelo'] = item['modelo']
            group['origens'].add(report['origem'])
            if item.get('km_anterior') and item['km_anterior'] > 0:
                first_time = min(((r['data'], r['hora']) for r in item['registros']), default=('', ''))
                group['baselines'].append((first_time, item['km_anterior']))
            for raw in item['registros']:
                origin = raw.get('origem') or report['origem']
                fingerprint = (origin.casefold().strip(), raw['cupom'], raw['produto'], raw['data'],
                               raw['hora'], raw['quantidade'], raw['valor'])
                if fingerprint in group['seen']:
                    continue
                group['seen'].add(fingerprint)
                group['registros'].append({**raw, 'origem': origin})
    for (period, plate), item in groups.items():
        vehicle = by_plate.get(plate)
        if unit != 'TODAS' and (not vehicle or vehicle.get('unidade', 'ARA') != unit):
            continue
        records = sorted(item['registros'], key=lambda r: (r['data'], r['hora'], r['cupom']))
        fuel = [row for row in records if row['combustivel']]
        liters = round(sum(row['quantidade'] for row in fuel), 3)
        cost = round(sum(row['valor'] for row in fuel), 2)
        readings = [r['km_atual'] for r in records if r['km_atual'] > 0]
        initial = min(item['baselines'], key=lambda v: v[0])[1] if item['baselines'] else (readings[0] if readings else None)
        previous = initial
        issues = []
        if not item['baselines'] and readings:
            issues.append('Sem odômetro anterior ao período; distância entre as leituras disponíveis.')
        for record in records:
            reading = record['km_atual']
            if reading > 0:
                if previous is not None and reading < previous:
                    issues.append(f"Odômetro diminuiu de {number(previous, 0)} para {number(reading, 0)} km em {record['data'][8:10]}/{record['data'][5:7]}.")
                previous = reading
            if record['combustivel'] and record['km_l_informado'] > 30:
                issues.append(f"Relatório informa {number(record['km_l_informado'])} km/L em {record['data'][8:10]}/{record['data'][5:7]}; conferir o histórico.")
        distance = previous - initial if initial is not None and readings and (item['baselines'] or len(readings) > 1) else None
        if distance is not None and distance < 0:
            distance = None
        summaries.append({
            'periodo': period, 'placa': item['placa'],
            'modelo': vehicle.get('modelo') if vehicle else item['modelo'],
            'unidade': vehicle.get('unidade', 'ARA') if vehicle else None,
            'vinculado': vehicle is not None, 'litros': liters,
            'valor': cost, 'abastecimentos': len(fuel), 'km': distance,
            'outras_compras': round(sum(row['valor'] for row in records if not row['combustivel']), 2),
            'km_l': distance / liters if liters and distance is not None and not issues else None,
            'custo_km': cost / distance if distance and liters and not issues else None,
            'alertas': issues, 'registros': records, 'km_anterior': initial,
            'km_final': previous, 'origem': ' / '.join(sorted(item['origens'])),
        })
    return summaries


def render_consumption(fleet, unit, unit_labels, db):
    import pandas as pd
    import streamlit as st

    st.markdown("<div class='title'>Consumo por veículo</div>", unsafe_allow_html=True)
    st.caption('Abastecimentos · Consumo consolidado por veículo')
    try:
        reports = load_reports(db)
    except Exception:
        st.info('A tela de consumo está instalada. A consulta aos relatórios aguarda a definição de acesso pelo responsável.')
        return
    if not reports:
        st.info('Nenhum relatório de consumo disponível para este acesso.')
        return
    st.caption('Postos: ' + ' · '.join(sorted({r['origem'] for r in reports})))
    periods = sorted({r['periodo'] for r in reports}, reverse=True)
    period = st.selectbox('Período do consumo', periods, format_func=period_label, key='consumption_period')
    all_rows = report_rows(reports, fleet, 'TODAS')
    scoped = report_rows(reports, fleet, unit)
    rows = [r for r in scoped if r['periodo'] == period]
    unlinked = sorted({r['placa'] for r in all_rows if r['periodo'] == period and not r['vinculado']})
    if unlinked:
        st.info('Placas do relatório sem vínculo no cadastro: ' + ', '.join(unlinked) +
                '. Aparecem em Todas as unidades; não são atribuídas automaticamente a uma unidade.')
    st.caption('Leituras do posto não alteram o KM atual do cadastro.')
    if not rows:
        st.info('Nenhum consumo vinculado a veículos desta unidade no período. Selecione Todas as unidades para consultar as placas sem vínculo.')
        return
    cost = sum(r['valor'] for r in rows)
    liters = sum(r['litros'] for r in rows)
    count = sum(r['abastecimentos'] for r in rows)
    c1, c2, c3 = st.columns(3)
    c1.metric('Combustível', 'R$ ' + number(cost))
    c2.metric('Litros abastecidos', number(liters, 3) + ' L')
    c3.metric('Abastecimentos', count)

    def ranking(metric, title, axis, color, digits):
        ranked = sorted([r for r in rows if r[metric] is not None and r[metric] > 0], key=lambda r: r[metric], reverse=True)
        st.markdown('#### ' + title)
        if not ranked:
            st.info('Sem registros para este ranking.')
            return
        maximum = max(r[metric] for r in ranked)
        bars = []
        for position, row in enumerate(ranked, 1):
            total = number(row[metric], digits) + (' L' if metric == 'litros' else ' km')
            label = html.escape(row['placa'])
            model = html.escape(row['modelo'])
            bars.append(f"<div style='margin:14px 0'><div style='display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap'><span>{position}º · <b>{label}</b></span><b>{total}</b></div><div style='font-size:12px;color:#60778b'>{model}</div><div role='img' aria-label='{label}: {total}' style='height:13px;background:#e8eff5;border-radius:4px;margin-top:6px;overflow:hidden'><div style='width:{row[metric]/maximum*100:.3f}%;height:100%;background:{color};border-radius:4px'></div></div></div>")
        st.markdown('<div>'+''.join(bars)+f"<div style='font-size:12px;color:#60778b'>{html.escape(axis)}</div></div>", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        ranking('litros', 'Ranking · Mais abastecidos', 'Combustível (L)', '#0868b6', 3)
    with right:
        ranking('km', 'Ranking · Mais rodados', 'Distância registrada (km)', '#198772', 0)
    st.caption('Quilometragem provisória: odômetro anterior do relatório até o último registro, não necessariamente até o último dia do mês. Leituras intermediárias inconsistentes ficam sinalizadas abaixo. Litros abastecidos representam compras de combustível, não uma medição exata do que foi consumido no mês.')

    st.markdown('#### Resumo por veículo')
    summary = pd.DataFrame([{
        'Placa': r['placa'], 'Veículo': r['modelo'], 'Postos': r['origem'],
        'Unidade': unit_labels.get(r['unidade'], 'Sem vínculo'),
        'Litros': number(r['litros'], 3), 'Combustível (R$)': number(r['valor']),
        'Km registrados*': number(r['km'], 0) if r['km'] is not None else 'Sem leitura',
        'Km/L indicativo*': number(r['km_l']) if r['km_l'] is not None else 'A conferir',
        'R$/km indicativo*': number(r['custo_km']) if r['custo_km'] is not None else 'A conferir',
        'Abastecimentos': r['abastecimentos'],
        'Situação': 'Conferir odômetro' if r['alertas'] else ('Sem combustível' if not r['abastecimentos'] else 'Indicativo'),
    } for r in sorted(rows, key=lambda r: r['valor'], reverse=True)])
    st.dataframe(summary, hide_index=True, use_container_width=True)
    st.caption('*Índices indicativos. Conferir odômetros e histórico completo; o relatório não informa se o tanque foi completado.')
    other = sum(r['outras_compras'] for r in rows)
    st.caption('Outras compras: R$ ' + number(other) + ' · separadas do combustível e do volume em litros.')

    selected = st.selectbox('Detalhar veículo', [r['placa'] for r in rows],
                            format_func=lambda p: p + ' — ' + next(r['modelo'] for r in rows if r['placa'] == p),
                            key='consumption_vehicle_' + unit + '_' + period)
    current = next(r for r in rows if r['placa'] == selected)
    history = sorted([r for r in scoped if normalize_plate(r['placa']) == normalize_plate(selected)], key=lambda r: r['periodo'])
    st.markdown('#### Gasto mensal · ' + selected)
    maximum = max((r['valor'] for r in history), default=0) or 1
    monthly_bars = []
    for row in history:
        label = html.escape(period_label(row['periodo']))
        total = 'R$ ' + number(row['valor'])
        monthly_bars.append(f"<div style='margin:12px 0'><div style='display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap'><span>{label}</span><b>{total}</b></div><div role='img' aria-label='{label}: {total}' style='height:15px;background:#e8eff5;border-radius:4px;margin-top:6px;overflow:hidden'><div style='height:100%;width:{row['valor']/maximum*100:.3f}%;background:#0868b6;border-radius:4px'></div></div></div>")
    st.markdown('<div>'+''.join(monthly_bars)+'</div>', unsafe_allow_html=True)
    if current['alertas']:
        st.warning('Quilometragem a conferir: ' + ' '.join(current['alertas']))
    if current['km'] is not None:
        st.caption('Odômetro anterior: ' + number(current['km_anterior'], 0) + ' km · Último registro: ' + number(current['km_final'], 0) + ' km')
    st.markdown('#### Histórico do veículo selecionado')
    details = pd.DataFrame([{
        'Data': r['data'][8:10] + '/' + r['data'][5:7] + '/' + r['data'][:4],
        'Hora': r['hora'], 'Posto': r['origem'], 'Cupom': r['cupom'], 'Produto': r['produto'],
        'Litros': number(r['quantidade'], 3) if r['combustivel'] else '—',
        'Quantidade de outros itens': '—' if r['combustivel'] else number(r['quantidade'], 0),
        'R$/unidade': number(r['preco_unitario']), 'Valor (R$)': number(r['valor']),
        'Odômetro (km)': number(r['km_atual'], 0),
    } for r in current['registros']])
    st.dataframe(details, hide_index=True, use_container_width=True)
    st.download_button('Baixar resumo do período (CSV)',
                       data=summary.to_csv(index=False, sep=';', lineterminator='\n').encode('utf-8-sig'),
                       file_name='consumo_veiculos_' + period + '_' + unit + '.csv', mime='text/csv',
                       key='consumption_export')
