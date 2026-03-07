import numpy as np
from typing import Tuple, List, Dict
from .twiss import TwissParameters

class Element:
    def __init__(self, length: float, name: str = ""):
        self.length = float(length)
        self.name = name
    
    def transfer_matrix(self) -> np.ndarray:
        raise NotImplementedError
    
    def get_length(self) -> float:
        return self.length

class Drift(Element):
    def transfer_matrix(self) -> np.ndarray:
        L = self.length
        return np.array([[1.0, L], [0.0, 1.0]])
    
    def to_dict(self, position: float) -> dict:
        return {'type': 'drift', 'length': float(self.length), 'position': float(position)}

class Quadrupole(Element):
    def __init__(self, length: float, gradient: float, rigidity: float, name: str = ""):
        super().__init__(length, name)
        self.gradient = float(gradient)
        self.rigidity = float(rigidity)
        self.k = float(gradient / rigidity) if abs(rigidity) > 1e-10 else 0.0
    
    def transfer_matrix_focusing(self) -> np.ndarray:
        L = self.length
        k = self.k
        
        if abs(k) < 1e-10:
            return np.array([[1.0, L], [0.0, 1.0]])
        
        if k > 0:
            sqrt_k = np.sqrt(k)
            return np.array([
                [np.cos(sqrt_k * L), np.sin(sqrt_k * L) / sqrt_k],
                [-sqrt_k * np.sin(sqrt_k * L), np.cos(sqrt_k * L)]
            ])
        else:
            sqrt_k = np.sqrt(abs(k))
            return np.array([
                [np.cosh(sqrt_k * L), np.sinh(sqrt_k * L) / sqrt_k],
                [sqrt_k * np.sinh(sqrt_k * L), np.cosh(sqrt_k * L)]
            ])
    
    def transfer_matrix_defocusing(self) -> np.ndarray:
        L = self.length
        k = self.k
        
        if abs(k) < 1e-10:
            return np.array([[1.0, L], [0.0, 1.0]])
        
        if k > 0:
            sqrt_k = np.sqrt(k)
            return np.array([
                [np.cosh(sqrt_k * L), np.sinh(sqrt_k * L) / sqrt_k],
                [sqrt_k * np.sinh(sqrt_k * L), np.cosh(sqrt_k * L)]
            ])
        else:
            sqrt_k = np.sqrt(abs(k))
            return np.array([
                [np.cos(sqrt_k * L), np.sin(sqrt_k * L) / sqrt_k],
                [-sqrt_k * np.sin(sqrt_k * L), np.cos(sqrt_k * L)]
            ])
    
    def to_dict(self, position: float) -> dict:
        return {
            'type': 'quadrupole',
            'subtype': 'QF' if self.gradient > 0 else 'QD',
            'length': float(self.length),
            'gradient': float(self.gradient),
            'position': float(position)
        }

class MatchingTriplet:
    def __init__(self, q1_length: float, q2_length: float, q3_length: float,
                 drift1: float, drift2: float, drift3: float, drift4: float,
                 gradients: Tuple[float, float, float], rigidity: float):
        self.rigidity = float(rigidity)
        
        self.drift1 = Drift(drift1, "D1")
        self.q1 = Quadrupole(q1_length, gradients[0], rigidity, "Q1")
        self.drift2 = Drift(drift2, "D2")
        self.q2 = Quadrupole(q2_length, gradients[1], rigidity, "Q2")
        self.drift3 = Drift(drift3, "D3")
        self.q3 = Quadrupole(q3_length, gradients[2], rigidity, "Q3")
        self.drift4 = Drift(drift4, "D4")
        
        self.elements = [self.drift1, self.q1, self.drift2, self.q2, self.drift3, self.q3, self.drift4]
        self.total_length = float(sum(e.get_length() for e in self.elements))
    
    def get_transfer_matrix_x(self) -> np.ndarray:
        M = np.eye(2)
        for elem in reversed(self.elements):
            if isinstance(elem, Quadrupole):
                M = elem.transfer_matrix_focusing() @ M
            else:
                M = elem.transfer_matrix() @ M
        return M
    
    def get_transfer_matrix_y(self) -> np.ndarray:
        M = np.eye(2)
        for elem in reversed(self.elements):
            if isinstance(elem, Quadrupole):
                M = elem.transfer_matrix_defocusing() @ M
            else:
                M = elem.transfer_matrix() @ M
        return M
    
    def get_twiss_along(self, twiss_x_in, twiss_y_in, n_points: int = 100):
        s_positions = np.linspace(0, self.total_length, n_points)
        twiss_x = []
        twiss_y = []
        
        for s in s_positions:
            M_x, M_y = self.get_matrix_at_s(s)
            twiss_x.append(twiss_x_in.transform(M_x).to_dict())
            twiss_y.append(twiss_y_in.transform(M_y).to_dict())
        
        return {
            's': [float(x) for x in s_positions.tolist()],
            'beta_x': [float(t['beta']) for t in twiss_x],
            'alpha_x': [float(t['alpha']) for t in twiss_x],
            'beta_y': [float(t['beta']) for t in twiss_y],
            'alpha_y': [float(t['alpha']) for t in twiss_y],
            'beam_size_x': [float(t['beam_size_mm']) for t in twiss_x],
            'beam_size_y': [float(t['beam_size_mm']) for t in twiss_y],
        }
    
    def get_matrix_at_s(self, s: float):
        M_x = np.eye(2)
        M_y = np.eye(2)
        current_s = 0.0
        
        for elem in self.elements:
            elem_length = elem.get_length()
            if current_s + elem_length > s:
                partial_length = max(0, s - current_s)
                M_partial = np.array([[1.0, partial_length], [0.0, 1.0]])
                M_x = M_partial @ M_x
                M_y = M_partial @ M_y
                break
            else:
                if isinstance(elem, Quadrupole):
                    M_x = elem.transfer_matrix_focusing() @ M_x
                    M_y = elem.transfer_matrix_defocusing() @ M_y
                else:
                    M_partial = elem.transfer_matrix()
                    M_x = M_partial @ M_x
                    M_y = M_partial @ M_y
            current_s += elem_length
        
        return M_x, M_y
    
    def to_dict(self) -> list:
        elements = []
        current_s = 0.0
        for elem in self.elements:
            elements.append(elem.to_dict(current_s))
            current_s += elem.get_length()
        return elements