
---
# Sipefield's pylab

[![codecov](https://codecov.io/gh/Gronemeyer/PyLab/branch/main/graph/badge.svg?token=PyLab_token_here)](https://codecov.io/gh/Gronemeyer/PyLab)
[![CI](https://github.com/Gronemeyer/PyLab/actions/workflows/main.yml/badge.svg)](https://github.com/Gronemeyer/PyLab/actions/workflows/main.yml)

Awesome pylab created by Gronemeyer

## Install it from PyPI

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/yourrepository.git
cd yourrepository

## Usage


```bash
$ python -m pylab launch
#or
$ python -m pylab launch --dev True
```

## Adding a configuration file to a mmc.core() object

```py
MM_CONFIG = r'C:/dev/micro-manager_configuration.cfg'

# Initialize the Core
mmc = CMMCorePlus().instance()
mmc.loadSystemConfiguration(MM_CONFIG)
```


Read the [CONTRIBUTING.md](CONTRIBUTING.md) file.
