FROM ubuntu:14.04
RUN echo "deb http://archive.ubuntu.com/ubuntu precise main universe" > /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y openssh-server python-pip
RUN apt-get install -y python-pycryptopp
RUN pip install fabric