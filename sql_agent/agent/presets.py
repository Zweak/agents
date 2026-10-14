"""Preloaded presentation and test scenarios for the SQL Debugging & Optimization Agent."""

from typing import Dict, Any, List

SAMPLE_SCHEMA_ECOMMERCE = """
CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    department_id INTEGER,
    salary REAL NOT NULL,
    hire_date TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date TEXT NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);
"""

SAMPLE_SEED_ECOMMERCE = """
INSERT INTO departments VALUES (1, 'Engineering'), (2, 'Sales'), (3, 'Finance'), (4, 'Product');

INSERT INTO employees VALUES
(101, 'Alice', 'Smith', 1, 95000, '2023-01-15'),
(102, 'Bob', 'Jones', 1, 88000, '2023-03-20'),
(103, 'Charlie', 'Brown', 2, 62000, '2022-07-11'),
(104, 'Diana', 'Prince', 2, 71000, '2021-11-05'),
(105, 'Evan', 'Wright', 3, 80000, '2024-02-01');

INSERT INTO customers VALUES
(1, 'TechCorp', 'info@techcorp.com', 'USA'),
(2, 'GlobalBiz', 'contact@globalbiz.com', 'UK'),
(3, 'InnovateLLC', 'hello@innovate.com', 'Canada'),
(4, 'SilentBuyer', 'ghost@quiet.com', 'USA');

INSERT INTO orders VALUES
(1001, 1, '2025-02-14 10:30:00', 450.00, 'COMPLETED'),
(1002, 1, '2025-03-01 14:20:00', 1200.50, 'COMPLETED'),
(1003, 2, '2025-03-10 09:15:00', 320.00, 'PENDING'),
(1004, NULL, '2025-03-12 11:00:00', 99.00, 'COMPLETED');

INSERT INTO order_items VALUES
(501, 1001, 'Cloud Hosting', 1, 450.00),
(502, 1002, 'Enterprise License', 2, 600.25),
(503, 1003, 'Consulting Hour', 2, 160.00),
(504, 1004, 'Setup Fee', 1, 99.00);
"""

PRESET_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "scenario_1",
        "title": "1. Cryptic GROUP BY Error (Syntax & Semantic)",
        "subtitle": "Column must appear in GROUP BY clause or be used in aggregate function",
        "dialect": "PostgreSQL",
        "query": """SELECT 
    d.department_name,
    e.first_name,
    COUNT(e.employee_id) AS total_employees,
    AVG(e.salary) AS average_salary
FROM departments d
JOIN employees e ON d.department_id = e.department_id
WHERE e.salary > 50000
GROUP BY d.department_name;""",
        "error_message": 'ERROR: column "e.first_name" must appear in the GROUP BY clause or be used in an aggregate function (PostgreSQL 42803)',
        "business_requirement": "List each department with total employee headcount and average salary for employees earning above 50,000. Do not list individual employee names.",
        "schema_ddl": SAMPLE_SCHEMA_ECOMMERCE,
        "seed_data": SAMPLE_SEED_ECOMMERCE,
        "highlight": "Syntax error: unaggregated column in SELECT without being in GROUP BY."
    },
    {
        "id": "scenario_2",
        "title": "2. Silent Cartesian Join (Data Explosion & CPU Spike)",
        "subtitle": "Legacy comma join missing relationship condition causing row multiplication",
        "dialect": "Generic ANSI SQL",
        "query": """SELECT 
    c.name,
    o.order_id,
    i.product_name,
    o.total_amount
FROM customers c, orders o, order_items i
WHERE o.order_id = i.order_id;""",
        "error_message": "",
        "business_requirement": "Show each customer's orders and individual purchased line items. Total amount must match the customer's actual purchases without duplicating across all customers.",
        "schema_ddl": SAMPLE_SCHEMA_ECOMMERCE,
        "seed_data": SAMPLE_SEED_ECOMMERCE,
        "highlight": "Semantic bug: missing join condition between `c` and `o` creates an accidental CROSS JOIN multiplying all rows."
    },
    {
        "id": "scenario_3",
        "title": "3. Non-SARGable WHERE Clause (Kills Database Index)",
        "subtitle": "Function wrapping indexed date column forces full table scan",
        "dialect": "PostgreSQL",
        "query": """SELECT 
    order_id, 
    customer_id, 
    total_amount, 
    order_date
FROM orders
WHERE strftime('%Y', order_date) = '2025'
  AND UPPER(status) = 'COMPLETED';""",
        "error_message": "",
        "business_requirement": "Retrieve all completed orders placed in calendar year 2025. Must execute with maximum index efficiency on high-traffic databases.",
        "schema_ddl": SAMPLE_SCHEMA_ECOMMERCE,
        "seed_data": SAMPLE_SEED_ECOMMERCE,
        "highlight": "Performance trap: functions on `order_date` prevent index range scans, forcing a full table scan."
    },
    {
        "id": "scenario_4",
        "title": "4. The Dangerous NOT IN (SELECT ...) NULL Trap",
        "subtitle": "Three-valued logic failure returns zero rows when subquery has a NULL",
        "dialect": "PostgreSQL",
        "query": """SELECT 
    customer_id, 
    name, 
    email 
FROM customers 
WHERE customer_id NOT IN (
    SELECT customer_id FROM orders
);""",
        "error_message": "",
        "business_requirement": "Identify all registered customers who have never placed an order (e.g. 'SilentBuyer' with ID 4). Currently the query returns 0 rows despite unengaged customers existing!",
        "schema_ddl": SAMPLE_SCHEMA_ECOMMERCE,
        "seed_data": SAMPLE_SEED_ECOMMERCE,
        "highlight": "Logic trap: if orders table contains a single NULL customer_id (guest checkout), NOT IN returns empty result."
    },
    {
        "id": "scenario_5",
        "title": "5. Inefficient Correlated Subquery -> Modern CTE & Window Function",
        "subtitle": "O(N^2) subquery rewritten into clean, performant Window Function",
        "dialect": "Generic ANSI SQL",
        "query": """SELECT 
    o.order_id,
    o.customer_id,
    o.order_date,
    o.total_amount
FROM orders o
WHERE o.order_date = (
    SELECT MAX(o2.order_date)
    FROM orders o2
    WHERE o2.customer_id = o.customer_id
);""",
        "error_message": "",
        "business_requirement": "Retrieve each customer's most recent order with full order details, optimized for large volume tables.",
        "schema_ddl": SAMPLE_SCHEMA_ECOMMERCE,
        "seed_data": SAMPLE_SEED_ECOMMERCE,
        "highlight": "Architectural upgrade: replace correlated subquery with ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC)."
    }
]
