import numpy as np
from scipy.optimize import minimize, differential_evolution
from typing import Dict, Tuple
from .twiss import TwissParameters
from .elements import MatchingTriplet

class MatchingSolver:
    """Решатель задачи согласования параметров пучка"""
    
    def __init__(self, twiss_in_x: TwissParameters, twiss_in_y: TwissParameters,
                 twiss_target_x: TwissParameters, twiss_target_y: TwissParameters,
                 rigidity: float, max_gradient: float = 20.0):
        self.twiss_in_x = twiss_in_x
        self.twiss_in_y = twiss_in_y
        self.twiss_target_x = twiss_target_x
        self.twiss_target_y = twiss_target_y
        self.rigidity = rigidity
        self.max_gradient = max_gradient
        
        print(f"🔧 MatchingSolver инициализирован")
        print(f"   rigidity: {rigidity:.4f} Тл·м")
        print(f"   max_gradient: {max_gradient} Тл/м")
    
    def objective(self, params):
        try:
            g1, g2, g3 = params[0:3]
            d1, d2, d3, d4 = params[3:7]
            
            # ✅ Плавный штраф за большие градиенты (не бинарный!)
            max_g = max(abs(g1), abs(g2), abs(g3))
            gradient_penalty = 0
            if max_g > 30:
                gradient_penalty = 0.01 * (max_g - 30)**2  # Квадратичный рост
            
            triplet = MatchingTriplet(
                q1_length=0.15, q2_length=0.15, q3_length=0.15,
                drift1=d1, drift2=d2, drift3=d3, drift4=d4,
                gradients=(g1, g2, g3),
                rigidity=self.rigidity
            )
            
            # ✅ Проверка устойчивости с плавным штрафом
            if not triplet.is_stable():
                trace_x = np.trace(triplet.get_transfer_matrix_x())
                trace_y = np.trace(triplet.get_transfer_matrix_y())
                # Штраф растёт постепенно по мере потери устойчивости
                stability_penalty = 10 * (max(abs(trace_x), abs(trace_y)) - 2)**2
                return stability_penalty + gradient_penalty
            
            M_x = triplet.get_transfer_matrix_x()
            M_y = triplet.get_transfer_matrix_y()
            
            # ✅ Проверка на NaN/Inf с плавным штрафом
            if np.any(np.isnan(M_x)) or np.any(np.isinf(M_x)):
                return 100 + gradient_penalty
            
            twiss_out_x = self.twiss_in_x.transform(M_x)
            twiss_out_y = self.twiss_in_y.transform(M_y)
            
            if twiss_out_x.beta <= 0 or twiss_out_y.beta <= 0:
                return 100 + gradient_penalty
            
            # Основная ошибка согласования
            error = (
                ((twiss_out_x.beta - self.twiss_target_x.beta) / self.twiss_target_x.beta)**2 +
                ((twiss_out_x.alpha - self.twiss_target_x.alpha))**2 +
                ((twiss_out_y.beta - self.twiss_target_y.beta) / self.twiss_target_y.beta)**2 +
                ((twiss_out_y.alpha - self.twiss_target_y.alpha))**2
            )
            
            return float(error) + gradient_penalty
            
        except Exception:
            return 1000  # Было 1e10
    
    def solve(self) -> Dict:
        """Решение задачи согласования"""
        # ✅ Более реалистичные начальные значения
        x0 = [0.0, 0.0, 0.0, 0.5, 0.5, 0.5, 0.5]
        
        # ✅ Расширенные ограничения
        bounds = [
            (-self.max_gradient, self.max_gradient),  # g1 в Тл/м
            (-self.max_gradient, self.max_gradient),  # g2
            (-self.max_gradient, self.max_gradient),  # g3
            (0.1, 2.0),    # d1 в метрах
            (0.1, 2.0),    # d2
            (0.1, 2.0),    # d3
            (0.1, 2.0)     # d4
        ]
        
        print(f"🔍 Начинаю оптимизацию... (max_gradient={self.max_gradient} Тл/м)")
        
        # ✅ Сначала пробуем L-BFGS-B с более мягкими параметрами
        result = minimize(
            self.objective,
            x0,
            method='L-BFGS-B',
            bounds=bounds,
            options={
                'maxiter': 5000,
                'ftol': 1e-8,
                'gtol': 1e-5,
                'disp': False,
                'maxls': 20
            }
        )
        
        # ✅ Если ошибка маленькая, считаем что успешно
        if result.fun < 0.01 and not np.isinf(result.fun):
            print(f"✅ L-BFGS-B сошёлся! Ошибка: {result.fun:.6f}")
            return self._build_result(result.x, result.fun)
        
        # ✅ Если L-BFGS-B не сошёлся, пробуем differential evolution
        print(f"⚠️ L-BFGS-B не сошёлся (ошибка: {result.fun:.2e}), пробую differential_evolution...")
        
        result_de = differential_evolution(
            self.objective,
            bounds,
            maxiter=1000,
            tol=1e-8,
            polish=True,
            disp=False,
            seed=42
        )
        
        if result_de.fun < 0.01 and not np.isinf(result_de.fun):
            print(f"✅ differential_evolution сошёлся! Ошибка: {result_de.fun:.6f}")
            return self._build_result(result_de.x, result_de.fun)
        
        # ✅ Если оба не сошлись
        print(f"❌ Оптимизация не сошлась: {result.message}, ошибка: {result.fun:.6f}")
        return {
            'success': False,
            'message': f"❌ Оптимизация не сошлась: {result.message}. Попробуйте другие входные параметры.",
            'error': float(result.fun) if not np.isinf(result.fun) else float('inf')
        }
    
    def _build_result(self, x, error):
        """Построение результата оптимизации"""
        g1, g2, g3 = x[0:3]
        d1, d2, d3, d4 = x[3:7]
        
        triplet = MatchingTriplet(
            q1_length=0.15, q2_length=0.15, q3_length=0.15,
            drift1=d1, drift2=d2, drift3=d3, drift4=d4,
            gradients=(g1, g2, g3),
            rigidity=self.rigidity
        )
        
        M_x = triplet.get_transfer_matrix_x()
        M_y = triplet.get_transfer_matrix_y()
        
        twiss_out_x = self.twiss_in_x.transform(M_x)
        twiss_out_y = self.twiss_in_y.transform(M_y)
        
        return {
            'success': True,
            'triplet': triplet,
            'gradients': (float(g1), float(g2), float(g3)),
            'drifts': (float(d1), float(d2), float(d3), float(d4)),
            'twiss_out_x': twiss_out_x,
            'twiss_out_y': twiss_out_y,
            'error': float(error),
            'message': f"✅ Согласование достигнуто (ошибка: {error:.6f})"
        }