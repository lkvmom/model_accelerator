document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('matching-form');
    const runBtn = document.getElementById('run-btn');
    const statusDiv = document.getElementById('status');
    const plotsContainer = document.getElementById('plots-container');
    const statsContainer = document.getElementById('stats-container');
    const vizSelector = document.getElementById('viz-selector');
    const vizTypeSelect = document.getElementById('viz-type');
    
    let allPlots = {};
    let currentFormData = {};
    
    const presets = {
        'default': {beta_x_in: 5.0, beta_y_in: 2.5, alpha_x_in: -0.5, alpha_y_in: 0.3, emittance_x: 10.0, emittance_y: 2.0, beta_x_out: 8.0, beta_y_out: 4.0, alpha_x_out: 0.0, alpha_y_out: 0.0, energy: 10.0, max_gradient: 20.0},
        'low_energy': {beta_x_in: 3.0, beta_y_in: 1.5, alpha_x_in: -0.3, alpha_y_in: 0.2, emittance_x: 5.0, emittance_y: 1.0, beta_x_out: 5.0, beta_y_out: 3.0, alpha_x_out: 0.0, alpha_y_out: 0.0, energy: 1.0, max_gradient: 10.0},
        'high_energy': {beta_x_in: 10.0, beta_y_in: 5.0, alpha_x_in: -1.0, alpha_y_in: 0.5, emittance_x: 20.0, emittance_y: 4.0, beta_x_out: 15.0, beta_y_out: 8.0, alpha_x_out: 0.0, alpha_y_out: 0.0, energy: 100.0, max_gradient: 50.0}
    };
    
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const preset = presets[e.target.dataset.preset];
            if (preset) {
                document.getElementById('beta_x_in').value = preset.beta_x_in;
                document.getElementById('beta_y_in').value = preset.beta_y_in;
                document.getElementById('alpha_x_in').value = preset.alpha_x_in;
                document.getElementById('alpha_y_in').value = preset.alpha_y_in;
                document.getElementById('emittance_x').value = preset.emittance_x;
                document.getElementById('emittance_y').value = preset.emittance_y;
                document.getElementById('beta_x_out').value = preset.beta_x_out;
                document.getElementById('beta_y_out').value = preset.beta_y_out;
                document.getElementById('alpha_x_out').value = preset.alpha_x_out;
                document.getElementById('alpha_y_out').value = preset.alpha_y_out;
                document.getElementById('energy').value = preset.energy;
                document.getElementById('max_gradient').value = preset.max_gradient;
                statusDiv.className = 'status-panel success';
                statusDiv.innerHTML = `✅ Пресет загружен`;
                setTimeout(() => statusDiv.innerHTML = '', 3000);
            }
        });
    });
    
    vizTypeSelect.addEventListener('change', (e) => {
        if (allPlots[e.target.value]) renderPlot(allPlots[e.target.value]);
    });
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        runBtn.disabled = true;
        runBtn.textContent = '⏳ Расчёт...';
        statusDiv.className = 'status-panel loading';
        statusDiv.innerHTML = '🔄 Расчёт...';
        
        try {
            currentFormData = {
                input: {
                    beta_x: parseFloat(document.getElementById('beta_x_in').value),
                    beta_y: parseFloat(document.getElementById('beta_y_in').value),
                    alpha_x: parseFloat(document.getElementById('alpha_x_in').value),
                    alpha_y: parseFloat(document.getElementById('alpha_y_in').value),
                    emittance_x: parseFloat(document.getElementById('emittance_x').value),
                    emittance_y: parseFloat(document.getElementById('emittance_y').value)
                },
                target: {
                    beta_x: parseFloat(document.getElementById('beta_x_out').value),
                    beta_y: parseFloat(document.getElementById('beta_y_out').value),
                    alpha_x: parseFloat(document.getElementById('alpha_x_out').value),
                    alpha_y: parseFloat(document.getElementById('alpha_y_out').value)
                },
                energy: parseFloat(document.getElementById('energy').value),
                particle_type: document.getElementById('particle_type').value,
                max_quad_gradient: parseFloat(document.getElementById('max_gradient').value)
            };
            
            const response = await fetch('/api/matching', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(currentFormData)
            });
            
            const result = await response.json();
            console.log('📊 Результат:', result);
            
            if (result.success) {
                statusDiv.className = 'status-panel success';
                statusDiv.innerHTML = '✅ ' + result.message;
                displayPlots(result.plots);
                displayStats(result.data);
            } else {
                statusDiv.className = 'status-panel error';
                statusDiv.innerHTML = '⚠️ ' + result.message;
            }
        } catch (error) {
            statusDiv.className = 'status-panel error';
            statusDiv.innerHTML = '❌ Ошибка: ' + error.message;
            console.error('Error:', error);
        } finally {
            runBtn.disabled = false;
            runBtn.textContent = '🚀 Рассчитать';
        }
    });
    
    function displayPlots(plots) {
        if (!plots || Object.keys(plots).length === 0) {
            plotsContainer.innerHTML = '<div class="placeholder"><p>⚠️ Нет данных</p></div>';
            return;
        }
        allPlots = plots;
        vizSelector.style.display = 'flex';
        const defaultViz = plots['beta_alpha'] ? 'beta_alpha' : Object.keys(plots)[0];
        renderPlot(plots[defaultViz]);
        vizTypeSelect.value = defaultViz;
    }
    
    function renderPlot(plotData) {
        if (!plotData || !plotData.script || !plotData.div) {
            console.error('❌ Нет данных графика:', plotData);
            plotsContainer.innerHTML = '<div class="placeholder"><p>⚠️ Ошибка загрузки графика</p></div>';
            return;
        }
        
        // ✅ Очищаем контейнер
        plotsContainer.innerHTML = '';
        
        // ✅ Создаём обёртку
        const wrapper = document.createElement('div');
        wrapper.className = 'plots-grid';
        
        const plotWrapper = document.createElement('div');
        plotWrapper.className = 'plot-wrapper';
        
        // ✅ Вставляем div с графиком
        plotWrapper.innerHTML = plotData.div;
        wrapper.appendChild(plotWrapper);
        
        // ✅ Вставляем script программно (чтобы выполнился!)
        const scriptContainer = document.createElement('div');
        scriptContainer.innerHTML = plotData.script;
        const scripts = scriptContainer.getElementsByTagName('script');
        
        for (let script of scripts) {
            const newScript = document.createElement('script');
            newScript.type = script.type || 'text/javascript';
            if (script.src) {
                newScript.src = script.src;
            } else {
                newScript.textContent = script.textContent;
            }
            document.head.appendChild(newScript);
        }
        
        plotsContainer.appendChild(wrapper);
        console.log('📈 График отрисован успешно');
    }
    
    function displayStats(data) {
        statsContainer.style.display = 'block';
        
        let elementsHtml = '';
        data.elements.forEach((elem, i) => {
            if (elem.type === 'quadrupole') {
                elementsHtml += `<div class="element-item"><label>${elem.subtype} @ ${elem.position.toFixed(2)}м</label><span>L=${elem.length.toFixed(3)}м, G=${elem.gradient.toFixed(1)}Тл/м</span></div>`;
            } else {
                elementsHtml += `<div class="element-item"><label>Дрейф @ ${elem.position.toFixed(2)}м</label><span>L=${elem.length.toFixed(3)}м</span></div>`;
            }
        });
        
        const q = data.match_quality;
        const qualityHtml = `
            <div class="stat-item"><label>Ошибка β_x</label><span style="color: ${q.beta_x_error < 5 ? '#4ade80' : '#f87171'}">${q.beta_x_error.toFixed(2)}%</span></div>
            <div class="stat-item"><label>Ошибка β_y</label><span style="color: ${q.beta_y_error < 5 ? '#4ade80' : '#f87171'}">${q.beta_y_error.toFixed(2)}%</span></div>
            <div class="stat-item"><label>Ошибка α_x</label><span style="color: ${q.alpha_x_error < 0.1 ? '#4ade80' : '#f87171'}">${q.alpha_x_error.toFixed(3)}</span></div>
            <div class="stat-item"><label>Ошибка α_y</label><span style="color: ${q.alpha_y_error < 0.1 ? '#4ade80' : '#f87171'}">${q.alpha_y_error.toFixed(3)}</span></div>
            <div class="stat-item"><label>Эмиттанс X</label><span style="color: ${q.emittance_preserved_x ? '#4ade80' : '#f87171'}">${q.emittance_preserved_x ? '✅' : '⚠️'}</span></div>
            <div class="stat-item"><label>Эмиттанс Y</label><span style="color: ${q.emittance_preserved_y ? '#4ade80' : '#f87171'}">${q.emittance_preserved_y ? '✅' : '⚠️'}</span></div>
        `;
        
        const twissHtml = `
            <div class="stat-item"><label>β_x (вход → выход)</label><span>${data.twiss_in.x.beta.toFixed(2)} → ${data.twiss_out.x.beta.toFixed(2)} м</span></div>
            <div class="stat-item"><label>β_y (вход → выход)</label><span>${data.twiss_in.y.beta.toFixed(2)} → ${data.twiss_out.y.beta.toFixed(2)} м</span></div>
            <div class="stat-item"><label>α_x (вход → выход)</label><span>${data.twiss_in.x.alpha.toFixed(2)} → ${data.twiss_out.x.alpha.toFixed(2)}</span></div>
            <div class="stat-item"><label>α_y (вход → выход)</label><span>${data.twiss_in.y.alpha.toFixed(2)} → ${data.twiss_out.y.alpha.toFixed(2)}</span></div>
        `;
        
        const additionalHtml = `
            <div class="stat-item"><label>Длина секции</label><span>${data.total_length.toFixed(3)} м</span></div>
            <div class="stat-item"><label>Элементов</label><span>${data.elements.length}</span></div>
            <div class="stat-item"><label>Энергия</label><span>${currentFormData.energy} МэВ</span></div>
            <div class="stat-item"><label>Тип частиц</label><span>${currentFormData.particle_type}</span></div>
        `;
        
        document.getElementById('elements-list').innerHTML = elementsHtml;
        document.getElementById('match-quality').innerHTML = qualityHtml;
        document.getElementById('twiss-comparison').innerHTML = twissHtml;
        document.getElementById('additional-stats').innerHTML = additionalHtml;
    }
});