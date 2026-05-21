# model_wrapper.py

import torch.nn as nn
from causal_discovery import STACD

class FastModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.stacd = STACD(text_emb_dim=768)

        self.cls = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 2)
        )

    def forward(self, text_emb, event_types, timestamps):
        event_reprs, causal_info = self.stacd(
            text_emb, event_types, timestamps
        )

        final = event_reprs[:, -1, :]
        logits = self.cls(final)

        return logits, causal_info