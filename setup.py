from setuptools import setup, find_packages

setup(
    name='cmpexpdata', 
    version='0.1.0',  
    packages=find_packages(),  
    install_requires=[
        'pydot',
        'typing_extensions',
        'mpmath==1.2.1',
        'sympy==1.10.1',
        'antlr4-python3-runtime==4.7.2'
    ],
    dependency_links=[
        'git+https://github.com/lambda-feedback/compareExpressions.git@tr141-temporary-data-analysis-modifications#egg=cmpexpdata'
    ],
    long_description=open('README.md').read(),  # Long description from a README file
    long_description_content_type='text/markdown',  # Content type of the long description
    url='https://github.com/lambda-feedback/compareExpressions',  # URL of the project's homepage
    python_requires='>=3.6',  # Specify the Python versions you support
)
