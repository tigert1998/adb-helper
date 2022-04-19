import setuptools

VERSION = "0.0.1"

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="adb-helper",
    version=VERSION,
    author="Xiaohu Tang",
    author_email="tigertang.zju@outlook.com",
    description="ADB Helper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tigert1998/adb-helper",
    packages=["adb-helper"],
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    install_requires=[],
    python_requires='>=3.5',
)
