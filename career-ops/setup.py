from setuptools import setup, find_packages

setup(
    name="career-ops",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.0", "jinja2>=3.0", "pyyaml>=6.0",
        "httpx>=0.27", "beautifulsoup4>=4.12", "lxml>=5.0",
    ],
    entry_points={
        "console_scripts": [
            "career=career_ops.cli:main",
        ],
    },
    python_requires=">=3.10",
)
