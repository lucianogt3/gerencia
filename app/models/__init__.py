from .user import User
from .sector import Sector

# Módulos de Enfermagem (Escalas Mensais)
from .nursing_schedule import (
    NursingMonthlySchedule,
    NursingMonthlyMember,
    NursingMonthlyCell,
    NursingDailyOverride,
)

# Módulo de Trocas
from .swap import ShiftSwap

# Módulo de Comunicados
try:
    from .announcement import Announcement, AnnouncementRead
except ImportError:
    pass

# ✅ CORREÇÃO: Módulo de Documentos (POPs, Protocolos e Manuais)
# O arquivo físico deve se chamar 'document.py'
try:
    from .document import Document, DocumentVersion, DocumentRead
except ImportError:
    # Caso o arquivo ainda não exista ou tenha outro nome
    pass

# ✅ CORREÇÃO: Módulo de Escalas e Atestados
try:
    from .scale import Scale
    from .sick_note import SickNote
except ImportError:
    pass

__all__ = [
    "User",
    "Sector",
    "NursingMonthlySchedule",
    "NursingMonthlyMember",
    "NursingMonthlyCell",
    "NursingDailyOverride",
    "ShiftSwap",
    "Announcement",
    "AnnouncementRead",
    "Document",
    "DocumentVersion",
    "DocumentRead",
    "Scale",
    "SickNote"
]