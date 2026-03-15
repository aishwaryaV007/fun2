"""
ai/services/incident_severity.py
================================
Incident Severity Classification Module

Defines severity weights for various crime types and provides the mathematical
logic to deduct safety points from a road segment's current score while 
ensuring it never drops below 0.
"""

from enum import Enum
import logging

logger = logging.getLogger(__name__)

class IncidentType(str, Enum):
    """
    Mapping of known incident types to their string representation.
    """
    ASSAULT = "assault"
    HARASSMENT = "harassment"
    THEFT = "theft"
    POOR_LIGHTING = "poor_lighting"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ROBBERY = "robbery"
    OTHER = "other"


# Map each incident type to its safety score impact (deduction)
SEVERITY_WEIGHTS = {
    IncidentType.ASSAULT: 30.0,
    IncidentType.ROBBERY: 25.0,
    IncidentType.HARASSMENT: 20.0,
    IncidentType.THEFT: 15.0,
    IncidentType.SUSPICIOUS_ACTIVITY: 10.0,
    IncidentType.POOR_LIGHTING: 5.0,
    IncidentType.OTHER: 10.0,
}


def get_severity_weight(incident_type: str) -> float:
    """
    Safely retrieve the severity weight for a given incident string.
    Normalizes the input to lower case and defaults to 10.0 if unknown.
    """
    normalized_type = incident_type.lower().strip().replace(" ", "_")
    
    try:
        # Try to map the string to the Enum
        incident_enum = IncidentType(normalized_type)
        return SEVERITY_WEIGHTS[incident_enum]
    except ValueError:
        # If it doesn't match an Enum, try to see if it partial-matches (e.g. "street harassment")
        for known_type, weight in SEVERITY_WEIGHTS.items():
            if known_type.value in normalized_type:
                logger.debug(f"Partial match found for '{incident_type}': matched '{known_type.value}'")
                return weight
        
        # Fallback for completely unknown incident types
        logger.warning(f"Unknown incident type '{incident_type}', defaulting to 10.0 penalty.")
        return SEVERITY_WEIGHTS[IncidentType.OTHER]


def calculate_new_safety_score(current_score: float, incident_type: str) -> float:
    """
    Calculates the impact of a crime report and deducts the appropriate points
    from the current safety score (0-100 scale).
    
    Ensures the score never drops below 0.0.
    
    Args:
        current_score (float): The segment's existing safety score (0 to 100).
        incident_type (str): The reported incident type (e.g., "assault").
        
    Returns:
        float: The new bounded safety score.
    """
    deduction = get_severity_weight(incident_type)
    
    # Calculate the new score
    new_score = current_score - deduction
    
    # Mathematical bounds: Clamp the score to never drop below 0.0 or exceed 100.0
    bounded_score = max(0.0, min(100.0, new_score))
    
    logger.info(
        f"Calculated new safety score: {current_score} - {deduction} ({incident_type}) = {bounded_score}"
    )
    
    return bounded_score
