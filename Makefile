IMAGE_NAME = researchmind
CONTAINER_NAME = researchmind-app

.PHONY: build run stop logs clean

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run -d --name $(CONTAINER_NAME) -p 8501:8501 --env-file .env $(IMAGE_NAME)

stop:
	docker stop $(CONTAINER_NAME) && docker rm $(CONTAINER_NAME)

logs:
	docker logs -f $(CONTAINER_NAME)

clean:
	docker rmi $(IMAGE_NAME)