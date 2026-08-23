"""
Model training script — fine-tunes a YOLOv8 object detector on your labelled
graffiti dataset.

Run prepare_data.py first so ml_pipeline/data/processed/data.yaml exists.

TODO (team):
  - Experiment with model size (yolov8n/s/m) depending on your compute budget.
  - Tune epochs/batch size based on dataset size and available GPU (Colab free
    tier, university HPC, etc.).
  - Track precision/recall/mAP — your proposal's NFR2 sets a 70% precision
    target; log these metrics so you can report them properly in your
    deliverables.
"""

from ultralytics import YOLO

DATA_YAML = "ml_pipeline/data/processed/data.yaml"
OUTPUT_MODEL_DIR = "ml_pipeline/models"


def train():
    # Start from a pretrained checkpoint (transfer learning) rather than
    # training from scratch — much faster convergence on a small dataset.
    model = YOLO("yolov8n.pt")

    results = model.train(
        data=DATA_YAML,
        epochs=50,
        imgsz=640,
        batch=16,
        project=OUTPUT_MODEL_DIR,
        name="graffiti_detector",
    )

    print("Training complete. Best weights saved under:")
    print(f"  {OUTPUT_MODEL_DIR}/graffiti_detector/weights/best.pt")
    return results


def evaluate(weights_path: str):
    """Run validation metrics on a trained model."""
    model = YOLO(weights_path)
    metrics = model.val(data=DATA_YAML)
    print(f"Precision: {metrics.box.mp:.3f}")
    print(f"Recall: {metrics.box.mr:.3f}")
    print(f"mAP50: {metrics.box.map50:.3f}")
    return metrics


if __name__ == "__main__":
    train()
