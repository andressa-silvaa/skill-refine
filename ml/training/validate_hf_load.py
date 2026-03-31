from __future__ import annotations

from pathlib import Path

from transformers import AutoModelForSequenceClassification, AutoTokenizer


def main() -> None:
    model_dir = Path("c:/Skill-Refine-TCC/ml/models/analysis_v1_pt/hf")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    print(type(model).__name__)
    print(tokenizer.__class__.__name__)
    print(model.config.model_type)
    print(model.config.num_labels)


if __name__ == "__main__":
    main()
