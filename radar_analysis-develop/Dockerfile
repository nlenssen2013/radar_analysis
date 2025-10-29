FROM python:3.11 as base
ENV PYTHONUNBUFFERED 1
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . /app
RUN mkdir /app/static
EXPOSE 5000
CMD [ "python", "app.py" ]