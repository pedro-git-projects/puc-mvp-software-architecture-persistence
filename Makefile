PYTHON_FILES := $(shell find app -name "*.py")

format:
	black $(PYTHON_FILES)

.PHONY: format

