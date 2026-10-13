UNITS = {'ARA': 'Aracruz / ES', 'BA': 'Itabatan / Bahia', 'TODAS': 'Todas as unidades'}

def resolve_unit(params, vehicles=()):
    raw = str(params.get('unidade', '')).upper()
    raw = {'BAHIA': 'BA', 'ITABATAN': 'BA', 'ARACRUZ': 'ARA', 'ALL': 'TODAS'}.get(raw, raw)
    view = params.get('view', 'vehicles')
    if raw in UNITS and (raw != 'TODAS' or view == 'admin'):
        return raw
    # Existing Android return links carry the plate, but no unit.
    if not raw and params.get('native') == 'android' and params.get('plate'):
        vehicle = next((v for v in vehicles if v['placa'] == params['plate']), None)
        if vehicle:
            return vehicle.get('unidade', 'ARA')
    return 'TODAS' if view == 'admin' else 'ARA'

def scope_fleet(vehicles, opened, unit):
    selected = [v for v in vehicles if unit == 'TODAS' or v.get('unidade', 'ARA') == unit]
    plates = {v['placa'] for v in selected}
    return selected, {plate: m for plate, m in opened.items() if plate in plates}

def route_params(view, unit, **kwargs):
    # Operational routes always show a single unit; the manager may show both.
    if unit == 'TODAS' and view != 'admin':
        unit = 'ARA'
    return {'view': view, 'unidade': unit, **kwargs}