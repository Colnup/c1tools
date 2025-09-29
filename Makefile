SHELL := /usr/bin/fish


install:
	uv tool install --with-editable "." .
	c1 --install-completion
	c1 --show-completion fish | source