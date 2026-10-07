-- ProcureX PostgreSQL schema for the Flask + Python backend
-- Run this inside a database named: procurex

DROP TABLE IF EXISTS payment CASCADE;
DROP TABLE IF EXISTS invoice CASCADE;
DROP TABLE IF EXISTS distribution CASCADE;
DROP TABLE IF EXISTS quality_inspection CASCADE;
DROP TABLE IF EXISTS delivery CASCADE;
DROP TABLE IF EXISTS purchase_order CASCADE;
DROP TABLE IF EXISTS vendor_rating CASCADE;
DROP TABLE IF EXISTS quotation CASCADE;
DROP TABLE IF EXISTS rfq_vendor CASCADE;
DROP TABLE IF EXISTS rfq CASCADE;
DROP TABLE IF EXISTS purchase_request_item CASCADE;
DROP TABLE IF EXISTS purchase_request CASCADE;
DROP TABLE IF EXISTS vendor CASCADE;
DROP TABLE IF EXISTS product CASCADE;
DROP TABLE IF EXISTS employee CASCADE;
DROP TABLE IF EXISTS role CASCADE;
DROP TABLE IF EXISTS department CASCADE;
DROP TABLE IF EXISTS corporation CASCADE;

CREATE TABLE corporation (
  company_id SERIAL PRIMARY KEY,
  company_name VARCHAR(150) NOT NULL,
  address VARCHAR(255),
  gst_no VARCHAR(20) UNIQUE
);

CREATE TABLE department (
  department_id SERIAL PRIMARY KEY,
  company_id INT NOT NULL REFERENCES corporation(company_id),
  department_name VARCHAR(100) NOT NULL
);

CREATE TABLE role (
  role_id SERIAL PRIMARY KEY,
  role_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE employee (
  employee_id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  department_id INT NOT NULL REFERENCES department(department_id),
  role_id INT NOT NULL REFERENCES role(role_id)
);

CREATE TABLE product (
  product_id SERIAL PRIMARY KEY,
  product_name VARCHAR(150) NOT NULL,
  category VARCHAR(80),
  unit VARCHAR(20)
);

CREATE TABLE vendor (
  vendor_id SERIAL PRIMARY KEY,
  vendor_name VARCHAR(150) NOT NULL,
  email VARCHAR(100) UNIQUE,
  phone VARCHAR(15),
  address VARCHAR(255),
  gst_no VARCHAR(20) UNIQUE
);

CREATE TABLE purchase_request (
  pr_id SERIAL PRIMARY KEY,
  requestor_id INT NOT NULL REFERENCES employee(employee_id),
  department_id INT NOT NULL REFERENCES department(department_id),
  request_date DATE NOT NULL DEFAULT CURRENT_DATE,
  approver_id INT REFERENCES employee(employee_id),
  approval_status VARCHAR(20) NOT NULL DEFAULT 'Pending'
    CHECK (approval_status IN ('Pending', 'Approved', 'Rejected'))
);

CREATE TABLE purchase_request_item (
  pr_item_id SERIAL PRIMARY KEY,
  pr_id INT NOT NULL REFERENCES purchase_request(pr_id) ON DELETE CASCADE,
  product_id INT NOT NULL REFERENCES product(product_id),
  quantity INT NOT NULL CHECK (quantity > 0),
  required_date DATE
);

CREATE TABLE rfq (
  rfq_id SERIAL PRIMARY KEY,
  pr_id INT NOT NULL REFERENCES purchase_request(pr_id),
  procurement_officer_id INT NOT NULL REFERENCES employee(employee_id),
  issue_date DATE NOT NULL DEFAULT CURRENT_DATE,
  due_date DATE
);

CREATE TABLE rfq_vendor (
  rfq_id INT NOT NULL REFERENCES rfq(rfq_id) ON DELETE CASCADE,
  vendor_id INT NOT NULL REFERENCES vendor(vendor_id),
  PRIMARY KEY (rfq_id, vendor_id)
);

CREATE TABLE quotation (
  quotation_id SERIAL PRIMARY KEY,
  rfq_id INT NOT NULL REFERENCES rfq(rfq_id),
  vendor_id INT NOT NULL REFERENCES vendor(vendor_id),
  quoted_price DECIMAL(12, 2) NOT NULL CHECK (quoted_price >= 0),
  delivery_days INT,
  submitted_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE vendor_rating (
  rating_id SERIAL PRIMARY KEY,
  vendor_id INT NOT NULL REFERENCES vendor(vendor_id),
  rating_score DECIMAL(3, 2) CHECK (rating_score BETWEEN 0 AND 5),
  rating_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE purchase_order (
  po_id SERIAL PRIMARY KEY,
  quotation_id INT NOT NULL REFERENCES quotation(quotation_id),
  procurement_officer_id INT NOT NULL REFERENCES employee(employee_id),
  po_date DATE NOT NULL DEFAULT CURRENT_DATE,
  total_amount DECIMAL(12, 2) NOT NULL,
  po_status VARCHAR(20) NOT NULL DEFAULT 'Issued'
    CHECK (po_status IN ('Issued', 'Completed', 'Cancelled'))
);

CREATE TABLE delivery (
  delivery_id SERIAL PRIMARY KEY,
  po_id INT NOT NULL REFERENCES purchase_order(po_id),
  delivery_date DATE,
  delivery_status VARCHAR(20) NOT NULL DEFAULT 'Pending'
    CHECK (delivery_status IN ('Pending', 'Delivered', 'Delayed'))
);

CREATE TABLE quality_inspection (
  inspection_id SERIAL PRIMARY KEY,
  delivery_id INT NOT NULL REFERENCES delivery(delivery_id),
  inspector_id INT NOT NULL REFERENCES employee(employee_id),
  inspection_date DATE NOT NULL DEFAULT CURRENT_DATE,
  result VARCHAR(20) NOT NULL
    CHECK (result IN ('Passed', 'Failed', 'Partially Accepted'))
);

CREATE TABLE distribution (
  distribution_id SERIAL PRIMARY KEY,
  delivery_id INT NOT NULL REFERENCES delivery(delivery_id),
  department_id INT NOT NULL REFERENCES department(department_id),
  distributed_date DATE NOT NULL DEFAULT CURRENT_DATE,
  received_by INT NOT NULL REFERENCES employee(employee_id)
);

CREATE TABLE invoice (
  invoice_id SERIAL PRIMARY KEY,
  po_id INT NOT NULL REFERENCES purchase_order(po_id),
  vendor_id INT NOT NULL REFERENCES vendor(vendor_id),
  invoice_amount DECIMAL(12, 2) NOT NULL,
  invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
  verification_status VARCHAR(20) NOT NULL DEFAULT 'Pending'
    CHECK (verification_status IN ('Pending', 'Verified', 'Disputed'))
);

CREATE TABLE payment (
  payment_id SERIAL PRIMARY KEY,
  invoice_id INT NOT NULL REFERENCES invoice(invoice_id),
  payment_date DATE,
  amount_paid DECIMAL(12, 2) NOT NULL,
  payment_status VARCHAR(20) NOT NULL DEFAULT 'Pending'
    CHECK (payment_status IN ('Pending', 'Paid', 'Failed'))
);
