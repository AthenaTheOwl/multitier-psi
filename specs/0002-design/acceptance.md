# spec 0002 design acceptance

the implementation is accepted when these commands pass:

```bash
python -m mtpsi validate
uv run pytest
python scripts/voice_lint.py
python scripts/validate_schemas.py
python eval/determinism.py
python eval/leakage_bound.py
```

the fixture intersection size is 1.
