#!/bin/sh
pip install -q torch transformers pyyaml scikit-learn
cd ml/training && python train.py --task seniority --language pt-BR --base_model neuralmind/bert-base-portuguese-cased --model_version analysis_v1_pt --epochs 1
