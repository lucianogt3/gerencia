from .user import User
from .document import Document, DocumentVersion, DocumentRead
from .scale import Scale

from .swap import ShiftSwap, SwapEvent
from .sick_note import SickNote
from .announcement import Announcement

from .sector import Sector
from .nursing_schedule import (
    NursingMonthlySchedule,
    NursingMonthlyMember,
    NursingMonthlyCell,
    NursingDailyOverride,
)

__all__ = [
    # Auth / Usuários / Config
    "User",
    "Sector",

    # Documentos
    "Document",
    "DocumentVersion",
    "DocumentRead",

    # Escalas (upload outras especialidades / PDFs)
    "Scale",

    # Escala de Enfermagem no sistema
    "NursingMonthlySchedule",
    "NursingMonthlyMember",
    "NursingMonthlyCell",
    "NursingDailyOverride",

    # Trocas
    "ShiftSwap",
    "SwapEvent",

    # Atestados
    "SickNote",

    # Comunicados
    "Announcement",
]

