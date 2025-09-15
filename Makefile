# Check staged files for hook compliance

.PHONY: check
check:
	poetry run pre-commit run --all-files

# Server running shortcut to match Django

.PHONY: runserver
runserver:
	poetry run python3 -m biostar.app
