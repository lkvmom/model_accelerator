import numpy as np
from typing import Dict
from .twiss import TwissParameters
from .elements import MatchingTriplet

class ParticleTracker:
    """Трекер частиц через секцию ускорителя"""
    
    def __init__(self, triplet: MatchingTriplet, twiss_x: TwissParameters, 
                 twiss_y: TwissParameters, n_particles: int = 1000):
        self.triplet = triplet
        self.twiss_x = twiss_x
        self.twiss_y = twiss_y
        self.n_particles = n_particles
        self.particles = self._generate_particles()
        
        print(f"🔬 ParticleTracker: {n_particles} частиц")
        print(f"   σ_x: {np.sqrt(twiss_x.beta * twiss_x.emittance) * 1000:.3f} мм")
        print(f"   σ_y: {np.sqrt(twiss_y.beta * twiss_y.emittance) * 1000:.3f} мм")
    
    def _generate_particles(self) -> np.ndarray:
        """Генерация начального распределения частиц с корреляцией"""
        # Ковариационная матрица для X
        cov_xx = self.twiss_x.beta * self.twiss_x.emittance
        cov_xxp = -self.twiss_x.alpha * self.twiss_x.emittance
        cov_xpxp = self.twiss_x.gamma * self.twiss_x.emittance
        cov_matrix_x = np.array([[cov_xx, cov_xxp], [cov_xxp, cov_xpxp]])
        
        # Генерация коррелированных частиц по X
        particles_x = np.random.multivariate_normal(
            [0, 0], cov_matrix_x, self.n_particles
        )
        
        # Ковариационная матрица для Y
        cov_yy = self.twiss_y.beta * self.twiss_y.emittance
        cov_yyp = -self.twiss_y.alpha * self.twiss_y.emittance
        cov_ypyp = self.twiss_y.gamma * self.twiss_y.emittance
        cov_matrix_y = np.array([[cov_yy, cov_yyp], [cov_yyp, cov_ypyp]])
        
        # Генерация коррелированных частиц по Y
        particles_y = np.random.multivariate_normal(
            [0, 0], cov_matrix_y, self.n_particles
        )
        
        return np.column_stack([particles_x, particles_y])
    
    def get_phase_space(self) -> Dict:
        """Получение фазового пространства"""
        return {
            'x': (self.particles[:, 0] * 1000).tolist(),  # мм
            'xp': (self.particles[:, 1] * 1000).tolist(),  # мрад
            'y': (self.particles[:, 2] * 1000).tolist(),  # мм
            'yp': (self.particles[:, 3] * 1000).tolist()   # мрад
        }