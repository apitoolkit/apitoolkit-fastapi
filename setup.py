from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="apitoolkit_fastapi",
    version="0.2.0",
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    author_email='hello@apitoolkit.io',
    author='APIToolkit',
    install_requires=[
        'fastapi',
        'google-cloud-pubsub',
        'google-auth',
        'starlette',
        'httpx',
        'jsonpath-ng',
        'apitoolkit-python'
    ]
)
