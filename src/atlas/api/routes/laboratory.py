from typing import Dict, List, Any
from datetime import datetime

# In-memory storage for Level 4 events (non-persistent for Laboratory Mode)
LAB_EVENTS: List[Dict] = []

def log_event(event_type: str, symbol: str, context: Dict, trigger: Dict = None):
    """
    LEVEL 4: EVENT LOGGING
    Records context changes and triggers for validation.
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "event": event_type,
        "context": context,
        "trigger": trigger
    }
    
    # Keep buffer size manageable
    LAB_EVENTS.insert(0, event) # Prepend to show newest first
    if len(LAB_EVENTS) > 50:
        LAB_EVENTS.pop()

def get_lab_events() -> List[Dict]:
    return LAB_EVENTS