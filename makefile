.PHONY: image daemon run

image:
	docker build -t kejinyan .

hechi2:
	docker build -t kejinyan/kejinyan:latest .
	docker push kejinyan/kejinyan:latest

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
