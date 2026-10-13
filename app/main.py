import logging
import uuid

from fastapi import FastAPI, HTTPException

from app.database import get_postgres_cursor
from app.graph import (
    find_related_claims,
    get_neo4j_driver,
    link_related_claims,
    save_claim_graph,
)
from app.schemas import ClaimCreate

logger = logging.getLogger(__name__)

app = FastAPI(title="InsurTech Claims PoC")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "claims-api"}


@app.get("/health/db")
def database_health():
    """Check that FastAPI can reach PostgreSQL and read the claims table."""
    try:
        with get_postgres_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM claims;")
            claims_count = cur.fetchone()[0]
        return {"postgres": "connected", "claims_count": claims_count}
    except Exception as error:
        raise HTTPException(
            status_code=503, detail=f"PostgreSQL connection failed: {error}"
        )


@app.get("/health/neo4j")
def neo4j_health():
    """Check that FastAPI can reach Neo4j and run a query."""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS node_count")
            node_count = result.single()["node_count"]
        return {"neo4j": "connected", "node_count": node_count}
    except Exception as error:
        raise HTTPException(
            status_code=503, detail=f"Neo4j connection failed: {error}"
        )


@app.post("/api/claims", status_code=201)
def submit_claim(claim: ClaimCreate):
    """Validate a claim, save it in PostgreSQL, then record it in Neo4j."""
    claim_number = "CLM-" + uuid.uuid4().hex[:8].upper()

    # ---- Part 1: PostgreSQL (the official record) ----
    try:
        with get_postgres_cursor() as cur:
            # Find the policy, its type, and the customer who owns it
            cur.execute(
                """
                SELECT p.policy_id, p.customer_id, p.status,
                       p.start_date, p.end_date, p.policy_type, c.full_name
                FROM policies p
                JOIN customers c ON c.customer_id = p.customer_id
                WHERE p.policy_number = %s
                """,
                (claim.policy_number,),
            )
            policy = cur.fetchone()

            if policy is None:
                raise HTTPException(status_code=404, detail="Policy not found")

            (
                policy_id,
                customer_id,
                policy_status,
                start_date,
                end_date,
                policy_type,
                full_name,
            ) = policy

            # Basic business rules
            if policy_status != "ACTIVE":
                raise HTTPException(status_code=400, detail="Policy is not active")
            if not (start_date <= claim.incident_date <= end_date):
                raise HTTPException(
                    status_code=400,
                    detail="Incident date is outside the policy coverage period",
                )

            # Save the claim and get the new values back
            cur.execute(
                """
                INSERT INTO claims
                    (claim_number, policy_id, customer_id,
                     incident_date, description, claim_amount)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING claim_id, status, created_at
                """,
                (
                    claim_number,
                    policy_id,
                    customer_id,
                    claim.incident_date,
                    claim.description,
                    claim.claim_amount,
                ),
            )
            claim_id, claim_status, created_at = cur.fetchone()

    except HTTPException:
        # Our own errors (404, 400): pass them through unchanged
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Database error: {error}")


           # ---- Part 2: Neo4j (the relationships) ----
    # The claim is already saved in PostgreSQL at this point. If Neo4j fails,
    # we do not lose the claim; we report that the graph step did not finish.
    graph_synced = True
    related_claims = []
    try:
        save_claim_graph(
            customer_id=customer_id,
            full_name=full_name,
            policy_number=claim.policy_number,
            policy_type=policy_type,
            claim_number=claim_number,
            claim_amount=claim.claim_amount,
            incident_date=claim.incident_date,
            status=claim_status,
        )
        related_claims = find_related_claims(
            customer_id=customer_id,
            policy_number=claim.policy_number,
            claim_number=claim_number,
            incident_date=claim.incident_date,
        )
        if related_claims:
            link_related_claims(
                claim_number, [item["claim_number"] for item in related_claims]
            )
    except Exception:
        graph_synced = False
        logger.exception("Claim %s saved in PostgreSQL but Neo4j step failed", claim_number)

    # ---- Part 3: decide the processing result ----
    if not graph_synced:
        final_status = claim_status
        flagged = False
        review_reason = "Relationship check could not be completed; claim left as SUBMITTED"
    elif related_claims:
        final_status = "FLAGGED_FOR_REVIEW"
        flagged = True
        review_reason = (
            f"{len(related_claims)} other claim(s) by the same customer on the same "
            "policy within 30 days; flagged for review by a claims officer"
        )
    else:
        final_status = "ACCEPTED_FOR_PROCESSING"
        flagged = False
        review_reason = "No related claims found"

    # Save the result back to PostgreSQL (the source of truth for claim status)
    if final_status != claim_status:
        try:
            with get_postgres_cursor() as cur:
                cur.execute(
                    """
                    UPDATE claims
                    SET status = %s, flagged_for_review = %s
                    WHERE claim_id = %s
                    """,
                    (final_status, flagged, claim_id),
                )
        except Exception as error:
            logger.exception("Could not update status for claim %s", claim_number)
            raise HTTPException(
                status_code=503,
                detail=f"Claim {claim_number} was saved but its status update failed: {error}",
            )

    return {
        "message": "Claim processed",
        "claim_id": claim_id,
        "claim_number": claim_number,
        "policy_number": claim.policy_number,
        "customer_id": customer_id,
        "claim_amount": str(claim.claim_amount),
        "status": final_status,
        "flagged_for_review": flagged,
        "review_reason": review_reason,
        "created_at": created_at,
        "graph_synced": graph_synced,
        "related_claims": related_claims,
    }