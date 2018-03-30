FROM geographica/gdal2:2.2.4

RUN apt-get update \
  && apt-get install -y python-dev python-pip \
  && pip install rasterio==1.0a12 boto3==1.6.20

RUN mkdir -p /opt/src/

COPY src/ /opt/src/

WORKDIR /opt

ENTRYPOINT ["python"]

CMD ["src/transform_tif.py"]
