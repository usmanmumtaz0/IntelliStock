# IntelliStock CV Pipeline

Computer Vision module for detecting, tracking, and ROI-assigning products on retail shelves.

## Architecture

The CV pipeline consists of 4 phases (CV-001 through CV-004):

### Phase 1: Video Ingestion (CV-001)
- **File**: `video_ingestion.py`
- **Class**: `VideoIngestionService`, `FrameSampler`
- Handles video input from:
  - Webcam (index 0, 1, etc.)
  - Video files (MP4, AVI, etc.)
  - RTSP streams
- Configurable frame sampling at target FPS (default 2 FPS)
- Statistics tracking: frames sampled, skipped, actual vs. target FPS

### Phase 2: YOLO Detection (CV-002)
- **File**: `yolo_detector.py`
- **Class**: `YOLODetector`, `Detection`
- Ultralytics YOLOv8 integration
- Configurable model size: n, s, m, l, x
- Confidence threshold filtering (default 0.5)
- CPU or GPU execution
- Bounding box + class + confidence output

### Phase 3: ByteTrack Integration (CV-003)
- **File**: `byte_tracker.py`
- **Class**: `ByteTracker`, `Track`
- Persistent track IDs across frames
- Lightweight tracking without re-ID model
- Configurable min track length (default 3 frames)
- Track buffer for temporary disappearances (default 30 frames)
- IoU-based detection matching

### Phase 4: ROI Assignment (CV-004)
- **File**: `roi_assignment.py`
- **Class**: `ROIAssigner`, `ShelfZone`
- Point-in-polygon detection assignment
- ROI polygons stored as JSON in database
- Center-based detection placement
- Statistics: detections assigned, zones defined

## Full Pipeline

The `CVPipeline` class (`pipeline.py`) orchestrates all 4 phases:

1. **Ingest** frame from video
2. **Detect** objects using YOLO
3. **Track** objects across frames using ByteTrack
4. **Assign** tracks to shelf zones using ROI polygons
5. **Generate** observations for reconciliation engine

Output: `Observation` objects containing:
- zone_id, product_id
- quantity (count of detections in zone)
- confidence (avg detection confidence)
- camera_id, frame_idx, track_ids

## Configuration

Set environment variables in `.env`:

```bash
# Video input
VIDEO_SOURCE=0              # 0 for webcam, or path to file
REPLAY_MODE=false          # Restart video when finished

# YOLO model
YOLO_MODEL=yolov8m.pt     # Model size: n, s, m, l, x
YOLO_CONFIDENCE_THRESHOLD=0.5
YOLO_DEVICE=cpu           # 'cpu' or 'cuda'

# ByteTrack
BYTETRACK_MIN_TRACK_LENGTH=3
BYTETRACK_TRACK_BUFFER=30
BYTETRACK_MATCH_THRESHOLD=0.7

# Frame sampling
CV_FPS=2                   # Target frames per second
```

## Usage

```python
from cv import CVPipeline
import json

# Create pipeline
pipeline = CVPipeline(
    camera_id="camera-001",
    product_class_id=0,     # YOLO class ID (0 for person)
    video_source="0",       # Webcam
    target_fps=2,
)

# Add shelf zones
roi_polygon = json.dumps([[0, 0], [1, 0], [1, 1], [0, 1]])  # Normalized coords
pipeline.add_zone("zone-A", "Shelf A", roi_polygon)

# Start pipeline
pipeline.start()

# Process frames
for _ in range(100):
    success, observations, debug_frame = pipeline.process_frame()
    
    if success and observations:
        for obs in observations:
            print(f"Observation: {obs.zone_id} = {obs.quantity} items (conf={obs.confidence:.2f})")

# Get statistics
stats = pipeline.get_stats()
print(f"Frames processed: {stats['frame_count']}")
print(f"Observations generated: {stats['observations_generated']}")

pipeline.stop()
```

## Testing

Run unit tests:

```bash
cd cv
pip install -r requirements.txt
python -m pytest test_pipeline.py -v
```

Tests cover:
- Frame sampling at target FPS
- Detection creation and serialization
- ByteTrack initialization and tracking
- IoU calculation
- Point-in-polygon algorithms
- ROI assignment
- Observation generation
- Pipeline initialization

## Known Limitations

1. **No re-ID model**: ByteTrack handles occlusion via motion prediction, not appearance. Long occlusions may cause track loss.
2. **Single product class**: Current implementation tracks one YOLO class per pipeline. Multiple products require multiple instances.
3. **Polygon ROI only**: No support for rotated bounding boxes or curved ROIs yet.
4. **No replay/recording**: Live frame capture only; use OpenCV to save frames separately if needed.

## Performance Notes

- **Model size tradeoff**: Larger models (l, x) are more accurate but slower. Start with 'm' for ~15 FPS on CPU.
- **FPS sampling**: 2 FPS default is conservative; adjust CV_FPS up to ~4-5 FPS for better temporal coverage.
- **GPU acceleration**: ~5-10x speedup with CUDA-capable GPU. Set YOLO_DEVICE=0 (for first GPU).

## Next Steps

- **CV-005**: Recorded video replay mode with frame caching
- **Phase 5**: Integration with backend API for observation submission
- **Phase 6**: End-to-end demo with reconciliation + events
