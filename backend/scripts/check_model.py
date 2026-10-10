"""Read-only artifact preflight; does not load weights unless explicitly requested."""
import argparse
import json

from app.cv.model_artifact import verify_artifact, verify_model_metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--load-trusted", action="store_true",
                        help="Deserialize trusted weights and verify embedded task/class labels")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    try:
        manifest = verify_artifact(args.model, args.manifest)
        if args.load_trusted:
            from app.cv.runtime import YOLOTracker
            tracker = YOLOTracker(args.model, args.device)
            verify_model_metadata(manifest, tracker.model)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"model_version": manifest.model_version, "sha256": manifest.sha256,
                      "class_count": len(manifest.classes),
                      "embedded_metadata_verified": args.load_trusted,
                      "accuracy_verified": False}, indent=2))


if __name__ == "__main__":
    main()
