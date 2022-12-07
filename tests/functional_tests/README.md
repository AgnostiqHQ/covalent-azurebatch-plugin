## Functional Test Instructions

### 1.Setup

In the project root run the following:

```sh
pip install -r ./tests/requirements.txt
pip install -r ./tests/functional_tests/requirements.txt
export PYTHONPATH=$(pwd)
```

Fill in the correct configuration values for the Azure Batch Executor resources.

### 2. Run Functional Tests

```sh
pytest -vvs -m functional_tests
```
