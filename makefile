.PHONY: image daemon run

image:
	docker build -t kejinyan .

hechi:
	docker build -t kejinyan/kejinyan:hechi .
	docker push kejinyan/kejinyan:hechi

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
