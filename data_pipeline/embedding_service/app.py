import hashlib
import json
import os
import threading

from contextlib import asynccontextmanager
from typing import Literal

import numpy as np
import torch

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer


PROFILE = {
    "model_name": "intfloat/multilingual-e5-small",
    "model_revision": "614241f622f53c4eeff9890bdc4f31cfecc418b3",
    "dimension": 384,
    "max_tokens": 512,
    "normalize": True,
    "query_prefix": "query: ",
    "passage_prefix": "passage: ",
    "encoder_version": "e5-cpu-v1",
}

PROFILE_ID = hashlib.sha256(
    json.dumps(PROFILE, sort_keys=True).encode()
).hexdigest()

LOCK = threading.Lock()


@asynccontextmanager
async def lifespan(app):
    torch.set_num_threads(
        int(os.getenv("TORCH_NUM_THREADS", "2"))
    )

    print(
        "Loading multilingual-e5-small on CPU...",
        flush=True,
    )

    app.state.model = SentenceTransformer(
        PROFILE["model_name"],
        revision=PROFILE["model_revision"],
        device="cpu",
        cache_folder="/models",
        trust_remote_code=False,
    )

    app.state.model.max_seq_length = PROFILE["max_tokens"]

    if (
        app.state.model.get_sentence_embedding_dimension()
        != PROFILE["dimension"]
    ):
        raise RuntimeError("Model dimension mismatch")

    print(
        "Embedding model ready | dimension=384",
        flush=True,
    )

    yield


app = FastAPI(
    title="AISC Embedding API",
    lifespan=lifespan,
)


class EmbedRequest(BaseModel):
    texts: list[str] = Field(
        min_length=1,
        max_length=32,
    )
    kind: Literal["query", "passage"] = "passage"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "profile_id": PROFILE_ID,
        **PROFILE,
    }


@app.post("/embed")
def embed(request: EmbedRequest):
    if any(
        not text.strip() or len(text) > 10000
        for text in request.texts
    ):
        raise HTTPException(
            422,
            "Text must contain 1-10000 characters",
        )

    prefix = PROFILE[request.kind + "_prefix"]

    inputs = [
        prefix + text.strip()
        for text in request.texts
    ]

    with LOCK:
        tokens = app.state.model.tokenizer(
            inputs,
            truncation=False,
        )

        lengths = [
            len(ids) for ids in tokens["input_ids"]
        ]

        if max(lengths) > PROFILE["max_tokens"]:
            raise HTTPException(
                422,
                "Input exceeds 512 tokens; "
                "split into smaller chunks",
            )

        vectors = app.state.model.encode(
            inputs,
            batch_size=8,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    if (
        vectors.shape
        != (len(inputs), PROFILE["dimension"])
        or not np.isfinite(vectors).all()
    ):
        raise HTTPException(
            500,
            "Invalid embedding output",
        )

    return {
        "profile_id": PROFILE_ID,
        "dimension": PROFILE["dimension"],
        "vectors": vectors.tolist(),
    }