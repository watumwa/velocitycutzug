# Roles, Departments, Employee Accounts, Approvals & Commission Update

## What was added

- Roles: Admin, Cashier, Employee.
- Departments:
  - Mens Department
  - Womens Department
  - Pedicure and Manicure Department
  - Cleaning Department
- Each employee belongs to one role and one department.
- Each employee is automatically linked to a Django login account.
- New employee accounts use default password `123`.
- On first login, employees are immediately forced to change the default password.
- Employee identification is now flexible:
  - National ID
  - Driving Licence
  - Refugee ID
  - Passport
  - Other
- Employees can be assigned only the services they perform.
- When employees log in, they only see and submit services assigned to their profile.
- Employee-submitted services are saved as **Pending Approval**.
- Admin/cashier can approve or reject submitted services from the Sales/POS page.
- Django admin also has bulk actions to approve or reject sales.
- Pending/rejected/cancelled services do **not** count in revenue or commission totals.
- Commission is counted only after a sale/service is approved.
- Employees can open **My Services** to see their submissions and approval status.
- Employees can open **My Commission** to see approved commission plus pending/rejected tracking.
- Daily report includes **Total Commission Per Employee** for end-of-day payout.
- Haircut commission rules:
  - UGX 20,000 haircut gives UGX 4,000 commission = 20%
  - UGX 15,000 haircut gives UGX 2,000 commission = 13.33%

## Recommended workflow

1. Admin creates/updates employee.
2. Admin selects the employee role, department, ID type/number, and assigned services.
3. Employee logs in using their generated username and password `123`.
4. Employee is forced to change password.
5. Employee opens **My Services** and submits the service done for the customer.
6. Admin/cashier opens **Sales/POS** and approves or rejects the pending service.
7. Approved services appear in revenue reports and commission reports.

## Deploy steps

After uploading the updated project, run:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

Then restart the Python/Django app from cPanel or by touching the restart file if you use Passenger:

```bash
touch tmp/restart.txt
```

## Important

Existing employees will be assigned the Employee role and Mens Department by the earlier migration if they did not already have a role/department. They will also get login accounts where missing.

Existing National ID values are copied into the new flexible ID fields during migration.

If an employee cannot see any service after logging in, edit that employee and select the services they perform.

The employee username is generated from the employee phone number when available, otherwise from the employee name. You can see the generated username in the Employees table.

## MySQL production settings added

The production settings now use the supplied cPanel/MySQL database by default:

```env
DB_ENGINE=django.db.backends.mysql
DB_NAME=velovkym_city
DB_USER=velovkym_velocity
DB_PASSWORD=jt@5UuT@es@4tap
DB_HOST=localhost
DB_PORT=3306
```

`PyMySQL` has been added to `requirements.txt` so the project can connect to MySQL on shared hosting without compiling `mysqlclient`.

Recommended production commands:

```bash
pip install -r requirements.txt
python manage.py migrate --settings=config.settings.production
python manage.py collectstatic --noinput --settings=config.settings.production
touch tmp/restart.txt
```

## Employee page upgrade

`/employees/` now uses professional employee cards with fast search and filters for role, department, ID type, and status. Each employee card links to a full employee details page showing:

- identity details
- role and department
- login username
- assigned services
- daily/monthly/lifetime sales and commission
- pending/rejected service records
- recent service history

## Expenses module completed

The sidebar Expenses link now opens a working expenses module at `/expenses/`.

Expenses can be created, edited, deleted, searched, filtered, and categorized. Daily and dashboard net profit now subtracts:

```text
approved sales - staff commission - expenses
```

## Employee page design update

The `/employees/` page now uses a Gentelella-style staff contact card layout:

- Circular profile image / initials avatar
- Employee name, role, and department
- Phone, username, ID type/number, and assigned services
- Monthly sales, commission, and job count
- Quick View Profile and Edit Details actions
- Fast search plus role, department, ID type, and status filters
- Responsive 3-column staff directory on desktop and single-column layout on mobile

If the old employee layout still appears on production, clear browser cache and run:

```bash
python manage.py collectstatic --noinput --settings=config.settings.production
touch tmp/restart.txt
```

## Inventory and expenses upgrade

Inventory now supports both salon retail products and salon-use consumables.

### Inventory item types

- **For Sale**: products sold directly to customers, such as beard oil, shampoo, conditioners, aftershave, or cosmetics.
- **Salon Use Only**: consumables used during services, such as gloves, blades, cotton wool, disinfectant, tissue, cleaning materials, towels, and detergents.
- **Sale + Salon Use**: products that can be sold and also used internally.

### Inventory fields added

Each inventory item now stores:

- Category
- Item type
- Unit of measure
- Buying price
- Selling price
- Supplier
- Expiry date, where applicable
- Low-stock threshold
- Active/inactive status

### Stock movement

Stock movement now records:

- Stock In / Restock
- Sold to Customer
- Used for Service
- Damaged
- Expired
- Lost
- Internal Use
- Adjustment

Restocking increases stock. Sold/used/lost/damaged/expired/internal-use entries reduce stock.

### Stock purchases and expenses

When restocking, the system can automatically create an expense using:

```text
quantity × unit cost
```

The expense category used is **Stock Purchase / Supplies**. This keeps salon expenses complete while also increasing inventory stock.

### Product sales

A new product-sales flow was added. When cashier/admin records a product sale:

1. Product revenue is recorded.
2. Stock is reduced automatically.
3. Product sales are included in dashboard revenue and daily report revenue.

### Profit calculation

Reports now calculate:

```text
Total Revenue = Approved Service Sales + Product Sales
Net Profit = Total Revenue - Employee Commission - Expenses
```

This keeps the salon reports simple and understandable.

### Deploy steps after this inventory upgrade

```bash
pip install -r requirements.txt
python manage.py migrate --settings=config.settings.production
python manage.py collectstatic --noinput --settings=config.settings.production
touch tmp/restart.txt
```

## Pending Approval Notifications Update

Admin and cashier users now receive clearer pending-sale notifications:

- A topbar approval bell appears when employee sale submissions are waiting.
- The POS/sidebar link shows a red count badge when approvals are pending.
- A professional warning banner appears with a direct "Review now" action.
- The browser checks for new pending submissions every 30 seconds and shows a toast notification when a new employee sale is submitted.
- The sidebar logout button has been styled with white text for better visibility.

No new database migration is required for this notification update.
