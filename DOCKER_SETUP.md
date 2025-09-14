# Docker Setup for YOLO Service

This guide explains how to build and run the YOLO Object Detection Service using Docker.

## 🐳 Docker Image

The service has been containerized with the following features:
- **Base Image**: Python 3.12.11-slim
- **Size**: ~2.14GB (includes PyTorch and YOLO dependencies)
- **Security**: Runs as non-root user
- **Health Check**: Built-in health monitoring
- **S3 Integration**: Full AWS S3 support

## 📋 Prerequisites

1. **Docker**: Install Docker Desktop or Docker Engine
2. **AWS Credentials**: Set up your AWS S3 credentials
3. **S3 Bucket**: Create an S3 bucket for image storage

## 🚀 Quick Start

### 1. Build the Docker Image

```bash
# Build the image
docker build -t yolo-service:1.0.0 .

# Or build with a different tag
docker build -t your-registry/yolo-service:latest .
```

### 2. Run with Docker Compose (Recommended)

Create a `.env` file with your AWS credentials:

```env
# AWS S3 Configuration
AWS_REGION=us-west-1
BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# Optional: Debug mode
DEBUG=0
```

Run with docker-compose:

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### 3. Run with Docker Run

```bash
# Run the container
docker run -d \
  --name yolo-service \
  -p 8080:8080 \
  -e AWS_REGION=us-west-1 \
  -e BUCKET_NAME=your-bucket-name \
  -e AWS_ACCESS_KEY_ID=your_access_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret_key \
  yolo-service:1.0.0

# Check logs
docker logs yolo-service

# Stop the container
docker stop yolo-service
docker rm yolo-service
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AWS_REGION` | AWS region for S3 | us-west-1 | Yes |
| `BUCKET_NAME` | S3 bucket name | - | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key | - | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - | Yes |
| `DB_BACKEND` | Database backend | sqlite | No |
| `DATABASE_URL` | Database connection string | sqlite:///./predictions.db | No |
| `DEBUG` | Debug mode | 0 | No |

### Volume Mounts

The service uses the following volumes:

- `./predictions.db:/app/predictions.db` - Database persistence
- `./uploads:/app/uploads` - Temporary file storage

## 🧪 Testing the Service

### 1. Health Check

```bash
# Check if service is running
curl http://localhost:8080/health

# Expected response: {"status":"ok"}
```

### 2. Upload and Predict

```bash
# Upload an image for prediction
curl -X POST \
  -F "file=@your-image.jpg" \
  http://localhost:8080/predict

# Expected response:
# {
#   "prediction_uid": "uuid",
#   "detection_count": 15,
#   "labels": ["person", "car", "dog"],
#   "time_took": 2.34,
#   "original_image_url": "https://bucket.s3.region.amazonaws.com/original/uuid.jpg",
#   "predicted_image_url": "https://bucket.s3.region.amazonaws.com/predicted/uuid.jpg"
# }
```

### 3. Get Prediction Details

```bash
# Get prediction details
curl http://localhost:8080/prediction/{uid}

# Get predicted image
curl http://localhost:8080/prediction/{uid}/image
```

## 📊 Monitoring

### Health Check

The container includes a built-in health check:

```bash
# Check container health
docker ps

# View health check logs
docker inspect yolo-service | grep -A 10 Health
```

### Logs

```bash
# View real-time logs
docker logs -f yolo-service

# View last 100 lines
docker logs --tail 100 yolo-service
```

## 🔒 Security Considerations

1. **Non-root User**: Container runs as `app` user (not root)
2. **Minimal Dependencies**: Only necessary packages installed
3. **Environment Variables**: Sensitive data passed via environment variables
4. **Network**: Service only exposes port 8080

## 🚀 Production Deployment

### 1. Use Docker Secrets

```bash
# Create secrets
echo "your-access-key" | docker secret create aws_access_key -
echo "your-secret-key" | docker secret create aws_secret_key -

# Run with secrets
docker service create \
  --name yolo-service \
  --secret aws_access_key \
  --secret aws_secret_key \
  -e AWS_ACCESS_KEY_ID_FILE=/run/secrets/aws_access_key \
  -e AWS_SECRET_ACCESS_KEY_FILE=/run/secrets/aws_secret_key \
  -p 8080:8080 \
  yolo-service:1.0.0
```

### 2. Use IAM Roles (AWS ECS/EKS)

```yaml
# task-definition.json
{
  "taskRoleArn": "arn:aws:iam::account:role/yolo-service-role",
  "executionRoleArn": "arn:aws:iam::account:role/yolo-service-execution-role"
}
```

### 3. Resource Limits

```yaml
# docker-compose.yml
services:
  yolo-service:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
```

## 🐛 Troubleshooting

### Common Issues

1. **"Failed to upload file to S3"**
   - Check AWS credentials
   - Verify bucket name and region
   - Ensure IAM permissions are correct

2. **"Container keeps restarting"**
   - Check logs: `docker logs yolo-service`
   - Verify environment variables
   - Check health check configuration

3. **"Out of memory"**
   - Increase memory limits
   - Use smaller images for processing
   - Consider using GPU-enabled containers

### Debug Mode

```bash
# Run with debug mode
docker run -e DEBUG=1 yolo-service:1.0.0

# Or with docker-compose
DEBUG=1 docker-compose up
```

## 📈 Performance Optimization

1. **Multi-stage Build**: Consider using multi-stage builds to reduce image size
2. **Layer Caching**: Optimize Dockerfile layer ordering
3. **Resource Limits**: Set appropriate CPU/memory limits
4. **S3 Transfer**: Use S3 Transfer Acceleration for faster uploads

## 🔄 Updates and Maintenance

### Updating the Image

```bash
# Pull latest changes
git pull

# Rebuild image
docker build -t yolo-service:1.0.1 .

# Update running container
docker-compose down
docker-compose up -d
```

### Backup Database

```bash
# Backup database
docker cp yolo-service:/app/predictions.db ./backup-predictions.db

# Restore database
docker cp ./backup-predictions.db yolo-service:/app/predictions.db
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)

