import hcl2
import requests
import boto3
import json

session = boto3.Session(
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    region_name='us-east-1'  # Pricing API is region-agnostic
)
pricing_client = session.client('pricing')

def get_ec2_pricing(instance_type):
    response = pricing_client.get_products(
        ServiceCode='AmazonEC2',
        Filters=[
            {
                'Type': 'TERM_MATCH',
                'Field': 'instanceType',
                'Value': instance_type
            }
        ],
        MaxResults=1  # Limit results for simplicity
    )
    
    for product in response['PriceList']:
        product_data = json.loads(product)
        price_dimensions = product_data['terms']['OnDemand']
        for price in price_dimensions.values():
            for dimension in price['priceDimensions'].values():
                return dimension['pricePerUnit']['USD']

def get_s3_pricing(storage_class):
    """
    Get S3 pricing for a specified storage class.

    Args:
        storage_class (str): The S3 storage class (e.g., "Standard", "Intelligent-Tiering").

    Returns:
        float: The price per GB for the specified storage class, or None if not found.
    """
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonS3',
            Filters=[
                {
                    'Type': 'TERM_MATCH',
                    'Field': 'storageClass',
                    'Value': storage_class
                }
            ],
            MaxResults=1  # Limit results for simplicity
        )

        # Parse the response to extract the price
        for product in response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']
            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    return float(price_dimension['pricePerUnit']['USD'])

    except Exception as e:
        print(f"Error fetching pricing data: {e}")

    return None

def get_rds_pricing(db_instance_class, engine, license_model):
    """
    Get RDS pricing for a specified DB instance class, engine, and license model.

    Args:
        db_instance_class (str): The RDS DB instance class (e.g., "db.t3.micro").
        engine (str): The database engine (e.g., "mysql", "postgresql").
        license_model (str): The license model (e.g., "license-included", "bring-your-own-license").

    Returns:
        float: The price per hour for the specified DB instance configuration, or None if not found.
    """
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonRDS',
            Filters=[
                {
                    'Type': 'TERM_MATCH',
                    'Field': 'dbInstanceClass',
                    'Value': db_instance_class
                },
                {
                    'Type': 'TERM_MATCH',
                    'Field': 'databaseEngine',
                    'Value': engine
                },
                {
                    'Type': 'TERM_MATCH',
                    'Field': 'licenseModel',
                    'Value': license_model
                }
            ],
            MaxResults=1  # Limit results for simplicity
        )

        # Parse the response to extract the price
        for product in response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']
            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    return float(price_dimension['pricePerUnit']['USD'])

def get_lambda_pricing():
    """
    Get AWS Lambda pricing and estimate monthly cost based on user input.

    Returns:
        dict: A dictionary with the estimated monthly cost or None if not found.
    """
    try:
        response = pricing_client.get_products(
            ServiceCode='AWSLambda',
            Filters=[],
            MaxResults=1  # Limit results for simplicity
        )

        # Parse the response to extract the price
        for product in response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']
            pricing_info = {}

            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    pricing_info['price_per_request'] = float(price_dimension['pricePerUnit']['USD'])  # Price per request
                    pricing_info['price_per_gb_second'] = float(price_dimension['pricePerUnit']['USD'])  # Price per GB-second

            # Get user input for estimation
            requests_per_day = int(input("Enter the estimated number of requests per day: "))
            execution_time_seconds = float(input("Enter the average execution time of the Lambda function in seconds: "))
            memory_size_mb = int(input("Enter the allocated memory size for the Lambda function (in MB): "))

            # Calculate estimated monthly cost
            days_per_month = 30  # Approximate number of days in a month
            total_requests = requests_per_day * days_per_month
            total_duration_gb_seconds = (execution_time_seconds / 1024) * memory_size_mb * total_requests  # GB-seconds

            monthly_cost = (total_requests * pricing_info['price_per_request']) + (total_duration_gb_seconds * pricing_info['price_per_gb_second'])

            return {
                'monthly_cost': monthly_cost,
                'price_per_request': pricing_info['price_per_request'],
                'price_per_gb_second': pricing_info['price_per_gb_second']
            }

    except Exception as e:
        print(f"Error fetching pricing data: {e}")

    return None


# Function to get AWS pricing information
def get_aws_price(service, region, instance_type):
    # Placeholder for AWS Pricing API call
    # Ideally, you would fetch pricing data here
    # Example: response = requests.get(...)
    return 0.0  # Replace with actual pricing

# Function to calculate estimated cost from Terraform config
def calculate_cost(terraform_file):
    with open(terraform_file, 'r') as file:
        terraform_config = hcl2.load(file)

    total_cost = 0.0
    
    # Iterate through resources
    for resource in terraform_config.get('resource', {}):
        for resource_type, resource_details in resource.items():
            # Extract details for EC2 instances as an example
            if resource_type == 'aws_instance':
                instance_type = resource_details['instance_type']
                region = resource_details['provider'].split('.')[-1]  # Assuming provider is specified
                # Call the pricing function
                cost = get_aws_price('EC2', region, instance_type)
                total_cost += cost  # You would need to multiply by count or hours, etc.

    return total_cost

# Example usage
terraform_file = 'path/to/your/terraform.tf'  # Specify your Terraform file path
estimated_cost = calculate_cost(terraform_file)
print(f'Estimated Monthly Cost: ${estimated_cost:.2f}')
