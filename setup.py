from setuptools import setup, find_packages

from _version import __version__


setup(
    name="monero_health",
    version=__version__,
    author="Norman Moeschter-Schenck",
    author_email="norman.moeschter@gmail.com",
    maintainer="Norman Moeschter-Schenck",
    maintainer_email="<norman.moeschter@gmail.com>",
    url="https://github.com/normoes/monero_health",
    download_url=f"https://github.com/normoes/monero_health/archive/{__version__}.tar.gz",
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
    install_requires=["python-monerorpc>=0.5.9"],
    extras_require={"test": ["mock", "pytest"]},
    py_modules=["monero_health"],
)
