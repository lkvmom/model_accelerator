from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class TwissInput(BaseModel):
    """Входные параметры пучка (Таблица 1)"""
    beta_x: float = Field(5.0, ge=0.1, le=100)
    beta_y: float = Field(2.5, ge=0.1, le=100)
    alpha_x: float = Field(-0.5, ge=-10, le=10)
    alpha_y: float = Field(0.3, ge=-10, le=10)
    emittance_x: float = Field(10.0, ge=0.1, le=1000)
    emittance_y: float = Field(2.0, ge=0.1, le=1000)

class TwissTarget(BaseModel):
    """Целевые параметры (Таблица 2)"""
    beta_x: float = Field(8.0, ge=0.1, le=100)
    beta_y: float = Field(4.0, ge=0.1, le=100)
    alpha_x: float = Field(0.0, ge=-10, le=10)
    alpha_y: float = Field(0.0, ge=-10, le=10)

class MatchingRequest(BaseModel):
    """Запрос на расчёт согласующей секции"""
    input: TwissInput = Field(default_factory=TwissInput)
    target: TwissTarget = Field(default_factory=TwissTarget)
    energy: float = Field(10.0, ge=0.1, le=1000)
    particle_type: str = Field("proton")
    max_gradient: float = Field(20.0, ge=1, le=100)

class MatchingResult(BaseModel):
    """Результат согласования"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    plots: Optional[Dict[str, Any]] = None