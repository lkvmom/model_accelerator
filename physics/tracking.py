import numpy as np
from typing import Dict
from .twiss import TwissParameters
from .elements import MatchingTriplet

class ParticleTracker:
    def __init__(self, triplet: MatchingTriplet, twiss_x: TwissParameters, 
                 twiss_y: TwissParameters, n_particles: int = 500):
        self.triplet = triplet
        self.twiss_x = twiss_x
        self.twiss_y = twiss_y
        self.n_particles = n_particles
        self.particles = self._generate_particles()
    
    def _generate_particles(self) -> np.ndarray:
        sigma_x = np.sqrt(self.twiss_x.beta * self.twiss_x.emittance)
        sigma_xp = np.sqrt(self.twiss_x.gamma * self.twiss_x.emittance)
        sigma_y = np.sqrt(self.twiss_y.beta * self.twiss_y.emittance)
        sigma_yp = np.sqrt(self.twiss_y.gamma * self.twiss_y.emittance)
        
        particles = np.zeros((self.n_particles, 4))
        particles[:, 0] = np.random.normal(0, sigma_x, self.n_particles)
        particles[:, 1] = np.random.normal(0, sigma_xp, self.n_particles)
        particles[:, 2] = np.random.normal(0, sigma_y, self.n_particles)
        particles[:, 3] = np.random.normal(0, sigma_yp, self.n_particles)
        
        return particles
    
    def track_through(self) -> np.ndarray:
        M_x = self.triplet.get_transfer_matrix_x()
        M_y = self.triplet.get_transfer_matrix_y()
        
        x_out = M_x[0,0] * self.particles[:,0] + M_x[0,1] * self.particles[:,1]
        xp_out = M_x[1,0] * self.particles[:,0] + M_x[1,1] * self.particles[:,1]
        y_out = M_y[0,0] * self.particles[:,2] + M_y[0,1] * self.particles[:,3]
        yp_out = M_y[1,0] * self.particles[:,2] + M_y[1,1] * self.particles[:,3]
        
        return np.column_stack([x_out, xp_out, y_out, yp_out])
    
    def get_phase_space(self, at_start: bool = True) -> Dict:
        particles = self.particles if at_start else self.track_through()
        return {
            'x': [float(x * 1000) for x in particles[:, 0]],
            'xp': [float(xp * 1000) for xp in particles[:, 1]],
            'y': [float(y * 1000) for y in particles[:, 2]],
            'yp': [float(yp * 1000) for yp in particles[:, 3]],
        }