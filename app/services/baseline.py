from ..models import Resource


def baseline_resources(limit=5, *, candidates=None):
    """Stable catalog order, optionally over an explicit offline candidate pool.

    The database-backed application keeps its existing 1–50 result limit.
    An explicit pool is already bounded by the evaluator and honors its cutoff.
    """
    if candidates is not None:
        return sorted(candidates, key=lambda resource: resource.id)[:max(0, int(limit))]
    return Resource.query.order_by(Resource.id.asc()).limit(max(1, min(int(limit), 50))).all()
