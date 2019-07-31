FROM python:3

RUN pip install --upgrade pip setuptools
ADD requirements.txt /requirements.txt
RUN pip install -r requirements.txt
ADD mordecai/ mordecai/
RUN pip install mordecai/
RUN python -m spacy download en_core_web_lg


ADD twitter-to-pubsub.py /twitter-to-pubsub.py
ADD pubsub-to-bigquery.py /pubsub-to-bigquery.py
ADD controller.py /controller.py
ADD utils.py /utils.py
ADD geo_utils.py /geo_utils.py

CMD python controller.py
