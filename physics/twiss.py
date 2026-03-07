import numpy as np
from typing import Dict

class TwissParameters:
    """Класс для работы с параметрами Твисса"""
    
    def __init__(self, beta: float, alpha: float, emittance: float):
        self.beta = float(beta)
        self.alpha = float(alpha)
        self.emittance = float(emittance)
        self.gamma = (1 + self.alpha**2) / self.beta if self.beta > 1e-10 else 1.0
    
    @classmethod
    def from_normalized(cls, beta_norm: float, alpha: float, 
                       emittance_norm: float, energy: float, 
                       particle_type: str = "proton"):
        """Создание из нормированного эмиттанса"""
        masses = {'proton': 938.272, 'electron': 0.511, 'ion': 1000}  # МэВ
        m0c2 = masses.get(particle_type, 938.272)
        
        gamma = 1 + energy / m0c2
        beta_rel = np.sqrt(max(0, 1 - 1/gamma**2))
        
        # ✅ Конверсия: нм·рад → м·рад
        emittance_geom = emittance_norm * 1e-9 / (beta_rel * gamma)
        
        return cls(beta_norm, alpha, emittance_geom)
    
    def transform(self, M: np.ndarray):
        """Трансформация параметров через матрицу переноса"""
        M11, M12 = M[0, 0], M[0, 1]
        M21, M22 = M[1, 0], M[1, 1]
        
        beta_new = M11**2 * self.beta - 2*M11*M12*self.alpha + M12**2 * self.gamma
        alpha_new = -M11*M21*self.beta + (M11*M22 + M12*M21)*self.alpha - M12*M22 * self.gamma
        
        beta_new = max(beta_new, 0.01)  # Защита от отрицательных значений
        gamma_new = (1 + alpha_new**2) / beta_new if beta_new > 1e-10 else 1.0
        
        return TwissParameters(beta_new, alpha_new, self.emittance)
    
    def get_beam_size(self) -> float:
        """Размер пучка (сигма) в метрах"""
        return np.sqrt(self.beta * self.emittance)
    
    def get_divergence(self) -> float:
        """Расходимость пучка в радианах"""
        return np.sqrt(self.gamma * self.emittance)
    
    def to_dict(self) -> Dict:
        return {
            'beta': float(self.beta),
            'alpha': float(self.alpha),
            'gamma': float(self.gamma),
            'emittance': float(self.emittance),
            'beam_size_mm': float(self.get_beam_size() * 1000),
            'divergence_mrad': float(self.get_divergence() * 1000)
        }