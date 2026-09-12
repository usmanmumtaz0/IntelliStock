"""
Tests for CV Pipeline (Phases 1-4)
"""
import pytest
import numpy as np
from uuid import uuid4

from video_ingestion import FrameSampler, VideoIngestionService
from yolo_detector import Detection, YOLODetector, draw_detections
from byte_tracker import ByteTracker, Track, calculate_iou
from roi_assignment import point_in_polygon, bbox_center_in_polygon, ROIAssigner, ShelfZone
from pipeline import Observation, CVPipeline


class TestFrameSampler:
    """Test video frame sampler."""
    
    def test_sampler_initialization(self):
        """Test sampler can be initialized."""
        sampler = FrameSampler(target_fps=2)
        assert sampler.target_fps == 2
        assert sampler.frames_sampled == 0
    
    def test_sampler_frame_selection(self):
        """Test sampler correctly selects frames at target FPS."""
        sampler = FrameSampler(target_fps=2)
        
        # 2 FPS = 500ms between frames
        times = [0, 200, 500, 700, 1000, 1200]
        sampled = [sampler.should_sample(t) for t in times]
        
        # Should sample at 0, 500, 1000
        expected = [True, False, True, False, True, False]
        assert sampled == expected
    
    def test_sampler_statistics(self):
        """Test sampler statistics."""
        sampler = FrameSampler(target_fps=2)
        
        for t in [0, 200, 500, 700, 1000]:
            sampler.should_sample(t)
        
        stats = sampler.get_stats()
        assert stats["sampled"] == 3
        assert stats["skipped"] == 2


class TestDetection:
    """Test detection object."""
    
    def test_detection_creation(self):
        """Test detection can be created."""
        det = Detection(
            class_id=0,
            class_name="person",
            confidence=0.95,
            x1=100, y1=150,
            x2=300, y2=400,
        )
        
        assert det.class_id == 0
        assert det.confidence == 0.95
    
    def test_detection_bbox_properties(self):
        """Test detection bbox properties."""
        det = Detection(0, "person", 0.9, 100, 100, 300, 300)
        
        assert det.bbox == (100, 100, 300, 300)
        assert det.center == (200, 200)
        assert det.width == 200
        assert det.height == 200
    
    def test_detection_to_dict(self):
        """Test detection serialization."""
        det = Detection(0, "person", 0.85, 50, 50, 150, 150)
        d = det.to_dict()
        
        assert d["class_name"] == "person"
        assert d["confidence"] == 0.85
        assert d["bbox"] == (50, 50, 150, 150)


class TestByteTracker:
    """Test ByteTrack integration."""
    
    def test_tracker_initialization(self):
        """Test tracker can be initialized."""
        tracker = ByteTracker(min_track_length=2)
        assert tracker.min_track_length == 2
        assert tracker.frame_count == 0
    
    def test_tracker_basic_tracking(self):
        """Test tracker maintains track IDs."""
        tracker = ByteTracker(min_track_length=1)
        
        # Create detections
        det1 = Detection(0, "product", 0.9, 100, 100, 150, 150)
        det2 = Detection(0, "product", 0.85, 120, 120, 170, 170)
        
        confirmed1 = tracker.update([det1], frame_idx=0)
        confirmed2 = tracker.update([det2], frame_idx=1)
        
        assert isinstance(confirmed1, dict)
        assert isinstance(confirmed2, dict)
    
    def test_tracker_statistics(self):
        """Test tracker statistics."""
        tracker = ByteTracker()
        
        det = Detection(0, "product", 0.9, 100, 100, 150, 150)
        tracker.update([det], frame_idx=0)
        
        stats = tracker.get_stats()
        assert stats["frame_count"] == 1
        assert stats["total_detections"] == 1


class TestIOUCalculation:
    """Test IoU calculation."""
    
    def test_iou_full_overlap(self):
        """Test IoU for fully overlapping boxes."""
        box1 = (0, 0, 100, 100)
        box2 = (0, 0, 100, 100)
        
        iou = calculate_iou(box1, box2)
        assert iou == 1.0
    
    def test_iou_no_overlap(self):
        """Test IoU for non-overlapping boxes."""
        box1 = (0, 0, 100, 100)
        box2 = (200, 200, 300, 300)
        
        iou = calculate_iou(box1, box2)
        assert iou == 0.0
    
    def test_iou_partial_overlap(self):
        """Test IoU for partially overlapping boxes."""
        box1 = (0, 0, 100, 100)
        box2 = (50, 50, 150, 150)
        
        iou = calculate_iou(box1, box2)
        # Intersection = 50x50 = 2500
        # Union = 10000 + 10000 - 2500 = 17500
        # IoU = 2500/17500 = 1/7
        assert 0.142 < iou < 0.144


class TestPointInPolygon:
    """Test point-in-polygon algorithm."""
    
    def test_point_inside_square(self):
        """Test point inside square polygon."""
        polygon = [(0, 0), (100, 0), (100, 100), (0, 100)]
        point = (50, 50)
        
        assert point_in_polygon(point, polygon) == True
    
    def test_point_outside_square(self):
        """Test point outside square polygon."""
        polygon = [(0, 0), (100, 0), (100, 100), (0, 100)]
        point = (150, 150)
        
        assert point_in_polygon(point, polygon) == False
    
    def test_point_on_edge(self):
        """Test point on polygon edge."""
        polygon = [(0, 0), (100, 0), (100, 100), (0, 100)]
        point = (50, 0)  # On edge
        
        # Edge cases vary by implementation, just verify it runs
        result = point_in_polygon(point, polygon)
        assert isinstance(result, bool)


class TestROIAssigner:
    """Test ROI assignment."""
    
    def test_roi_assigner_initialization(self):
        """Test ROI assigner can be initialized."""
        assigner = ROIAssigner()
        assert len(assigner.zones) == 0
    
    def test_add_zone(self):
        """Test adding a zone."""
        assigner = ROIAssigner()
        roi_json = '[[0, 0], [100, 0], [100, 100], [0, 100]]'
        
        assigner.add_zone("zone-1", "Shelf A", roi_json)
        
        assert len(assigner.zones) == 1
        assert "zone-1" in assigner.zones
    
    def test_assignment_inside_zone(self):
        """Test detection inside zone is assigned."""
        assigner = ROIAssigner()
        roi_json = '[[0, 0], [100, 0], [100, 100], [0, 100]]'
        assigner.add_zone("zone-1", "Shelf A", roi_json)
        
        det = Detection(0, "product", 0.9, 25, 25, 75, 75)  # Center at (50, 50)
        zone_id = assigner.assign_detection(det)
        
        assert zone_id == "zone-1"
    
    def test_assignment_outside_zone(self):
        """Test detection outside zone is not assigned."""
        assigner = ROIAssigner()
        roi_json = '[[0, 0], [100, 0], [100, 100], [0, 100]]'
        assigner.add_zone("zone-1", "Shelf A", roi_json)
        
        det = Detection(0, "product", 0.9, 150, 150, 200, 200)  # Center at (175, 175)
        zone_id = assigner.assign_detection(det)
        
        assert zone_id is None


class TestObservation:
    """Test observation object."""
    
    def test_observation_creation(self):
        """Test observation can be created."""
        obs = Observation(
            zone_id="zone-1",
            product_id="prod-1",
            quantity=3,
            confidence=0.85,
            camera_id="cam-1",
            frame_idx=42,
            track_ids=[1, 2, 3],
        )
        
        assert obs.quantity == 3
        assert obs.confidence == 0.85
    
    def test_observation_to_dict(self):
        """Test observation serialization."""
        obs = Observation("z1", "p1", 5, 0.9, "c1", 100, [1, 2, 3])
        d = obs.to_dict()
        
        assert d["quantity"] == 5
        assert d["confidence"] == 0.9
        assert d["track_ids"] == [1, 2, 3]


class TestCVPipeline:
    """Test full CV pipeline (integration tests)."""
    
    def test_pipeline_initialization(self):
        """Test pipeline can be initialized."""
        pipeline = CVPipeline(
            camera_id=str(uuid4()),
            product_class_id=0,
            target_fps=2,
        )
        
        assert pipeline.camera_id is not None
        assert pipeline.product_class_id == 0
        assert pipeline.is_running == False
    
    def test_pipeline_add_zone(self):
        """Test adding zone to pipeline."""
        pipeline = CVPipeline(camera_id=str(uuid4()))
        roi_json = '[[0, 0], [100, 0], [100, 100], [0, 100]]'
        
        pipeline.add_zone("zone-1", "Shelf A", roi_json)
        
        stats = pipeline.get_stats()
        assert "roi_assigner" in stats
        assert stats["roi_assigner"]["zones_defined"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
