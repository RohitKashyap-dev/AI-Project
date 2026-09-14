from pathlib import Path

import pandas as pd

from scam_detector.classifier import classify_message
from scam_detector.config import (
    DEFAULT_DATASET_PATH,
    DEFAULT_DRY_PREDICTIONS_PATH,
    DEFAULT_PREDICTIONS_PATH,
    MAX_EVAL_EXAMPLES,
)
from scam_detector.logging_config import get_logger
from scam_detector.schemas import SCAM_TYPES
from scam_detector.utils import normalize_label

logger = get_logger(__name__)


def evaluate_dataset(
    dataset_path: str | Path | None = None,
    dry: int = 0,
    out_path: str | Path | None = None,
    confidence_threshold: float = 0.0,
    treat_low_as_unknown: bool = False,
    max_examples: int = MAX_EVAL_EXAMPLES,
    force: bool = False,
):
    dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
    logger.info("Starting dataset evaluation from: %s", dataset_path)
    logger.info("Parameters: dry=%s, max_examples=%s, force=%s", dry, max_examples, force)

    df_full = pd.read_csv(dataset_path)
    logger.info("Loaded dataset with %s rows", len(df_full))

    if not force and len(df_full) > max_examples and dry == 0:
        error_msg = (
            f"Dataset has {len(df_full)} rows which exceeds safety cap of {max_examples}. "
            "Use --dry N, --max-examples, or --force to proceed."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    df = df_full.head(dry) if dry and dry > 0 else df_full
    if dry and dry > 0:
        logger.info("Evaluating first %s rows (dry run)", len(df))

    results = []
    for _, row in df.iterrows():
        msg = str(row["message_text"])
        gold = row.get("label")
        pred = classify_message(msg)

        predicted_is_scam = "Unknown"
        predicted_type = "Other"
        confidence = 0.0
        reply = ""
        indicators = []
        recommended_action = ""

        if pred:
            predicted_is_scam = getattr(pred, "is_scam", "Unknown")
            predicted_type = getattr(pred, "scam_type", "Other") or "Other"
            confidence = float(getattr(pred, "confidence", 0.0) or 0.0)
            reply = getattr(pred, "reply", "")
            indicators = getattr(pred, "indicators", []) or []
            recommended_action = getattr(pred, "recommended_action", "") or ""

        predicted_type_normalized = predicted_type if predicted_type in SCAM_TYPES else "Other"
        low_confidence = confidence < float(confidence_threshold or 0.0)
        if low_confidence and treat_low_as_unknown:
            predicted_is_scam = "Unknown"
            predicted_type_normalized = "Other"

        results.append(
            {
                "message_text": msg,
                "label": gold,
                "predicted_is_scam": predicted_is_scam,
                "predicted_type": predicted_type,
                "predicted_type_normalized": predicted_type_normalized,
                "confidence": confidence,
                "low_confidence": low_confidence,
                "reply": reply,
                "indicators": indicators,
                "recommended_action": recommended_action,
            }
        )

    out_df = pd.DataFrame(results)
    if out_path is None:
        out_path = DEFAULT_PREDICTIONS_PATH if not dry else DEFAULT_DRY_PREDICTIONS_PATH
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)

    try:
        from sklearn.metrics import (
            accuracy_score,
            classification_report,
            confusion_matrix,
            precision_recall_fscore_support,
        )

        y_true = df["label"].map(lambda x: 1 if x == "Scam" else 0).tolist()
        y_pred = out_df["predicted_is_scam"].map(lambda x: 1 if x == "Scam" else 0).tolist()
        acc = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="binary", zero_division=0
        )
        cm = confusion_matrix(y_true, y_pred)
        print("Evaluation results:")
        print(f"Accuracy: {acc:.4f}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall: {recall:.4f}")
        print(f"F1: {f1:.4f}")
        print("Confusion matrix (rows=true [Not Scam,Scam], cols=predicted [Not Scam,Scam]):")
        print(cm)

        gt_type_col = None
        if "intent_type" in df.columns:
            gt_type_col = "intent_type"
        elif "scam_type" in df.columns:
            gt_type_col = "scam_type"

        if gt_type_col is not None:
            # Normalize ground-truth and predicted type labels using shared util
            y_true_type = df[gt_type_col].fillna("Other").astype(str).apply(normalize_label).tolist()
            y_pred_type = out_df["predicted_type_normalized"].fillna("Other").astype(str).apply(normalize_label).tolist()
            print(f"\nScam-type classification report (ground-truth from '{gt_type_col}'):")
            try:
                print(classification_report(y_true_type, y_pred_type, labels=SCAM_TYPES, zero_division=0))
            except Exception:
                print(classification_report(y_true_type, y_pred_type, zero_division=0))
    except Exception:
        print(f"Wrote predictions to {out_path}. Skipping metrics (scikit-learn not installed).")
