import numpy as np
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.layouts import row

def create_beta_alpha_plot(twiss_along, twiss_target_x, twiss_target_y):
    """График β/α функций (из fo_channel_beta_function.ipynb)"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.layouts import column
    
    p_beta = figure(
        title="β-функции",
        x_axis_label="s (м)",
        y_axis_label="β (м)",
        width=700, height=300,
        tools='pan,wheel_zoom,box_zoom,reset,save'
    )
    
    p_beta.line(twiss_along['s'], twiss_along['beta_x'], 
           legend_label="β_x", color='#1f77b4', line_width=2)
    p_beta.line(twiss_along['s'], twiss_along['beta_y'], 
           legend_label="β_y", color='#ff7f0e', line_width=2, line_dash='dashed')
    
    p_beta.line([min(twiss_along['s']), max(twiss_along['s'])], 
           [twiss_target_x.beta, twiss_target_x.beta],
           color='#1f77b4', line_dash='dotted', alpha=0.5, 
           legend_label="β_x цель")
    p_beta.line([min(twiss_along['s']), max(twiss_along['s'])], 
           [twiss_target_y.beta, twiss_target_y.beta],
           color='#ff7f0e', line_dash='dotted', alpha=0.5, 
           legend_label="β_y цель")
    
    p_beta.legend.location = "top_right"
    p_beta.legend.click_policy = "hide"
    
    p_alpha = figure(
        title="α-функции",
        x_axis_label="s (м)",
        y_axis_label="α",
        width=700, height=300,
        tools='pan,wheel_zoom,box_zoom,reset,save'
    )
    
    p_alpha.line(twiss_along['s'], twiss_along['alpha_x'],
           legend_label="α_x", color='#1f77b4', line_width=2)
    p_alpha.line(twiss_along['s'], twiss_along['alpha_y'],
           legend_label="α_y", color='#ff7f0e', line_width=2, line_dash='dashed')
    
    p_alpha.legend.location = "top_right"
    p_alpha.legend.click_policy = "hide"
    
    script, div = components(column(p_beta, p_alpha))
    return {"script": script, "div": div}

def create_beam_envelope_plot(twiss_along):
    """График оболочки пучка (из beam_spreading.ipynb)"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    
    p = figure(
        title="Оболочка пучка σ(s)",
        x_axis_label="s (м)",
        y_axis_label="σ (мм)",
        width=700, height=400,
        tools='pan,wheel_zoom,box_zoom,reset,save'
    )
    
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
    """График сохранения эмиттанса (из fo_channel_nonlinear_dynamics.ipynb)"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    
    s = twiss_along['s']
    
    # Расчёт эмиттанса вдоль секции: ε = σ²/β
    eps_x = [
        twiss_along['beam_size_x'][i]**2 / twiss_along['beta_x'][i] * 1e9 
        if twiss_along['beta_x'][i] > 1e-6 else twiss_in_x.emittance * 1e9
        for i in range(len(s))
    ]
    eps_y = [
        twiss_along['beam_size_y'][i]**2 / twiss_along['beta_y'][i] * 1e9 
        if twiss_along['beta_y'][i] > 1e-6 else twiss_in_y.emittance * 1e9
        for i in range(len(s))
    ]
    
    p = figure(
        title="Сохранение эмиттанса (Лиувилль)",
        x_axis_label="s (м)",
        y_axis_label="ε (нм·рад)",
        width=700, height=400,
        tools='pan,wheel_zoom,box_zoom,reset,save'
    )
    
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

def create_phase_space_comparison_plot(phase_space, twiss_in_x, twiss_in_y):
    """Фазовое пространство (из ellipse.ipynb и fo_do_channel.ipynb)"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.models import ColumnDataSource
    from bokeh.layouts import row
    import numpy as np
    
    # ✅ Проверка данных
    if not phase_space or not isinstance(phase_space, dict) or 'x' not in phase_space:
        print(f"❌ phase_space invalid: {phase_space}")
        p = figure(title="Ошибка данных", width=350, height=350)
        p.text(0, 0, text=["Нет данных"])
        script, div = components(p)
        return {"script": script, "div": div}
    
    print(f"📊 Phase space x len: {len(phase_space.get('x', []))}")
    
    # X-X' фазовое пространство
    p_x = figure(
        title="Фазовое пространство X-X'",
        x_axis_label="x (мм)",
        y_axis_label="x' (мрад)",
        width=350, height=350,
        tools='pan,wheel_zoom,box_zoom,reset,save'
    )
    
    step = max(1, len(phase_space['x']) // 100)
    source = ColumnDataSource(data={
        'x': phase_space['x'][::step],
        'xp': phase_space['xp'][::step]
    })
    
    p_x.scatter('x', 'xp', source=source, size=3, 
                color='#1f77b4', alpha=0.4, legend_label="Частицы")
    
    a = np.sqrt(twiss_in_x.beta * twiss_in_x.emittance) * 1000
    b = np.sqrt(twiss_in_x.gamma * twiss_in_x.emittance) * 1000
    p_x.ellipse(0, 0, width=a*2, height=b*2, 
                line_color='#2ca02c', line_dash='dashed', 
                line_width=2, legend_label="Эллипс ε")
    
    p_x.legend.location = "top_right"
    p_x.legend.click_policy = "hide"
    
    # Y-Y' фазовое пространство
    p_y = figure(
        title="Фазовое пространство Y-Y'",
        x_axis_label="y (мм)",
        y_axis_label="y' (мрад)",
        width=350, height=350,
        tools='pan,wheel_zoom,box_zoom,reset,save'
    )
    
    source_y = ColumnDataSource(data={
        'y': phase_space['y'][::step],
        'yp': phase_space['yp'][::step]
    })
    
    p_y.scatter('y', 'yp', source=source_y, size=3, 
                color='#ff7f0e', alpha=0.4, legend_label="Частицы")
    
    a_y = np.sqrt(twiss_in_y.beta * twiss_in_y.emittance) * 1000
    b_y = np.sqrt(twiss_in_y.gamma * twiss_in_y.emittance) * 1000
    p_y.ellipse(0, 0, width=a_y*2, height=b_y*2, 
                line_color='#2ca02c', line_dash='dashed', 
                line_width=2, legend_label="Эллипс ε")
    
    p_y.legend.location = "top_right"
    p_y.legend.click_policy = "hide"
    
    # ✅ Объединяем в один layout и возвращаем ПЛОСКУЮ структуру
    script, div = components(row(p_x, p_y))
    return {"script": script, "div": div}  # ✅ НЕ {"x": {...}, "y": {...}}

def create_ellipse_evolution_plot(triplet, twiss_in_x, n_positions=6):
    """Эволюция эллипса (из ellipse.ipynb)"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.layouts import gridplot
    import numpy as np
    
    positions = np.linspace(0, triplet.total_length, n_positions)
    plots = []
    
    for s in positions:
        M_x, _ = triplet.get_matrix_at_s(s)
        twiss_at_s = twiss_in_x.transform(M_x)
        
        # Параметризация эллипса: γ·x² + 2α·x·x' + β·x'² = ε
        theta = np.linspace(0, 2*np.pi, 100)
        x = np.sqrt(twiss_at_s.beta * twiss_at_s.emittance) * np.cos(theta) * 1000
        xp = (-twiss_at_s.alpha/np.sqrt(twiss_at_s.beta) * np.cos(theta) 
              - np.sqrt(1/twiss_at_s.beta) * np.sin(theta)) * np.sqrt(twiss_at_s.emittance) * 1000
        
        p = figure(
            title=f"s = {s:.2f} м",
            x_axis_label="x (мм)",
            y_axis_label="x' (мрад)",
            width=200, height=200,
            tools='reset'
        )
        p.line(x, xp, color='#1f77b4', line_width=2)
        p.grid.grid_line_alpha = 0.3
        plots.append(p)
    
    grid = [plots[:3], plots[3:]] if len(plots) > 4 else [plots]
    
    script, div = components(gridplot(grid, toolbar_location=None))
    return {"script": script, "div": div}

def create_fodo_channel_plot(triplet):
    """Схема канала (из fo_do_channel.ipynb)"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    
    p = figure(
        title="Схема согласующей секции",
        x_axis_label="s (м)",
        y_axis_label="",
        width=800, height=150,
        tools=''
    )
    
    colors = {'QF': '#2ecc71', 'QD': '#e74c3c', 'drift': '#95a5a6'}
    
    for elem in triplet.to_dict():
        if elem['type'] == 'quadrupole':
            color = colors['QF'] if elem['subtype'] == 'QF' else colors['QD']
            y, h, label = (0.6, 0.3, elem['subtype'])
        else:
            color, y, h, label = colors['drift'], 0, 0.1, "D"
        
        p.rect(x=elem['position'] + elem['length']/2, y=y,
               width=elem['length']*0.95, height=h,
               fill_color=color, fill_alpha=0.8, line_color='black')
        p.text(x=elem['position'] + elem['length']/2, y=y+h+0.12,
               text=[label], text_align='center', text_font_size='10pt', text_color='white')
    
    p.y_range.start, p.y_range.end = -1, 1
    p.yaxis.visible = False
    p.grid.visible = False
    p.outline_line_color = None
    
    script, div = components(p)
    return {"script": script, "div": div}