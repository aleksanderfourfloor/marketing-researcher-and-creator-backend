from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    """Health check for load balancers and monitoring."""
    return {"status": "ok"}


@router.get("/")
def root():
    """Root API message."""
    return {"message": "Research App API", "docs": "/docs"}
