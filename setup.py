from setuptools import setup, find_packages

setup(
    name='finisterra',
    version='1.0.32',
    packages=find_packages(),
    package_data={
        'finisterra': ['providers/**/*.yaml'],
    },    
    install_requires=[
        'wheel==0.43.0',
        'boto3==1.26.94',
        'PyJWT==2.7.0',
        'pycryptodome==3.18.0',
        'cryptography==41.0.1',
        'PyYAML==6.0',
        'click==8.1.7',
        'rich==13.7.0',
        'deepdiff==5.5.0',
        'cloudflare==2.19.2',
        'pdpyras==5.2.0',
        'kafka-python==2.0.2',
    ],
    entry_points={
        'console_scripts': [
            'finisterra=finisterra.main:main',
        ],
    },
    author='Finisterra',
    author_email='daniel@finisterra.io',
    description='Terraform in minutes not months.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/finisterra-io/finisterra',
)
