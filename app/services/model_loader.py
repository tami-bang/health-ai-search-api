# model_loader.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from datasets import load_dataset  # Hugging Face 공개 데이터셋 로드
from sklearn.feature_extraction.text import TfidfVectorizer  # 텍스트를 TF-IDF 벡터로 변환
from sklearn.linear_model import LogisticRegression  # 간단한 텍스트 분류 모델

_vectorizer: TfidfVectorizer | None = None
_model: LogisticRegression | None = None


def train_model() -> None:
    global _vectorizer, _model

    print("[MODEL] loading dataset...")
    dataset = load_dataset("gretelai/symptom_to_diagnosis")

    print(f"[MODEL] splits: {list(dataset.keys())}")
    print(f"[MODEL] train columns: {dataset['train'].column_names}")

    texts = [str(row["input_text"]).strip() for row in dataset["train"] if row.get("input_text")]
    labels = [str(row["output_text"]).strip() for row in dataset["train"] if row.get("output_text")]

    print(f"[MODEL] train rows: {len(texts)}")

    if not texts or not labels:
        raise RuntimeError("Training dataset is empty.")

    print("[MODEL] vectorizing...")
    _vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_features=20000,
    )
    x_train = _vectorizer.fit_transform(texts)

    print("[MODEL] training...")
    _model = LogisticRegression(
        max_iter=1000,
        random_state=42,
    )
    _model.fit(x_train, labels)

    print("[MODEL] training complete")


def predict(text: str) -> str:
    global _vectorizer, _model

    cleaned = str(text).strip() if text is not None else ""
    if not cleaned:
        return ""

    if _vectorizer is None or _model is None:
        raise RuntimeError("Model is not trained yet.")

    x_input = _vectorizer.transform([cleaned])
    prediction = _model.predict(x_input)[0]
    return str(prediction)


def predict_with_confidence(text: str) -> tuple[str | None, float]:
    global _vectorizer, _model

    cleaned = str(text).strip() if text is not None else ""
    if not cleaned:
        return None, 0.0

    if _vectorizer is None or _model is None:
        raise RuntimeError("Model is not trained yet.")

    x_input = _vectorizer.transform([cleaned])

    try:
        probabilities = _model.predict_proba(x_input)[0]
        best_index = int(probabilities.argmax())
        best_label = str(_model.classes_[best_index])
        best_score = float(probabilities[best_index])
        return best_label, round(best_score, 4)
    except Exception:
        predicted = _model.predict(x_input)[0]
        return str(predicted), 0.0