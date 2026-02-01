
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
            {"name": "Reports", "description": "Financial and Activity Reports"},
            {"name": "Locations", "description": "Geographical Data (Kenya)"},
            {"name": "Welfare", "description": "Welfare Contributions and Benefits"},
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

            # --- Loans ---
            "/sacc_app.api.apply_for_loan": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Apply for a Loan",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member": {"type": "string"}, "amount": {"type": "number"}, "loan_product": {"type": "string"}, "guarantors": {"type": "array", "items": {"type": "object"}}}, "required": ["member", "amount", "loan_product"]}}}},
                    "responses": {"200": {"description": "Applied"}}
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
            "/sacc_app.api.get_all_loan_products": {
                "get": {
                    "tags": ["Loans"],
                    "summary": "Get All Loan Products",
                    "responses": {"200": {"description": "List"}}
                }
            },
            "/sacc_app.api.disburse_loan": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Disburse Approved Loan",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"loan_id": {"type": "string"}}}}}},
                    "responses": {"200": {"description": "Disbursed"}}
                }
            },
            "/sacc_app.api.record_loan_repayment": {
                "post": {
                    "tags": ["Loans"],
                    "summary": "Record Loan Repayment",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"loan": {"type": "string"}, "amount": {"type": "number"}, "member": {"type": "string"}, "deduct_from_savings": {"type": "boolean"}, "reference": {"type": "string"}}, "required": ["loan", "amount", "member"]}}}},
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
                    "parameters": [
                        {"name": "account", "in": "query", "schema": {"type": "string"}},
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
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"member": {"type": "string"}, "amount": {"type": "number"}, "purpose": {"type": "string"}, "type": {"type": "string"}}, "required": ["member", "amount"]}}}},
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
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                    "responses": {"200": {"description": "Updated"}}
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
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                    "responses": {"200": {"description": "Created"}}
                }
            }
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
