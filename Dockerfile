FROM python:3.8-alpine

COPY main.py /app/
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

CMD ["python","-u","/app/main.py"]
