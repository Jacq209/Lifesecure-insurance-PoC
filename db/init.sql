-- Customers who hold policies and file claims
CREATE TABLE IF NOT EXISTS customers (
    customer_id   SERIAL PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(100) NOT NULL UNIQUE,
    phone         VARCHAR(30),
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Each policy belongs to one customer
CREATE TABLE IF NOT EXISTS policies (
    policy_id        SERIAL PRIMARY KEY,
    policy_number    VARCHAR(30) NOT NULL UNIQUE,
    customer_id      INTEGER NOT NULL REFERENCES customers(customer_id),
    policy_type      VARCHAR(30) NOT NULL,
    coverage_amount  NUMERIC(12,2) NOT NULL CHECK (coverage_amount > 0),
    start_date       DATE NOT NULL,
    end_date         DATE NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
);

-- Each claim is filed by a customer under a policy
CREATE TABLE IF NOT EXISTS claims (
    claim_id         SERIAL PRIMARY KEY,
    claim_number     VARCHAR(30) NOT NULL UNIQUE,
    policy_id        INTEGER NOT NULL REFERENCES policies(policy_id),
    customer_id      INTEGER NOT NULL REFERENCES customers(customer_id),
    incident_date    DATE NOT NULL,
    description      TEXT,
    claim_amount     NUMERIC(12,2) NOT NULL CHECK (claim_amount > 0),
    status           VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED',
    flagged_for_review BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW()
);