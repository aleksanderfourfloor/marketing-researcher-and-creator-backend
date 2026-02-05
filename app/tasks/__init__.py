"""Optional Celery tasks (only if celery is installed). Use POST /api/analysis/{id}/run for sync execution without a worker."""
try:
    from app.tasks.analysis_tasks import (
        run_full_analysis,
        collect_competitor_news,
        extract_competitor_website,
        calculate_market_metrics,
        generate_insights,
    )
except ImportError:
    run_full_analysis = None
    collect_competitor_news = None
    extract_competitor_website = None
    calculate_market_metrics = None
    generate_insights = None

__all__ = [
    "run_full_analysis",
    "collect_competitor_news",
    "extract_competitor_website",
    "calculate_market_metrics",
    "generate_insights",
]
