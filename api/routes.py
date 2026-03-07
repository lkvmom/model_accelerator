from fastapi import APIRouter
from fastapi.responses import JSONResponse
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.layouts import column, row, gridplot
import numpy as np
import traceback

from models.schemas import MatchingRequest
from physics.twiss import TwissParameters
from physics.elements import MatchingTriplet
from physics.matching import MatchingSolver
from physics.tracking import ParticleTracker

router = APIRouter(prefix="/api", tags=["matching"])

def convert_numpy_types(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    else:
        return obj

@router.post("/matching")
async def calculate_matching(request: MatchingRequest):
    try:
        twiss_in_x = TwissParameters.from_normalized(
            request.input.beta_x, request.input.alpha_x,
            request.input.emittance_x, request.energy, request.particle_type
        )
        twiss_in_y = TwissParameters.from_normalized(
            request.input.beta_y, request.input.alpha_y,
            request.input.emittance_y, request.energy, request.particle_type
        )
        
        twiss_target_x = TwissParameters(request.target.beta_x, request.target.alpha_x, twiss_in_x.emittance)
        twiss_target_y = TwissParameters(request.target.beta_y, request.target.alpha_y, twiss_in_y.emittance)
        
        masses = {'proton': 938.272, 'electron': 0.511, 'ion': 1000}
        m0c2 = masses.get(request.particle_type, 938.272)
        gamma = 1 + request.energy / m0c2
        beta_rel = np.sqrt(max(0, 1 - 1/gamma**2))
        rigidity = beta_rel * gamma * m0c2 / 299.792
        
        solver = MatchingSolver(twiss_in_x, twiss_in_y, twiss_target_x, twiss_target_y,
                               rigidity, request.max_quad_gradient)
        result = solver.solve()
        
        if not result['success']:
            return JSONResponse(content={"success": False, "message": result['message'], "data": None})
        
        triplet = result['triplet']
        twiss_along = triplet.get_twiss_along(twiss_in_x, twiss_in_y)
        
        tracker = ParticleTracker(triplet, twiss_in_x, twiss_in_y)
        ps_start = tracker.get_phase_space(at_start=True)
        ps_end = tracker.get_phase_space(at_start=False)
        
        plots = create_plots(twiss_along, triplet, ps_start, ps_end,
                            twiss_in_x, twiss_in_y, result['twiss_out_x'], result['twiss_out_y'])
        
        match_quality = {
            'beta_x_error': float(abs(result['twiss_out_x'].beta - request.target.beta_x) / request.target.beta_x * 100),
            'beta_y_error': float(abs(result['twiss_out_y'].beta - request.target.beta_y) / request.target.beta_y * 100),
            'alpha_x_error': float(abs(result['twiss_out_x'].alpha - request.target.alpha_x)),
            'alpha_y_error': float(abs(result['twiss_out_y'].alpha - request.target.alpha_y)),
            'emittance_preserved_x': bool(abs(twiss_in_x.emittance - result['twiss_out_x'].emittance) < 1e-15),
            'emittance_preserved_y': bool(abs(twiss_in_y.emittance - result['twiss_out_y'].emittance) < 1e-15),
        }
        
        return JSONResponse(content={
            "success": True,
            "message": "✅ Согласование успешно!",
            "data": convert_numpy_types({
                "elements": triplet.to_dict(),
                "total_length": float(triplet.total_length),
                "twiss_along": twiss_along,
                "match_quality": match_quality,
                "twiss_in": {'x': twiss_in_x.to_dict(), 'y': twiss_in_y.to_dict()},
                "twiss_out": {'x': result['twiss_out_x'].to_dict(), 'y': result['twiss_out_y'].to_dict()},
                "phase_space": {"start": ps_start, "end": ps_end}
            }),
            "plots": plots
        })
        
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": f"Ошибка: {str(e)}",
            "traceback": traceback.format_exc()
        })

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "accelerator-matching"}

def create_plots(twiss_along, triplet, ps_start, ps_end,
                 twiss_in_x, twiss_in_y, twiss_out_x, twiss_out_y):
    plots = {}
    try:
        plots['beta_alpha'] = create_beta_alpha_plot(twiss_along, triplet, twiss_in_x, twiss_in_y, twiss_out_x, twiss_out_y)
        plots['beam_envelope'] = create_beam_envelope_plot(twiss_along, triplet)
        plots['emittance_check'] = create_emittance_conservation_plot(twiss_along, twiss_in_x, twiss_in_y)
        plots['phase_space'] = create_phase_space_comparison_plot(ps_start, ps_end, twiss_in_x, twiss_in_y)
        plots['ellipse_evolution'] = create_ellipse_evolution_plot(triplet, twiss_in_x, n_positions=6)
        plots['fodo_scheme'] = create_fodo_channel_plot(triplet)
    except Exception as e:
        print(f"❌ Ошибка создания графиков: {e}")
        traceback.print_exc()
    return plots

def create_beta_alpha_plot(twiss_along, triplet, twiss_in_x, twiss_in_y, twiss_out_x, twiss_out_y):
    """β и α функции вдоль секции"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.layouts import column
    
    p_beta = figure(title="β-функции", x_axis_label="s (м)", y_axis_label="β (м)",
                    width=700, height=300, tools='pan,wheel_zoom,box_zoom,reset,save')
    p_beta.line(twiss_along['s'], twiss_along['beta_x'], 
                legend_label="β_x", color='#1f77b4', line_width=2)
    p_beta.line(twiss_along['s'], twiss_along['beta_y'], 
                legend_label="β_y", color='#ff7f0e', line_width=2, line_dash='dashed')
    p_beta.legend.location = "top_right"
    p_beta.legend.click_policy = "hide"
    
    p_alpha = figure(title="α-функции", x_axis_label="s (м)", y_axis_label="α",
                     width=700, height=300, tools='pan,wheel_zoom,box_zoom,reset,save')
    p_alpha.line(twiss_along['s'], twiss_along['alpha_x'],
                 legend_label="α_x", color='#1f77b4', line_width=2)
    p_alpha.line(twiss_along['s'], twiss_along['alpha_y'],
                 legend_label="α_y", color='#ff7f0e', line_width=2, line_dash='dashed')
    p_alpha.legend.location = "top_right"
    p_alpha.legend.click_policy = "hide"
    
    script, div = components(column(p_beta, p_alpha))
    # ✅ ВОЗВРАЩАЕМ СЛОВАРЬ, НЕ КОРТЕЖ!
    return {"script": script, "div": div}


def create_beam_envelope_plot(twiss_along, triplet):
    """Оболочка пучка σ(s)"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    
    p = figure(title="Оболочка пучка σ(s)", x_axis_label="s (м)", y_axis_label="σ (мм)",
               width=700, height=400, tools='pan,wheel_zoom,box_zoom,reset,save')
    p.line(twiss_along['s'], [x*1000 for x in twiss_along['beam_size_x']],
           legend_label="σ_x", color='#1f77b4', line_width=2)
    p.line(twiss_along['s'], [x*1000 for x in twiss_along['beam_size_y']],
           legend_label="σ_y", color='#ff7f0e', line_width=2, line_dash='dashed')
    p.varea(x=twiss_along['s'],
            y1=[x*2000 for x in twiss_along['beam_size_x']],
            y2=[-x*2000 for x in twiss_along['beam_size_x']],
            fill_color='#1f77b4', fill_alpha=0.15, legend_label="±2σ_x")
    p.legend.location = "top_right"
    p.legend.click_policy = "hide"
    
    script, div = components(p)
    return {"script": script, "div": div}


def create_emittance_conservation_plot(twiss_along, twiss_in_x, twiss_in_y):
    """Проверка сохранения эмиттанса"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    
    s = twiss_along['s']
    eps_x = [twiss_along['beam_size_x'][i]**2 / twiss_along['beta_x'][i] * 1e9 
             if twiss_along['beta_x'][i] > 1e-6 else twiss_in_x.emittance * 1e9
             for i in range(len(s))]
    eps_y = [twiss_along['beam_size_y'][i]**2 / twiss_along['beta_y'][i] * 1e9 
             if twiss_along['beta_y'][i] > 1e-6 else twiss_in_y.emittance * 1e9
             for i in range(len(s))]
    
    p = figure(title="Сохранение эмиттанса (Лиувилль)", x_axis_label="s (м)", y_axis_label="ε (нм·рад)",
               width=700, height=400, tools='pan,wheel_zoom,box_zoom,reset,save')
    p.line(s, eps_x, legend_label="ε_x", color='#1f77b4', line_width=2)
    p.line(s, eps_y, legend_label="ε_y", color='#ff7f0e', line_width=2, line_dash='dashed')
    p.line([min(s), max(s)], [twiss_in_x.emittance*1e9, twiss_in_x.emittance*1e9],
           color='#1f77b4', line_dash='dotted', alpha=0.5, legend_label="ε_x цель")
    p.line([min(s), max(s)], [twiss_in_y.emittance*1e9, twiss_in_y.emittance*1e9],
           color='#ff7f0e', line_dash='dotted', alpha=0.5, legend_label="ε_y цель")
    p.legend.location = "top_right"
    p.legend.click_policy = "hide"
    
    script, div = components(p)
    return {"script": script, "div": div}


def create_phase_space_comparison_plot(ps_start, ps_end, twiss_in_x, twiss_in_y):
    """Фазовое пространство начало/конец"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.models import ColumnDataSource
    from bokeh.layouts import row
    import numpy as np
    
    p_x = figure(title="Фазовое пространство X-X'", x_axis_label="x (мм)", y_axis_label="x' (мрад)",
                 width=350, height=350, tools='pan,wheel_zoom,box_zoom,reset,save')
    source_start = ColumnDataSource(data={'x': ps_start['x'][::10], 'xp': ps_start['xp'][::10]})
    source_end = ColumnDataSource(data={'x': ps_end['x'][::10], 'xp': ps_end['xp'][::10]})
    p_x.scatter('x', 'xp', source=source_start, size=3, color='#1f77b4', alpha=0.4, legend_label="Начало")
    p_x.scatter('x', 'xp', source=source_end, size=3, color='#ff7f0e', alpha=0.4, legend_label="Конец")
    a = np.sqrt(twiss_in_x.beta * twiss_in_x.emittance) * 1000
    b = np.sqrt(twiss_in_x.gamma * twiss_in_x.emittance) * 1000
    p_x.ellipse(0, 0, width=a*2, height=b*2, line_color='#2ca02c', line_dash='dashed', line_width=2, legend_label="Эллипс ε")
    p_x.legend.location = "top_right"
    p_x.legend.click_policy = "hide"
    
    p_y = figure(title="Фазовое пространство Y-Y'", x_axis_label="y (мм)", y_axis_label="y' (мрад)",
                 width=350, height=350, tools='pan,wheel_zoom,box_zoom,reset,save')
    source_start_y = ColumnDataSource(data={'y': ps_start['y'][::10], 'yp': ps_start['yp'][::10]})
    source_end_y = ColumnDataSource(data={'y': ps_end['y'][::10], 'yp': ps_end['yp'][::10]})
    p_y.scatter('y', 'yp', source=source_start_y, size=3, color='#1f77b4', alpha=0.4, legend_label="Начало")
    p_y.scatter('y', 'yp', source=source_end_y, size=3, color='#ff7f0e', alpha=0.4, legend_label="Конец")
    a_y = np.sqrt(twiss_in_y.beta * twiss_in_y.emittance) * 1000
    b_y = np.sqrt(twiss_in_y.gamma * twiss_in_y.emittance) * 1000
    p_y.ellipse(0, 0, width=a_y*2, height=b_y*2, line_color='#2ca02c', line_dash='dashed', line_width=2, legend_label="Эллипс ε")
    p_y.legend.location = "top_right"
    p_y.legend.click_policy = "hide"
    
    script, div = components(row(p_x, p_y))
    return {"script": script, "div": div}


def create_ellipse_evolution_plot(triplet, twiss_in_x, n_positions=6):
    """Эволюция эллипса эмиттанса"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.layouts import gridplot
    import numpy as np
    
    positions = np.linspace(0, triplet.total_length, n_positions)
    plots = []
    for s in positions:
        M_x, _ = triplet.get_matrix_at_s(s)
        twiss_at_s = twiss_in_x.transform(M_x)
        theta = np.linspace(0, 2*np.pi, 100)
        x = np.sqrt(twiss_at_s.beta * twiss_at_s.emittance) * np.cos(theta) * 1000
        xp = (-twiss_at_s.alpha/np.sqrt(twiss_at_s.beta) * np.cos(theta) 
              - np.sqrt(1/twiss_at_s.beta) * np.sin(theta)) * np.sqrt(twiss_at_s.emittance) * 1000
        p = figure(title=f"s = {s:.2f} м", x_axis_label="x (мм)", y_axis_label="x' (мрад)",
                   width=200, height=200, tools='reset')
        p.line(x, xp, color='#1f77b4', line_width=2)
        plots.append(p)
    grid = [plots[:3], plots[3:]] if len(plots) > 4 else [plots]
    
    script, div = components(gridplot(grid, toolbar_location=None))
    return {"script": script, "div": div}


def create_fodo_channel_plot(triplet):
    """Схема канала"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    
    p = figure(title="Схема согласующей секции", x_axis_label="s (м)", y_axis_label="",
               width=800, height=150, tools='')
    colors = {'QF': '#2ecc71', 'QD': '#e74c3c', 'drift': '#95a5a6'}
    for elem in triplet.to_dict():
        if elem['type'] == 'quadrupole':
            color = colors['QF'] if elem['subtype'] == 'QF' else colors['QD']
            y, h, label = (0.6, 0.3, elem['subtype'])
        else:
            color, y, h, label = colors['drift'], 0, 0.1, "D"
        p.rect(x=elem['position'] + elem['length']/2, y=y,
               width=elem['length']*0.95, height=h, fill_color=color, fill_alpha=0.8, line_color='black')
        p.text(x=elem['position'] + elem['length']/2, y=y+h+0.12,
               text=[label], text_align='center', text_font_size='10pt', text_color='white')
    p.y_range.start, p.y_range.end = -1, 1
    p.yaxis.visible = False
    p.grid.visible = False
    p.outline_line_color = None
    
    script, div = components(p)
    return {"script": script, "div": div}