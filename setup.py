from setuptools import setup, find_packages

install_requires = [
      "windows-curses"
]

setup(name='trade_strategy',
      version='0.0.1',
      packages=find_packages(),
      data_files=['./trade_strategy/settings.json'],
      install_requires=install_requires,
      include_package_data=True
)