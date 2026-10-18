import os
from functools import lru_cache

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Read the values from the .env file in the project root
load_dotenv()


@lru_cache(maxsize=1)
def get_neo4j_driver():
    """Create the Neo4j driver once and reuse it.

    The driver manages the connections for us, so we don't open a new one
    for every request.
    """
    host = os.getenv("NEO4J_HOST", "localhost")
    port = os.getenv("NEO4J_BOLT_PORT", "7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    return GraphDatabase.driver(f"bolt://{host}:{port}", auth=(user, password))

def save_claim_graph(
    customer_id,
    full_name,
    policy_number,
    policy_type,
    claim_number,
    claim_amount,
    incident_date,
    status,
):
    """Record a claim and its relationships in Neo4j."""
    # MERGE = "find it, or create it if it doesn't exist yet".
    # So a customer or policy is never duplicated, but every claim is new.
    query = """
    MERGE (c:Customer {customer_id: $customer_id})
      SET c.full_name = $full_name
    MERGE (p:Policy {policy_number: $policy_number})
      SET p.policy_type = $policy_type
    MERGE (c)-[:HAS_POLICY]->(p)
    MERGE (cl:Claim {claim_number: $claim_number})
      SET cl.claim_amount = $claim_amount,
          cl.incident_date = date($incident_date),
          cl.policy_number = $policy_number,
          cl.status = $status
    MERGE (c)-[:FILED]->(cl)
    """
    parameters = {
        "customer_id": customer_id,
        "full_name": full_name,
        "policy_number": policy_number,
        "policy_type": policy_type,
        "claim_number": claim_number,
        "claim_amount": float(claim_amount),
        "incident_date": incident_date.isoformat(),
        "status": status,
    }

    driver = get_neo4j_driver()
    with driver.session() as session:
        # consume() waits until Neo4j has finished the query
        session.run(query, parameters).consume()
        
def find_related_claims(customer_id, policy_number, claim_number, incident_date):
    """Find other claims by the same customer on the same policy
    with an incident date within 30 days of this one."""
    query = """
    MATCH (c:Customer {customer_id: $customer_id})-[:FILED]->(other:Claim)
    WHERE other.claim_number <> $claim_number
      AND other.policy_number = $policy_number
      AND other.incident_date >= date($incident_date) - duration({days: 30})
      AND other.incident_date <= date($incident_date) + duration({days: 30})
    RETURN other.claim_number AS claim_number,
           toString(other.incident_date) AS incident_date,
           other.claim_amount AS claim_amount
    ORDER BY other.incident_date DESC
    LIMIT 10
    """
    parameters = {
        "customer_id": customer_id,
        "policy_number": policy_number,
        "claim_number": claim_number,
        "incident_date": incident_date.isoformat(),
    }

    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(query, parameters)
        # record.data() turns each result row into a normal Python dictionary
        return [record.data() for record in result]

def link_related_claims(claim_number, related_claim_numbers):
    """Create RELATED_TO relationships from a new claim to earlier claims."""
    query = """
    MATCH (new:Claim {claim_number: $claim_number})
    UNWIND $related_numbers AS related_number
    MATCH (old:Claim {claim_number: related_number})
    MERGE (new)-[r:RELATED_TO]->(old)
      SET r.reason = $reason
    """
    parameters = {
        "claim_number": claim_number,
        "related_numbers": related_claim_numbers,
        "reason": "same customer, same policy, incident within 30 days",
    }

    driver = get_neo4j_driver()
    with driver.session() as session:
        session.run(query, parameters).consume()


def update_claim_status(claim_number, status):
    """Update an existing claim's status in Neo4j."""
    query = """
    MATCH (cl:Claim {claim_number: $claim_number})
    SET cl.status = $status
    RETURN cl.claim_number AS claim_number
    """
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(
            query,
            {"claim_number": claim_number, "status": status},
        )
        return result.single() is not None


