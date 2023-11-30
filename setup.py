import distutils.spawn
import os
import re
import shlex
import subprocess
import sys

from setuptools import find_packages
from setuptools import setup


def get_version():
    filename = "boardcardautotest/__init__.py"
    with open(filename) as f:
        match = re.search(
            r"""^__version__ = ['"]([^'"]*)['"]""", f.read(), re.M
        )
    if not match:
        raise RuntimeError("{} doesn't contain __version__".format(filename))
    version = match.groups()[0]
    return version


def get_install_requires():
    install_requires = [
        "imgviz>=0.11",
        "matplotlib<3.3",  # for PyInstaller
        "opencv_python<4.3.0",
        "numpy",
        "Pillow>=2.8",
        "PyYAML",
        "qtpy",
        "termcolor",
        "requests",
        "scipy",
    ]

    if os.name == "nt":  # Windows
        install_requires.append("colorama")

    return install_requires


def get_long_description():
    with open("README.md") as f:
        long_description = f.read()
    try:
        import github2pypi

        return github2pypi.replace_url(
            slug="kelamini/BoardCardAutoTest", content=long_description
        )
    except Exception:
        return long_description


def main():
    version = get_version()

    # if sys.argv[1] == "release":
    #     if not distutils.spawn.find_executable("twine"):
    #         print(
    #             "Please install twine:\n\n\tpip install twine\n",
    #             file=sys.stderr,
    #         )
    #         sys.exit(1)

    #     commands = [
    #         "python tests/docs_tests/man_tests/test_labelme_1.py",
    #         "git push origin main",
    #         "git tag v{:s}".format(version),
    #         "git push origin --tags",
    #         "python setup.py sdist",
    #         "twine upload dist/labelme-{:s}.tar.gz".format(version),
    #     ]
    #     for cmd in commands:
    #         print("+ {:s}".format(cmd))
    #         subprocess.check_call(shlex.split(cmd))
    #     sys.exit(0)

    setup(
        name="BoardCarAutoTest",
        version=version,
        packages=find_packages(exclude=["github2pypi"]),
        description="Board Car Auto Test.",
        long_description=get_long_description(),
        long_description_content_type="text/markdown",
        author="kelamini",
        author_email="kelamini_0216@163.com",
        url="https://github.com/kelamini/BoardCardAutoTest",
        install_requires=get_install_requires(),
        license="Apache License Version 2.0",
        keywords="Image Annotation, Machine Learning",
        classifiers=[
            "Development Status :: 3 - Production/Stable",
            "Intended Audience :: Developers",
            "Natural Language :: English",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
        ],
        package_data={"boardcardautotest": ["icons/*"]},
        entry_points={
            "console_scripts": [
                "boardcardautotest=boardcardautotest.main:main",
            ],
        },
    )


if __name__ == "__main__":
    main()
