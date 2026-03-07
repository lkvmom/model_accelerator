import numpy as np
from typing import Dict

class TwissParameters:
    """Класс для работы с Twiss параметрами"""
    
    def __init__(self, beta: float, alpha: float, emittance: float):
        self.beta = float(beta)
        self.alpha = float(alpha)
        self.gamma = float((1 + alpha**2) / beta) if beta > 0 else 1.0
        self.emittance = float(emittance)
    
    @classmethod
    def from_normalized(cls, beta: float, alpha: float, 
                        emittance_norm: float, energy: float,
                        particle_type: str = 'proton'):
        masses = {'proton': 938.272, 'electron': 0.511, 'ion': 1000}
        m0c2 = masses.get(particle_type, 938.272)
        
        gamma = 1 + energy / m0c2
        beta_rel = np.sqrt(max(0, 1 - 1/gamma**2))
        
        emittance_geom = emittance_norm * 1e-9 / (beta_rel * gamma)
        
        return cls(beta, alpha, emittance_geom)
    
    def get_beam_size(self) -> float:
        return float(np.sqrt(self.beta * self.emittance))
    
    def get_divergence(self) -> float:
        return float(np.sqrt(self.gamma * self.emittance))
    
    def transform(self, M: np.ndarray):
        beta_new = float((M[0,0]**2) * self.beta - 2*M[0,0]*M[0,1]*self.alpha + (M[0,1]**2) * self.gamma)
        alpha_new = float(-M[0,0]*M[1,0]*self.beta + (M[0,0]*M[1,1] + M[0,1]*M[1,0])*self.alpha - M[0,1]*M[1,1]*self.gamma)
        beta_new = max(beta_new, 0.01)
        gamma_new = float((1 + alpha_new**2) / beta_new)
        
        return TwissParameters(beta_new, alpha_new, self.emittance)
    
    def to_dict(self) -> Dict:
        return {
            'beta': float(self.beta),
            'alpha': float(self.alpha),
            'gamma': float(self.gamma),
            'emittance': float(self.emittance),
            'beam_size_mm': float(self.get_beam_size() * 1000),
            'divergence_mrad': float(self.get_divergence() * 1000)
        }