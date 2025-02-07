# docker build -t chess-server .
# sudo docker run -p 80:80 -it chess-server
FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

ENV REDIS_URL=127.0.0.1

RUN apt-get update
RUN apt-get install -y python3 gunicorn supervisor git nginx redis-server
RUN apt-get install python3-pip  -y && pip3 install --no-cache-dir --upgrade pip

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

RUN rm /etc/nginx/sites-enabled/default
COPY chess-server.conf /etc/nginx/sites-available/
RUN ln -s /etc/nginx/sites-available/chess-server.conf /etc/nginx/sites-enabled/chess-server.conf
RUN echo "daemon off;" >> /etc/nginx/nginx.conf

RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY gunicorn.conf /etc/supervisor/conf.d/gunicorn.conf

RUN python3 --version

COPY . /app

CMD ["/usr/bin/supervisord"]
