.PHONY: bootstrap dev test install-service status stop clean-kill

bootstrap:
	./scripts/bootstrap.sh

dev:
	./scripts/run_server.sh

test:
	@if [ ! -d .venv ]; then ./scripts/bootstrap.sh; fi
	. .venv/bin/activate && pytest -q

install-service:
	./scripts/install_launchd.sh

status:
	launchctl print gui/$$(id -u)/com.macaccess.api

stop:
	launchctl bootout gui/$$(id -u)/com.macaccess.api

clean-kill:
	rm -f ~/.mac_access_api.kill
