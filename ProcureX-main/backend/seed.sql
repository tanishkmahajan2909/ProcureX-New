-- ProcureX sample data. Run after schema.sql on a fresh database.

INSERT INTO corporation (company_name, address, gst_no) VALUES
('TechNova Pvt Ltd', 'Andheri, Mumbai', '27AATCT1234R1Z5');

INSERT INTO department (company_id, department_name) VALUES
(1, 'IT'),
(1, 'Finance'),
(1, 'Procurement');

INSERT INTO role (role_name) VALUES
('Employee'),
('Manager'),
('Procurement Officer');

INSERT INTO employee (name, email, department_id, role_id) VALUES
('Rohan Shah', 'rohan.shah@technova.com', 1, 1),
('Priya Mehta', 'priya.mehta@technova.com', 2, 2),
('Aman Verma', 'aman.verma@technova.com', 3, 3);

INSERT INTO product (product_name, category, unit) VALUES
('Laptop', 'Electronics', 'piece'),
('Office Chair', 'Furniture', 'piece'),
('Printer Paper', 'Stationery', 'ream');

INSERT INTO vendor (vendor_name, email, phone, address, gst_no) VALUES
('Alpha Traders', 'contact@alphatraders.com', '9876543210', 'Pune', '27AAACA1111R1Z1'),
('Beta Supplies', 'sales@betasupplies.com', '9876501234', 'Nashik', '27AAACB2222R1Z2'),
('Gamma Enterprises', 'info@gammaent.com', '9876512345', 'Thane', '27AAACG3333R1Z3');

INSERT INTO purchase_request (requestor_id, department_id, request_date, approver_id, approval_status) VALUES
(1, 1, CURRENT_DATE - 10, 2, 'Approved'),
(1, 1, CURRENT_DATE - 2, 2, 'Pending');

INSERT INTO purchase_request_item (pr_id, product_id, quantity, required_date) VALUES
(1, 1, 5, CURRENT_DATE + 15),
(1, 3, 20, CURRENT_DATE + 15),
(2, 2, 10, CURRENT_DATE + 20);

INSERT INTO rfq (pr_id, procurement_officer_id, issue_date, due_date) VALUES
(1, 3, CURRENT_DATE - 9, CURRENT_DATE - 5);

INSERT INTO rfq_vendor (rfq_id, vendor_id) VALUES
(1, 1),
(1, 2),
(1, 3);

INSERT INTO quotation (rfq_id, vendor_id, quoted_price, delivery_days, submitted_date) VALUES
(1, 1, 250000.00, 7, CURRENT_DATE - 7),
(1, 2, 245000.00, 10, CURRENT_DATE - 6);

INSERT INTO vendor_rating (vendor_id, rating_score, rating_date) VALUES
(1, 4.5, CURRENT_DATE - 30),
(2, 4.0, CURRENT_DATE - 30);

INSERT INTO purchase_order (quotation_id, procurement_officer_id, po_date, total_amount, po_status) VALUES
(1, 3, CURRENT_DATE - 5, 250000.00, 'Completed');

INSERT INTO delivery (po_id, delivery_date, delivery_status) VALUES
(1, CURRENT_DATE - 1, 'Delivered');

INSERT INTO quality_inspection (delivery_id, inspector_id, inspection_date, result) VALUES
(1, 3, CURRENT_DATE, 'Passed');

INSERT INTO distribution (delivery_id, department_id, distributed_date, received_by) VALUES
(1, 1, CURRENT_DATE, 1);

INSERT INTO invoice (po_id, vendor_id, invoice_amount, invoice_date, verification_status) VALUES
(1, 1, 250000.00, CURRENT_DATE - 1, 'Verified');

INSERT INTO payment (invoice_id, payment_date, amount_paid, payment_status) VALUES
(1, CURRENT_DATE, 250000.00, 'Paid');
