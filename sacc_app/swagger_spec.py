
def get_swagger_spec():
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "SACCO Management API",
            "description": "API for SACCO Member Management, Loans, and Savings",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": "/api/method",
                "description": "Frappe API Base URL"
            }
        ],
        "tags": [
            {"name": "Auth", "description": "Authentication and User Verification"},
            {"name": "Members", "description": "Member Management and Profiles"},
            {"name": "Savings", "description": "Savings Deposits and Withdrawals"},
            {"name": "Loans", "description": "Loan Products, Applications, and Repayments"},
            {"name": "Accounts", "description": "Account management and hierarchy"},
            {"name": "Expenses", "description": "Expense Tracking and Management"},
            {"name": "Welfare", "description": "Welfare Contributions and Benefits"},
            {"name": "Roles & Permissions", "description": "System roles, access control, and permissions"},
            {"name": "Reports", "description": "Financial and Activity Reports"},
            {"name": "Locations", "description": "Geographical Data (Kenya)"},
            {"name": "Admin", "description": "System Settings, Roles, and Permissions"}
        ],
        "paths": {
            # --- Auth ---
            "/sacc_app.api.login": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "User Login + OTP",
                    "description": "Authenticate user and receive API keys",
                    "requestBody": {"content": {"application/x-www-form-urlencoded": {"schema": {"type": "object", "properties": {"usr": {"type": "string"}, "pwd": {"type": "string"}}, "required": ["usr", "pwd"]}}}},
                    "responses": {"200": {"description": "Successful Login"}}
                }
            },
            "/sacc_app.api.check_user_exists": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Check User Exists",
                    "requestBody": {"content": {"application/x-www-form-urlencoded": {"schema": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}}}},
                    "responses": {"200": {"description": "Result"}}
                }
            },
            "/sacc_app.api.send_otp": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Send OTP",
                    "requestBody": {"content": {"application/x-www-form-urlencoded": {"schema": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}}}},
                    "responses": {"200": {"description": "Result"}}
                }
            },
            "/sacc_app.api.verify_otp": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Verify OTP",
                    "requestBody": {"content": {"application/x-www-form-urlencoded": {"schema": {"type": "object", "properties": {"email": {"type": "string"}, "otp": {"type": "string"}}, "required": ["email", "otp"]}}}},
                    "responses": {"200": {"description": "Result"}}
                }
            },
            "/sacc_app.api.reset_password": {
                "post": {
                    "tags": ["Auth"],
                    "summary": "Reset Password",
                    "requestBody": {"content": {"application/x-www-form-urlencoded": {"schema": {"type": "object", "properties": {"email": {"type": "string"}, "otp": {"type": "string"}, "new_password": {"type": "string"}}, "required": ["email", "otp", "new_password"]}}}},
                    "responses": {"200": {"description": "Result"}}
                }
            },

            # --- Members ---
            "/sacc_app.api.get_member_profile": {
                "get": {
                    "tags": ["Members"],
                    "summary": "Get Member Profile",
                    "security": [{"ApiKeyAuth": []}],
                    "responses": {"200": {"description": "Member Profile Data"}}
                }
            },
            "/sacc_app.api.delete_member": {
                "post": {
                    "tags": ["Members"],
                    "summary": "Delete Member Record",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member_id": {"type": "string"}}, "required": ["member_id"]}}}},
                    "responses": {"200": {"description": "Deleted"}}
                }
            },
            "/sacc_app.api.create_member_application": {
                "post": {
                    "tags": ["Members"],
                    "summary": "Create Member Application",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string"}, "phone": {"type": "string"}, "national_id": {"type": "string"}, "county": {"type": "string"}, "sub_county": {"type": "string"}, "ward": {"type": "string"}, "village": {"type": "string"}, "national_id_image": {"type": "string"}, "passport_photo": {"type": "string"}}, "required": ["first_name", "last_name", "email", "phone", "national_id"]}}}},
                    "responses": {"200": {"description": "Application Created"}}
                }
            },
            "/sacc_app.api.get_all_members": {
                "get": {
                    "tags": ["Members"],
                    "summary": "Get All Members (Simple List)",
                    "responses": {"200": {"description": "List of Members"}}
                }
            },
            "/sacc_app.member_api.get_member_list": {
                "get": {
                    "tags": ["Members"],
                    "summary": "Get Member List (Paginated & Searchable)",
                    "parameters": [
                        {"name": "limit_start", "in": "query", "schema": {"type": "integer", "default": 0}},
                        {"name": "limit_page_length", "in": "query", "schema": {"type": "integer", "default": 20}},
                        {"name": "search", "in": "query", "schema": {"type": "string"}},
                        {"name": "status", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "List of Members"}}
                }
            },
            "/sacc_app.member_api.get_member_stats": {
                "get": {
                    "tags": ["Members"],
                    "summary": "Get Member Statistics",
                    "responses": {"200": {"description": "Statistics"}}
                }
            },
            "/sacc_app.member_api.edit_member": {
                "post": {
                    "tags": ["Members"],
                    "summary": "Edit Member Details",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "member_id": {"type": "string"},
                                        "first_name": {"type": "string"},
                                        "last_name": {"type": "string"},
                                        "email": {"type": "string"},
                                        "phone": {"type": "string"},
                                        "national_id": {"type": "string"},
                                        "county": {"type": "string"},
                                        "sub_county": {"type": "string"},
                                        "ward": {"type": "string"},
                                        "village": {"type": "string"},
                                        "national_id_image": {"type": "string"},
                                        "passport_photo": {"type": "string"}
                                    },
                                    "required": ["member_id"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Member updated"}}
                }
            },
            "/sacc_app.api.update_member": {
                "post": {
                    "tags": ["Members"],
                    "summary": "Update Member Record (Generic)",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member_id": {"type": "string"}, "data": {"type": "object"}}, "required": ["member_id"]}}}},
                    "responses": {"200": {"description": "Updated"}}
                }
            },
            "/sacc_app.api.set_member_status": {
                "post": {
                    "tags": ["Members"],
                    "summary": "Set Member Status (Direct)",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["member_id", "status"]}}}},
                    "responses": {"200": {"description": "Status Updated"}}
                }
            },
            "/sacc_app.member_api.disable_member": {
                "post": {
                    "tags": ["Members"],
                    "summary": "Disable a Member (Set to Inactive)",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "member_id": {"type": "string"}
                                    },
                                    "required": ["member_id"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Member disabled"}}
                }
            },
            "/sacc_app.member_api.enable_member": {
                "post": {
                    "tags": ["Members"],
                    "summary": "Enable a Member (Set to Active)",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "member_id": {"type": "string"}
                                    },
                                    "required": ["member_id"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Member enabled"}}
                }
            },
            "/sacc_app.api.pay_registration_fee": {
                "post": {
                    "tags": ["Members"],
                    "summary": "Pay Registration Fee",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member": {"type": "string"}, "amount": {"type": "number"}, "mode": {"type": "string"}, "reference": {"type": "string"}}, "required": ["member"]}}}},
                    "responses": {"200": {"description": "Success"}}
                }
            },
            "/sacc_app.api.generate_loan_ready_member": {
                "post": {
                    "tags": ["Members"],
                    "summary": "Generate Test Member (Loan Ready)",
                    "description": "Creates a random member, pays registration fee, and deposits initial savings.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "savings_amount": {"type": "number", "default": 100000},
                                        "registration_date": {"type": "string", "format": "date", "description": "Backdate the member registration (YYYY-MM-DD)"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Member Generated"}}
                }
            },
            "/sacc_app.member_api.get_member_full_details": {
                "get": {
                    "tags": ["Members"],
                    "summary": "Get Full Member Details (Financials + Registration)",
                    "parameters": [{"name": "member_id", "in": "query", "schema": {"type": "string"}, "required": True}],
                    "responses": {"200": {"description": "Full Details"}}
                }
            },
            "/sacc_app.api.get_member_financial_history": {
                "get": {
                    "tags": ["Members"],
                    "summary": "Member Financial History",
                    "parameters": [{"name": "member", "in": "query", "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "History"}}
                }
            },
            "/sacc_app.api.get_member_invoices": {
                "get": {
                    "tags": ["Members"],
                    "summary": "Get Member Pending Invoices",
                    "parameters": [{"name": "member", "in": "query", "schema": {"type": "string"}, "required": True}],
                    "responses": {"200": {"description": "List of Invoices"}}
                }
            },

            # --- Savings ---
            "/sacc_app.api.record_savings_deposit": {
                "post": {
                    "tags": ["Savings"],
                    "summary": "Record Savings Deposit",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member": {"type": "string"}, "amount": {"type": "number"}, "mode": {"type": "string"}, "reference": {"type": "string"}}, "required": ["member", "amount"]}}}},
                    "responses": {"200": {"description": "Success"}}
                }
            },
            "/sacc_app.api.record_savings_withdrawal": {
                "post": {
                    "tags": ["Savings"],
                    "summary": "Record Savings Withdrawal",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member": {"type": "string"}, "amount": {"type": "number"}, "mode": {"type": "string"}, "reference": {"type": "string"}}, "required": ["member", "amount"]}}}},
                    "responses": {"200": {"description": "Success"}}
                }
            },
            "/sacc_app.api.get_all_savings_deposits": {
                "get": {
                    "tags": ["Savings"],
                    "summary": "Get All Savings Deposits",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.dashboard_api.get_savings_growth": {
                "get": {
                    "tags": ["Savings", "Reports"],
                    "summary": "Get Savings Growth Monthly",
                    "responses": {"200": {"description": "Growth Data"}}
                }
            },
            "/sacc_app.api.get_savings_dashboard": {
                "get": {
                    "tags": ["Savings"],
                    "summary": "Get Savings Dashboard Stats",
                    "responses": {"200": {"description": "Dashboard Data"}}
                }
            },
            "/sacc_app.api.get_savings_vs_expense": {
                "get": {
                    "tags": ["Savings", "Reports"],
                    "summary": "Get Savings vs Expense (Last 6 Months)",
                    "responses": {"200": {"description": "Comparison Data"}}
                }
            },
            "/sacc_app.api.get_top_savers": {
                "get": {
                    "tags": ["Savings"],
                    "summary": "Get Top 5 Savers",
                    "responses": {"200": {"description": "List of Top Savers"}}
                }
            },
            "/sacc_app.api.get_savings_transactions": {
                "get": {
                    "tags": ["Savings"],
                    "summary": "Get Savings Transactions (Paginated & Filterable)",
                    "parameters": [
                        {"name": "limit_start", "in": "query", "schema": {"type": "integer", "default": 0}},
                        {"name": "limit_page_length", "in": "query", "schema": {"type": "integer", "default": 20}},
                        {"name": "member", "in": "query", "schema": {"type": "string"}},
                        {"name": "type", "in": "query", "schema": {"type": "string", "enum": ["Deposit", "Withdrawal"]}},
                        {"name": "date_from", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "date_to", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "searchTerm", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "List of Transactions"}}
                }
            },

            # --- Loans ---
            "/sacc_app.api.apply_for_loan": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Apply for a Loan",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member": {"type": "string"}, "amount": {"type": "number"}, "loan_product": {"type": "string"}, "repayment_period": {"type": "integer"}, "purpose": {"type": "string"}, "guarantors": {"type": "array", "items": {"type": "object"}}}, "required": ["member", "amount", "loan_product"]}}}},
                    "responses": {"200": {"description": "Applied"}}
                }
            },
            "/sacc_app.api.submit_loan_application": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Submit Loan Application",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"loan_id": {"type": "string"}}, "required": ["loan_id"]}}}},
                    "responses": {"200": {"description": "Submitted"}}
                }
            },
            "/sacc_app.api.approve_loan_application": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Approve Loan Application",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"loan_id": {"type": "string"}}, "required": ["loan_id"]}}}},
                    "responses": {"200": {"description": "Approved"}}
                }
            },
            "/sacc_app.api.disburse_loan": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Disburse Loan (Submit & Activate)",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"loan_id": {"type": "string"}}, "required": ["loan_id"]}}}},
                    "responses": {"200": {"description": "Disbursed"}}
                }
            },
            "/sacc_app.api.mark_loan_default": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Mark Loan as Defaulted",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"loan_id": {"type": "string"}}, "required": ["loan_id"]}}}},
                    "responses": {"200": {"description": "Marked Defaulted"}}
                }
            },
            "/sacc_app.api.create_loan_product": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Create Loan Product",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "product_name": {"type": "string"},
                                        "interest_rate": {"type": "number"},
                                        "interest_period": {"type": "string", "enum": ["Monthly", "Annually"]},
                                        "interest_method": {"type": "string", "enum": ["Flat Rate", "Reducing Balance"]},
                                        "max_repayment_period": {"type": "integer"},
                                        "min_loan_amount": {"type": "number"},
                                        "max_loan_amount": {"type": "number"},
                                        "requires_guarantor": {"type": "integer", "enum": [0, 1]},
                                        "min_guarantors": {"type": "integer"},
                                        "description": {"type": "string"}
                                    },
                                    "required": ["product_name", "interest_rate", "interest_period", "interest_method", "max_repayment_period"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Created"}}
                }
            },
            "/sacc_app.api.update_loan_product": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Update Loan Product",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"product_name": {"type": "string"}, "data": {"type": "object"}}, "required": ["product_name"]}}}},
                    "responses": {"200": {"description": "Updated"}}
                }
            },
            "/sacc_app.api.delete_loan_product": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Delete Loan Product",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}}},
                    "responses": {"200": {"description": "Deleted"}}
                }
            },
            "/sacc_app.api.get_loan_products": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get Loan Products Config (Simple)",
                    "responses": {"200": {"description": "List of configurations"}}
                }
            },
            "/sacc_app.api.get_all_loan_products": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get All Loan Products Detail",
                    "responses": {"200": {"description": "Detailed list of products"}}
                }
            },

            "/sacc_app.api.get_all_loan_repayments": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get All Loan Repayments",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.api.record_loan_repayment": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Record Loan Repayment",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"loan": {"type": "string"}, "amount": {"type": "number"}, "member": {"type": "string"}, "mode": {"type": "string"}, "deduct_from_savings": {"type": "boolean"}, "reference": {"type": "string"}}, "required": ["loan", "amount", "member"]}}}},
                    "responses": {"200": {"description": "Success"}}
                }
            },
            "/sacc_app.api.get_member_loans": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get Member Loans",
                    "parameters": [{"name": "member", "in": "query", "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Loans"}}
                }
            },
            "/sacc_app.api.get_loan_dashboard": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get Loan Dashboard Statistics",
                    "responses": {"200": {"description": "Dashboard Stats"}}
                }
            },
            "/sacc_app.api.get_loan_applications": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get Loan Applications (Paginated & Filterable)",
                    "parameters": [
                        {"name": "status", "in": "query", "schema": {"type": "string"}},
                        {"name": "member_name", "in": "query", "schema": {"type": "string"}},
                        {"name": "member_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "loan_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "limit_start", "in": "query", "schema": {"type": "integer", "default": 0}},
                        {"name": "limit_page_length", "in": "query", "schema": {"type": "integer", "default": 20}}
                    ],
                    "responses": {"200": {"description": "List of Loans"}}
                }
            },
            "/sacc_app.api.get_all_loan_applications": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get All Loan Applications (Simple List)",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.api.get_loan_application_by_id": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get Loan Application by ID",
                    "parameters": [
                        {"name": "loan_id", "in": "query", "schema": {"type": "string"}, "required": True}
                    ],
                    "responses": {"200": {"description": "Loan Details"}}
                }
            },
            "/sacc_app.dashboard_api.get_loan_breakdown": {
                "get": {
                    "tags": ["Loans", "Reports"],
                    "summary": "Get Loan Product Breakdown",
                    "responses": {"200": {"description": "Breakdown"}}
                }
            },
            "/sacc_app.dashboard_api.get_payment_requests": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get Payment Requests (Due)",
                    "parameters": [
                        {"name": "limit_start", "in": "query", "schema": {"type": "integer", "default": 0}},
                        {"name": "limit_page_length", "in": "query", "schema": {"type": "integer", "default": 20}},
                        {"name": "search", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "List"}}
                }
            },

            # --- Reports ---
            "/sacc_app.api.get_profit_and_loss": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Profit & Loss Statement",
                    "parameters": [
                        {"name": "from_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "to_date", "in": "query", "schema": {"type": "string", "format": "date"}}
                    ],
                    "responses": {"200": {"description": "P&L Report"}}
                }
            },
            "/sacc_app.api.get_balance_sheet": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Balance Sheet",
                    "parameters": [{"name": "to_date", "in": "query", "schema": {"type": "string", "format": "date"}}],
                    "responses": {"200": {"description": "Balance Sheet"}}
                }
            },
            "/sacc_app.api.get_trial_balance": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Trial Balance",
                    "parameters": [
                        {"name": "from_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "to_date", "in": "query", "schema": {"type": "string", "format": "date"}}
                    ],
                    "responses": {"200": {"description": "Trial Balance"}}
                }
            },
            "/sacc_app.api.get_account_statement": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Account Statement (GL)",
                    "description": "Get General Ledger statement. Provide either 'account' or 'member'.",
                    "parameters": [
                        {"name": "account", "in": "query", "schema": {"type": "string"}, "description": "Account Name or ID"},
                        {"name": "member", "in": "query", "schema": {"type": "string"}, "description": "Member ID (resolves to Savings Account)"},
                        {"name": "from_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "to_date", "in": "query", "schema": {"type": "string", "format": "date"}}
                    ],
                    "responses": {"200": {"description": "Statement"}}
                }
            },
            "/sacc_app.api.get_loan_repayment_summary": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Loan Repayment Summary",
                    "responses": {"200": {"description": "Report"}}
                }
            },
            "/sacc_app.api.get_loan_aging_report": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Loan Aging Report",
                    "responses": {"200": {"description": "Report"}}
                }
            },
            "/sacc_app.api.get_loan_performance_report": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Loan Performance Overview",
                    "responses": {"200": {"description": "Report"}}
                }
            },
            "/sacc_app.api.get_interest_collection_report": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Interest Collection Report",
                    "parameters": [
                        {"name": "loan_product", "in": "query", "schema": {"type": "string"}},
                        {"name": "from_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "to_date", "in": "query", "schema": {"type": "string", "format": "date"}}
                    ],
                    "responses": {"200": {"description": "Report"}}
                }
            },
            "/sacc_app.api.get_loan_ledger_report": {
                "get": {
                    "tags": ["Reports"],
                    "summary": "Loan Ledger Report",
                    "description": "Get loan ledger transactions with running balance. Filter by date range, member, or loan ID.",
                    "parameters": [
                        {"name": "date_from", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "date_to", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "member", "in": "query", "schema": {"type": "string"}},
                        {"name": "loan_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "limit_start", "in": "query", "schema": {"type": "integer", "default": 0}},
                        {"name": "limit_page_length", "in": "query", "schema": {"type": "integer", "default": 100}}
                    ],
                    "responses": {"200": {"description": "Ledger Report with Running Balance"}}
                }
            },
            "/sacc_app.api.get_auth_logs": {
                "get": {
                    "tags": ["Reports", "Admin"],
                    "summary": "Get Authentication Logs",
                    "parameters": [
                        {"name": "user", "in": "query", "schema": {"type": "string"}},
                        {"name": "from_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "to_date", "in": "query", "schema": {"type": "string", "format": "date"}}
                    ],
                    "responses": {"200": {"description": "Logs List"}}
                }
            },
            "/sacc_app.api.get_document_history": {
                "get": {
                    "tags": ["Reports", "Admin"],
                    "summary": "Get Audit History for a Document",
                    "parameters": [
                        {"name": "doctype", "in": "query", "schema": {"type": "string"}, "required": True},
                        {"name": "docname", "in": "query", "schema": {"type": "string"}, "required": True}
                    ],
                    "responses": {"200": {"description": "Timeline"}}
                }
            },
            "/sacc_app.api.get_all_audit_trails": {
                "get": {
                    "tags": ["Reports", "Admin"],
                    "summary": "System Activity Logs",
                    "responses": {"200": {"description": "Trails"}}
                }
            },

            # --- Locations ---
            "/sacc_app.location_api.seed_kenya_data": {
                "post": {
                    "tags": ["Locations"],
                    "summary": "Seed Kenya Location Data",
                    "responses": {"200": {"description": "Success"}}
                }
            },
            "/sacc_app.location_api.get_counties": {
                "get": {
                    "tags": ["Locations"],
                    "summary": "Get All Counties",
                    "responses": {"200": {"description": "Counties"}}
                }
            },
            "/sacc_app.location_api.get_constituencies": {
                "get": {
                    "tags": ["Locations"],
                    "summary": "Get Constituencies",
                    "parameters": [{"name": "county", "in": "query", "schema": {"type": "string"}, "required": True}],
                    "responses": {"200": {"description": "Constituencies"}}
                }
            },
            "/sacc_app.location_api.get_wards": {
                "get": {
                    "tags": ["Locations"],
                    "summary": "Get Wards",
                    "parameters": [{"name": "constituency", "in": "query", "schema": {"type": "string"}, "required": True}],
                    "responses": {"200": {"description": "Wards"}}
                }
            },

            # --- Welfare ---
            "/sacc_app.api.record_welfare_contribution": {
                "post": {
                    "tags": ["Welfare"],
                    "summary": "Record Welfare Transaction",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member": {"type": "string"}, "amount": {"type": "number"}, "purpose": {"type": "string"}, "type": {"type": "string"}, "claim_id": {"type": "string"}}, "required": ["member", "amount"]}}}},
                    "responses": {"200": {"description": "Success"}}
                }
            },
            "/sacc_app.api.get_member_welfare_history": {
                "get": {
                    "tags": ["Welfare"],
                    "summary": "Member Welfare History",
                    "parameters": [{"name": "member", "in": "query", "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "History List"}}
                }
            },
            "/sacc_app.api.get_all_welfare_contributions": {
                "get": {
                    "tags": ["Welfare"],
                    "summary": "Get All Welfare Contributions",
                    "parameters": [
                        {"name": "from_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "to_date", "in": "query", "schema": {"type": "string", "format": "date"}}
                    ],
                    "responses": {"200": {"description": "List of Contributions"}}
                }
            },
            "/sacc_app.welfare_claims_api.create_welfare_claim": {
                "post": {
                    "tags": ["Welfare"],
                    "summary": "Create Welfare Claim",
                    "description": "Create a new welfare claim for a member with reason and amount",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "member_id": {"type": "string"},
                                        "reason": {"type": "string", "enum": ["Medical Emergency", "Funeral/Demise", "Education Support", "Disaster Relief", "Other"]},
                                        "claim_amount": {"type": "number"},
                                        "description": {"type": "string"}
                                    },
                                    "required": ["member_id", "reason", "claim_amount"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Claim Created"}}
                }
            },
            "/sacc_app.welfare_claims_api.get_all_welfare_claims": {
                "get": {
                    "tags": ["Welfare"],
                    "summary": "Get All Welfare Claims",
                    "description": "Retrieve all welfare claims with optional filtering and pagination",
                    "parameters": [
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["Pending", "Approved", "Rejected", "Partially Paid", "Paid"]}},
                        {"name": "member_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "limit_start", "in": "query", "schema": {"type": "integer", "default": 0}},
                        {"name": "limit_page_length", "in": "query", "schema": {"type": "integer", "default": 20}}
                    ],
                    "responses": {"200": {"description": "List of Claims"}}
                }
            },
            "/sacc_app.welfare_claims_api.pay_welfare_claim": {
                "post": {
                    "tags": ["Welfare"],
                    "summary": "Pay Welfare Claim",
                    "description": "Process payment for a welfare claim and link it via Journal Entry",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "claim_id": {"type": "string"},
                                        "payment_amount": {"type": "number"},
                                        "payment_mode": {"type": "string", "enum": ["Cash", "Bank Transfer", "Mobile Money", "Cheque"], "default": "Cash"}
                                    },
                                    "required": ["claim_id", "payment_amount"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Payment Processed"}}
                }
            },
            "/sacc_app.welfare_claims_api.get_welfare_claim_by_id": {
                "get": {
                    "tags": ["Welfare"],
                    "summary": "Get Welfare Claim by ID",
                    "description": "Retrieve detailed information about a specific welfare claim",
                    "parameters": [
                        {"name": "claim_id", "in": "query", "schema": {"type": "string"}, "required": True}
                    ],
                    "responses": {"200": {"description": "Claim Details"}}
                }
            },
            "/sacc_app.welfare_claims_api.approve_welfare_claim": {
                "post": {
                    "tags": ["Welfare"],
                    "summary": "Approve Welfare Claim",
                    "description": "Approve a welfare claim and set the approved amount per member",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "claim_id": {"type": "string"},
                                        "amount_per_member": {"type": "number"}
                                    },
                                    "required": ["claim_id", "amount_per_member"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Claim Approved"}}
                }
            },
            "/sacc_app.welfare_dashboard_api.get_welfare_stats": {
                "get": {
                    "tags": ["Welfare", "Reports"],
                    "summary": "Get Welfare Dashboard Statistics",
                    "description": "Get statistics for Claims and Contributions",
                    "responses": {"200": {"description": "Stats"}}
                }
            },

            "/sacc_app.api.get_transactions_dashboard": {
                "get": {
                    "tags": ["Transactions"],
                    "summary": "Get Transaction Dashboard Stats",
                    "responses": {"200": {"description": "Stats Data"}}
                }
            },
            "/sacc_app.api.get_all_transactions": {
                "get": {
                    "tags": ["Transactions"],
                    "summary": "Get All Transactions (Paginated & Filterable)",
                    "parameters": [
                        {"name": "limit_start", "in": "query", "schema": {"type": "integer", "default": 0}},
                        {"name": "limit_page_length", "in": "query", "schema": {"type": "integer", "default": 20}},
                        {"name": "category", "in": "query", "schema": {"type": "string", "enum": ["Savings", "Loan", "Expense"]}},
                        {"name": "start_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "end_date", "in": "query", "schema": {"type": "string", "format": "date"}},
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["Completed", "Cancelled", "Draft"]}},
                        {"name": "search", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "List of Transactions"}}
                }
            },
            "/sacc_app.api.get_transaction_details": {
                "get": {
                    "tags": ["Transactions"],
                    "summary": "Get Transaction Details",
                    "parameters": [{"name": "transaction_id", "in": "query", "schema": {"type": "string"}, "required": True}],
                    "responses": {"200": {"description": "Transaction Details"}}
                }
            },
            # --- Accounts ---
            "/sacc_app.api.create_account": {
                "post": {
                    "tags": ["Accounts"],
                    "summary": "Create GL Account",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"account_name": {"type": "string"}, "parent_account": {"type": "string"}, "is_group": {"type": "integer", "enum": [0, 1]}, "account_type": {"type": "string"}}, "required": ["account_name", "parent_account"]}}}},
                    "responses": {"200": {"description": "Created"}}
                }
            },
            "/sacc_app.api.get_parent_accounts": {
                "get": {
                    "tags": ["Accounts"],
                    "summary": "Get Group Accounts (Parents)",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.api.get_expense_accounts": {
                "get": {
                    "tags": ["Accounts"],
                    "summary": "Get Expense Accounts",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.api.get_all_accounts_with_balances": {
                "get": {
                    "tags": ["Accounts"],
                    "summary": "Get All Accounts with Current Balances",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.api.update_account": {
                "post": {
                    "tags": ["Accounts"],
                    "summary": "Update GL Account",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"account_name": {"type": "string"}, "data": {"type": "object"}}, "required": ["account_name"]}}}},
                    "responses": {"200": {"description": "Updated"}}
                }
            },
            "/sacc_app.api.delete_account": {
                "post": {
                    "tags": ["Accounts"],
                    "summary": "Delete GL Account",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"account_name": {"type": "string"}}, "required": ["account_name"]}}}},
                    "responses": {"200": {"description": "Deleted"}}
                }
            },
            # --- Expenses ---
            "/sacc_app.expense_api.get_expense_dashboard_stats": {
                "get": {
                    "tags": ["Expenses"],
                    "summary": "Get Expense Dashboard Statistics",
                    "responses": {"200": {"description": "Dashboard Stats"}}
                }
            },
            "/sacc_app.expense_api.get_expenses_by_category": {
                "get": {
                    "tags": ["Expenses"],
                    "summary": "Get Expenses Breakdown by Category",
                    "responses": {"200": {"description": "Category Breakdown"}}
                }
            },
            "/sacc_app.expense_api.get_monthly_expense_trends": {
                "get": {
                    "tags": ["Expenses"],
                    "summary": "Get Monthly Expense Trends (Last 6 Months)",
                    "responses": {"200": {"description": "Monthly Trends"}}
                }
            },
            "/sacc_app.expense_api.get_all_expense_transactions": {
                "get": {
                    "tags": ["Expenses"],
                    "summary": "Get All Expense Transactions (Paginated & Filterable)",
                    "parameters": [
                        {"name": "limit_start", "in": "query", "schema": {"type": "integer", "default": 0}},
                        {"name": "limit_page_length", "in": "query", "schema": {"type": "integer", "default": 20}},
                        {"name": "search", "in": "query", "schema": {"type": "string"}},
                        {"name": "category", "in": "query", "schema": {"type": "string"}},
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["Completed", "Cancelled"]}}
                    ],
                    "responses": {"200": {"description": "List of Expenses"}}
                }
            },
            "/sacc_app.expense_api.get_expense_details": {
                "get": {
                    "tags": ["Expenses"],
                    "summary": "Get Expense Transaction Details by ID",
                    "parameters": [
                        {"name": "expense_id", "in": "query", "schema": {"type": "string"}, "required": True}
                    ],
                    "responses": {"200": {"description": "Expense Details"}}
                }
            },
            "/sacc_app.api.record_expense": {
                "post": {
                    "tags": ["Expenses"],
                    "summary": "Record Expense (Journal Entry)",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"amount": {"type": "number"}, "expense_account": {"type": "string"}, "description": {"type": "string"}, "mode_of_payment": {"type": "string"}, "vendor_name": {"type": "string"}}, "required": ["amount", "expense_account", "description"]}}}},
                    "responses": {"200": {"description": "Success"}}
                }
            },
            "/sacc_app.api.get_all_expenses": {
                "get": {
                    "tags": ["Expenses"],
                    "summary": "Get All Expenses (Vouchers)",
                    "responses": {"200": {"description": "List"}}
                }
            },

            # --- Roles & Permissions ---
            "/sacc_app.api.get_all_roles": {
                "get": {
                    "tags": ["Roles & Permissions"],
                    "summary": "Get All System Roles",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.api.create_role": {
                "post": {
                    "tags": ["Roles & Permissions"],
                    "summary": "Create System Role",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"role_name": {"type": "string"}}, "required": ["role_name"]}}}},
                    "responses": {"200": {"description": "Created"}}
                }
            },
            "/sacc_app.api.update_role": {
                "post": {
                    "tags": ["Roles & Permissions"],
                    "summary": "Update Role Access",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"role_name": {"type": "string"}, "desk_access": {"type": "integer", "enum": [0, 1]}}, "required": ["role_name"]}}}},
                    "responses": {"200": {"description": "Updated"}}
                }
            },
            "/sacc_app.api.delete_role": {
                "post": {
                    "tags": ["Roles & Permissions"],
                    "summary": "Delete System Role",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"role_name": {"type": "string"}}, "required": ["role_name"]}}}},
                    "responses": {"200": {"description": "Deleted"}}
                }
            },
            "/sacc_app.api.get_role_permissions": {
                "get": {
                    "tags": ["Roles & Permissions"],
                    "summary": "Get Permissions for a Role",
                    "parameters": [{"name": "role", "in": "query", "schema": {"type": "string"}, "required": True}],
                    "responses": {"200": {"description": "Permissions List"}}
                }
            },
            "/sacc_app.api.assign_permission": {
                "post": {
                    "tags": ["Roles & Permissions"],
                    "summary": "Assign DocType Permission to Role",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"doctype": {"type": "string"}, "role": {"type": "string"}, "read": {"type": "integer"}, "write": {"type": "integer"}, "create": {"type": "integer"}, "delete": {"type": "integer"}}, "required": ["doctype", "role"]}}}},
                    "responses": {"200": {"description": "Assigned"}}
                }
            },
            "/sacc_app.api.update_doctype_permissions": {
                "post": {
                    "tags": ["Roles & Permissions"],
                    "summary": "Batch Update DocType Permissions",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"doctype": {"type": "string"}, "role": {"type": "string"}, "permissions": {"type": "object"}}, "required": ["doctype", "role", "permissions"]}}}},
                    "responses": {"200": {"description": "Updated"}}
                }
            },
            "/sacc_app.api.get_doctypes_and_permissions": {
                "get": {
                    "tags": ["Roles & Permissions"],
                    "summary": "Get All DocTypes and their Active Permissions",
                    "parameters": [{"name": "module", "in": "query", "schema": {"type": "string", "default": "Sacco"}}],
                    "responses": {"200": {"description": "Data Map"}}
                }
            },
            # --- Admin ---
            "/sacc_app.dashboard_api.get_dashboard_stats": {
                "get": {
                    "tags": ["Admin"],
                    "summary": "Get Dashboard High-level Stats",
                    "responses": {"200": {"description": "Stats"}}
                }
            },
            "/sacc_app.dashboard_api.get_recent_activities": {
                "get": {
                    "tags": ["Admin"],
                    "summary": "Get Recent System Activities",
                    "parameters": [
                        {"name": "limit_start", "in": "query", "schema": {"type": "integer", "default": 0}},
                        {"name": "limit_page_length", "in": "query", "schema": {"type": "integer", "default": 15}},
                        {"name": "search", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "Activity Feed"}}
                }
            },
            "/sacc_app.api.get_company_details": {
                "get": {
                    "tags": ["Admin"],
                    "summary": "Get Company Details",
                    "responses": {"200": {"description": "Company Details"}}
                }
            },
            "/sacc_app.api.get_sacco_settings": {
                "get": {
                    "tags": ["Admin"],
                    "summary": "Get SACCO Global Settings",
                    "responses": {"200": {"description": "Settings"}}
                }
            },
            "/sacc_app.api.update_sacco_settings": {
                "post": {
                    "tags": ["Admin"],
                    "summary": "Update SACCO Global Settings",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "registration_fee": {"type": "number"},
                                        "charge_registration_fee_on_onboarding": {"type": "integer", "enum": [0, 1]}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Updated"}}
                }
            },
            
            # --- Budgeting ---
            "/sacc_app.budget_api.get_cost_centers": {
                "get": {
                    "tags": ["Budgeting"],
                    "summary": "Get All Cost Centers",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.budget_api.get_fiscal_years": {
                "get": {
                    "tags": ["Budgeting"],
                    "summary": "Get Fiscal Years",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.budget_api.create_budget_request": {
                "post": {
                    "tags": ["Budgeting"],
                    "summary": "Create Budget (Draft)",
                    "description": "Creates a budget for a cost center. Blocks transactions by default.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "cost_center": {"type": "string"},
                                        "fiscal_year": {"type": "string"},
                                        "items": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "account": {"type": "string"},
                                                    "budget_amount": {"type": "number"}
                                                }
                                            }
                                        }
                                    },
                                    "required": ["cost_center", "fiscal_year", "items"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Created"}}
                }
            },
            "/sacc_app.budget_api.approve_budget": {
                "post": {
                    "tags": ["Budgeting"],
                    "summary": "Approve/Enable Budget",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"budget_id": {"type": "string"}}, "required": ["budget_id"]}}}},
                    "responses": {"200": {"description": "Enabled"}}
                }
            },
            "/sacc_app.budget_api.disable_budget": {
                "post": {
                    "tags": ["Budgeting"],
                    "summary": "Disable Budget (Cancel)",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"budget_id": {"type": "string"}}, "required": ["budget_id"]}}}},
                    "responses": {"200": {"description": "Disabled"}}
                }
            },
            "/sacc_app.budget_api.enable_budget": {
                "post": {
                    "tags": ["Budgeting"],
                    "summary": "Re-enable Budget",
                    "description": "Re-activates a disabled budget by creating a new version",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"budget_id": {"type": "string"}}, "required": ["budget_id"]}}}},
                    "responses": {"200": {"description": "Re-enabled"}}
                }
            },
            "/sacc_app.budget_api.get_budgets": {
                "get": {
                    "tags": ["Budgeting"],
                    "summary": "Get Budgets",
                    "parameters": [
                        {"name": "cost_center", "in": "query", "schema": {"type": "string"}},
                        {"name": "fiscal_year", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.budget_api.delete_budget": {
                "post": {
                    "tags": ["Budgeting"],
                    "summary": "Delete Budget (Draft Only)",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"budget_id": {"type": "string"}}, "required": ["budget_id"]}}}},
                    "responses": {"200": {"description": "Deleted"}}
                }
            },
            "/sacc_app.api.delete_sacco_settings": {
                "post": {
                    "tags": ["Admin"],
                    "summary": "Delete SACCO Global Settings",
                    "responses": {"200": {"description": "Deleted"}}
                }
            },
            "/sacc_app.api.get_openapi_spec": {
                "get": {
                    "tags": ["Admin"],
                    "summary": "Get OpenAPI/Swagger JSON Spec",
                    "responses": {"200": {"description": "JSON Content"}}
                }
            },
            "/sacc_app.api.get_all_users": {
                "get": {
                    "tags": ["Admin"],
                    "summary": "Get All System Users",
                    "description": "Returns all users with their roles and status",
                    "responses": {"200": {"description": "List of Users"}}
                }
            },
            "/sacc_app.api.get_current_user": {
                "get": {
                    "tags": ["Admin"],
                    "summary": "Get Current User & Permissions",
                    "responses": {"200": {"description": "User Info"}}
                }
            },
            "/sacc_app.api.create_user": {
                "post": {
                    "tags": ["Admin"],
                    "summary": "Create System User",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"email": {"type": "string"}, "first_name": {"type": "string"}, "last_name": {"type": "string"}, "roles": {"type": "array", "items": {"type": "string"}}}, "required": ["email", "first_name", "last_name"]}}}},
                    "responses": {"200": {"description": "Created"}}
                }
            },
            "/sacc_app.api.set_user_status": {
                "post": {
                    "tags": ["Admin"],
                    "summary": "Enable/Disable User",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"user_id": {"type": "string"}, "status": {"type": "string", "enum": ["Enabled", "Disabled"]}}, "required": ["user_id", "status"]}}}},
                    "responses": {"200": {"description": "Updated"}}
                }
            },

            # Note: Other niche admin APIs like permissions/roles are present but omitted from this condensed list for brevity in Swagger, 
            # though usually they'd be fully documented.
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": "Enter your API Key and Secret in the format: `token <api_key>:<api_secret>`"
                }
            }
        }
    }
