# UrbanStay – Setup Instructions

## 1. Set up the database
Open your MySQL terminal and run:
```
SOURCE urbanstay_schema.sql;
```
(Use the schema file generated earlier, placed in the same folder or with correct path.)

## 2. Install dependencies
In this project folder, run:
```
pip install -r requirements.txt
```

## 3. Configure your DB password
Open `app.py` and update this section with your actual MySQL password:
```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_mysql_password",   # <-- change this
    "database": "urbanstay"
}
```

## 4. Run the app
```
python app.py
```
Then open your browser to: http://127.0.0.1:5000

## 5. Test login
Use the sample owner account from the schema's sample data:
- Email: rajesh@urbanstay.com
- Password: hashed_pw_1
- Role: Owner

(Note: in the sample data, passwords are stored as plain placeholder text like
"hashed_pw_1" for demo purposes. For a real system you would hash passwords
using a library like werkzeug.security before storing them.)

## What's implemented
- **Login** (User Management module) — role-based login for Owner/Tenant/Staff
- **Dashboard** — pulls live summary counts from the database (Reports & Analytics)
- **Units** — list, add, delete (Data Management module)
- **Tenants** — list, add (Data Management module)
- **Leases** — list, create; automatically marks a unit "Occupied" when leased (Data Management module)
- **Payments** — list, record new payment against a lease (Data Management module)
- **Maintenance Requests** — list, log new request, update status Pending/In Progress/Resolved (Data Management module)
- **Reports** — Occupancy status, Overdue payments, Occupancy rate per building (Reports & Analytics module, using the queries from urbanstay_schema.sql)
- **Settings** — view/add amenities, view maintenance staff (Admin/Settings module)

## Notifications module (not separately built)
Notifications are stubbed as flash messages where they'd logically trigger
(e.g., after logging a maintenance request or updating its status) —
see the comments in app.py marked "Notifications module would alert...".
A full implementation would insert a row into a `notifications` table and
display it to the relevant user on their next login. This is a good
next step if your team has time before the deadline.

## Suggested testing checklist (for your final report's Test Results section)
- [ ] Login with correct credentials for each role (Owner, Tenant, Staff)
- [ ] Login with incorrect password → should show error, not log in
- [ ] Add a new unit → confirm it appears in Units list and in the database
- [ ] Create a lease with end_date before start_date → should fail (CHECK constraint)
- [ ] Create a lease for a unit already occupied → confirm only vacant units are selectable
- [ ] Record a payment → confirm it appears in Payments list
- [ ] Log a maintenance request → confirm status defaults to "Pending"
- [ ] Update a maintenance request status → confirm it updates correctly
- [ ] View Reports page → confirm occupancy and overdue data matches the database
- [ ] Delete a unit → confirm it's removed from the list
