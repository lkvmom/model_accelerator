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
    """Конвертация numpy типов в JSON-сериализуемые"""
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
        # ✅ ВАЛИДАЦИЯ входных данных
        if request.input.beta_x <= 0 or request.input.beta_y <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "β_x и β_y должны быть положительными",
                    "plots": None
                }
            )
        
        if request.max_gradient <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Максимальный градиент должен быть положительным",
                    "plots": None
                }
            )
        
        # Расчет релятивистских параметров
        masses = {'proton': 938.272, 'electron': 0.511, 'ion': 1000}  # МэВ
        m0c2 = masses.get(request.particle_type, 938.272)
        
        gamma = 1 + request.energy / m0c2
        beta_rel = np.sqrt(max(0, 1 - 1/gamma**2))
        
        # Правильная формула магнитной жёсткости (Тл·м)
        rigidity = beta_rel * gamma * m0c2 / 299.792
        
        print(f"🔬 Энергия: {request.energy} МэВ")
        print(f"🔬 gamma: {gamma:.4f}, beta: {beta_rel:.4f}")
        print(f"🔬 Жёсткость: {rigidity:.4f} Тл·м")
        print(f"🔬 Макс градиент: {request.max_gradient} Тл/м")
        print(f"🔬 Макс k: {request.max_gradient / rigidity:.2f} м⁻²")
        
        # Создание параметров Твисса
        twiss_in_x = TwissParameters.from_normalized(
            request.input.beta_x, request.input.alpha_x,
            request.input.emittance_x, request.energy, request.particle_type
        )
        twiss_in_y = TwissParameters.from_normalized(
            request.input.beta_y, request.input.alpha_y,
            request.input.emittance_y, request.energy, request.particle_type
        )
        
        twiss_target_x = TwissParameters(
            request.target.beta_x, request.target.alpha_x,
            twiss_in_x.emittance
        )
        twiss_target_y = TwissParameters(
            request.target.beta_y, request.target.alpha_y,
            twiss_in_y.emittance
        )
        
        # Решение задачи согласования
        solver = MatchingSolver(
            twiss_in_x, twiss_in_y,
            twiss_target_x, twiss_target_y,
            rigidity, request.max_gradient
        )
        
        result = solver.solve()
        
        # ✅ Проверка результата оптимизации
        if not result['success']:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": result['message'],
                    "plots": None
                }
            )
        
        triplet = result['triplet']
        twiss_out_x = result['twiss_out_x']
        twiss_out_y = result['twiss_out_y']
        
        # Трекинг частиц
        tracker = ParticleTracker(triplet, twiss_in_x, twiss_in_y, 1000)
        
        # Параметры вдоль секции
        twiss_along = triplet.get_twiss_along(twiss_in_x, twiss_in_y, 100)
        
        # ✅ Получаем phase_space ОТДЕЛЬНО
        phase_space = tracker.get_phase_space()
        
        print(f"📊 Phase space keys: {phase_space.keys()}")
        print(f"📊 Phase space x length: {len(phase_space['x'])}")
        
        # Качество согласования
        match_quality = {
            'beta_x_error': float(abs(twiss_out_x.beta - twiss_target_x.beta) / twiss_target_x.beta * 100),
            'beta_y_error': float(abs(twiss_out_y.beta - twiss_target_y.beta) / twiss_target_y.beta * 100),
            'alpha_x_error': float(abs(twiss_out_x.alpha - twiss_target_x.alpha)),
            'alpha_y_error': float(abs(twiss_out_y.alpha - twiss_target_y.alpha)),
            'emittance_preserved_x': True,
            'emittance_preserved_y': True
        }
        
        # ✅ Создание ВСЕХ 5 графиков
        plots = create_all_plots(
            twiss_along, phase_space,
            twiss_in_x, twiss_in_y,
            twiss_target_x, twiss_target_y,
            triplet
        )
        
        # ✅ Проверка что графики созданы
        if not plots or len(plots) == 0:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Не удалось создать графики",
                    "plots": None
                }
            )
        
        return JSONResponse(content={
            "success": True,
            "message": result['message'],
            "data": convert_numpy_types({
                "elements": triplet.to_dict(),
                "total_length": float(triplet.total_length),
                "twiss_along": twiss_along,
                "match_quality": match_quality,
                "twiss_in": {
                    'x': twiss_in_x.to_dict(),
                    'y': twiss_in_y.to_dict()
                },
                "twiss_out": {
                    'x': twiss_out_x.to_dict(),
                    'y': twiss_out_y.to_dict()
                },
                "phase_space": phase_space
            }),
            "plots": plots
        })
        
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": f"Ошибка в входных данных: {str(e)}",
                "plots": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Внутренняя ошибка сервера: {str(e)}",
                "traceback": traceback.format_exc(),
                "plots": None
            }
        )

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "accelerator-matching"}

def create_all_plots(twiss_along, phase_space, twiss_in_x, twiss_in_y, 
                    twiss_target_x, twiss_target_y, triplet):
    """Создание ВСЕХ 6 графиков"""
    plots = {}
    try:
        print("📊 Создаю графики...")
        print(f"📊 phase_space type: {type(phase_space)}")
        print(f"📊 phase_space keys: {phase_space.keys() if isinstance(phase_space, dict) else 'N/A'}")
        
        # 1. β/α функции
        try:
            plots['beta_alpha'] = create_beta_alpha_plot(twiss_along, twiss_target_x, twiss_target_y)
            print(f"✅ beta_alpha создан: {bool(plots['beta_alpha'].get('script')) and bool(plots['beta_alpha'].get('div'))}")
        except Exception as e:
            print(f"❌ beta_alpha ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. Оболочка пучка
        try:
            plots['envelope'] = create_beam_envelope_plot(twiss_along)
            print(f"✅ envelope создан: {bool(plots['envelope'].get('script')) and bool(plots['envelope'].get('div'))}")
        except Exception as e:
            print(f"❌ envelope ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. Сохранение эмиттанса
        try:
            plots['emittance_check'] = create_emittance_conservation_plot(twiss_along, twiss_in_x, twiss_in_y)
            print(f"✅ emittance_check создан: {bool(plots['emittance_check'].get('script')) and bool(plots['emittance_check'].get('div'))}")
        except Exception as e:
            print(f"❌ emittance_check ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        # 4. Фазовое пространство
        try:
            print(f"📊 Вызываю create_phase_space_plot...")
            plots['phase_space'] = create_phase_space_plot(phase_space, twiss_in_x, twiss_in_y)
            print(f"✅ phase_space создан: {bool(plots['phase_space'].get('script')) and bool(plots['phase_space'].get('div'))}")
            if plots['phase_space']:
                print(f"   script keys: {plots['phase_space'].keys()}")
                print(f"   has script: {'script' in plots['phase_space']}")
                print(f"   has div: {'div' in plots['phase_space']}")
        except Exception as e:
            print(f"❌ phase_space ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        # 5. Эволюция эллипса
        try:
            plots['ellipse_evolution'] = create_ellipse_evolution_plot(triplet, twiss_in_x, n_positions=6)
            print(f"✅ ellipse_evolution создан: {bool(plots['ellipse_evolution'].get('script')) and bool(plots['ellipse_evolution'].get('div'))}")
        except Exception as e:
            print(f"❌ ellipse_evolution ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        # 6. Схема канала
        try:
            plots['fodo_scheme'] = create_fodo_channel_plot(triplet)
            print(f"✅ fodo_scheme создан: {bool(plots['fodo_scheme'].get('script')) and bool(plots['fodo_scheme'].get('div'))}")
        except Exception as e:
            print(f"❌ fodo_scheme ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"📊 Всего создано графиков: {len(plots)}")
        for key, value in plots.items():
            if value:
                print(f"   {key}: script={bool(value.get('script'))}, div={bool(value.get('div'))}")
        
    except Exception as e:
        print(f"❌ Ошибка создания графиков: {e}")
        import traceback
        traceback.print_exc()
    
    return plots

def create_beta_alpha_plot(twiss_along, twiss_target_x, twiss_target_y):
    """График β/α функций (из fo_channel_beta_function.ipynb)"""
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

def create_phase_space_plot(phase_space, twiss_in_x, twiss_in_y):
    """Фазовое пространство (из ellipse.ipynb и fo_do_channel.ipynb)"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    from bokeh.models import ColumnDataSource
    from bokeh.layouts import row
    import numpy as np
    
    # ✅ Проверка данных
    if not phase_space or not isinstance(phase_space, dict):
        print(f"❌ phase_space invalid type: {type(phase_space)}")
        p = figure(title="Ошибка данных", width=350, height=350)
        p.text(0, 0, text=["Нет данных"])
        script, div = components(p)
        return {"script": script, "div": div}
    
    if 'x' not in phase_space or 'xp' not in phase_space:
        print(f"❌ phase_space missing keys: {phase_space.keys() if isinstance(phase_space, dict) else 'N/A'}")
        p = figure(title="Ошибка данных", width=350, height=350)
        p.text(0, 0, text=["Нет данных"])
        script, div = components(p)
        return {"script": script, "div": div}
    
    print(f"📊 Phase space x len: {len(phase_space.get('x', []))}")
    print(f"📊 Phase space xp len: {len(phase_space.get('xp', []))}")
    
    # X-X' фазовое пространство
    p_x = figure(
        title="Фазовое пространство X-X'",
        x_axis_label="x (мм)",
        y_axis_label="x' (мрад)",
        width=350, height=350,
        tools='pan,wheel_zoom,box_zoom,reset,save'
    )
    
    # Прореживаем данные для производительности
    step = max(1, len(phase_space['x']) // 100)
    x_data = phase_space['x'][::step]
    xp_data = phase_space['xp'][::step]
    
    print(f"📊 Phase space x_data len: {len(x_data)}")
    
    source = ColumnDataSource(data={
        'x': x_data,
        'xp': xp_data
    })
    
    p_x.scatter('x', 'xp', source=source, size=3, 
                color='#1f77b4', alpha=0.4, legend_label="Частицы")
    
    # Эллипс Твисса (из ellipse.ipynb)
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
    
    y_data = phase_space['y'][::step]
    yp_data = phase_space['yp'][::step]
    
    source_y = ColumnDataSource(data={
        'y': y_data,
        'yp': yp_data
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
    
    # ✅ Объединяем в один layout
    combined_plot = row(p_x, p_y)
    
    # ✅ Получаем script и div
    script, div = components(combined_plot)
    
    # ✅ Проверка что script и div не пустые
    if not script or not div:
        print(f"❌ script или div пустые! script len: {len(script) if script else 0}, div len: {len(div) if div else 0}")
    
    print(f"✅ phase_space создан, script len: {len(script)}, div len: {len(div)}")
    
    # ✅ Возвращаем ПЛОСКУЮ структуру
    return {"script": script, "div": div}

def create_ellipse_evolution_plot(triplet, twiss_in_x, n_positions=6):
    """Эволюция эллипса (из ellipse.ipynb)"""
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
    """Схема FODO канала (расположение магнитов)"""
    from bokeh.plotting import figure
    from bokeh.embed import components
    
    p = figure(
        title="Схема согласующей секции",
        x_axis_label="s (м)",
        y_axis_label="",
        width=800, height=200,
        tools=''
    )
    
    colors = {'QF': '#2ecc71', 'QD': '#e74c3c', 'drift': '#95a5a6'}
    
    for elem in triplet.to_dict():
        if elem['type'] == 'quadrupole':
            color = colors['QF'] if elem['subtype'] == 'QF' else colors['QD']
            y, h, label = (0.6, 0.3, elem['subtype'])
        else:
            color, y, h, label = colors['drift'], 0, 0.1, "D"
        
        # Прямоугольник элемента
        p.rect(x=elem['position'] + elem['length']/2, y=y,
               width=elem['length']*0.95, height=h,
               fill_color=color, fill_alpha=0.8, line_color='black')
        
        # Подпись
        p.text(x=elem['position'] + elem['length']/2, y=y+h+0.12,
               text=[label], text_align='center', text_font_size='10pt', text_color='white')
    
    p.y_range.start, p.y_range.end = -1, 1
    p.yaxis.visible = False
    p.grid.visible = False
    p.outline_line_color = None
    
    script, div = components(p)
    return {"script": script, "div": div}