.PHONY: dev test lint build install uninstall clean help

help:
	@echo "make dev        run backend (mock) + frontend dev servers together"
	@echo "make test       backend pytest + frontend Playwright e2e"
	@echo "make lint       frontend type-check + backend syntax check"
	@echo "make build      production frontend build (frontend/dist)"
	@echo "make seed       install a few demo apps into a running dev backend"
	@echo "make install    install onto the real PC (Linux only, session/install.sh)"
	@echo "make uninstall  reverse of install (Linux only, session/uninstall.sh)"
	@echo "make clean      remove node_modules, .venv, dist and caches"

dev:
	./scripts/dev.sh

test:
	./scripts/test.sh

lint:
	./scripts/lint.sh

build:
	cd frontend && npm install && npm run build

seed:
	./scripts/seed-mock-apps.sh

install:
	./session/install.sh

uninstall:
	./session/uninstall.sh

clean:
	rm -rf frontend/node_modules frontend/dist frontend/test-results frontend/playwright-report
	rm -rf backend/.venv backend/.pytest_cache
	find backend -name '__pycache__' -type d -prune -exec rm -rf {} +
