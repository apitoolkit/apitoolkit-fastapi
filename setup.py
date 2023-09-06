from setuptools import setup, find_packages

setup(
    name="apitoolkit_fastapi",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'fastapi',
        'google-cloud-pubsub',
        'google-auth',
        'starlette',
        'httpx',
    ]
)
