from __future__ import annotations


def ensure_padding_token(tokenizer, model=None):
    """Ensure tokenizer/model have a valid pad token for fixed-length batching."""
    if getattr(tokenizer, "pad_token", None):
        if model is not None and getattr(model.config, "pad_token_id", None) is None:
            model.config.pad_token_id = tokenizer.pad_token_id
        return tokenizer, model

    fallback_token = (
        getattr(tokenizer, "sep_token", None)
        or getattr(tokenizer, "eos_token", None)
        or getattr(tokenizer, "unk_token", None)
    )
    if fallback_token:
        tokenizer.pad_token = fallback_token
    else:
        tokenizer.add_special_tokens({"pad_token": "[PAD]"})
        if model is not None:
            model.resize_token_embeddings(len(tokenizer))

    if model is not None:
        model.config.pad_token_id = tokenizer.pad_token_id
    return tokenizer, model
