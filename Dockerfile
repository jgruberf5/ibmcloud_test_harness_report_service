FROM ubuntu:18.04
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y python3-pip \
    python3-setuptools \
    python3-wheel \
    git

## INJECT_PATCH_INSTRUCTION ##
RUN git clone https://github.com/jgruberf5/ibmcloud_test_harness_report_service.git

RUN pip3 install Flask requests

ENTRYPOINT [ "/ibmcloud_test_harness_report_service/server.py" ]