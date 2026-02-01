from sacc_app.swagger_spec import get_swagger_spec
import json

def run_test():
    print("Verifying Swagger Spec for create_loan_product...")
    spec = get_swagger_spec()
    path = "/sacc_app.api.create_loan_product"
    
    if path in spec["paths"]:
        post_spec = spec["paths"][path].get("post", {})
        request_body = post_spec.get("requestBody", {})
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})
        properties = schema.get("properties", {})
        
        if properties:
            print(f"✅ Success: Properties found for {path}:")
            print(json.dumps(properties, indent=4))
            
            required = schema.get("required", [])
            print(f"Required fields: {required}")
        else:
            print(f"❌ Failure: No properties found for {path}")
    else:
        print(f"❌ Failure: Path {path} not found in spec")

if __name__ == "__main__":
    run_test()
