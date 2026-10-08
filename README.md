# Leave Management

Enhanced leave request and allocation management for Odoo 18.

## Overview

The **Leave Management** module extends the standard Odoo HR toolkit with a
self-contained leave workflow: create leave types, allocate days to employees,
submit requests, and track approvals — all with role-based access control.

## Features

- **Custom Leave Types** — Define named leave categories (e.g. Vacation, Sick
  Leave) with an optional maximum day count and colour coding.
- **Leave Allocations** — Grant a number of leave days to a specific employee
  for a given type within a date range.
- **Leave Requests** — Employees submit date-bounded requests; managers confirm,
  approve, or refuse them.
- **Balance checking** — Requests are blocked when the remaining allocated
  balance is insufficient.
- **Overlap prevention** — The system rejects new requests that overlap with an
  already confirmed or approved request for the same employee.
- **Role-based access** — Two groups (`Leave User`, `Leave Manager`) control
  who can read, write, and manage data.
- **Multi-view support** — List, calendar, form, graph, and pivot views for
  requests; list and form views for allocations and leave types.
- **Audit trail** — Both `LeaveRequest` and `LeaveAllocation` inherit
  `mail.thread` and `mail.activity.mixin` for chatter, followers, and
  activities.

## Module metadata

| Key | Value |
|---|---|
| Name | `Leave Management` |
| Version | `1.0.0` |
| License | `LGPL-3` |
| Category | `Human Resources` |
| Dependencies | `base`, `hr`, `mail` |

## Data model

### `leave.type`
| Field | Type | Description |
|---|---|---|
| `name` | Char | Leave type name (required) |
| `code` | Char | Short code for the type |
| `max_days` | Integer | Maximum days allowed per request |
| `requires_allocation` | Boolean | Whether an allocation is required before requesting |
| `active` | Boolean | Archived when unchecked |
| `color` | Integer | Calendar colour index |

### `leave.request`
| Field | Type | Description |
|---|---|---|
| `name` | Char (computed) | Display name: *Employee – Type – Date range* |
| `employee_id` | Many2one → `hr.employee` | Requesting employee (required) |
| `leave_type_id` | Many2one → `leave.type` | Leave type (required) |
| `manager_id` | Many2one → `hr.employee` | Employee's manager (auto-filled from hierarchy) |
| `date_from` | Date | Start date (required) |
| `date_to` | Date | End date (required) |
| `reason` | Text | Reason for leave (required) |
| `number_of_days` | Integer (computed) | Inclusive day count between `date_from` and `date_to` |
| `available_balance` | Float (computed) | Remaining approved allocation minus approved usage |
| `state` | Selection | `draft` → `confirm` → `approved` / `refused`; `cancelled` |
| `leave_type_color` | Integer (related) | Mirrors `leave_type_id.color` |

### `leave.allocation`
| Field | Type | Description |
|---|---|---|
| `name` | Char | Allocation name (required) |
| `employee_id` | Many2one → `hr.employee` | Allocated to (required) |
| `leave_type_id` | Many2one → `leave.type` | Leave type (required) |
| `number_of_days` | Integer | Number of days allocated (required, > 0) |
| `date_from` | Date | Valid-from date |
| `date_to` | Date | Valid-to date |
| `notes` | Text | Free-form notes |
| `state` | Selection | Same lifecycle states as leave requests |

## Workflow

Leave requests and allocations share the same state machine:

```
draft ──confirm──▶ confirm ──approve──▶ approved
                   │                    │
                   └──refuse──▶ refused │
                   │                    │
                   └──cancel──▶ cancelled
                                   │
                                   └──draft (Reset to Draft)
```

| Action | Available in states | Description |
|---|---|---|
| **Confirm** | `draft` | Moves to `confirm` after verifying sufficient balance |
| **Approve** | `confirm` | Moves to `approved` (manager/HR access required, balance checked) |
| **Refuse** | `confirm` | Moves to `refused` (manager/HR access required) |
| **Cancel** | `draft`, `confirm`, `approved` | Moves to `cancelled` |
| **Reset to Draft** | `cancelled`, `refused` | Moves back to `draft` |

## Security

### Groups
| Group | Description |
|---|---|
| `group_leave_user` | Can view leave types; create, read, and write own leave requests |
| `group_leave_manager` | Full access: approve/refuse leaves, manage allocations and leave types |

`group_leave_manager` implies `group_leave_user` and is assigned to
`base.user_root` and `base.user_admin` by default.

### Record rules
- **Users** can only see their own leave requests
  (`('employee_id.user_id', '=', user.id)`).
- **Managers** see all leave requests (`(1, '=', 1)`).

### Access rights (`ir.model.access.csv`)
| Model | Leave User | Leave Manager |
|---|---|---|
| `leave.type` | read | CRUD |
| `leave.request` | read, write, create | CRUD |
| `leave.allocation` | read | CRUD |

## Views

| File | Views |
|---|---|
| `views/leave_views.xml` | Leave Type — list, form; root menu, action, menu item |
| `views/leave_request_view.xml` | Leave Request — list, calendar, search, form, graph, pivot; action, menu, reporting submenu |
| `views/leave_allocation_view.xml` | Leave Allocation — form, list; action, menu |

## Project structure

```
leave_management/
├── __init__.py
├── __manifest__.py
├── README.md                 ← this file
├── models/
│   ├── __init__.py
│   └── models.py             # LeaveType, LeaveRequest, LeaveAllocation
├── security/
│   ├── leave_security.xml    # Groups & module category
│   ├── ir.model.access.csv   # Access rights
│   └── leave_record_rules.xml  # Record rules
└── views/
    ├── leave_views.xml       # Leave Type views & menu
    ├── leave_request_view.xml  # Leave Request views & menu
    └── leave_allocation_view.xml  # Leave Allocation views & menu
```

## Installation

1. Copy the `leave_management` folder into your Odoo `addons` path
   (the `custom_modules/` directory is already configured in this
   project's `conf/odoo.conf`).

2. Update the apps list and install:

   ```bash
   .venv/bin/python odoo-18.0/odoo-bin -c conf/odoo.conf -d odoo18 -i leave_management --stop-after-init
   ```

3. Or use the VS Code task **Odoo: Install module** and enter
   `leave_management` when prompted.

## Usage

1. **Configure leave types** under *Leave Management ▸ Leave Type*.
2. **Allocate days** under *Leave Management ▸ Leave Allocation* — assign
   days to an employee for a specific type.
3. **Submit requests** under *Leave Management ▸ Leave Requests* — employees
   fill in the form, then click **Confirm** → **Approve**.
4. **Analyse** results via *Leave Management ▸ Reporting ▸ Leave Analysis*
   (graph/pivot views).

## Dependencies

- `base`
- `hr` (employee hierarchy, manager relations)
- `mail` (chatter, activities)
