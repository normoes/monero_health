from setuptools import setup, find_packages


VERSION = "v1.1.5"

setup(
    name="monero_health",
    version=VERSION,
    author="Norman Moeschter-Schenck",
    author_email="norman.moeschter@gmail.com",
    maintainer="Norman Moeschter-Schenck",
    maintainer_email="<norman.moeschter@gmail.com>",
    url="https://github.com/monero-ecosystem/monero_health",
    download_url=f"https://github.com/monero-ecosystem/monero_health/archive/{VERSION}.tar.gz",
    description=("Check health of monero daemons."),
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python",
    ],
    packages=find_packages(exclude=["tests*"]),
    install_requires=["python-monerorpc>=0.5.12", "monero-scripts>=0.0.7"],
    extras_require={"test": ["mock", "pytest"]},
)
