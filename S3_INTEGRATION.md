# S3 Integration for YOLO Service

This document describes the AWS S3 integration that has been added to the YOLO Object Detection Service.

## Overview

The service has been refactored to use AWS S3 for image storage instead of local file storage. This provides several benefits:

- **Scalability**: Images are stored in the cloud and can be accessed from anywhere
- **Durability**: S3 provides 99.999999999% (11 9's) durability
- **Cost-effective**: Pay only for what you use
- **Performance**: Fast access to images via CDN

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# AWS S3 Configuration
AWS_REGION=us-west-1
BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# Database Configuration (optional)
DB_BACKEND=sqlite
DATABASE_URL=sqlite:///./predictions.db
```

### AWS Setup

1. **Create an S3 Bucket**:
   - Go to AWS S3 Console
   - Create a new bucket with a unique name
   - Choose your preferred region
   - Set appropriate permissions

2. **Create IAM User**:
   - Go to AWS IAM Console
   - Create a new user with programmatic access
   - Attach a policy with S3 permissions:
     ```json
     {
         "Version": "2012-10-17",
         "Statement": [
             {
                 "Effect": "Allow",
                 "Action": [
                     "s3:GetObject",
                     "s3:PutObject",
                     "s3:DeleteObject"
                 ],
                 "Resource": "arn:aws:s3:::your-bucket-name/*"
             }
         ]
     }
     ```

3. **Get Credentials**:
   - Save the Access Key ID and Secret Access Key
   - Add them to your `.env` file

## API Changes

### Updated Endpoints

#### POST /predict
- **Input**: File upload (same as before)
- **Output**: Enhanced response with S3 URLs
```json
{
    "prediction_uid": "uuid",
    "detection_count": 15,
    "labels": ["person", "car", "dog"],
    "time_took": 2.34,
    "original_image_url": "https://bucket.s3.region.amazonaws.com/original/uuid.jpg",
    "predicted_image_url": "https://bucket.s3.region.amazonaws.com/predicted/uuid.jpg"
}
```

#### GET /prediction/{uid}
- **Output**: Same as before, but `original_image` and `predicted_image` fields now contain S3 URLs

#### GET /prediction/{uid}/image
- **Behavior**: Downloads image from S3 and serves it directly
- **Content-Type**: Automatically determined based on Accept header

#### DELETE /prediction/{uid}
- **Behavior**: Deletes both database records and S3 objects

### New S3 Utility Functions

The `utils/s3_utils.py` module provides:

- `upload_image_to_s3()`: Upload image data to S3
- `download_image_from_s3()`: Download image from S3 URL
- `delete_file_from_s3()`: Delete file from S3
- `upload_file_to_s3()`: Generic file upload to S3
- `download_file_from_s3()`: Generic file download from S3

## File Structure in S3

```
your-bucket/
├── original/
│   ├── uuid1.jpg
│   ├── uuid2.png
│   └── ...
└── predicted/
    ├── uuid1.jpg
    ├── uuid2.png
    └── ...
```

## Database Changes

The database schema remains the same, but the `original_image` and `predicted_image` fields in the `PredictionSession` table now store S3 URLs instead of local file paths.

## Migration from Local Storage

If you have existing data with local file paths, you'll need to:

1. Upload existing images to S3
2. Update database records with S3 URLs
3. Remove local files

## Error Handling

The S3 integration includes comprehensive error handling:

- **Upload failures**: Returns HTTP 500 with descriptive error message
- **Download failures**: Returns HTTP 500 with descriptive error message
- **Missing files**: Returns HTTP 404
- **Invalid credentials**: Returns HTTP 500 with authentication error

## Performance Considerations

- **Temporary files**: Images are temporarily stored locally during YOLO processing, then cleaned up
- **Memory usage**: Images are processed in memory to minimize disk I/O
- **S3 costs**: Consider S3 storage classes and lifecycle policies for cost optimization

## Testing

The existing test suite should work with minimal changes. Update any tests that expect local file paths to expect S3 URLs instead.

## Security

- **Credentials**: Store AWS credentials securely (use IAM roles in production)
- **Bucket permissions**: Use least-privilege access
- **HTTPS**: All S3 URLs use HTTPS for secure transmission

## Troubleshooting

### Common Issues

1. **"Failed to upload file to S3"**
   - Check AWS credentials
   - Verify bucket name and region
   - Ensure IAM permissions are correct

2. **"Failed to download file from S3"**
   - Check if file exists in S3
   - Verify S3 URL format
   - Check network connectivity

3. **"Client does not accept an image format"**
   - Add appropriate Accept header: `Accept: image/jpeg` or `Accept: image/png`

### Debug Mode

Set environment variable `DEBUG=1` for detailed error messages in development.
