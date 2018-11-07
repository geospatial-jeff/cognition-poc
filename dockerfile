FROM quay.io/mojodna/gdal:v2.3.x

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        bc \
        ca-certificates \
        curl \
        git \
        jq \
        nfs-common \
        parallel \
        python-pip \
        python-wheel \
        python-setuptools \
        unzip \
    && apt-get clean

WORKDIR /opt/cognition

COPY requirements.txt /opt/cognition/requirements.txt

RUN pip install cython

RUN pip install -r requirements.txt