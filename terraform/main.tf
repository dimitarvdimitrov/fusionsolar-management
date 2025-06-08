terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "fusionsolar-vpc"
    Application = "fusionsolar-management"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "fusionsolar-igw"
    Application = "fusionsolar-management"
  }
}

# Public subnet for NAT Gateway
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name        = "fusionsolar-public-subnet"
    Application = "fusionsolar-management"
  }
}

# Private subnet for EC2 instance
resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name        = "fusionsolar-private-subnet"
    Application = "fusionsolar-management"
  }
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name        = "fusionsolar-nat-eip"
    Application = "fusionsolar-management"
  }
}

# NAT Gateway
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id

  tags = {
    Name        = "fusionsolar-nat-gateway"
    Application = "fusionsolar-management"
  }

  depends_on = [aws_internet_gateway.main]
}

# Public route table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "fusionsolar-public-rt"
    Application = "fusionsolar-management"
  }
}

# Private route table
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name        = "fusionsolar-private-rt"
    Application = "fusionsolar-management"
  }
}

# Route table associations
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

# Security Group
resource "aws_security_group" "fusionsolar" {
  name_prefix = "fusionsolar-management-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for FusionSolar Management application"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "fusionsolar-security-group"
    Application = "fusionsolar-management"
  }
}

# IAM Role for EC2 instance
resource "aws_iam_role" "fusionsolar_role" {
  name = "FusionSolarManagementRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "fusionsolar-iam-role"
    Application = "fusionsolar-management"
  }
}

resource "aws_iam_role_policy" "fusionsolar_policy" {
  name = "FusionSolarManagementPolicy"
  role = aws_iam_role.fusionsolar_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach AWS managed policy for Session Manager
resource "aws_iam_role_policy_attachment" "ssm_managed_instance_core" {
  role       = aws_iam_role.fusionsolar_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "fusionsolar_profile" {
  name = "FusionSolarManagementProfile"
  role = aws_iam_role.fusionsolar_role.name
}

# S3 Bucket for data storage
resource "aws_s3_bucket" "fusionsolar_data" {
  bucket = var.s3_bucket_name

  tags = {
    Name        = "fusionsolar-management"
    Application = "fusionsolar-management"
  }
}

resource "aws_s3_bucket_versioning" "fusionsolar_data_versioning" {
  bucket = aws_s3_bucket.fusionsolar_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "fusionsolar_data_encryption" {
  bucket = aws_s3_bucket.fusionsolar_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# EC2 Instance
resource "aws_instance" "fusionsolar" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.fusionsolar.id]
  subnet_id              = aws_subnet.private.id
  iam_instance_profile   = aws_iam_instance_profile.fusionsolar_profile.name

  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    s3_bucket_name = aws_s3_bucket.fusionsolar_data.bucket
    aws_region     = var.aws_region
  }))

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  tags = {
    Name        = "FusionSolar-Management"
    Application = "fusionsolar-management"
    Environment = "production"
  }
}

# Null resource to handle deployment after instance is ready
resource "null_resource" "deploy_app" {
  depends_on = [aws_instance.fusionsolar]

  triggers = {
    instance_id = aws_instance.fusionsolar.id
    # Trigger redeployment when any of these files change
    deploy_script_hash = filemd5("${path.module}/../deploy.sh")
    app_files_hash = join("", [
      for f in fileset("${path.module}/..", "**/*.py") : filemd5("${path.module}/../${f}")
    ])
  }

  provisioner "local-exec" {
    command = "../deploy.sh"
    environment = {
      INSTANCE_ID = aws_instance.fusionsolar.id
      S3_BUCKET   = aws_s3_bucket.fusionsolar_data.bucket
    }
  }
}
