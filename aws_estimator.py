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


def get_dynamodb_pricing():
    """
    Get AWS DynamoDB pricing and estimate monthly cost based on user input.

    Returns:
        dict: A dictionary with the estimated monthly cost or None if not found.
    """
    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonDynamoDB',
            Filters=[],
            MaxResults=1  # Limit results for simplicity
        )

        # Parse the response to extract the pricing information
        for product in response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']
            pricing_info = {}

            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    if 'ReadCapacityUnit' in price_dimension['description']:
                        pricing_info['price_per_read'] = float(price_dimension['pricePerUnit']['USD'])  # Price per read request
                    elif 'WriteCapacityUnit' in price_dimension['description']:
                        pricing_info['price_per_write'] = float(price_dimension['pricePerUnit']['USD'])  # Price per write request
                    elif 'DataTransfer' in price_dimension['description']:
                        pricing_info['price_per_data_transfer'] = float(price_dimension['pricePerUnit']['USD'])  # Price per GB transferred

            # Get user input for estimation
            reads_per_month = int(input("Enter the estimated number of read requests per month: "))
            writes_per_month = int(input("Enter the estimated number of write requests per month: "))
            data_transfer_gb = float(input("Enter the estimated data transfer in GB per month: "))

            # Calculate estimated monthly cost
            monthly_cost = (
                (reads_per_month * pricing_info['price_per_read']) +
                (writes_per_month * pricing_info['price_per_write']) +
                (data_transfer_gb * pricing_info['price_per_data_transfer'])
            )

            return {
                'monthly_cost': monthly_cost,
                'price_per_read': pricing_info['price_per_read'],
                'price_per_write': pricing_info['price_per_write'],
                'price_per_data_transfer': pricing_info['price_per_data_transfer']
            }

    except Exception as e:
        print(f"Error fetching pricing data: {e}")

    return None

def get_vpc_pricing():
    """
    Get AWS VPC pricing and estimate monthly cost based on user input.

    Returns:
        dict: A dictionary with the estimated monthly cost or None if not found.
    """
    try:
        # Fetch VPC pricing
        response = pricing_client.get_products(
            ServiceCode='AmazonVPC',
            Filters=[],
            MaxResults=1  # Limit results for simplicity
        )

        # Parse the response to extract the pricing information
        pricing_info = {
            'price_per_hour': 0,
            'price_per_data_transfer': 0,
            'price_per_elastic_ip': 0
        }

        for product in response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']

            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    if 'VPC' in price_dimension['description']:
                        pricing_info['price_per_hour'] = float(price_dimension['pricePerUnit']['USD'])  # Price per hour for VPC
                    elif 'DataTransfer' in price_dimension['description']:
                        pricing_info['price_per_data_transfer'] = float(price_dimension['pricePerUnit']['USD'])  # Price per GB transferred

        # Fetch Elastic IP pricing
        elastic_ip_response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {
                    'Type': 'TERM_MATCH',
                    'Field': 'productFamily',
                    'Value': 'Elastic IP Addresses'
                }
            ],
            MaxResults=1
        )

        for product in elastic_ip_response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']

            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    pricing_info['price_per_elastic_ip'] = float(price_dimension['pricePerUnit']['USD'])  # Price per Elastic IP

        # Get user input for estimation
        hours_per_day = float(input("Enter the number of hours the VPC will be active per day: "))
        days_per_month = 30  # Approximate number of days in a month
        data_transfer_gb = float(input("Enter the estimated data transfer in GB per month: "))
        elastic_ips_count = int(input("Enter the number of Elastic IPs in use: "))

        # Calculate estimated monthly cost
        monthly_cost = (
            (hours_per_day * days_per_month * pricing_info['price_per_hour']) +
            (data_transfer_gb * pricing_info['price_per_data_transfer']) +
            (elastic_ips_count * pricing_info['price_per_elastic_ip'] * days_per_month)  # Cost for Elastic IPs
        )

        return {
            'monthly_cost': monthly_cost,
            'price_per_hour': pricing_info['price_per_hour'],
            'price_per_data_transfer': pricing_info['price_per_data_transfer'],
            'price_per_elastic_ip': pricing_info['price_per_elastic_ip']
        }

    except Exception as e:
        print(f"Error fetching pricing data: {e}")

    return None


def get_ecs_pricing():
    """
    Get AWS ECS pricing and estimate monthly cost based on user input.

    Returns:
        dict: A dictionary with the estimated monthly cost or None if not found.
    """
    try:
        # Fetch EC2 instance pricing
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {
                    'Type': 'TERM_MATCH',
                    'Field': 'productFamily',
                    'Value': 'Compute Instance'
                }
            ],
            MaxResults=1
        )

        # Parse the response to extract EC2 instance pricing information
        pricing_info = {
            'price_per_hour_ec2': 0,
            'price_per_hour_fargate': 0
        }

        # Get EC2 instance pricing
        for product in response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']

            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    if 'Linux' in price_dimension['description']:  # Adjust for your instance type
                        pricing_info['price_per_hour_ec2'] = float(price_dimension['pricePerUnit']['USD'])  # Price per hour for EC2

        # Fetch Fargate pricing
        fargate_response = pricing_client.get_products(
            ServiceCode='AWSFargate',
            Filters=[],
            MaxResults=1
        )

        for product in fargate_response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']

            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    if 'Fargate' in price_dimension['description']:
                        pricing_info['price_per_hour_fargate'] = float(price_dimension['pricePerUnit']['USD'])  # Price per hour for Fargate

        # Get user input for estimation
        ec2_hours_per_day = float(input("Enter the number of hours the EC2 instances will be active per day: "))
        fargate_hours_per_day = float(input("Enter the number of hours the Fargate tasks will be active per day: "))
        days_per_month = 30  # Approximate number of days in a month

        # Calculate estimated monthly cost
        monthly_cost = (
            (ec2_hours_per_day * days_per_month * pricing_info['price_per_hour_ec2']) +
            (fargate_hours_per_day * days_per_month * pricing_info['price_per_hour_fargate'])
        )

        return {
            'monthly_cost': monthly_cost,
            'price_per_hour_ec2': pricing_info['price_per_hour_ec2'],
            'price_per_hour_fargate': pricing_info['price_per_hour_fargate']
        }

    except Exception as e:
        print(f"Error fetching pricing data: {e}")

    return None

def get_eks_pricing():
    """
    Get AWS EKS pricing and estimate monthly cost based on user input.

    Returns:
        dict: A dictionary with the estimated monthly cost or None if not found.
    """
    try:
        # Fetch EKS control plane pricing
        eks_control_plane_response = pricing_client.get_products(
            ServiceCode='AmazonEKS',
            Filters=[],
            MaxResults=1
        )

        pricing_info = {
            'control_plane_price_per_hour': 0,
            'worker_node_price_per_hour': 0
        }

        # Get EKS control plane pricing
        for product in eks_control_plane_response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']

            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    pricing_info['control_plane_price_per_hour'] = float(price_dimension['pricePerUnit']['USD'])  # Price per hour for EKS control plane

        # Fetch EC2 instance pricing for worker nodes
        ec2_response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {
                    'Type': 'TERM_MATCH',
                    'Field': 'productFamily',
                    'Value': 'Compute Instance'
                }
            ],
            MaxResults=1
        )

        # Get EC2 instance pricing
        for product in ec2_response['PriceList']:
            product_data = json.loads(product)
            terms = product_data['terms']['OnDemand']

            for term in terms.values():
                for price_dimension in term['priceDimensions'].values():
                    if 'Linux' in price_dimension['description']:  # Adjust for your instance type
                        pricing_info['worker_node_price_per_hour'] = float(price_dimension['pricePerUnit']['USD'])  # Price per hour for worker nodes

        # Get user input for estimation
        control_plane_hours_per_day = float(input("Enter the number of hours the EKS control plane will be active per day: "))
        worker_node_hours_per_day = float(input("Enter the number of hours the worker nodes will be active per day: "))
        days_per_month = 30  # Approximate number of days in a month

        # Calculate estimated monthly cost
        monthly_cost = (
            (control_plane_hours_per_day * days_per_month * pricing_info['control_plane_price_per_hour']) +
            (worker_node_hours_per_day * days_per_month * pricing_info['worker_node_price_per_hour'])
        )

        return {
            'monthly_cost': monthly_cost,
            'control_plane_price_per_hour': pricing_info['control_plane_price_per_hour'],
            'worker_node_price_per_hour': pricing_info['worker_node_price_per_hour']
        }

    except Exception as e:
        print(f"Error fetching pricing data: {e}")

    return None


# Function to get AWS pricing information
def get_aws_price(service, region, instance_type):
    total_cost = 0

    if service == 'EC2':
        ec2_price = get_ec2_pricing(instance_type)
        if ec2_price is not None:
            total_cost += ec2_price

    elif service == 'S3':
        # Example: if you want to check for a specific storage class
        storage_class = input("Enter the S3 storage class (e.g., Standard, Intelligent-Tiering): ")
        s3_price = get_s3_pricing(storage_class)
        if s3_price is not None:
            total_cost += s3_price

    elif service == 'RDS':
        # Example: get user inputs for RDS
        engine = input("Enter the database engine (e.g., mysql, postgresql): ")
        license_model = input("Enter the license model (e.g., license-included, bring-your-own-license): ")
        rds_price = get_rds_pricing(instance_type, engine, license_model)
        if rds_price is not None:
            total_cost += rds_price

    elif service == 'Lambda':
        lambda_price = get_lambda_pricing()
        if lambda_price is not None:
            total_cost += lambda_price['monthly_cost']

    elif service == 'DynamoDB':
        dynamodb_price = get_dynamodb_pricing()
        if dynamodb_price is not None:
            total_cost += dynamodb_price['monthly_cost']

    elif service == 'VPC':
        vpc_price = get_vpc_pricing()
        if vpc_price is not None:
            total_cost += vpc_price['monthly_cost']

    elif service == 'ECS':
        ecs_price = get_ecs_pricing()
        if ecs_price is not None:
            total_cost += ecs_price['monthly_cost']

    elif service == 'EKS':
        eks_price = get_eks_pricing()
        if eks_price is not None:
            total_cost += eks_price['control_plane_price_per_hour']

    # Add more services as needed

    return total_cost

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
