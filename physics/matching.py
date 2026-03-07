import numpy as np
from scipy.optimize import minimize
from typing import Tuple, Dict
from .twiss import TwissParameters
from .elements import MatchingTriplet

class MatchingSolver:
    def __init__(self, twiss_in_x, twiss_in_y, twiss_target_x, twiss_target_y,
                 rigidity: float, max_gradient: float = 20.0):
        self.twiss_in_x = twiss_in_x
        self.twiss_in_y = twiss_in_y
        self.twiss_target_x = twiss_target_x
        self.twiss_target_y = twiss_target_y
        self.rigidity = rigidity
        self.max_gradient = max_gradient
    
    def objective(self, params):
        g1, g2, g3 = params[0:3] * self.max_gradient
        d1, d2, d3, d4 = params[3:7] * 2.0
        
        try:
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
            
            error = (
                (twiss_out_x.beta - self.twiss_target_x.beta)**2 / self.twiss_target_x.beta**2 +
                (twiss_out_x.alpha - self.twiss_target_x.alpha)**2 +
                (twiss_out_y.beta - self.twiss_target_y.beta)**2 / self.twiss_target_y.beta**2 +
                (twiss_out_y.alpha - self.twiss_target_y.alpha)**2
            )
            
            return float(error)
        except:
            return 1e10
    
    def solve(self, max_iterations: int = 100) -> Dict:
        x0 = np.array([0.5, -0.5, 0.5, 0.3, 0.3, 0.3, 0.3])
        bounds = [(-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0),
                  (0.05, 1.0), (0.05, 1.0), (0.05, 1.0), (0.05, 1.0)]
        
        result = minimize(self.objective, x0, method='L-BFGS-B', bounds=bounds,
                         options={'maxiter': max_iterations})
        
        if result.success:
            g1, g2, g3 = result.x[0:3] * self.max_gradient
            d1, d2, d3, d4 = result.x[3:7] * 2.0
            
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
                'error': float(result.fun),
                'message': f"Согласование достигнуто (ошибка: {result.fun:.6f})"
            }
        else:
            return {'success': False, 'message': f"Не удалось: {result.message}", 'error': float(result.fun)}