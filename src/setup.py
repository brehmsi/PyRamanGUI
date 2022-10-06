from setuptools import find_packages, setup

setup(
    name='PyRamanGUI',
    version='0.1.0',
    description='multi-purpose tool to analyze Raman spectra',
    author='Simon Brehm',
    author_email='simon.brehm@physik.tu-freiberg.de',
    url='https://gitlab.com/brehmsi/PyRamanGUI',
    packages=find_packages(),
    license='APACHE2.0',
    install_requires=['matplotlib==3.5.3', 'pyqt5==5.15.7'],
    # include_package_data=True,
    # zip_safe=False,
    python_requires='>=3.6'
)
