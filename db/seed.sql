-- Mock customers
INSERT INTO customers (full_name, email, phone) VALUES
    ('Juan Dela Cruz', 'juan.delacruz@example.com', '09170000001'),
    ('Maria Santos',   'maria.santos@example.com',   '09170000002')
ON CONFLICT (email) DO NOTHING;

-- One active policy for each customer
INSERT INTO policies (policy_number, customer_id, policy_type, coverage_amount, start_date, end_date, status)
SELECT 'POL-1001', customer_id, 'AUTO', 500000.00, '2026-01-01', '2026-12-31', 'ACTIVE'
FROM customers WHERE email = 'juan.delacruz@example.com'
ON CONFLICT (policy_number) DO NOTHING;

INSERT INTO policies (policy_number, customer_id, policy_type, coverage_amount, start_date, end_date, status)
SELECT 'POL-1002', customer_id, 'PROPERTY', 1000000.00, '2026-01-01', '2026-12-31', 'ACTIVE'
FROM customers WHERE email = 'maria.santos@example.com'
ON CONFLICT (policy_number) DO NOTHING;