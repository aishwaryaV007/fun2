"""
services/background_jobs.py
===========================
Background tasks using APScheduler.

Runs every 5 minutes:
1. Recomputes crime heatmap
2. Detects danger zones
3. Updates route safety weights
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler = None

def update_safety_data():
    """Background job to recompute all safety data."""
    try:
        logger.info("[BG] Starting safety data update...")
        
        # Recompute heatmap
        from services.crime_heatmap_service import get_heatmap_service
        heatmap_service = get_heatmap_service()
        heatmap = heatmap_service.get_heatmap(force_refresh=True)
        logger.info(f"[BG] Heatmap updated: {len(heatmap)} cells")
        
        # Detect danger zones
        from services.danger_zone_detector import get_danger_zone_detector
        detector = get_danger_zone_detector()
        zones = detector.detect_danger_zones()
        logger.info(f"[BG] Danger zones detected: {len(zones)} zones")
        
        logger.info("[BG] Safety data update completed successfully")
        
    except Exception as e:
        logger.error(f"[BG] Safety data update failed: {e}")

def start_background_scheduler():
    """Initialize and start the background scheduler."""
    global _scheduler
    
    if _scheduler is not None and _scheduler.running:
        logger.info("Background scheduler already running")
        return
    
    try:
        _scheduler = BackgroundScheduler()
        
        # Add job: update safety data every 5 minutes
        _scheduler.add_job(
            update_safety_data,
            'interval',
            minutes=5,
            id='update_safety_data',
            name='Update crime heatmap and danger zones',
            replace_existing=True
        )
        
        _scheduler.start()
        logger.info("Background scheduler started (updates every 5 minutes)")
        
    except Exception as e:
        logger.error(f"Failed to start background scheduler: {e}")

def stop_background_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("Background scheduler stopped")

def get_scheduler_status():
    """Get scheduler status."""
    return {
        "running": _scheduler is not None and _scheduler.running,
        "jobs": len(_scheduler.get_jobs()) if _scheduler else 0,
        "timestamp": datetime.now().isoformat()
    }
