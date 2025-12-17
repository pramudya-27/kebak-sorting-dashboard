# API Documentation

## Base URL
```
http://<wsl-server-ip>:8000
```

## Endpoints

### Health Check

#### GET /health
Check if the API server is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-16T10:30:00"
}
```

---

### Root

#### GET /
Get API information.

**Response:**
```json
{
  "service": "YOLO Detection API",
  "version": "1.0.0",
  "status": "running"
}
```

---

### Latest Detection

#### GET /api/v1/detections/latest
Get the most recent detection result.

**Response:**
```json
{
  "frame_id": 12345,
  "timestamp": "2025-12-16T10:30:00.123456",
  "fused_detections": [
    {
      "bbox": [100.5, 150.2, 300.7, 400.9],
      "confidence": 0.87,
      "class_id": 0,
      "class_name": "person",
      "num_models": 3,
      "models": ["yolov8n", "yolov8s", "yolov8m"],
      "original_confidences": [0.85, 0.88, 0.89]
    }
  ],
  "num_detections": 1,
  "inference_time": 0.045,
  "fusion_time": 0.002,
  "total_time": 0.047,
  "models": 3
}
```

**Error Response (404):**
```json
{
  "detail": "No detections available"
}
```

---

### Detection History

#### GET /api/v1/detections/history
Get historical detection results.

**Query Parameters:**
- `limit` (optional, default: 50): Maximum number of results to return

**Example:**
```
GET /api/v1/detections/history?limit=10
```

**Response:**
```json
{
  "count": 10,
  "history": [
    {
      "frame_id": 12345,
      "timestamp": "2025-12-16T10:30:00",
      "fused_detections": [...],
      "num_detections": 2,
      "inference_time": 0.045
    },
    ...
  ]
}
```

---

### System Statistics

#### GET /api/v1/stats
Get comprehensive system statistics.

**Response:**
```json
{
  "detection": {
    "total_detections": 5432,
    "uptime_seconds": 3600.5,
    "fps": 15.2,
    "history_size": 100,
    "subscribers": 2
  },
  "system": {
    "frames_processed": 5432,
    "uptime": 3600.5,
    "receiver": {
      "packets_received": 54320,
      "bytes_received": 1234567890,
      "frames_received": 5432,
      "frames_dropped": 10
    },
    "inference": {
      "total_frames": 5432,
      "avg_inference_time_ms": 45.2,
      "device": "cuda:0"
    },
    "fusion": {
      "total_fusions": 5432,
      "avg_input_detections": 8.5,
      "avg_output_detections": 3.2,
      "reduction_percent": 62.4
    },
    "models": [
      {
        "model_name": "yolov8n",
        "total_inferences": 5432,
        "avg_inference_time_ms": 18.5,
        "avg_detections": 2.8,
        "total_detections": 15200
      },
      ...
    ]
  }
}
```

---

### Detection Statistics Only

#### GET /api/v1/stats/detections
Get only detection-related statistics.

**Response:**
```json
{
  "total_detections": 5432,
  "uptime_seconds": 3600.5,
  "fps": 15.2,
  "history_size": 100,
  "subscribers": 2
}
```

---

### Update Configuration

#### POST /api/v1/config
Update system configuration (placeholder for future implementation).

**Request Body:**
```json
{
  "inference": {
    "confidence_threshold": 0.35
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Configuration update received"
}
```

---

## WebSocket API

### Real-time Detection Stream

#### WS /ws/detections
WebSocket endpoint for receiving real-time detection updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/detections');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const detection = JSON.parse(event.data);
  console.log('New detection:', detection);
};

// Send keepalive
setInterval(() => {
  ws.send('ping');
}, 20000);
```

**Message Types:**

1. **Detection Update:**
```json
{
  "frame_id": 12345,
  "timestamp": "2025-12-16T10:30:00",
  "fused_detections": [...],
  "num_detections": 2
}
```

2. **Keepalive:**
```json
{
  "type": "keepalive"
}
```

---

## Dashboard

### Web Dashboard

#### GET /dashboard
Access the real-time detection visualization dashboard.

**URL:**
```
http://localhost:8000/dashboard
```

**Features:**
- Real-time video feeds with detection overlays
- Live detection statistics
- System performance metrics
- Model performance breakdown
- Detection history timeline

---

## Data Models

### Detection Object
```typescript
{
  bbox: [number, number, number, number],  // [x1, y1, x2, y2]
  confidence: number,                       // 0.0 to 1.0
  class_id: number,
  class_name: string,
  num_models?: number,                      // Number of models that detected this
  models?: string[],                        // Models that detected this
  original_confidences?: number[]           // Confidence from each model
}
```

### Detection Result
```typescript
{
  frame_id: number,
  timestamp: string,                        // ISO 8601 format
  fused_detections: Detection[],
  num_detections: number,
  inference_time: number,                   // seconds
  fusion_time?: number,                     // seconds
  total_time: number,                       // seconds
  models: number                            // number of models used
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

Currently no rate limiting is implemented. For production use, consider implementing rate limiting based on your requirements.

---

## CORS

CORS is enabled for all origins by default. Configure in `wsl/config.yml`:

```yaml
api:
  cors_origins:
    - "http://localhost:3000"
    - "https://yourdomain.com"
```

---

## Example Usage

### Python
```python
import requests

# Get latest detection
response = requests.get('http://localhost:8000/api/v1/detections/latest')
detection = response.json()
print(f"Detected {detection['num_detections']} objects")

# Get statistics
response = requests.get('http://localhost:8000/api/v1/stats')
stats = response.json()
print(f"FPS: {stats['detection']['fps']:.2f}")
```

### JavaScript
```javascript
// Fetch latest detection
fetch('http://localhost:8000/api/v1/detections/latest')
  .then(res => res.json())
  .then(data => {
    console.log(`Detected ${data.num_detections} objects`);
  });

// WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws/detections');
ws.onmessage = (event) => {
  const detection = JSON.parse(event.data);
  updateUI(detection);
};
```

### cURL
```bash
# Health check
curl http://localhost:8000/health

# Get statistics
curl http://localhost:8000/api/v1/stats | jq

# Get latest detection
curl http://localhost:8000/api/v1/detections/latest | jq
```
