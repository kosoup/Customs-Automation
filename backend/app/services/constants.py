"""여러 서비스 모듈에서 공유하는 상수."""

INCOTERMS_VALID = frozenset({
    "EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP",
})
