import json
from typing import Dict, List
from common.db import run_sql

def save_proposal(tenant_id: str, user_id: str | None, payload: Dict):
    run_sql("""
        insert into production_proposals (tenant_id, created_by, payload)
        values (:t, :u, :p::jsonb)
    """, {"t": tenant_id, "u": user_id, "p": json.dumps(payload)})

def list_proposals(tenant_id: str, limit: int = 50) -> List[Dict]:
    rows = run_sql("""
        select id, created_at, status, payload
        from production_proposals
        where tenant_id = :t
        order by created_at desc
        limit :l
    """, {"t": tenant_id, "l": limit})
    return [dict(r._mapping) for r in rows]
