PY ?= .venv/bin/python
SCALE ?= starter
SEED ?= 20261022

.PHONY: all generate detect plan validate evaluate reproduce docs test clean

all:        ; $(PY) -m oryva all --scale $(SCALE) --seed $(SEED)
generate:   ; $(PY) -m oryva generate --scale $(SCALE) --seed $(SEED)
detect:     ; $(PY) -m oryva detect --scale $(SCALE)
plan:       ; $(PY) -m oryva plan --scale $(SCALE)
validate:   ; $(PY) -m oryva validate --scale $(SCALE)
evaluate:   ; $(PY) -m oryva evaluate --scale $(SCALE) --seed $(SEED)
reproduce:  ; $(PY) -m oryva reproduce --scale $(SCALE) --seed $(SEED)
docs:       ; $(PY) -m oryva docs
test:       ; $(PY) -m pytest -q
clean:      ; rm -rf output/*/oryva.sqlite .pytest_cache
