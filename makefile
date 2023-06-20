.PHONY: image daemon run

image:
	docker build -t kejinyan .

run:
	docker run \
		--rm \
		-it \
		--name kejinyan \
		--entrypoint bash \
		kejinyan

daemon: image
	docker run \
		-it \
		--name kejinyan \
		--rm \
		-p7777:8000 \
		-d \
		kejinyan
