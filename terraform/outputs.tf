output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.fusionsolar.id
}

output "nat_gateway_public_ip" {
  description = "Public IP address of the NAT Gateway (for outbound traffic)"
  value       = aws_eip.nat.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.fusionsolar.private_ip
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.fusionsolar_data.bucket
}

output "session_manager_command" {
  description = "AWS Session Manager command to connect to the instance"
  value       = "aws ssm start-session --target ${aws_instance.fusionsolar.id}"
}

output "application_logs" {
  description = "Location of application logs on the instance"
  value = [
    "/var/log/cloud-init-output.log",
    "/var/log/fusionsolar-setup.log",
    "/opt/fusionsolar-management/logs/"
  ]
}