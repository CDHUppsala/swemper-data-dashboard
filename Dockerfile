FROM python:3-slim
WORKDIR /app
RUN pip install --no-cache-dir flask markdown

COPY templates ./templates
COPY dataset_webapp.py .
RUN mkdir -p tmp
EXPOSE 9092

ENTRYPOINT ["python", "dataset_webapp.py"]
CMD ["--help"]