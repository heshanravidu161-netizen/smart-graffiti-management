from pathlib import Path
import argparse

from ultralytics import YOLO


ML_PIPELINE_DIR = Path(__file__).resolve().parents[1]

DATA_YAML = (
    ML_PIPELINE_DIR
    / "data"
    / "17k-graffiti-1"
    / "data.yaml"
)

MODELS_DIR = ML_PIPELINE_DIR / "models"

SIZE_THRESHOLDS = {
    "small": 0.05,
    "medium": 0.20,
}


def bucket_size(area_fraction: float) -> str:
    # Estimate size using the percentage of the image covered.
    if area_fraction < SIZE_THRESHOLDS["small"]:
        return "small"

    if area_fraction < SIZE_THRESHOLDS["medium"]:
        return "medium"

    return "large"


def train(
    epochs: int = 50,
    batch_size: int = 4,
    run_name: str = "graffiti_detector",
):
    # Check that the dataset configuration exists.
    if not DATA_YAML.exists():
        raise FileNotFoundError(
            f"Dataset configuration was not found: {DATA_YAML}"
        )

    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"Dataset: {DATA_YAML}")
    print(f"Epochs: {epochs}")
    print(f"Batch size: {batch_size}")
    print(f"Output: {MODELS_DIR / run_name}")

    # Load the pretrained YOLOv8 Nano model.
    model = YOLO("yolov8n.pt")

    # Fine-tune the model using the graffiti dataset.
    results = model.train(
        data=str(DATA_YAML),
        epochs=epochs,
        imgsz=640,
        batch=batch_size,
        device="mps",
        project=str(MODELS_DIR),
        name=run_name,
        workers=2,
        patience=10,
        seed=42,
        plots=True,
    )

    best_weights = (
        MODELS_DIR
        / run_name
        / "weights"
        / "best.pt"
    )

    print("\nTraining completed.")
    print(f"Best model: {best_weights}")

    return results


def evaluate(weights_path: str):
    # Evaluate the trained model using the untouched test set.
    weights = Path(weights_path)

    if not weights.exists():
        raise FileNotFoundError(
            f"Model weights were not found: {weights}"
        )

    model = YOLO(str(weights))

    metrics = model.val(
        data=str(DATA_YAML),
        split="test",
    )

    print("\nTest results")
    print(f"Precision: {metrics.box.mp:.3f}")
    print(f"Recall: {metrics.box.mr:.3f}")
    print(f"mAP50: {metrics.box.map50:.3f}")
    print(f"mAP50-95: {metrics.box.map:.3f}")

    return metrics


def run_inference(
    weights_path: str,
    image_path: str,
) -> list[dict]:
    # Run graffiti detection on one image.
    weights = Path(weights_path)
    image = Path(image_path)

    if not weights.exists():
        raise FileNotFoundError(
            f"Model weights were not found: {weights}"
        )

    if not image.exists():
        raise FileNotFoundError(
            f"Image was not found: {image}"
        )

    model = YOLO(str(weights))

    results = model.predict(
        source=str(image),
        conf=0.25,
        save=True,
        project=str(MODELS_DIR),
        name="predictions",
        exist_ok=True,
        verbose=False,
    )

    detections = []

    for result in results:
        image_height, image_width = result.orig_shape
        image_area = image_height * image_width

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            box_width = max(0, x2 - x1)
            box_height = max(0, y2 - y1)
            box_area = box_width * box_height

            area_fraction = box_area / image_area

            detection = {
                "class_name": "graffiti",
                "confidence": round(
                    float(box.conf[0]),
                    3,
                ),
                "size_category": bucket_size(
                    area_fraction
                ),
                "area_fraction": round(
                    area_fraction,
                    4,
                ),
                "bbox": {
                    "x1": round(x1, 1),
                    "y1": round(y1, 1),
                    "x2": round(x2, 1),
                    "y2": round(y2, 1),
                },
                "image_width": image_width,
                "image_height": image_height,
            }

            detections.append(detection)

    return detections


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--name",
        default="graffiti_detector",
    )

    arguments = parser.parse_args()

    train(
        epochs=arguments.epochs,
        batch_size=arguments.batch,
        run_name=arguments.name,
    )


if __name__ == "__main__":
    main()
