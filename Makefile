# Makefile for Job Hunter project
# To start development, run:
#   make setup
# Then:
#   make fullrun

.PHONY: help setup run fullrun countcode size

setup:
	@echo "Installing build and test dependencies..."
	@python3 -m pip install --upgrade pip 
	@python3 -m pip install pytest feedparser numpy scikit-learn rapidfuzz

help:
	@echo "Available commands:"
	@echo "  make setup"
	@echo "  make run"
	@echo "  make fullrun"
	@echo "  make countcode"
	@echo "  make size"

run:
	@python3 checker.py

fullrun:
	@$(MAKE) setup
	@$(MAKE) run

# Count lines of code in all Python files
countcode:
	@echo "Counting lines of code..."
	@find . -name "*.py" -type f -print0 | xargs -0 cat | wc -l

# Calculate total project size
size:
	@echo "Calculating project size..."
	@du -sh .

s_build:
	@python3 synonym_finder_v2/build.py

s_demo:
	@python3 synonym_finder_v2/demo.py  
# Catch unknown commands
%:
	@echo "Unknown command: $@"
	@$(MAKE) help