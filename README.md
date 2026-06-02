# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/EffectiveRange/debian-package-repository/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                     |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| package\_repository/\_\_init\_\_.py      |        8 |        0 |        0 |        0 |    100% |           |
| package\_repository/directoryServer.py   |       55 |        3 |        4 |        2 |     92% |65, 75-\>exit, 90-91 |
| package\_repository/directoryService.py  |       95 |        0 |       20 |        2 |     98% |114-\>117, 141-\>143 |
| package\_repository/packageWatcher.py    |       50 |        0 |        4 |        0 |    100% |           |
| package\_repository/repositoryCache.py   |       34 |        0 |        8 |        0 |    100% |           |
| package\_repository/repositoryCreator.py |      120 |        3 |       24 |        2 |     95% |93-96, 118-\>126 |
| package\_repository/repositoryServer.py  |       85 |       44 |        2 |        0 |     47% |66-119, 123, 127-130, 134-137 |
| package\_repository/repositoryService.py |       54 |        0 |        8 |        0 |    100% |           |
| package\_repository/repositorySigner.py  |      100 |        0 |       14 |        0 |    100% |           |
| **TOTAL**                                |  **601** |   **50** |   **84** |    **6** | **91%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/EffectiveRange/debian-package-repository/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/debian-package-repository/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/EffectiveRange/debian-package-repository/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/debian-package-repository/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FEffectiveRange%2Fdebian-package-repository%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/debian-package-repository/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.