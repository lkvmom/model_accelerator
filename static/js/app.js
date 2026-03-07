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
    
    // ✅ Константы для валидации
    const VALIDATION_RULES = {
        beta: { min: 0.1, max: 100, name: 'β' },
        alpha: { min: -10, max: 10, name: 'α' },
        emittance: { min: 0.1, max: 1000, name: 'ε' },
        energy: { min: 0.1, max: 1000, name: 'Энергия' },
        gradient: { min: 1, max: 100, name: 'Градиент' }
    };
    
    const presets = {
        'default': {beta_x_in: 5.0, beta_y_in: 2.5, alpha_x_in: -0.5, alpha_y_in: 0.3, emittance_x: 10.0, emittance_y: 2.0, beta_x_out: 8.0, beta_y_out: 4.0, alpha_x_out: 0.0, alpha_y_out: 0.0, energy: 10.0, max_gradient: 30.0},
        'low_energy': {beta_x_in: 3.0, beta_y_in: 1.5, alpha_x_in: -0.3, alpha_y_in: 0.2, emittance_x: 5.0, emittance_y: 1.0, beta_x_out: 5.0, beta_y_out: 3.0, alpha_x_out: 0.0, alpha_y_out: 0.0, energy: 1.0, max_gradient: 15.0},
        'high_energy': {beta_x_in: 10.0, beta_y_in: 5.0, alpha_x_in: -1.0, alpha_y_in: 0.5, emittance_x: 20.0, emittance_y: 4.0, beta_x_out: 15.0, beta_y_out: 8.0, alpha_x_out: 0.0, alpha_y_out: 0.0, energy: 100.0, max_gradient: 50.0}
    };
    
    // ✅ Функция валидации
    function validateInput() {
        const errors = [];
        
        // Получаем значения
        const values = {
            'β_x вход': {value: parseFloat(document.getElementById('beta_x_in').value), rule: VALIDATION_RULES.beta},
            'β_y вход': {value: parseFloat(document.getElementById('beta_y_in').value), rule: VALIDATION_RULES.beta},
            'α_x вход': {value: parseFloat(document.getElementById('alpha_x_in').value), rule: VALIDATION_RULES.alpha},
            'α_y вход': {value: parseFloat(document.getElementById('alpha_y_in').value), rule: VALIDATION_RULES.alpha},
            'ε_x': {value: parseFloat(document.getElementById('emittance_x').value), rule: VALIDATION_RULES.emittance},
            'ε_y': {value: parseFloat(document.getElementById('emittance_y').value), rule: VALIDATION_RULES.emittance},
            'β_x выход': {value: parseFloat(document.getElementById('beta_x_out').value), rule: VALIDATION_RULES.beta},
            'β_y выход': {value: parseFloat(document.getElementById('beta_y_out').value), rule: VALIDATION_RULES.beta},
            'α_x выход': {value: parseFloat(document.getElementById('alpha_x_out').value), rule: VALIDATION_RULES.alpha},
            'α_y выход': {value: parseFloat(document.getElementById('alpha_y_out').value), rule: VALIDATION_RULES.alpha},
            'Энергия': {value: parseFloat(document.getElementById('energy').value), rule: VALIDATION_RULES.energy},
            'Градиент': {value: parseFloat(document.getElementById('max_gradient').value), rule: VALIDATION_RULES.gradient}
        };
        
        // ✅ Проверка каждого значения
        for (const [name, data] of Object.entries(values)) {
            if (isNaN(data.value)) {
                errors.push(`${name}: некорректное число`);
            } else if (data.value < data.rule.min || data.value > data.rule.max) {
                errors.push(`${name}: должно быть от ${data.rule.min} до ${data.rule.max}`);
            }
        }
        
        // ✅ Проверка: выходной β должен быть больше входного (для ускорителя)
        const beta_x_in = values['β_x вход'].value;
        const beta_x_out = values['β_x выход'].value;
        const beta_y_in = values['β_y вход'].value;
        const beta_y_out = values['β_y выход'].value;
        
        if (!isNaN(beta_x_in) && !isNaN(beta_x_out)) {
            if (beta_x_out < beta_x_in * 0.5 || beta_x_out > beta_x_in * 10) {
                errors.push('β_x выход должен быть в 0.5-10 раз от β_x вход');
            }
        }
        
        if (!isNaN(beta_y_in) && !isNaN(beta_y_out)) {
            if (beta_y_out < beta_y_in * 0.5 || beta_y_out > beta_y_in * 10) {
                errors.push('β_y выход должен быть в 0.5-10 раз от β_y вход');
            }
        }
        
        return errors;
    }
    
    // ✅ Функция отображения ошибок валидации
    function showValidationErrors(errors) {
        statusDiv.className = 'status-panel error';
        statusDiv.innerHTML = `
            <strong>⚠️ Ошибки валидации:</strong>
            <ul style="margin: 10px 0 0 20px; padding: 0;">
                ${errors.map(err => `<li>${err}</li>`).join('')}
            </ul>
        `;
    }
    
    // Обработчик пресетов
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
                statusDiv.innerHTML = `✅ Пресет "${e.target.dataset.preset}" загружен`;
                setTimeout(() => statusDiv.innerHTML = '', 3000);
            }
        });
    });
    
    vizTypeSelect.addEventListener('change', (e) => {
        if (allPlots[e.target.value]) renderPlot(allPlots[e.target.value]);
    });
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // ✅ 1. Валидация входных данных
        const validationErrors = validateInput();
        if (validationErrors.length > 0) {
            showValidationErrors(validationErrors);
            return;
        }
        
        runBtn.disabled = true;
        runBtn.textContent = '⏳ Расчёт...';
        statusDiv.className = 'status-panel loading';
        statusDiv.innerHTML = '🔄 Расчёт согласующей секции...';
        
        // ✅ Скрываем старые результаты
        plotsContainer.innerHTML = '<div class="placeholder"><p>⏳ Загрузка результатов...</p></div>';
        statsContainer.style.display = 'none';
        
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
                max_gradient: parseFloat(document.getElementById('max_gradient').value)
            };
            
            console.log('🔍 Отправка:', currentFormData);
            
            const response = await fetch('/api/matching', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(currentFormData)
            });
            
            console.log('📥 Статус ответа:', response.status);
            
            // ✅ 2. Проверка статуса ответа
            if (!response.ok) {
                throw new Error(`Ошибка сервера: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('📊 Результат:', result);
            
            // ✅ 3. Проверка успеха
            if (result.success) {
                statusDiv.className = 'status-panel success';
                statusDiv.innerHTML = '✅ ' + result.message;
                
                // ✅ 4. Проверка данных для графиков
                if (result.plots && Object.keys(result.plots).length > 0) {
                    displayPlots(result.plots);
                } else {
                    plotsContainer.innerHTML = '<div class="placeholder"><p>⚠️ Графики не созданы</p></div>';
                }
                
                // ✅ 5. Проверка данных для статистики
                if (result.data) {
                    displayStats(result.data);
                }
            } else {
                // ✅ 6. Обработка ошибки от сервера
                statusDiv.className = 'status-panel error';
                statusDiv.innerHTML = `⚠️ ${result.message || 'Ошибка расчёта'}`;
                plotsContainer.innerHTML = '<div class="placeholder"><p>⚠️ Расчёт не выполнен</p></div>';
            }
        } catch (error) {
            // ✅ 7. Обработка исключений
            console.error('❌ Error:', error);
            statusDiv.className = 'status-panel error';
            
            let errorMessage = error.message;
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorMessage = 'Нет соединения с сервером. Проверьте, запущен ли сервер.';
            } else if (error.name === 'SyntaxError') {
                errorMessage = 'Ошибка формата ответа сервера.';
            }
            
            statusDiv.innerHTML = `❌ Ошибка: ${errorMessage}`;
            plotsContainer.innerHTML = '<div class="placeholder"><p>❌ Произошла ошибка при расчёте</p></div>';
        } finally {
            runBtn.disabled = false;
            runBtn.textContent = '🚀 Рассчитать';
        }
    });
    
    function displayPlots(plots) {
        if (!plots || Object.keys(plots).length === 0) {
            plotsContainer.innerHTML = '<div class="placeholder"><p>⚠️ Нет данных для отображения</p></div>';
            return;
        }
        allPlots = plots;
        vizSelector.style.display = 'flex';
        
        const availableTypes = Object.keys(plots).filter(key => plots[key]);
        console.log('📊 Доступные графики:', availableTypes);
        
        const defaultViz = availableTypes.includes('beta_alpha') ? 'beta_alpha' : availableTypes[0];
        
        if (defaultViz) {
            renderPlot(plots[defaultViz]);
            vizTypeSelect.value = defaultViz;
        }
    }
    
    function renderPlot(plotData) {

        console.log('🎨 renderPlot получил:', {
            hasScript: !!plotData?.script,
            hasDiv: !!plotData?.div,
            keys: plotData ? Object.keys(plotData) : 'null',
            type: typeof plotData,
            isPhaseSpace: plotData?.x || plotData?.y  // Проверка на вложенную структуру
        });
        
        // ✅ Проверка на null/undefined
        if (!plotData) {
            console.error('❌ plotData is null/undefined');
            plotsContainer.innerHTML = '<div class="placeholder"><p>⚠️ Данные графика недоступны</p></div>';
            return;
        }
        
        // ✅ Проверка структуры (поддержка обоих форматов)
        let script, div;
        
        if (Array.isArray(plotData)) {
            script = plotData[0];
            div = plotData[1];
        } else if (typeof plotData === 'object') {
            script = plotData.script;
            div = plotData.div;
        }
        
        if (!script || !div) {
            console.error('❌ Нет script или div:', {hasScript: !!script, hasDiv: !!div});
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
        plotWrapper.innerHTML = div;
        wrapper.appendChild(plotWrapper);
        
        // ✅ Надёжная вставка скриптов
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = script;
        const scripts = Array.from(tempDiv.getElementsByTagName('script'));
        
        let scriptIndex = 0;
        function executeNextScript() {
            if (scriptIndex >= scripts.length) {
                plotsContainer.appendChild(wrapper);
                console.log('📈 График отрисован успешно');
                return;
            }
            const oldScript = scripts[scriptIndex++];
            const newScript = document.createElement('script');
            for (const attr of oldScript.attributes) {
                newScript.setAttribute(attr.name, attr.value);
            }
            if (oldScript.src) {
                newScript.src = oldScript.src;
                newScript.onload = executeNextScript;
                newScript.onerror = () => { 
                    console.error('❌ Ошибка загрузки скрипта:', oldScript.src); 
                    executeNextScript(); 
                };
            } else {
                newScript.textContent = oldScript.textContent;
                setTimeout(executeNextScript, 0);
            }
            document.head.appendChild(newScript);
        }
        executeNextScript();
    }
    
    function displayStats(data) {
        // ✅ Проверка данных
        if (!data) {
            console.error('❌ Нет данных для статистики');
            return;
        }
        
        statsContainer.style.display = 'block';
        
        let elementsHtml = '';
        if (data.elements && Array.isArray(data.elements)) {
            data.elements.forEach((elem, i) => {
                if (elem.type === 'quadrupole') {
                    elementsHtml += `<div class="element-item"><label>${elem.subtype || '?'} @ ${(elem.position||0).toFixed(2)}м</label><span>L=${(elem.length||0).toFixed(3)}м, G=${(elem.gradient||0).toFixed(1)}Тл/м</span></div>`;
                } else {
                    elementsHtml += `<div class="element-item"><label>Дрейф @ ${(elem.position||0).toFixed(2)}м</label><span>L=${(elem.length||0).toFixed(3)}м</span></div>`;
                }
            });
        }
        
        const q = data.match_quality || {};
        const qualityHtml = `
            <div class="stat-item"><label>Ошибка β_x</label><span style="color: ${(q.beta_x_error??999)<5?'#4ade80':'#f87171'}">${(q.beta_x_error??999).toFixed(2)}%</span></div>
            <div class="stat-item"><label>Ошибка β_y</label><span style="color: ${(q.beta_y_error??999)<5?'#4ade80':'#f87171'}">${(q.beta_y_error??999).toFixed(2)}%</span></div>
            <div class="stat-item"><label>Ошибка α_x</label><span style="color: ${(q.alpha_x_error??999)<0.1?'#4ade80':'#f87171'}">${(q.alpha_x_error??999).toFixed(3)}</span></div>
            <div class="stat-item"><label>Ошибка α_y</label><span style="color: ${(q.alpha_y_error??999)<0.1?'#4ade80':'#f87171'}">${(q.alpha_y_error??999).toFixed(3)}</span></div>
            <div class="stat-item"><label>Эмиттанс X</label><span style="color: ${q.emittance_preserved_x ? '#4ade80' : '#f87171'}">${q.emittance_preserved_x ? '✅' : '⚠️'}</span></div>
            <div class="stat-item"><label>Эмиттанс Y</label><span style="color: ${q.emittance_preserved_y ? '#4ade80' : '#f87171'}">${q.emittance_preserved_y ? '✅' : '⚠️'}</span></div>
        `;
        
        const twiss_in = data.twiss_in || {x: {}, y: {}};
        const twiss_out = data.twiss_out || {x: {}, y: {}};
        const twissHtml = `
            <div class="stat-item"><label>β_x</label><span>${twiss_in.x.beta?.toFixed(2)||'?'} → ${twiss_out.x.beta?.toFixed(2)||'?'} м</span></div>
            <div class="stat-item"><label>β_y</label><span>${twiss_in.y.beta?.toFixed(2)||'?'} → ${twiss_out.y.beta?.toFixed(2)||'?'} м</span></div>
            <div class="stat-item"><label>α_x</label><span>${twiss_in.x.alpha?.toFixed(2)||'?'} → ${twiss_out.x.alpha?.toFixed(2)||'?'}</span></div>
            <div class="stat-item"><label>α_y</label><span>${twiss_in.y.alpha?.toFixed(2)||'?'} → ${twiss_out.y.alpha?.toFixed(2)||'?'}</span></div>
        `;
        
        const additionalHtml = `
            <div class="stat-item"><label>Длина секции</label><span>${(data.total_length??0).toFixed(3)} м</span></div>
            <div class="stat-item"><label>Элементов</label><span>${data.elements?.length || 0}</span></div>
            <div class="stat-item"><label>Энергия</label><span>${currentFormData.energy || '?'} МэВ</span></div>
            <div class="stat-item"><label>Тип частиц</label><span>${currentFormData.particle_type || '?'}</span></div>
        `;
        
        // ✅ Безопасная установка innerHTML с проверкой существования элементов
        const elementsList = document.getElementById('elements-list');
        const matchQuality = document.getElementById('match-quality');
        const twissComparison = document.getElementById('twiss-comparison');
        const additionalStats = document.getElementById('additional-stats');
        
        if (elementsList) elementsList.innerHTML = elementsHtml;
        else console.warn('⚠️ Элемент elements-list не найден');
        
        if (matchQuality) matchQuality.innerHTML = qualityHtml;
        else console.warn('⚠️ Элемент match-quality не найден');
        
        if (twissComparison) twissComparison.innerHTML = twissHtml;
        else console.warn('⚠️ Элемент twiss-comparison не найден');
        
        if (additionalStats) additionalStats.innerHTML = additionalHtml;
        else console.warn('⚠️ Элемент additional-stats не найден');
    }
});